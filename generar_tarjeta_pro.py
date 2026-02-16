"""
Genera una tarjeta/banner corporativo en PDF con QR (Digital Comunity).

USO (Windows PowerShell / CMD):
  1) Instala dependencias UNA VEZ (en consola, NO dentro del .py):
       pip install reportlab pillow
  2) Ejecuta:
       python generar_tarjeta_pro.py

Personaliza:
  - tutorial_url (link del QR)
  - correo / web
  - logo_path (puedes dejarlo vacío si aún no tienes logo)
"""

import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from PIL import Image

# ========= CONFIG =========
OUT_PDF = "Tarjeta_Digital_Comunity_Banner.pdf"

NOMBRE_EMPRESA = "DIGITAL COMUNITY"
ESLOGAN = "Generando Proyectos en un Mar de Oportunidades"

NOMBRE = "Juan Manuel Gallardo"
CARGO = "Fundador / Director CEO"
TELEFONO = "+56 9 6588 3527"

CORREO = "juan.gallardo@tudominio.cl"
WEB = "www.digitalcomunity.cl"

# QR apunta al tutorial (mientras no haya web definitiva)
tutorial_url = "https://www.digitalcomunity.cl/tutorial"

# Logo (opcional): deja "" si no quieres logo aún
logo_path = "logo.png"  # por ejemplo: "static/logo.png" o "assets/logo.png"

# Tamaño lienzo (puntos PDF). 1000x600 funciona bien para digital.
W, H = 1000, 600


def register_fonts():
    # Fuente profesional (DejaVu) – viene en la mayoría de Linux.
    # En Windows, si falla, cambia a Arial usando fuentes del sistema o usa Helvetica.
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
        return "DejaVu", "DejaVu-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


def draw_gradient_bg(c):
    start = Color(0.07, 0.36, 0.63)  # azul profundo
    end = Color(0.53, 0.83, 0.93)    # celeste
    steps = 120
    for i in range(steps):
        t = i / (steps - 1)
        col = Color(
            start.red * (1 - t) + end.red * t,
            start.green * (1 - t) + end.green * t,
            start.blue * (1 - t) + end.blue * t,
        )
        y = H * i / steps
        c.setFillColor(col)
        c.setStrokeColor(col)
        c.rect(0, y, W, H / steps + 1, stroke=0, fill=1)

    # círculos suaves
    c.setFillColor(Color(1, 1, 1, 0.12))
    for (cx, cy, r) in [(180, 520, 220), (880, 120, 260), (840, 520, 180), (120, 110, 170)]:
        c.circle(cx, cy, r, stroke=0, fill=1)

    # líneas “tech”
    c.setStrokeColor(Color(1, 1, 1, 0.15))
    c.setLineWidth(2)
    for x in range(520, 980, 60):
        c.line(x, 0, x, H)
    for y in range(80, 560, 80):
        c.line(450, y, W, y)

    # divisiones
    c.setStrokeColor(Color(1, 1, 1, 0.65))
    c.setLineWidth(2)
    c.line(640, 120, 640, 500)
    c.line(60, 120, 940, 120)


def draw_logo(c):
    if not logo_path:
        return
    if not os.path.exists(logo_path):
        return

    img = Image.open(logo_path).convert("RGBA")
    c.drawImage(ImageReader(img), 90, 360, width=140, height=140, mask="auto")


def draw_text(c, font, bold_font):
    c.setFillColor(colors.white)
    c.setFont(bold_font, 54)
    c.drawString(250, 430, NOMBRE_EMPRESA)

    c.setFont(font, 18)
    c.setFillColor(Color(1, 1, 1, 0.9))
    c.drawString(252, 400, ESLOGAN)

    c.setFont(bold_font, 28)
    c.setFillColor(colors.white)
    c.drawString(90, 260, NOMBRE)

    c.setFont(font, 18)
    c.setFillColor(Color(1, 1, 1, 0.9))
    c.drawString(90, 232, CARGO)
    c.drawString(90, 204, f"Teléfono: {TELEFONO}")
    c.drawString(90, 150, f"Contacto: {CORREO}  •  {WEB}")

    c.setFont(font, 12)
    c.setFillColor(Color(1, 1, 1, 0.75))
    c.drawCentredString(W / 2, 40, "© 2026 Digital Comunity")


def draw_qr(c, font):
    qrw = qr.QrCodeWidget(tutorial_url)
    bounds = qrw.getBounds()
    size = 240
    d = Drawing(
        size, size,
        transform=[
            size / (bounds[2] - bounds[0]),
            0,
            0,
            size / (bounds[3] - bounds[1]),
            0,
            0,
        ],
    )
    d.add(qrw)
    renderPDF.draw(d, c, 700, 240)

    c.setFont(font, 14)
    c.setFillColor(Color(1, 1, 1, 0.9))
    c.drawCentredString(820, 220, "Escanea para ver el tutorial")


def main():
    font, bold_font = register_fonts()

    c = canvas.Canvas(OUT_PDF, pagesize=(W, H))
    draw_gradient_bg(c)
    draw_logo(c)
    draw_text(c, font, bold_font)
    draw_qr(c, font)
    c.showPage()
    c.save()

    print(f"✅ PDF generado: {OUT_PDF}")


if __name__ == "__main__":
    main()
