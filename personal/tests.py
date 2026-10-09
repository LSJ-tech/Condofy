from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Condominio, Membresia

from .calculo import calcular_liquidacion
from .models import Afp, Empleado, Liquidacion, ParametrosPeriodo, TramoImpuestoUnico


def crear_membresia(condominio, rol, unidad=None, **user_kwargs):
    username = user_kwargs.pop("username", f"t_{rol}_{Membresia.objects.count()}")
    user = User.objects.create_user(username=username, **user_kwargs)
    return Membresia.objects.create(user=user, condominio=condominio, rol=rol, unidad=unidad, terminos_aceptados_en=timezone.now())


def _parametros(**overrides):
    datos = dict(
        periodo="2026-10", valor_utm=Decimal("65000"), valor_uf=Decimal("38000"),
        ingreso_minimo_mensual=500000, tope_imponible_uf=Decimal("87.8"),
        tasa_cesantia_trabajador_indefinido_pct=Decimal("0.6"), tasa_cesantia_trabajador_plazo_fijo_pct=Decimal("0"),
    )
    datos.update(overrides)
    return ParametrosPeriodo(**datos)


def _tramos():
    return [
        TramoImpuestoUnico(desde_utm=Decimal("0"), hasta_utm=Decimal("13.5"), tasa_pct=Decimal("0"), rebaja_utm=Decimal("0")),
        TramoImpuestoUnico(desde_utm=Decimal("13.5"), hasta_utm=Decimal("30"), tasa_pct=Decimal("4"), rebaja_utm=Decimal("0.54")),
    ]


class CalculoLiquidacionTests(TestCase):
    """Casos calculados a mano (ver conversación) -- validan que el código hace
    exactamente lo que dice la fórmula, no una certificación legal: las tasas y
    tramos usados acá son ilustrativos, no verificados contra el SII."""

    def test_sin_gratificacion_fonasa_indefinido(self):
        empleado = Empleado(
            sueldo_base=500000, asignacion_colacion=50000, asignacion_movilizacion=30000,
            tipo_contrato="indefinido", sistema_salud="fonasa", aplica_gratificacion=False,
            afp=Afp(nombre="Test AFP", tasa_total_pct=Decimal("11.44")),
        )
        resultado = calcular_liquidacion(empleado, _parametros(), _tramos())

        self.assertEqual(resultado["gratificacion"], 0)
        self.assertEqual(resultado["total_haberes"], 580000)
        self.assertEqual(resultado["descuento_afp"], 57200)
        self.assertEqual(resultado["descuento_salud"], 35000)
        self.assertEqual(resultado["descuento_cesantia"], 3000)
        self.assertEqual(resultado["impuesto_unico"], 0)
        self.assertEqual(resultado["total_descuentos"], 95200)
        self.assertEqual(resultado["liquido_a_pagar"], 484800)

    def test_con_gratificacion_isapre_plazo_fijo(self):
        empleado = Empleado(
            sueldo_base=600000, asignacion_colacion=0, asignacion_movilizacion=0,
            tipo_contrato="plazo_fijo", sistema_salud="isapre", plan_isapre_uf=Decimal("8.5"),
            aplica_gratificacion=True,
            afp=Afp(nombre="Test AFP 2", tasa_total_pct=Decimal("10.49")),
        )
        resultado = calcular_liquidacion(empleado, _parametros(), _tramos())

        self.assertEqual(resultado["gratificacion"], 150000)
        self.assertEqual(resultado["total_haberes"], 750000)
        self.assertEqual(resultado["descuento_afp"], 78675)
        self.assertEqual(resultado["descuento_salud"], 323000)
        self.assertEqual(resultado["descuento_cesantia"], 0)
        self.assertEqual(resultado["total_descuentos"], 401675)
        self.assertEqual(resultado["liquido_a_pagar"], 348325)

    def test_tramo_con_impuesto_unico(self):
        empleado = Empleado(
            sueldo_base=1800000, asignacion_colacion=0, asignacion_movilizacion=0,
            tipo_contrato="indefinido", sistema_salud="fonasa", aplica_gratificacion=False,
            afp=Afp(nombre="Test AFP", tasa_total_pct=Decimal("11.44")),
        )
        resultado = calcular_liquidacion(empleado, _parametros(), _tramos())

        self.assertEqual(resultado["descuento_afp"], 205920)
        self.assertEqual(resultado["descuento_salud"], 126000)
        self.assertEqual(resultado["descuento_cesantia"], 10800)
        self.assertEqual(resultado["impuesto_unico"], 23191)
        self.assertEqual(resultado["total_descuentos"], 365911)
        self.assertEqual(resultado["liquido_a_pagar"], 1434089)

    def test_tope_imponible_limita_la_base_de_descuentos(self):
        parametros = _parametros(tope_imponible_uf=Decimal("10"))  # tope bajo a propósito, en pesos: 10*38000=380000
        empleado = Empleado(
            sueldo_base=1000000, asignacion_colacion=0, asignacion_movilizacion=0,
            tipo_contrato="indefinido", sistema_salud="fonasa", aplica_gratificacion=False,
            afp=Afp(nombre="Test AFP", tasa_total_pct=Decimal("10")),
        )
        resultado = calcular_liquidacion(empleado, parametros, _tramos())
        # el descuento de AFP/salud/cesantía se calcula sobre el tope (380000), no sobre el sueldo completo
        self.assertEqual(resultado["descuento_afp"], 38000)
        self.assertEqual(resultado["descuento_salud"], 26600)


