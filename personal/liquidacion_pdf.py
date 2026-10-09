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
GRIS_CLARO = HexColor("#F3F4F6")
LINEA = HexColor("#D1D5DB")
BLANCO = HexColor("#FFFFFF")

DESCARGO = (
    "Esta liquidación es una estimación calculada según las reglas generales vigentes. "
    "Verifícala con tu contador antes de pagar -- no reemplaza asesoría profesional."
)

MESES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _peso(monto):
    return f"${monto:,}".replace(",", ".")


def _periodo_largo(periodo):
    anio, mes = periodo.split("-")
    return f"{MESES[int(mes)]} del {anio}"


def _codigo_verificacion(liquidacion):
    base = f"{liquidacion.pk}-{liquidacion.liquido_a_pagar}-{liquidacion.periodo}-{liquidacion.empleado_id}"
    return hashlib.sha256(base.encode()).hexdigest()[:8].upper()


def nombre_archivo_liquidacion(liquidacion):
    return f"liquidacion_{liquidacion.empleado.rut}_{liquidacion.periodo}.pdf".replace(" ", "_")


def _dato(c, x, y, etiqueta, valor):
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 8)
    c.drawString(x, y, etiqueta.upper())
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(x, y - 13, valor)


def _envolver_texto(c, texto, fuente, tamano, ancho_max):
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        candidato = f"{actual} {palabra}".strip()
        if actual and c.stringWidth(candidato, fuente, tamano) > ancho_max:
            lineas.append(actual)
            actual = palabra
        else:
            actual = candidato
    if actual:
        lineas.append(actual)
    return lineas


def _fila_columna(c, x1, x2, y, etiqueta, valor, negrita=False):
    c.setFillColor(GRIS if not negrita else NAVY)
    c.setFont("Helvetica-Bold" if negrita else "Helvetica", 9.5)
    c.drawString(x1, y, etiqueta)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold" if negrita else "Helvetica", 9.5)
    c.drawRightString(x2, y, valor)


