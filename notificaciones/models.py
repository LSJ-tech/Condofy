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
