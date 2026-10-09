import string

from django.contrib.auth.models import User
from django.test import TestCase

from .usuarios import generar_codigo_invitacion, generar_password_temporal, generar_username


class GenerarUsernameTests(TestCase):
    def test_caso_basico_es_inicial_mas_apellido(self):
        self.assertEqual(generar_username("Juan", "Pérez"), "jperez")

    def test_colision_usa_inicial_del_segundo_apellido(self):
        User.objects.create_user(username="jperez")
        self.assertEqual(generar_username("Juan", "Pérez", "Soto"), "jperezs")

    def test_colision_sin_segundo_apellido_cae_a_numero(self):
        User.objects.create_user(username="jperez")
        self.assertEqual(generar_username("Juan", "Pérez"), "jperez2")

    def test_doble_colision_incluido_el_segundo_apellido_cae_a_numero(self):
        User.objects.create_user(username="jperez")
        User.objects.create_user(username="jperezs")
        self.assertEqual(generar_username("Juan", "Pérez", "Soto"), "jperez2")

    def test_numero_sigue_subiendo_si_tambien_choca(self):
        User.objects.create_user(username="jperez")
        User.objects.create_user(username="jperez2")
        self.assertEqual(generar_username("Juan", "Pérez"), "jperez3")


class GenerarPasswordYCodigoTests(TestCase):
    def test_password_temporal_longitud_por_defecto(self):
        self.assertEqual(len(generar_password_temporal()), 10)

    def test_password_temporal_longitud_custom(self):
        self.assertEqual(len(generar_password_temporal(16)), 16)

    def test_codigo_invitacion_longitud_y_alfabeto(self):
        codigo = generar_codigo_invitacion()
        self.assertEqual(len(codigo), 8)
        self.assertTrue(all(c in string.ascii_uppercase + string.digits for c in codigo))