def generar_liquidacion_pdf_bytes(liquidacion):
    condominio = liquidacion.empleado.condominio
    empleado = liquidacion.empleado
    ancho, alto = A4
    margen = 40
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # Encabezado
    c.setFillColor(NAVY)
    c.rect(0, alto - 75, ancho, 75, fill=True, stroke=False)
    c.setFillColor(BLANCO)
    c.setFont("Helvetica-Bold", 19)
    c.drawString(margen, alto - 32, "Condofy")
    c.setFont("Helvetica", 10)
    c.drawString(margen, alto - 48, "Liquidación de remuneraciones")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(ancho - margen, alto - 32, condominio.nombre)
    c.setFont("Helvetica", 9.5)
    c.drawRightString(ancho - margen, alto - 48, _periodo_largo(liquidacion.periodo))
    if condominio.direccion:
        c.setFont("Helvetica", 8)
        c.drawRightString(ancho - margen, alto - 61, condominio.direccion)

    # Datos del trabajador (grilla 2 filas x 3 columnas)
    y = alto - 110
    col_w = (ancho - 2 * margen) / 3
    _dato(c, margen, y, "Nombre", empleado.nombre)
    _dato(c, margen + col_w, y, "RUT", empleado.rut)
    _dato(c, margen + 2 * col_w, y, "Cargo", empleado.cargo)
    y -= 32
    _dato(c, margen, y, "Fecha de ingreso", str(empleado.fecha_ingreso))
    _dato(c, margen + col_w, y, "AFP", liquidacion.afp_nombre_usada)
    _dato(c, margen + 2 * col_w, y, "Salud", "Isapre" if empleado.sistema_salud == "isapre" else "Fonasa")
    y -= 28

    c.setStrokeColor(LINEA)
    c.line(margen, y, ancho - margen, y)
    y -= 24

    # Dos columnas: Haberes (izquierda) / Descuentos (derecha)
    col_izq_x1, col_izq_x2 = margen, margen + col_w * 1.42
    col_der_x1, col_der_x2 = margen + col_w * 1.62, ancho - margen
    y_inicio_columnas = y

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(col_izq_x1, y, "HABERES")
    c.drawString(col_der_x1, y, "DESCUENTOS LEGALES")
    y -= 18

    y_izq = y
    _fila_columna(c, col_izq_x1, col_izq_x2, y_izq, "Sueldo base", _peso(liquidacion.sueldo_base))
    y_izq -= 15
    if liquidacion.gratificacion:
        _fila_columna(c, col_izq_x1, col_izq_x2, y_izq, "Gratificación legal", _peso(liquidacion.gratificacion))
        y_izq -= 15
    if liquidacion.asignacion_colacion:
        _fila_columna(c, col_izq_x1, col_izq_x2, y_izq, "Asignación de colación", _peso(liquidacion.asignacion_colacion))
        y_izq -= 15
    if liquidacion.asignacion_movilizacion:
        _fila_columna(c, col_izq_x1, col_izq_x2, y_izq, "Asignación de movilización", _peso(liquidacion.asignacion_movilizacion))
        y_izq -= 15

    y_der = y
    _fila_columna(c, col_der_x1, col_der_x2, y_der, f"AFP {liquidacion.afp_tasa_usada}%", _peso(liquidacion.descuento_afp))
    y_der -= 15
    etiqueta_salud = "Isapre" if empleado.sistema_salud == "isapre" else "Salud (Fonasa) 7%"
    _fila_columna(c, col_der_x1, col_der_x2, y_der, etiqueta_salud, _peso(liquidacion.descuento_salud))
    y_der -= 15
    _fila_columna(c, col_der_x1, col_der_x2, y_der, "Seguro de cesantía", _peso(liquidacion.descuento_cesantia))
    y_der -= 15
    if liquidacion.impuesto_unico:
        _fila_columna(c, col_der_x1, col_der_x2, y_der, "Impuesto único", _peso(liquidacion.impuesto_unico))
        y_der -= 15

    y = min(y_izq, y_der) - 8
    c.setStrokeColor(LINEA)
    c.line(col_izq_x1, y, col_izq_x2, y)
    c.line(col_der_x1, y, col_der_x2, y)
    y -= 18

    _fila_columna(c, col_izq_x1, col_izq_x2, y, "Total haberes", _peso(liquidacion.total_haberes), negrita=True)
    _fila_columna(c, col_der_x1, col_der_x2, y, "Total descuentos", _peso(liquidacion.total_descuentos), negrita=True)
    y -= 45

    # Líquido a pagar
    c.setFillColor(GRIS_CLARO)
    c.rect(margen, y - 15, ancho - 2 * margen, 45, fill=True, stroke=False)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 11)
    c.drawString(margen + 15, y + 10, "Líquido a pagar")
    c.setFillColor(TERRACOTA)
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(ancho - margen - 15, y + 6, _peso(liquidacion.liquido_a_pagar))
    y -= 50

    # Certificado de recepción + firma
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 8.5)
    certificado = (
        f"Certifico que he recibido de {condominio.nombre} la suma de {_peso(liquidacion.liquido_a_pagar)} "
        f"a mi satisfacción como saldo líquido de la presente liquidación."
    )
    for linea in _envolver_texto(c, certificado, "Helvetica", 8.5, ancho - 2 * margen):
        c.drawString(margen, y, linea)
        y -= 12

    y -= 28
    c.setStrokeColor(GRIS)
    c.line(margen, y, margen + 220, y)
    y -= 11
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 8)
    c.drawString(margen, y, "Firma del trabajador")

    # Pie: descargo legal + verificación
    y -= 30
    c.setStrokeColor(GRIS)
    c.setDash(2, 2)
    c.line(margen, y, ancho - margen, y)
    c.setDash()
    y -= 16

    c.setFillColor(GRIS)
    c.setFont("Helvetica-Oblique", 7.5)
    for linea in _envolver_texto(c, DESCARGO, "Helvetica-Oblique", 7.5, ancho - 2 * margen):
        c.drawString(margen, y, linea)
        y -= 10
    y -= 4
    generado = timezone.localtime().strftime("%d-%m-%Y %H:%M")
    c.drawString(margen, y, f"Comprobante generado digitalmente por Condofy el {generado}.")
    y -= 10
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
