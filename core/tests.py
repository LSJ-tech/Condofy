from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import CrearMiembroForm, RegistroCondominioForm, RegistroResidenteForm
from .models import CodigoInvitacion, Condominio, Membresia, Torre, Unidad


def crear_membresia(condominio, rol, unidad=None, terminos=True, **user_kwargs):
    username = user_kwargs.pop("username", f"t_{rol}_{Membresia.objects.count()}")
    user = User.objects.create_user(username=username, password="x12345678", **user_kwargs)
    return Membresia.objects.create(
        user=user, condominio=condominio, rol=rol, unidad=unidad,
        terminos_aceptados_en=timezone.now() if terminos else None,
    )


class RolesPermisosTests(TestCase):
    """Cada rol debe poder llegar solo a lo que le corresponde -- ver los
    mixins en core/mixins.py. Esto cubre el día a día (miembros/torres/
    unidades), lo exclusivo de directiva (Mi condominio) y lo exclusivo del
    admin de la plataforma (crear torre)."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Roles", plan="premium")
        cls.torre = Torre.objects.create(condominio=cls.condominio, nombre="1")
        cls.unidad = Unidad.objects.create(condominio=cls.condominio, torre=cls.torre, numero="101")

    def setUp(self):
        self.directiva = crear_membresia(self.condominio, "directiva", username="roles_directiva")
        self.administracion = crear_membresia(self.condominio, "administracion", username="roles_admon")
        self.conserje = crear_membresia(self.condominio, "conserje", username="roles_conserje")
        self.residente = crear_membresia(self.condominio, "residente", unidad=self.unidad, username="roles_residente")

    def _login(self, membresia):
        self.client.login(username=membresia.user.username, password="x12345678")

    def test_dia_a_dia_directiva_y_administracion_permitido(self):
        for membresia in (self.directiva, self.administracion):
            self._login(membresia)
            for url_name in ("miembros", "torres", "unidades", "gastos-comunes-list"):
                r = self.client.get(reverse(url_name))
                self.assertEqual(r.status_code, 200, f"{membresia.rol} debería poder ver {url_name}")
            self.client.logout()

    def test_dia_a_dia_bloqueado_para_conserje_y_residente(self):
        for membresia in (self.conserje, self.residente):
            self._login(membresia)
            for url_name in ("miembros", "torres", "unidades", "gastos-comunes-list"):
                r = self.client.get(reverse(url_name))
                self.assertEqual(r.status_code, 302, f"{membresia.rol} NO debería poder ver {url_name}")
            self.client.logout()

    def test_accesos_permitido_para_directiva_administracion_conserje(self):
        for membresia in (self.directiva, self.administracion, self.conserje):
            self._login(membresia)
            r = self.client.get(reverse("registro-ingreso-list"))
            self.assertEqual(r.status_code, 200)
            self.client.logout()

    def test_accesos_bloqueado_para_residente(self):
        self._login(self.residente)
        r = self.client.get(reverse("registro-ingreso-list"))
        self.assertEqual(r.status_code, 302)

    def test_mi_condominio_exclusivo_directiva(self):
        self._login(self.directiva)
        self.assertEqual(self.client.get(reverse("mi-condominio")).status_code, 200)
        self.client.logout()
        self._login(self.administracion)
        self.assertEqual(self.client.get(reverse("mi-condominio")).status_code, 302)

    def test_crear_torre_exclusivo_del_admin_de_la_plataforma(self):
        """Ni siquiera la directiva puede crear torres -- eso es de DevQuad (/admin)."""
        for membresia in (self.directiva, self.administracion):
            self._login(membresia)
            r = self.client.post(reverse("crear-torre"), {"nombre": "Nueva"})
            self.assertEqual(r.status_code, 302)
            self.client.logout()
        self.assertEqual(Torre.objects.filter(condominio=self.condominio, nombre="Nueva").count(), 0)

    def test_crear_miembro_form_rol_aware(self):
        """Administración no puede nombrar directiva/administración, directiva sí."""
        form_admon = CrearMiembroForm(condominio=self.condominio, creador_rol="administracion")
        self.assertEqual([c[0] for c in form_admon.fields["rol"].choices], ["conserje", "residente"])

        form_directiva = CrearMiembroForm(condominio=self.condominio, creador_rol="directiva")
        choices_directiva = [c[0] for c in form_directiva.fields["rol"].choices]
        self.assertIn("directiva", choices_directiva)
        self.assertIn("administracion", choices_directiva)

    def test_crear_miembro_residente_exige_unidad(self):
        form = CrearMiembroForm(
            data={"nombre": "Ana", "apellido": "Soto", "rol": "residente"},
            condominio=self.condominio, creador_rol="directiva",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Selecciona la unidad", str(form.errors))


class MembresiaValidacionTests(TestCase):
    """Membresia.clean() -- unidad obligatoria para residente, y debe ser del
    mismo condominio que la membresía (regla agregada tras el commit 1f88c69)."""

    @classmethod
    def setUpTestData(cls):
        cls.cond1 = Condominio.objects.create(nombre="Cond 1", plan="premium")
        cls.cond2 = Condominio.objects.create(nombre="Cond 2", plan="premium")
        cls.unidad_cond1 = Unidad.objects.create(condominio=cls.cond1, numero="1")
        cls.unidad_cond2 = Unidad.objects.create(condominio=cls.cond2, numero="99")

    def test_residente_sin_unidad_es_invalido(self):
        user = User.objects.create(username="sin_unidad")
        m = Membresia(user=user, condominio=self.cond1, rol="residente", unidad=None)
        with self.assertRaises(ValidationError):
            m.full_clean()

    def test_residente_con_unidad_de_otro_condominio_es_invalido(self):
        user = User.objects.create(username="unidad_cruzada")
        m = Membresia(user=user, condominio=self.cond1, rol="residente", unidad=self.unidad_cond2)
        with self.assertRaises(ValidationError):
            m.full_clean()

    def test_conserje_sin_unidad_es_valido(self):
        user = User.objects.create(username="conserje_sin_unidad")
        m = Membresia(user=user, condominio=self.cond1, rol="conserje", unidad=None)
        m.full_clean()  # no debe lanzar

    def test_residente_con_unidad_correcta_es_valido(self):
        user = User.objects.create(username="residente_ok")
        m = Membresia(user=user, condominio=self.cond1, rol="residente", unidad=self.unidad_cond1)
        m.full_clean()  # no debe lanzar


class TerminosAceptacionTests(TestCase):
    """El gate de Términos de Uso / Política de Privacidad: nadie debería
    poder usar una página protegida sin haber aceptado, pero tampoco debería
    quedar atrapado sin poder cerrar sesión (commit b58ea4e)."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Terminos", plan="premium")

    def setUp(self):
        self.membresia = crear_membresia(self.condominio, "directiva", terminos=False, username="pendiente_terminos")
        self.client.login(username="pendiente_terminos", password="x12345678")

    def test_inicio_redirige_a_aceptar_terminos(self):
        r = self.client.get(reverse("inicio"))
        self.assertRedirects(r, reverse("aceptar-terminos"))

    def test_cualquier_pagina_protegida_redirige_a_aceptar_terminos(self):
        r = self.client.get(reverse("mi-perfil"))
        self.assertRedirects(r, reverse("aceptar-terminos"))

    def test_pantalla_aceptar_terminos_no_hace_loop(self):
        r = self.client.get(reverse("aceptar-terminos"))
        self.assertEqual(r.status_code, 200)

    def test_logout_funciona_con_terminos_pendientes(self):
        r = self.client.post(reverse("logout"))
        self.assertEqual(r.status_code, 302)

    def test_aceptar_terminos_desbloquea_el_resto(self):
        self.client.post(reverse("aceptar-terminos"), {"acepto": "on"})
        self.membresia.refresh_from_db()
        self.assertIsNotNone(self.membresia.terminos_aceptados_en)
        r = self.client.get(reverse("inicio"))
        self.assertEqual(r.status_code, 200)

    def test_aceptar_terminos_sin_marcar_checkbox_no_avanza(self):
        r = self.client.post(reverse("aceptar-terminos"), {})
        self.membresia.refresh_from_db()
        self.assertIsNone(self.membresia.terminos_aceptados_en)
        self.assertRedirects(r, reverse("aceptar-terminos"))