class EmpleadoPermisosTests(TestCase):
    """Mismo criterio que GastoComun: administración crea/edita (datos de
    sueldo), directiva supervisa (ve pero no crea)."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Personal", plan="premium")
        cls.afp = Afp.objects.create(nombre="Test AFP", tasa_total_pct=Decimal("11.44"))

    def setUp(self):
        self.administracion = crear_membresia(self.condominio, "administracion", username="personal_admon")
        self.directiva = crear_membresia(self.condominio, "directiva", username="personal_directiva")
        self.residente = crear_membresia(self.condominio, "residente", username="personal_residente")

    def _datos_empleado(self):
        return {
            "nombre": "Juan Pérez", "rut": "11.111.111-1", "cargo": "Conserje",
            "tipo_contrato": "indefinido", "fecha_ingreso": "2026-01-01",
            "afp": self.afp.pk, "sistema_salud": "fonasa", "sueldo_base": "500000",
            "asignacion_colacion": "0", "asignacion_movilizacion": "0",
        }

    def test_administracion_puede_crear_empleado(self):
        self.client.force_login(self.administracion.user)
        r = self.client.post(reverse("empleado-crear"), self._datos_empleado())
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Empleado.objects.filter(condominio=self.condominio, nombre="Juan Pérez").exists())

    def test_directiva_no_puede_crear_empleado(self):
        self.client.force_login(self.directiva.user)
        r = self.client.post(reverse("empleado-crear"), self._datos_empleado())
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Empleado.objects.filter(condominio=self.condominio).exists())

    def test_directiva_puede_ver_la_lista(self):
        self.client.force_login(self.directiva.user)
        r = self.client.get(reverse("empleados"))
        self.assertEqual(r.status_code, 200)

    def test_residente_no_puede_ver_la_lista(self):
        self.client.force_login(self.residente.user)
        r = self.client.get(reverse("empleados"))
        self.assertEqual(r.status_code, 302)


class LiquidacionGenerarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Liquidaciones", plan="premium")
        cls.afp = Afp.objects.create(nombre="Test AFP", tasa_total_pct=Decimal("11.44"))
        cls.empleado = Empleado.objects.create(
            condominio=cls.condominio, nombre="Juan Pérez", rut="11.111.111-1", cargo="Conserje",
            tipo_contrato="indefinido", fecha_ingreso="2026-01-01", afp=cls.afp,
            sistema_salud="fonasa", sueldo_base=500000, email="juan@example.com",
        )
        TramoImpuestoUnico.objects.bulk_create(_tramos())

    def setUp(self):
        self.administracion = crear_membresia(self.condominio, "administracion", username="liq_admon")

    def test_falla_con_mensaje_claro_si_faltan_parametros_del_periodo(self):
        self.client.force_login(self.administracion.user)
        r = self.client.post(reverse("liquidacion-generar", args=[self.empleado.pk]), {"periodo": "2099-01"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Liquidacion.objects.count(), 0)

    def test_genera_liquidacion_y_manda_correo_si_se_indica(self):
        from django.core import mail

        ParametrosPeriodo.objects.create(
            periodo="2026-10", valor_utm=Decimal("65000"), valor_uf=Decimal("38000"),
            ingreso_minimo_mensual=500000, tope_imponible_uf=Decimal("87.8"),
        )
        self.client.force_login(self.administracion.user)
        r = self.client.post(
            reverse("liquidacion-generar", args=[self.empleado.pk]),
            {"periodo": "2026-10", "correo_destino": "juan@example.com"},
        )
        self.assertEqual(r.status_code, 302)
        liquidacion = Liquidacion.objects.get(empleado=self.empleado, periodo="2026-10")
        # mismo sueldo_base que el caso 1 de CalculoLiquidacionTests, pero sin
        # asignación de colación/movilización (no se setearon en este empleado)
        self.assertEqual(liquidacion.liquido_a_pagar, 404800)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["juan@example.com"])
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertTrue(mail.outbox[0].attachments[0][1].startswith(b"%PDF"))

    def test_no_permite_duplicar_liquidacion_del_mismo_periodo(self):
        ParametrosPeriodo.objects.create(
            periodo="2026-10", valor_utm=Decimal("65000"), valor_uf=Decimal("38000"),
            ingreso_minimo_mensual=500000, tope_imponible_uf=Decimal("87.8"),
        )
        self.client.force_login(self.administracion.user)
        self.client.post(reverse("liquidacion-generar", args=[self.empleado.pk]), {"periodo": "2026-10"})
        self.client.post(reverse("liquidacion-generar", args=[self.empleado.pk]), {"periodo": "2026-10"})
        self.assertEqual(Liquidacion.objects.filter(empleado=self.empleado, periodo="2026-10").count(), 1)

    def test_pdf_descargable_despues_de_generar(self):
        ParametrosPeriodo.objects.create(
            periodo="2026-10", valor_utm=Decimal("65000"), valor_uf=Decimal("38000"),
            ingreso_minimo_mensual=500000, tope_imponible_uf=Decimal("87.8"),
        )
        self.client.force_login(self.administracion.user)
        self.client.post(reverse("liquidacion-generar", args=[self.empleado.pk]), {"periodo": "2026-10"})
        liquidacion = Liquidacion.objects.get(empleado=self.empleado, periodo="2026-10")

        r = self.client.get(reverse("liquidacion-pdf", args=[liquidacion.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
