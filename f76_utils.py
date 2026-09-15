"""
Lógica de F-76 Form Filler: quitar fondo (remove.bg), oscurecer firma y
componer el PDF final. Nada para editar acá.
"""

import io
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "F-76_base.pdf")


def obtener_pdf_base() -> bytes:
    if os.path.exists(PDF_PATH):
        with open(PDF_PATH, "rb") as f:
            return f.read()
    raise FileNotFoundError("No se encontró F-76_base.pdf en el servidor.")


def quitar_fondo_api(imagen_bytes: bytes, api_key: str) -> bytes:
    import requests as req_lib

    resp = req_lib.post(
        "https://api.remove.bg/v1.0/removebg",
        files={"image_file": ("image", imagen_bytes)},
        data={"size": "auto"},
        headers={"X-Api-Key": api_key},
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"remove.bg respondió {resp.status_code}: {resp.text[:200]}")
    return resp.content


def oscurecer_firma(img_rgba):
    from PIL import Image
    import numpy as np

    arr = np.array(img_rgba).astype(float)
    alpha = arr[:, :, 3]
    visible = alpha > 30
    if not visible.any():
        return img_rgba
    arr[visible, 0] = 0
    arr[visible, 1] = 0
    arr[visible, 2] = 0
    return Image.fromarray(arr.astype("uint8"), "RGBA")


def procesar_firma(raw: bytes, api_key: str) -> io.BytesIO:
    from PIL import Image

    sin_fondo = quitar_fondo_api(raw, api_key)
    img = Image.open(io.BytesIO(sin_fondo)).convert("RGBA")
    img = oscurecer_firma(img)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


def procesar_foto(raw: bytes, api_key: str) -> io.BytesIO:
    sin_fondo = quitar_fondo_api(raw, api_key)
    return io.BytesIO(sin_fondo)


def generar_pdf(pdf_bytes, firma_bytes, foto_bytes, api_key) -> bytes:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader

    firma_buf = procesar_firma(firma_bytes, api_key)
    foto_buf  = procesar_foto(foto_bytes,  api_key)

    FIRMA = dict(x=105, y=105, w=210, h=75)
    FOTO  = dict(x=405, y=73,  w=115, h=100)

    packet = io.BytesIO()
    c = rl_canvas.Canvas(packet, pagesize=(612, 1008))
    c.drawImage(ImageReader(foto_buf),
                x=FOTO["x"], y=FOTO["y"],
                width=FOTO["w"], height=FOTO["h"],
                preserveAspectRatio=True, anchor="c", mask="auto")
    c.drawImage(ImageReader(firma_buf),
                x=FIRMA["x"], y=FIRMA["y"],
                width=FIRMA["w"], height=FIRMA["h"],
                preserveAspectRatio=True, anchor="c", mask="auto")
    c.save()
    packet.seek(0)

    blank   = PdfReader(io.BytesIO(pdf_bytes))
    overlay = PdfReader(packet)
    writer  = PdfWriter()
    pagina  = blank.pages[0]
    pagina.merge_page(overlay.pages[0])
    writer.add_page(pagina)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
