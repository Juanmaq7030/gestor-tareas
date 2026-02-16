from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

# ===============================
# CONFIGURACIÓN
# ===============================

archivo_salida = "Tarjeta_Digital_Comunity.pdf"

# 👉 Aquí puedes cambiar después por tu web real
url_qr = "https://digitalcomunity.cl/tutorial"

# ===============================
# CREAR DOCUMENTO (tamaño tarjeta)
# ===============================

doc = SimpleDocTemplate(
    archivo_salida,
    pagesize=(90*mm, 55*mm),
    rightMargin=10,
    leftMargin=10,
    topMargin=10,
    bottomMargin=10
)

# ===============================
# ESTILOS
# ===============================

empresa = ParagraphStyle(name="empresa", fontSize=14, leading=16)
slogan = ParagraphStyle(name="slogan", fontSize=8, leading=10)
nombre = ParagraphStyle(name="nombre", fontSize=11, leading=14)
cargo = ParagraphStyle(name="cargo", fontSize=9, leading=12)
footer = ParagraphStyle(name="footer", fontSize=7, alignment=TA_CENTER)

# ===============================
# CREAR QR
# ===============================

qr_code = qr.QrCodeWidget(url_qr)
bounds = qr_code.getBounds()
width = bounds[2] - bounds[0]
height = bounds[3] - bounds[1]

d = Drawing(30*mm, 30*mm, transform=[30*mm/width, 0, 0, 30*mm/height, 0, 0])
d.add(qr_code)

# ===============================
# CONTENIDO TARJETA
# ===============================

texto = [
    Paragraph("<b>DIGITAL COMUNITY</b>", empresa),
    Paragraph("Generando Proyectos en un Mar de Oportunidades", slogan),
    Spacer(1, 6),
    Paragraph("<b>Juan Manuel Gallardo</b>", nombre),
    Paragraph("Fundador / Director CEO", cargo),
    Paragraph("+56 9 6588 3527", cargo),
]

tabla = Table([[texto, d]])

elementos = [tabla, Spacer(1, 6),
             Paragraph("Escanea el QR para ver el tutorial", footer)]

doc.build(elementos)

print("✅ Tarjeta creada:", archivo_salida)

