from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Condominio, Membresia

from .models import GastoComun


def crear_membresia(condominio, rol, **user_kwargs):
    username = user_kwargs.pop("username", f"t_{rol}_{Membresia.objects.count()}")
    user = User.objects.create_user(username=username, **user_kwargs)
    return Membresia.objects.create(user=user, condominio=condominio, rol=rol, terminos_aceptados_en=timezone.now())


class GenerarGastoComunPermisosTests(TestCase):
    """Generar un gasto común (fijar el monto del periodo) quedó exclusivo
    de administración -- ni siquiera directiva puede, a pedido explícito del
    usuario (distinto del resto de gastos comunes, que sigue abierto a
    ambas: ver EsDirectivaOAdministracionMixin en GastoComunListView)."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Gasto Permisos", plan="premium")

    def setUp(self):
        self.administracion = crear_membresia(self.condominio, "administracion", username="gasto_admon")
        self.directiva = crear_membresia(self.condominio, "directiva", username="gasto_directiva")

    def test_administracion_puede_generar_gasto_comun(self):
        self.client.force_login(self.administracion.user)
        r = self.client.post(reverse("gastos-comunes-crear"), {
            "periodo": "2026-11", "modo": "total", "monto_total": "240000",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(GastoComun.objects.filter(condominio=self.condominio, periodo="2026-11").exists())

    def test_directiva_no_puede_generar_gasto_comun(self):
        self.client.force_login(self.directiva.user)
        r = self.client.get(reverse("gastos-comunes-crear"))
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse("gastos-comunes-crear"), {
            "periodo": "2026-11", "modo": "total", "monto_total": "240000",
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(GastoComun.objects.filter(condominio=self.condominio, periodo="2026-11").exists())

    def test_directiva_sigue_viendo_la_lista_sin_boton_de_crear(self):
        self.client.force_login(self.directiva.user)
        r = self.client.get(reverse("gastos-comunes-list"))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(reverse("gastos-comunes-crear").encode(), r.content)


class DatosTransferenciaPermisosTests(TestCase):
    """Los datos de transferencia (banco/cuenta/RUT para pagar gastos
    comunes) quedaron exclusivos de administración -- antes vivían en "Mi
    condominio" (exclusivo directiva), ahora ni directiva puede editarlos."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Transferencia Permisos", plan="premium")

    def setUp(self):
        self.administracion = crear_membresia(self.condominio, "administracion", username="transf_admon")
        self.directiva = crear_membresia(self.condominio, "directiva", username="transf_directiva")

    def test_administracion_puede_editar_datos_transferencia(self):
        self.client.force_login(self.administracion.user)
        r = self.client.post(reverse("datos-transferencia"), {"datos_transferencia": "Banco Estado, cta 123, RUT 11.111.111-1"})
        self.assertEqual(r.status_code, 302)
        self.condominio.refresh_from_db()
        self.assertIn("Banco Estado", self.condominio.datos_transferencia)

    def test_directiva_no_puede_editar_datos_transferencia(self):
        self.client.force_login(self.directiva.user)
        r = self.client.get(reverse("datos-transferencia"))
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse("datos-transferencia"), {"datos_transferencia": "Intento de directiva"})
        self.assertEqual(r.status_code, 302)
        self.condominio.refresh_from_db()
        self.assertNotIn("Intento de directiva", self.condominio.datos_transferencia or "")

    def test_mi_condominio_ya_no_tiene_el_form_de_transferencia(self):
        self.client.force_login(self.directiva.user)
        r = self.client.get(reverse("mi-condominio"))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"datos_transferencia", r.content)
