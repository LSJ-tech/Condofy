from notificaciones.services import enviar_push_a_condominio

TITULOS_POR_TIPO = {
    "robo": "🚨 Alerta de robo",
    "incendio": "🔥 Alerta de incendio",
    "accidente": "🚑 Alerta de accidente",
    "otro": "🚨 Alerta de emergencia",
}


def notificar_alerta(alerta):
    titulo = TITULOS_POR_TIPO.get(alerta.tipo, TITULOS_POR_TIPO["otro"])
    cuerpo = alerta.mensaje or f"{alerta.autor.user.get_full_name()} activó el botón de pánico."
    enviar_push_a_condominio(
        alerta.condominio,
        titulo,
        cuerpo,
        data={"tipo": "alerta", "alerta_id": alerta.id},
        excluir_user_id=alerta.autor.user_id,
    )
