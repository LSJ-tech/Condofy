import hashlib
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A6
from reportlab.pdfgen import canvas

NAVY = HexColor("#1A2E40")
TERRACOTA = HexColor("#E07A5F")
GRIS = HexColor("#6B7280")


def _codigo_verificacion(cuota):
    base = f"{cuota.pk}-{cuota.monto}-{cuota.fecha_pago}-{cuota.gasto_comun.periodo}"
    return hashlib.sha256(base.encode()).hexdigest()[:8].upper()


def generar_boucher_pdf(cuota):
    """Comprobante de pago de una cuota de gasto común -- reemplaza el talonario
    de papel que llena a mano quien cobra. Firma electrónica simple (un sello
    con código de verificación derivado de los datos del pago), no una firma
    electrónica avanzada/certificada -- no corresponde para un comprobante."""
    condominio = cuota.gasto_comun.condominio
    unidad = cuota.unidad
    ancho, alto = A6
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A6)

    c.setFillColor(NAVY)
    c.rect(0, alto - 60, ancho, 60, fill=True, stroke=False)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(ancho / 2, alto - 35, "Condofy")
    c.setFont("Helvetica", 9)
    c.drawCentredString(ancho / 2, alto - 50, "Comprobante de pago")

    y = alto - 85
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(ancho / 2, y, condominio.nombre)
    y -= 25

    filas = []
    if unidad.torre:
        filas.append((f"{condominio.etiqueta_torre}", unidad.torre.nombre))
    filas.append((f"{condominio.etiqueta_unidad} N°", unidad.numero))
    filas.append(("Periodo", cuota.gasto_comun.periodo))
    filas.append(("Fecha de pago", str(cuota.fecha_pago) if cuota.fecha_pago else "—"))

    c.setFont("Helvetica", 10)
    for etiqueta, valor in filas:
        c.setFillColor(GRIS)
        c.drawString(20, y, etiqueta)
        c.setFillColor(NAVY)
        c.drawRightString(ancho - 20, y, str(valor))
        y -= 18

    y -= 10
    c.setStrokeColor(GRIS)
    c.line(20, y, ancho - 20, y)
    y -= 25

    c.setFillColor(GRIS)
    c.setFont("Helvetica", 10)
    c.drawString(20, y, "Total pagado")
    c.setFillColor(TERRACOTA)
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(ancho - 20, y - 4, f"${cuota.monto:,}".replace(",", "."))

    y -= 50
    c.setStrokeColor(GRIS)
    c.setDash(2, 2)
    c.line(20, y, ancho - 20, y)
    c.setDash()
    y -= 20

    c.setFillColor(GRIS)
    c.setFont("Helvetica-Oblique", 7)
    generado = timezone.localtime().strftime("%d-%m-%Y %H:%M")
    c.drawString(20, y, f"Comprobante generado digitalmente por Condofy el {generado}.")
    y -= 11
    c.drawString(20, y, f"Código de verificación: {_codigo_verificacion(cuota)}")

    c.showPage()
    c.save()
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type="application/pdf")
    nombre_archivo = f"boucher_{unidad.numero}_{cuota.gasto_comun.periodo}.pdf".replace(" ", "_")
    response["Content-Disposition"] = f'inline; filename="{nombre_archivo}"'
    return response
