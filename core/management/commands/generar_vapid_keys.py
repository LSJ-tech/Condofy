import base64

from django.core.management.base import BaseCommand
from py_vapid import Vapid02


class Command(BaseCommand):
    help = (
        "Genera un par de llaves VAPID nuevo para Web Push (botón de pánico, avisos) y lo "
        "imprime listo para pegar en las variables de entorno de Render. Se genera una sola "
        "vez -- volver a correrlo invalida las suscripciones de navegador ya registradas."
    )

    def handle(self, *args, **options):
        vapid = Vapid02()
        vapid.generate_keys()

        numeros_privados = vapid.private_key.private_numbers()
        clave_privada = base64.urlsafe_b64encode(
            numeros_privados.private_value.to_bytes(32, "big")
        ).rstrip(b"=").decode()

        numeros_publicos = vapid.public_key.public_numbers()
        punto_publico = b"\x04" + numeros_publicos.x.to_bytes(32, "big") + numeros_publicos.y.to_bytes(32, "big")
        clave_publica = base64.urlsafe_b64encode(punto_publico).rstrip(b"=").decode()

        self.stdout.write("Agrega estas variables de entorno en Render:\n")
        self.stdout.write(f"VAPID_PRIVATE_KEY={clave_privada}")
        self.stdout.write(f"VAPID_PUBLIC_KEY={clave_publica}")
