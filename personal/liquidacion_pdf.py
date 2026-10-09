import hashlib
from io import BytesIO

from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

NAVY = HexColor("#1A2E40")
TERRACOTA = HexColor("#E07A5F")
GRIS = HexColor("#6B7280")
BLANCO = HexColor("#FFFFFF")

DESCARGO = (
    "Esta liquidación es una estimación calculada según las reglas generales vigentes. "
    "Verifícala con tu contador antes de pagar -- no reemplaza asesoría profesional."
)


def _peso(monto):
    return f"${monto:,}".replace(",", ".")


def _codigo_verificacion(liquidacion):
    base = f"{liquidacion.pk}-{liquidacion.liquido_a_pagar}-{liquidacion.periodo}-{liquidacion.empleado_id}"
    return hashlib.sha256(base.encode()).hexdigest()[:8].upper()


def nombre_archivo_liquidacion(liquidacion):
    return f"liquidacion_{liquidacion.empleado.rut}_{liquidacion.periodo}.pdf".replace(" ", "_")


def _fila(c, x1, x2, y, etiqueta, valor, color_valor=NAVY, negrita=False):
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 10)
    c.drawString(x1, y, etiqueta)
    c.setFillColor(color_valor)
    c.setFont("Helvetica-Bold" if negrita else "Helvetica", 10)
    c.drawRightString(x2, y, valor)


def generar_liquidacion_pdf_bytes(liquidacion):
    condominio = liquidacion.empleado.condominio
    empleado = liquidacion.empleado
    ancho, alto = A4
    margen = 40
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    c.setFillColor(NAVY)
    c.rect(0, alto - 80, ancho, 80, fill=True, stroke=False)
    c.setFillColor(BLANCO)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(margen, alto - 40, "Condofy")
    c.setFont("Helvetica", 11)
    c.drawString(margen, alto - 60, "Liquidación de sueldo")
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(ancho - margen, alto - 40, condominio.nombre)
    c.setFont("Helvetica", 10)
    c.drawRightString(ancho - margen, alto - 58, f"Periodo {liquidacion.periodo}")

    y = alto - 110
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(margen, y, empleado.nombre)
    y -= 18
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 10)
    c.drawString(margen, y, f"RUT {empleado.rut} -- {empleado.cargo}")
    y -= 40

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margen, y, "Haberes")
    y -= 20
    _fila(c, margen, ancho - margen, y, "Sueldo base", _peso(liquidacion.sueldo_base))
    y -= 18
    if liquidacion.gratificacion:
        _fila(c, margen, ancho - margen, y, "Gratificación legal", _peso(liquidacion.gratificacion))
        y -= 18
    if liquidacion.asignacion_colacion:
        _fila(c, margen, ancho - margen, y, "Asignación de colación", _peso(liquidacion.asignacion_colacion))
        y -= 18
    if liquidacion.asignacion_movilizacion:
        _fila(c, margen, ancho - margen, y, "Asignación de movilización", _peso(liquidacion.asignacion_movilizacion))
        y -= 18
    y -= 5
    c.setStrokeColor(GRIS)
    c.line(margen, y, ancho - margen, y)
    y -= 20
    _fila(c, margen, ancho - margen, y, "Total haberes", _peso(liquidacion.total_haberes), negrita=True)
    y -= 45

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margen, y, "Descuentos")
    y -= 20
    _fila(c, margen, ancho - margen, y, f"AFP ({liquidacion.afp_nombre_usada}, {liquidacion.afp_tasa_usada}%)", _peso(liquidacion.descuento_afp))
    y -= 18
    _fila(c, margen, ancho - margen, y, "Salud", _peso(liquidacion.descuento_salud))
    y -= 18
    _fila(c, margen, ancho - margen, y, "Seguro de cesantía", _peso(liquidacion.descuento_cesantia))
    y -= 18
    _fila(c, margen, ancho - margen, y, "Impuesto único", _peso(liquidacion.impuesto_unico))
    y -= 5
    c.setStrokeColor(GRIS)
    c.line(margen, y, ancho - margen, y)
    y -= 20
    _fila(c, margen, ancho - margen, y, "Total descuentos", _peso(liquidacion.total_descuentos), negrita=True)
    y -= 50

    c.setFillColor(HexColor("#F3F4F6"))
    c.rect(margen, y - 15, ancho - 2 * margen, 45, fill=True, stroke=False)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 11)
    c.drawString(margen + 15, y + 10, "Líquido a pagar")
    c.setFillColor(TERRACOTA)
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(ancho - margen - 15, y + 6, _peso(liquidacion.liquido_a_pagar))

    y -= 60
    c.setStrokeColor(GRIS)
    c.setDash(2, 2)
    c.line(margen, y, ancho - margen, y)
    c.setDash()
    y -= 20

    c.setFillColor(GRIS)
    c.setFont("Helvetica-Oblique", 8)
    for linea in [DESCARGO[i:i + 100] for i in range(0, len(DESCARGO), 100)]:
        c.drawString(margen, y, linea)
        y -= 11
    y -= 5
    generado = timezone.localtime().strftime("%d-%m-%Y %H:%M")
    c.drawString(margen, y, f"Comprobante generado digitalmente por Condofy el {generado}.")
    y -= 11
    c.drawString(margen, y, f"Código de verificación: {_codigo_verificacion(liquidacion)}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def generar_liquidacion_pdf(liquidacion):
    response = HttpResponse(generar_liquidacion_pdf_bytes(liquidacion), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{nombre_archivo_liquidacion(liquidacion)}"'
    return response


def enviar_liquidacion_por_correo(liquidacion, destinatario):
    """Correo opcional a UN destinatario elegido por quien genera la
    liquidación -- no bloquea si el envío falla (mismo criterio que
    enviar_boucher_por_correo en gastoscomunes/boucher.py)."""
    from core.views import EMAIL_CONTACTO_DEVQUAD

    condominio = liquidacion.empleado.condominio
    try:
        correo = EmailMessage(
            subject=f"Liquidación de sueldo -- {liquidacion.periodo}",
            body=(
                f"Hola,\n\nAdjunto tu liquidación de sueldo de {condominio.nombre}, "
                f"periodo {liquidacion.periodo}.\n\n"
                f"Cualquier duda, escríbenos a {EMAIL_CONTACTO_DEVQUAD}."
            ),
            from_email=None,
            to=[destinatario],
        )
        correo.attach(nombre_archivo_liquidacion(liquidacion), generar_liquidacion_pdf_bytes(liquidacion), "application/pdf")
        correo.send()
    except Exception:
        pass