class ConsentimientoRegistroTests(TestCase):
    """Los dos registros públicos exigen el checkbox de Términos/Privacidad
    (commit b58ea4e)."""

    def test_registro_condominio_exige_checkbox(self):
        codigo = CodigoInvitacion.objects.create()
        datos = {
            "codigo_invitacion": codigo.codigo, "nombre_condominio": "Nuevo Condo",
            "nombre": "Logan", "apellido": "Test",
            "password1": "unaClaveSegura123", "password2": "unaClaveSegura123",
        }
        form_sin_checkbox = RegistroCondominioForm(data=datos)
        self.assertFalse(form_sin_checkbox.is_valid())

        datos["acepto_terminos"] = True
        form_con_checkbox = RegistroCondominioForm(data=datos)
        self.assertTrue(form_con_checkbox.is_valid(), form_con_checkbox.errors)

    def test_registro_residente_exige_checkbox(self):
        condominio = Condominio.objects.create(nombre="Test Registro Residente", plan="premium")
        unidad = Unidad.objects.create(condominio=condominio, numero="1")
        datos = {
            "nombre": "Rosa", "apellido": "Mena", "unidad": unidad.pk,
            "password1": "unaClaveSegura123", "password2": "unaClaveSegura123",
        }
        form_sin_checkbox = RegistroResidenteForm(data=datos, condominio=condominio)
        self.assertFalse(form_sin_checkbox.is_valid())

        datos["acepto_terminos"] = True
        form_con_checkbox = RegistroResidenteForm(data=datos, condominio=condominio)
        self.assertTrue(form_con_checkbox.is_valid(), form_con_checkbox.errors)
