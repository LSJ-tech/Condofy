import re
import secrets
import string

from django.contrib.auth.models import User
from django.utils.text import slugify


def _solo_letras(texto):
    """Minúsculas, sin tildes/ñ, sin espacios ni símbolos."""
    return re.sub(r"[^a-z0-9]", "", slugify(texto or ""))


def generar_username(nombre, apellido, segundo_apellido=""):
    """
    Usuario = primera letra del nombre + apellido paterno (ej. Juan Pérez -> jperez).
    Si ya existe, se agrega al final la primera letra del segundo apellido/materno.
    Si aun así choca, se agrega un número al final.
    """
    inicial = _solo_letras(nombre)[:1]
    apellido_limpio = _solo_letras(apellido)
    base = f"{inicial}{apellido_limpio}"

    if not User.objects.filter(username__iexact=base).exists():
        return base

    inicial_segundo = _solo_letras(segundo_apellido)[:1]
    if inicial_segundo:
        alterno = f"{base}{inicial_segundo}"
        if not User.objects.filter(username__iexact=alterno).exists():
            return alterno

    contador = 2
    candidato = f"{base}{contador}"
    while User.objects.filter(username__iexact=candidato).exists():
        contador += 1
        candidato = f"{base}{contador}"
    return candidato


def generar_password_temporal(longitud=10):
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))
