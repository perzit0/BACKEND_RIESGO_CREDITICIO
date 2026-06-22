import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def generar_pdf_evaluacion(usuario, evaluacion) -> bytes:
    """Recibe el objeto Usuario y el objeto Evaluacion, devuelve los bytes
    del PDF generado. user_routes.py se encarga de convertir esto en una
    respuesta descargable."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("UNFV — Reporte de Riesgo Crediticio", styles["Title"]))
    elementos.append(Spacer(1, 0.5 * cm))

    elementos.append(Paragraph(f"Usuario: {usuario.nombre}", styles["Normal"]))
    elementos.append(Paragraph(f"Correo: {usuario.email}", styles["Normal"]))
    elementos.append(Paragraph(f"Fecha de evaluacion: {evaluacion.fecha_evaluacion.strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    elementos.append(Spacer(1, 0.5 * cm))

    elementos.append(Paragraph("Resultado", styles["Heading2"]))
    tabla_resultado = Table([
        ["Nivel de riesgo crediticio", evaluacion.categoria_riesgo.upper()],
    ], colWidths=[8 * cm, 8 * cm])
    tabla_resultado.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla_resultado)
    elementos.append(Spacer(1, 0.5 * cm))

    elementos.append(Paragraph("Factores que influyeron", styles["Heading2"]))
    for factor in (evaluacion.factores_influyentes or []):
        texto = f"- {factor.get('factor')}: {factor.get('impacto')}"
        elementos.append(Paragraph(texto, styles["Normal"]))
    elementos.append(Spacer(1, 0.5 * cm))

    elementos.append(Paragraph("Recomendaciones", styles["Heading2"]))
    for recomendacion in (evaluacion.recomendaciones or []):
        elementos.append(Paragraph(f"- {recomendacion}", styles["Normal"]))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()