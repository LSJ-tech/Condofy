from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Condominio, Membresia

from .models import Alerta


def crear_membresia(condominio, rol, **user_kwargs):
    """Sin password: los tests se autentican con force_login."""
    username = user_kwargs.pop("username", f"t_{rol}_{Membresia.objects.count()}")
    user = User.objects.create_user(username=username, **user_kwargs)
    return Membresia.objects.create(user=user, condominio=condominio, rol=rol, terminos_aceptados_en=timezone.now())


class FiltroEstadoAlertaTests(TestCase):
    """`?estado=activa` alguna vez no filtraba nada (no había filter_backend
    configurado) y 'Alertas activas' mostraba TODAS las alertas, incluidas
    las resueltas. Esto fija ese comportamiento."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Filtro Alertas", plan="premium")

    def setUp(self):
        self.membresia = crear_membresia(self.condominio, "residente", username="filtro_residente")
        self.client.force_login(self.membresia.user)
        Alerta.objects.create(condominio=self.condominio, autor=self.membresia, tipo="robo", estado="activa")
        Alerta.objects.create(condominio=self.condominio, autor=self.membresia, tipo="incendio", estado="resuelta")
        Alerta.objects.create(condominio=self.condominio, autor=self.membresia, tipo="otro", estado="falsa_alarma")

    def test_estado_activa_filtra_de_verdad(self):
        r = self.client.get(reverse("alerta-list") + "?estado=activa")
        datos = r.json()
        resultados = datos["results"] if isinstance(datos, dict) else datos
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["tipo"], "robo")

    def test_sin_filtro_devuelve_todas(self):
        r = self.client.get(reverse("alerta-list"))
        datos = r.json()
        resultados = datos["results"] if isinstance(datos, dict) else datos
        self.assertEqual(len(resultados), 3)


class AutoCierreYResolucionAbiertaTests(TestCase):
    """Cualquier rol puede resolver una alerta (no solo directiva/conserjería,
    ver TieneMembresia en vez de EsDirectivaOConserje), y una alerta activa
    hace más de 30 min se autocierra sola al listarse."""

    @classmethod
    def setUpTestData(cls):
        cls.condominio = Condominio.objects.create(nombre="Test Autocierre", plan="premium")

    def setUp(self):
        self.autor = crear_membresia(self.condominio, "residente", username="auto_autor")
        self.vecino = crear_membresia(self.condominio, "residente", username="auto_vecino")

    def test_un_residente_puede_resolver_la_alerta_de_otro(self):
        alerta = Alerta.objects.create(condominio=self.condominio, autor=self.autor, tipo="robo", estado="activa")
        self.client.force_login(self.vecino.user)
        r = self.client.patch(
            reverse("alerta-resolver", kwargs={"pk": alerta.pk}),
            data={"estado": "resuelta"}, content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, "resuelta")
        self.assertEqual(alerta.resuelta_por_id, self.vecino.pk)

    def test_alerta_vieja_se_autocierra_al_listar(self):
        alerta = Alerta.objects.create(condominio=self.condominio, autor=self.autor, tipo="robo", estado="activa")
        Alerta.objects.filter(pk=alerta.pk).update(fecha_creacion=timezone.now() - timedelta(minutes=45))
        self.client.force_login(self.vecino.user)
        self.client.get(reverse("alerta-list"))
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, "auto_cerrada")
