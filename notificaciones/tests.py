from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pywebpush import WebPushException

from core.models import Condominio, Membresia

from .models import DispositivoPush, SuscripcionWebPush
from .services import enviar_web_push_a_condominio


def crear_membresia(condominio, rol, **user_kwargs):
    username = user_kwargs.pop("username", f"t_{rol}_{Membresia.objects.count()}")
    user = User.objects.create_user(username=username, **user_kwargs)
    return Membresia.objects.create(user=user, condominio=condominio, rol=rol, terminos_aceptados_en=timezone.now())


class SuscripcionWebPushCreateViewTests(TestCase):
    """Registrar la suscripción de Web Push del navegador actual (commit de
    hoy) -- update_or_create por endpoint, mismo criterio que DispositivoPush."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Web Push", plan="premium")

    def setUp(self):
        self.membresia = crear_membresia(self.condominio, "residente", username="webpush_user")
        self.client.force_login(self.membresia.user)

    def test_registra_una_suscripcion_nueva(self):
        r = self.client.post(reverse("api-web-push"), {
            "endpoint": "https://fcm.googleapis.com/fcm/send/abc123",
            "p256dh": "clave-p256dh", "auth": "clave-auth",
        }, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        sub = SuscripcionWebPush.objects.get(endpoint="https://fcm.googleapis.com/fcm/send/abc123")
        self.assertEqual(sub.user, self.membresia.user)

    def test_reenviar_el_mismo_endpoint_actualiza_en_vez_de_duplicar(self):
        datos = {"endpoint": "https://fcm.googleapis.com/fcm/send/xyz", "p256dh": "p1", "auth": "a1"}
        self.client.post(reverse("api-web-push"), datos, content_type="application/json")
        datos["p256dh"] = "p2"
        self.client.post(reverse("api-web-push"), datos, content_type="application/json")
        self.assertEqual(SuscripcionWebPush.objects.filter(endpoint=datos["endpoint"]).count(), 1)
        self.assertEqual(SuscripcionWebPush.objects.get(endpoint=datos["endpoint"]).p256dh, "p2")

    def test_sin_login_no_puede_registrar(self):
        self.client.logout()
        r = self.client.post(reverse("api-web-push"), {
            "endpoint": "https://fcm.googleapis.com/fcm/send/anon", "p256dh": "p", "auth": "a",
        }, content_type="application/json")
        self.assertEqual(r.status_code, 401)


class DispositivoPushCreateViewTests(TestCase):
    """Regresión: reenviar el mismo token de Expo (ej. el dueño vuelve a
    abrir la app) caía en un 400 por el UniqueValidator automático de DRF,
    en vez de actualizar como dice el docstring de la vista."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Expo", plan="premium")

    def setUp(self):
        self.membresia = crear_membresia(self.condominio, "residente", username="expo_user")
        self.client.force_login(self.membresia.user)

    def test_reenviar_el_mismo_token_actualiza_en_vez_de_fallar(self):
        datos = {"token": "ExponentPushToken[abc]", "plataforma": "android"}
        r1 = self.client.post(reverse("api-dispositivos"), datos, content_type="application/json")
        self.assertEqual(r1.status_code, 201)

        datos["plataforma"] = "ios"
        r2 = self.client.post(reverse("api-dispositivos"), datos, content_type="application/json")
        self.assertEqual(r2.status_code, 201)

        dispositivo = DispositivoPush.objects.get(token="ExponentPushToken[abc]")
        self.assertEqual(dispositivo.plataforma, "ios")
        self.assertEqual(DispositivoPush.objects.filter(token="ExponentPushToken[abc]").count(), 1)


class EnviarWebPushTests(TestCase):
    """enviar_web_push_a_condominio -- sin tocar la red real de ningún
    servicio de push del navegador, se mockea pywebpush.webpush."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Enviar Web Push", plan="premium")

    def setUp(self):
        self.autor = crear_membresia(self.condominio, "residente", username="wp_autor")
        self.vecino = crear_membresia(self.condominio, "residente", username="wp_vecino")

    @override_settings(VAPID_PRIVATE_KEY="")
    def test_sin_vapid_configurado_no_hace_nada(self):
        SuscripcionWebPush.objects.create(user=self.vecino.user, endpoint="https://x.test/1", p256dh="p", auth="a")
        with patch("notificaciones.services.webpush") as mock_webpush:
            enviar_web_push_a_condominio(self.condominio, "Título", "Cuerpo")
        mock_webpush.assert_not_called()

    @override_settings(VAPID_PRIVATE_KEY="clave-privada-falsa", VAPID_CLAIMS_EMAIL="contacto@devquad.cl")
    def test_envia_a_las_suscripciones_del_condominio_excluyendo_al_autor(self):
        SuscripcionWebPush.objects.create(user=self.autor.user, endpoint="https://x.test/autor", p256dh="p", auth="a")
        SuscripcionWebPush.objects.create(user=self.vecino.user, endpoint="https://x.test/vecino", p256dh="p", auth="a")
        with patch("notificaciones.services.webpush") as mock_webpush:
            enviar_web_push_a_condominio(self.condominio, "Título", "Cuerpo", excluir_user_id=self.autor.user_id)
        self.assertEqual(mock_webpush.call_count, 1)
        enviado = mock_webpush.call_args.kwargs["subscription_info"]
        self.assertEqual(enviado["endpoint"], "https://x.test/vecino")

    @override_settings(VAPID_PRIVATE_KEY="clave-privada-falsa")
    def test_suscripcion_vencida_se_borra_sola(self):
        sub = SuscripcionWebPush.objects.create(user=self.vecino.user, endpoint="https://x.test/vieja", p256dh="p", auth="a")
        error = WebPushException("Gone", response=Mock(status_code=410))
        with patch("notificaciones.services.webpush", side_effect=error):
            enviar_web_push_a_condominio(self.condominio, "Título", "Cuerpo")
        self.assertFalse(SuscripcionWebPush.objects.filter(pk=sub.pk).exists())

    @override_settings(VAPID_PRIVATE_KEY="clave-privada-falsa")
    def test_otros_errores_no_borran_la_suscripcion(self):
        sub = SuscripcionWebPush.objects.create(user=self.vecino.user, endpoint="https://x.test/temporal", p256dh="p", auth="a")
        error = WebPushException("Server error", response=Mock(status_code=500))
        with patch("notificaciones.services.webpush", side_effect=error):
            enviar_web_push_a_condominio(self.condominio, "Título", "Cuerpo")
        self.assertTrue(SuscripcionWebPush.objects.filter(pk=sub.pk).exists())
