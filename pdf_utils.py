"""
Lógica de generación de PDF: lectura de páginas, registro de fuentes, rejilla
de calibración e inserción de texto. Nada para editar acá — los valores que
se ajustan a mano están en config.py.
"""

import hashlib
import io
import os
import tempfile

from config import BASE_DIR, FUENTE_POR_DEFECTO, MATRIX_FILAS

_NOMBRE_FUENTE_DEFECTO = "FuentePorDefecto"
_FONT_CACHE = {}


def extraer_pagina(pdf_bytes: bytes, pagina_idx: int) -> bytes:
    """Devuelve un PDF de una sola página (la `pagina_idx` del documento
    completo). Se usa para la vista previa en vivo, así el visor no muestra
    de arrastre el resto de las páginas del documento original."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.add_page(reader.pages[pagina_idx])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def leer_tamano_pagina(pdf_bytes: bytes, pagina_idx: int):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if pagina_idx < 0 or pagina_idx >= len(reader.pages):
        raise ValueError(f"El PDF tiene {len(reader.pages)} página(s); pediste la página {pagina_idx + 1}.")
    box = reader.pages[pagina_idx].mediabox
    return float(box.width), float(box.height), len(reader.pages)


def _resolver_ruta_proyecto(nombre_archivo: str) -> str:
    """Resuelve un nombre de archivo relativo a la carpeta del proyecto,
    o lo deja tal cual si ya es una ruta absoluta."""
    if os.path.isabs(nombre_archivo):
        return nombre_archivo
    return os.path.join(BASE_DIR, nombre_archivo)


def _leer_archivo_proyecto(nombre_archivo: str) -> bytes:
    """Lee de disco un archivo por nombre (relativo a la carpeta del
    proyecto) o ruta absoluta."""
    with open(_resolver_ruta_proyecto(nombre_archivo), "rb") as f:
        return f.read()


def _tamano_imagen(ruta: str, ancho, alto):
    """Calcula el tamaño final de una imagen: si faltan ancho o alto, los
    calcula manteniendo la proporción original de la imagen."""
    if ancho and alto:
        return ancho, alto
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(ruta).getSize()
    if ancho:
        return ancho, ancho * ih / iw
    if alto:
        return alto * iw / ih, alto
    return iw, ih


def leer_fuente_predeterminada(nombre_archivo: str) -> bytes:
    return _leer_archivo_proyecto(nombre_archivo)


def leer_pdf_predeterminado(nombre_archivo: str) -> bytes:
    return _leer_archivo_proyecto(nombre_archivo)


def preparar_imagenes(imagenes_config: list) -> list:
    """Convierte config.IMAGENES_PREDETERMINADAS (con 'archivo' y 'pagina'
    1-indexada) al formato que espera generar_pdf_con_texto (con 'ruta'
    resuelta en disco y 'pagina_idx' 0-indexada). Lanza ValueError con un
    mensaje claro si algún archivo de imagen no existe."""
    resultado = []
    for i, img in enumerate(imagenes_config, start=1):
        archivo = img.get("archivo", "")
        ruta = _resolver_ruta_proyecto(archivo)
        if not os.path.isfile(ruta):
            raise ValueError(
                f"No se encontró la imagen #{i} configurada en IMAGENES_PREDETERMINADAS: {archivo}"
            )
        item = {
            "ruta": ruta,
            "x": img.get("x", 0),
            "y": img.get("y", 0),
            "ancho": img.get("ancho"),
            "alto": img.get("alto"),
        }
        if "pagina" in img:
            item["pagina_idx"] = int(img["pagina"]) - 1
        resultado.append(item)
    return resultado


def registrar_fuente(font_bytes: "bytes | None" = None, etiqueta: str = "") -> str:
    """Registra una fuente y devuelve su nombre interno.
    Sin `font_bytes` usa FUENTE_POR_DEFECTO (config.py); si se pasan bytes de
    una fuente propia, se registra (una sola vez por contenido) bajo un
    nombre propio."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont, TTFError

    if font_bytes is None:
        if _NOMBRE_FUENTE_DEFECTO not in pdfmetrics.getRegisteredFontNames():
            ruta = os.path.join(BASE_DIR, FUENTE_POR_DEFECTO)
            pdfmetrics.registerFont(TTFont(_NOMBRE_FUENTE_DEFECTO, ruta))
        return _NOMBRE_FUENTE_DEFECTO

    clave = hashlib.sha1(font_bytes).hexdigest()
    if clave in _FONT_CACHE:
        return _FONT_CACHE[clave]

    suffix = ".otf" if font_bytes[:4] == b"OTTO" else ".ttf"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(font_bytes)
        tmp.flush()
        tmp.close()
        nombre = f"Fuente_{clave[:12]}"
        try:
            pdfmetrics.registerFont(TTFont(nombre, tmp.name))
        except TTFError as e:
            donde = f" en la fila {etiqueta}" if etiqueta else ""
            raise ValueError(
                f"No se pudo usar la fuente indicada{donde}: {e}. "
                "Los archivos .otf con contornos PostScript no son compatibles; usa un .ttf."
            )
        _FONT_CACHE[clave] = nombre
        return nombre
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def hex_a_color(hex_str: str):
    from reportlab.lib.colors import HexColor
    hex_str = (hex_str or "#000000").strip()
    if not hex_str.startswith("#"):
        hex_str = "#" + hex_str
    return HexColor(hex_str)


