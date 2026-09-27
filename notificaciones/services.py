import logging

import requests

from .models import DispositivoPush

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def enviar_push_a_condominio(condominio, titulo, cuerpo, data=None, excluir_user_id=None):
    """Envía una push notification a todos los dispositivos registrados de
    usuarios con membresía en `condominio`, vía el servicio de push de Expo
    (que a su vez enruta a FCM en Android y APNs en iOS -- no hace falta
    hablar directo con Firebase mientras la app sea 100% Expo).

    No lanza excepción si Expo falla o no hay red: una alerta no debe
    fallar en crearse solo porque el push no salió, así que el error
    solo se registra en el log.
    """
    dispositivos = DispositivoPush.objects.filter(user__membresia__condominio=condominio)
    if excluir_user_id:
        dispositivos = dispositivos.exclude(user_id=excluir_user_id)

    tokens = list(dispositivos.values_list("token", flat=True))
    if not tokens:
        return

    mensajes = [
        {"to": token, "title": titulo, "body": cuerpo, "data": data or {}, "sound": "default", "priority": "high"}
        for token in tokens
    ]

    # Expo recomienda lotes de máximo 100 mensajes por request.
    for i in range(0, len(mensajes), 100):
        lote = mensajes[i:i + 100]
        try:
            respuesta = requests.post(EXPO_PUSH_URL, json=lote, timeout=10)
            respuesta.raise_for_status()
        except requests.RequestException:
            logger.exception("Falló el envío de push a Expo para %s dispositivos.", len(lote))
