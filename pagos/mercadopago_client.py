import logging

import mercadopago
from django.conf import settings

logger = logging.getLogger(__name__)


def _access_token():
    return settings.MERCADOPAGO_ACCESS_TOKEN.strip()


def _sdk():
    return mercadopago.SDK(_access_token())


def crear_preferencia_pago(pago, request):
    """Crea la preferencia de Checkout Pro para este Pago y devuelve la URL
    a la que hay que redirigir al condominio para pagar. None si Mercado
    Pago rechazó la solicitud."""
    base_url = request.build_absolute_uri("/").rstrip("/")
    if pago.tipo == "donacion":
        titulo = f"Donación a {settings.PLATFORM_NAME} - {pago.condominio.nombre}"
    else:
        titulo = f"Suscripción {settings.PLATFORM_NAME} - {pago.condominio.nombre}"
    preferencia = {
        "items": [{
            "title": titulo,
            "quantity": 1,
            "unit_price": float(pago.monto),
            "currency_id": "CLP",
        }],
        "external_reference": str(pago.pk),
        "back_urls": {
            "success": f"{base_url}/pago/resultado/",
            "pending": f"{base_url}/pago/resultado/",
            "failure": f"{base_url}/pago/resultado/",
        },
        "auto_return": "approved",
        "notification_url": f"{base_url}/pago/webhook/",
    }
    resultado = _sdk().preference().create(preferencia)
    if not resultado.is_success:
        logger.error(
            "Mercado Pago rechazó la preferencia del pago #%s: status=%s respuesta=%s",
            pago.pk, resultado.get("status"), resultado.get("response"),
        )
        return None

    datos = resultado["response"]
    pago.mercadopago_preference_id = datos["id"]
    pago.save(update_fields=["mercadopago_preference_id"])

    es_credencial_de_prueba = _access_token().startswith("TEST-")
    if es_credencial_de_prueba and datos.get("sandbox_init_point"):
        return datos["sandbox_init_point"]
    return datos["init_point"]


def obtener_pago_mercadopago(payment_id):
    """Consulta un pago por su ID directo a la API de Mercado Pago. Nunca se
    confía en el estado que venga en el cuerpo del webhook."""
    resultado = _sdk().payment().get(payment_id)
    if not resultado.is_success:
        logger.error(
            "No se pudo consultar el pago %s en Mercado Pago: status=%s respuesta=%s",
            repr(payment_id), resultado.get("status"), resultado.get("response"),
        )
        return None
    return resultado["response"]