def _fusionar_overlays(pdf_bytes: bytes, dibujar_por_pagina: dict) -> bytes:
    """`dibujar_por_pagina` es {pagina_idx: dibujar_fn(c, ancho, alto)}. Para
    cada página indicada crea un overlay de su mismo tamaño, ejecuta su
    función de dibujo, y lo fusiona con esa página del PDF original. El
    resto de las páginas quedan intactas."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas as rl_canvas

    original = PdfReader(io.BytesIO(pdf_bytes))
    overlays = {}
    for pagina_idx, dibujar_fn in dibujar_por_pagina.items():
        ancho, alto, _ = leer_tamano_pagina(pdf_bytes, pagina_idx)
        packet = io.BytesIO()
        c = rl_canvas.Canvas(packet, pagesize=(ancho, alto))
        dibujar_fn(c, ancho, alto)
        c.save()
        packet.seek(0)
        overlays[pagina_idx] = PdfReader(packet).pages[0]

    writer = PdfWriter()
    for i, pagina in enumerate(original.pages):
        if i in overlays:
            pagina.merge_page(overlays[i])
        writer.add_page(pagina)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _fusionar_overlay(pdf_bytes: bytes, pagina_idx: int, dibujar_fn) -> bytes:
    """Caso particular de `_fusionar_overlays` para una sola página."""
    return _fusionar_overlays(pdf_bytes, {pagina_idx: dibujar_fn})


def _color_para_fila(numero: int):
    """Devuelve un color distinto y estable para cada fila de la matriz (1..MATRIX_FILAS)."""
    import colorsys
    from reportlab.lib.colors import Color

    hue = ((numero - 1) % MATRIX_FILAS) / MATRIX_FILAS
    r, g, b = colorsys.hsv_to_rgb(hue, 0.72, 0.82)
    return Color(r, g, b)


def generar_rejilla(pdf_bytes: bytes, pagina_idx: int, puntos: "list | None" = None, paso: int = 50) -> bytes:
    from reportlab.lib.colors import Color

    puntos = puntos or []

    def dibujar(c, ancho, alto):
        gris = Color(0.85, 0.15, 0.15, alpha=0.65)
        c.setStrokeColor(gris)
        c.setFillColor(gris)
        c.setFont("Helvetica", 6)
        c.setLineWidth(0.4)

        x = 0
        while x <= ancho:
            c.line(x, 0, x, alto)
            c.drawString(x + 2, alto - 9, str(x))
            x += paso

        y = 0
        while y <= alto:
            c.line(0, y, ancho, y)
            c.drawString(2, y + 2, str(y))
            y += paso

        c.setFont("Helvetica-Bold", 8)
        c.drawString(6, alto - 20, f"Tamaño de página: {ancho:.0f} x {alto:.0f} pt")

        for punto in puntos:
            color = _color_para_fila(punto["numero"])
            c.setFillColor(color)
            c.setStrokeColor(Color(1, 1, 1))
            c.setLineWidth(1)
            c.circle(punto["x"], punto["y"], 7, stroke=1, fill=1)
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(Color(1, 1, 1))
            c.drawCentredString(punto["x"], punto["y"] - 2.5, str(punto["numero"]))

    return _fusionar_overlay(pdf_bytes, pagina_idx, dibujar)


def generar_pdf_con_texto(pdf_bytes: bytes, pagina_idx: int, stamps: list,
                           color_hex: str, imagenes: "list | None" = None) -> bytes:
    """Inserta varias marcas de texto (una por elemento de `stamps`) en la
    página `pagina_idx`, más las imágenes fijas de config.py (que pueden ir
    en cualquier página, no solo en `pagina_idx`).

    Cada stamp es un dict con: texto, x, y, tamano y, opcionalmente,
    font_bytes (fuente propia de esa fila), etiqueta (para mensajes de error)
    y centrado (si es True, x,y es el centro del texto: mitad para cada lado;
    si es False/falta, x,y es el borde izquierdo, como antes).

    Cada imagen es un dict con: ruta, x, y, ancho, alto y, opcionalmente,
    pagina_idx (página 0-indexada; si falta, va en `pagina_idx`)."""
    color = hex_a_color(color_hex)
    imagenes = imagenes or []

    imagenes_por_pagina = {}
    for img in imagenes:
        idx = img.get("pagina_idx", pagina_idx)
        imagenes_por_pagina.setdefault(idx, []).append(img)

    def hacer_dibujar_fn(idx):
        def dibujar(c, ancho, alto):
            if idx == pagina_idx:
                c.setFillColor(color)
                for stamp in stamps:
                    nombre_fuente = registrar_fuente(stamp.get("font_bytes"), stamp.get("etiqueta", ""))
                    c.setFont(nombre_fuente, stamp["tamano"])
                    if stamp.get("centrado"):
                        c.drawCentredString(stamp["x"], stamp["y"], stamp["texto"])
                    else:
                        c.drawString(stamp["x"], stamp["y"], stamp["texto"])
            for img in imagenes_por_pagina.get(idx, []):
                ancho_img, alto_img = _tamano_imagen(img["ruta"], img.get("ancho"), img.get("alto"))
                c.drawImage(
                    img["ruta"], img["x"], img["y"],
                    width=ancho_img, height=alto_img,
                    mask="auto", preserveAspectRatio=True,
                )
        return dibujar

    paginas = set(imagenes_por_pagina) | {pagina_idx}
    dibujar_por_pagina = {idx: hacer_dibujar_fn(idx) for idx in paginas}
    return _fusionar_overlays(pdf_bytes, dibujar_por_pagina)
