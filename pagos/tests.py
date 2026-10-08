import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Condominio, Membresia, Torre, Unidad

from .models import Pago


def crear_membresia(condominio, rol, unidad=None, **user_kwargs):
    username = user_kwargs.pop("username", f"t_{rol}_{Membresia.objects.count()}")
    user = User.objects.create_user(username=username, password="x12345678", **user_kwargs)
    return Membresia.objects.create(
        user=user, condominio=condominio, rol=rol, unidad=unidad, terminos_aceptados_en=timezone.now(),
    )


@override_settings(MERCADOPAGO_ACCESS_TOKEN="TEST-fake-token")
class DonarViewTests(TestCase):
    """Cualquier miembro puede donar (commit 6e4a108) -- sin tocar la red real
    de Mercado Pago, se mockea crear_preferencia_pago."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Donar", plan="premium")
        cls.torre = Torre.objects.create(condominio=cls.condominio, nombre="5")
        cls.unidad = Unidad.objects.create(condominio=cls.condominio, torre=cls.torre, numero="502")

    def setUp(self):
        self.residente = crear_membresia(self.condominio, "residente", unidad=self.unidad, username="don_residente")
        self.client.login(username="don_residente", password="x12345678")

    @patch("pagos.views.crear_preferencia_pago", return_value="https://fake-mp.test/pagar/1")
    def test_residente_puede_donar(self, mock_pref):
        r = self.client.post(reverse("donar"), {"monto": "3000"})
        self.assertEqual(r.status_code, 302)
        pago = Pago.objects.get(condominio=self.condominio, tipo="donacion")
        self.assertEqual(pago.membresia_id, self.residente.pk)
        self.assertEqual(pago.monto, Decimal("3000"))
        self.assertEqual(pago.plan, "")

    def test_monto_invalido_no_crea_pago(self):
        r = self.client.post(reverse("donar"), {"monto": "no-es-numero"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Pago.objects.filter(condominio=self.condominio).exists())

    @override_settings(MERCADOPAGO_ACCESS_TOKEN="")
    def test_sin_token_configurado_no_crea_pago(self):
        r = self.client.post(reverse("donar"), {"monto": "3000"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Pago.objects.filter(condominio=self.condominio).exists())

    def test_usuario_sin_membresia_no_puede_donar(self):
        User.objects.create_user(username="sin_membresia", password="x12345678")
        self.client.logout()
        self.client.login(username="sin_membresia", password="x12345678")
        r = self.client.post(reverse("donar"), {"monto": "3000"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Pago.objects.exists())


class WebhookMercadoPagoTests(TestCase):
    """La donación aprobada NO debe tocar pagado_hasta/plan del condominio --
    eso es exclusivo de un pago de tipo 'suscripcion' (commit c8c030c)."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Webhook", plan="free", pagado_hasta=None)

    def _simular_webhook(self, pago, estado_mp="approved"):
        with patch(
            "pagos.views.obtener_pago_mercadopago",
            return_value={"status": estado_mp, "external_reference": str(pago.pk)},
        ):
            return self.client.post(
                reverse("pago-webhook"), data=json.dumps({"data": {"id": "999"}}), content_type="application/json",
            )

    def test_donacion_aprobada_no_extiende_plan_ni_vencimiento(self):
        pago = Pago.objects.create(condominio=self.condominio, tipo="donacion", monto=Decimal("5000"))
        self._simular_webhook(pago)
        pago.refresh_from_db()
        self.condominio.refresh_from_db()
        self.assertEqual(pago.estado, "aprobado")
        self.assertIsNone(self.condominio.pagado_hasta)
        self.assertEqual(self.condominio.plan, "free")

    def test_suscripcion_aprobada_si_extiende_plan_y_vencimiento(self):
        pago = Pago.objects.create(condominio=self.condominio, tipo="suscripcion", monto=Decimal("9990"), plan="premium")
        self._simular_webhook(pago)
        pago.refresh_from_db()
        self.condominio.refresh_from_db()
        self.assertEqual(pago.estado, "aprobado")
        self.assertIsNotNone(self.condominio.pagado_hasta)
        self.assertEqual(self.condominio.plan, "premium")

    def test_pago_rechazado_queda_marcado(self):
        pago = Pago.objects.create(condominio=self.condominio, tipo="donacion", monto=Decimal("1000"))
        self._simular_webhook(pago, estado_mp="rejected")
        pago.refresh_from_db()
        self.assertEqual(pago.estado, "rechazado")
