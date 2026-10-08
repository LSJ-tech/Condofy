from django.contrib.auth.models import User
from django.db import models

PLATAFORMA_CHOICES = [
    ("ios", "iOS"),
    ("android", "Android"),
]


class DispositivoPush(models.Model):
    """Token de push (Expo push token, que internamente enruta a FCM/APNs) de un dispositivo del usuario."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dispositivos_push")
    token = models.CharField(max_length=255, unique=True)
    plataforma = models.CharField(max_length=10, choices=PLATAFORMA_CHOICES)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.plataforma}"


class SuscripcionWebPush(models.Model):
    """Suscripción de Web Push de un navegador (la PWA) -- separada de
    DispositivoPush (Expo, para la futura app nativa): la forma de los datos
    es completamente distinta (endpoint + un par de claves p256dh/auth, no
    un token simple), así que no comparten modelo ni lógica de envío."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="suscripciones_web_push")
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - web push"
