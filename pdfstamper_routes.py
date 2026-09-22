"""
PDF Stamper — vista dentro del proyecto combinado.
Rutas bajo /pdfstamper. Para editar valores por defecto usá config.py; la
lógica de generación de PDF vive en pdf_utils.py; la interfaz en
templates/pdfstamper.html y static/pdfstamper/.
"""

import io
import os
import re

from flask import Blueprint, request, send_file, render_template, jsonify

from config import (
    COLOR_POR_DEFECTO,
    FILAS_PREDETERMINADAS_SIN_PDF,
    IMAGENES_PREDETERMINADAS,
    MATRIX_FILAS,
    PDFS_DISPONIBLES,
)
from pdf_utils import (
    extraer_pagina,
    generar_pdf_con_texto,
    generar_rejilla,
    leer_fuente_predeterminada,
    leer_pdf_predeterminado,
    preparar_imagenes,
)

pdfstamper_bp = Blueprint("pdfstamper", __name__, url_prefix="/pdfstamper")


def _sanitizar_nombre_archivo(texto: str) -> str:
    """Saca caracteres inválidos en nombres de archivo (Windows) y espacios
    de sobra, para poder usar el texto tal cual en un nombre descargable."""
    texto = re.sub(r'[<>:"/\\|?*]', "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _nombre_descarga(texto_fila1: str, nombre_pdf_subido: "str | None") -> str:
    """Arma el nombre del PDF a descargar: texto de la fila 1 + nombre del
    PDF base, o un nombre genérico si la fila 1 está vacía."""
    texto_fila1 = _sanitizar_nombre_archivo(texto_fila1.strip())
    nombre_base = _sanitizar_nombre_archivo(os.path.splitext(nombre_pdf_subido or "")[0])

    partes = [p for p in (texto_fila1, nombre_base) if p]
    if not partes:
        return "documento_con_texto.pdf"
    return " - ".join(partes) + ".pdf"


@pdfstamper_bp.route("/")
def index():
    # Sin un PDF elegido todavía, la matriz arranca vacía: se rellena sola
    # (vía JS, con lo que definas en PDFS_DISPONIBLES[...]["filas"] de
    # config.py, texto predeterminado incluido) apenas se elige un PDF del
    # desplegable. Si no hay desplegable (PDFS_DISPONIBLES vacío, formulario
    # en modo "subir archivo"), se usa el respaldo de config.py.
    filas_iniciales = {} if PDFS_DISPONIBLES else FILAS_PREDETERMINADAS_SIN_PDF
    return render_template(
        "pdfstamper.html",
        matrix_filas=MATRIX_FILAS,
        filas_predeterminadas=filas_iniciales,
        color_por_defecto=COLOR_POR_DEFECTO,
        pdfs_disponibles=PDFS_DISPONIBLES,
    )


@pdfstamper_bp.route("/pdf_predeterminado")
def pdf_predeterminado():
    nombre = request.args.get("nombre", "")
    entrada = PDFS_DISPONIBLES.get(nombre)
    if not entrada:
        return jsonify({"error": f"No existe el PDF predeterminado '{nombre}'"}), 404
    archivo = entrada.get("archivo", "")

    try:
        pdf_bytes = leer_pdf_predeterminado(archivo)
    except OSError:
        return jsonify({"error": f"No se encontró el archivo del PDF '{nombre}': {archivo}"}), 400

    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", download_name=archivo)


@pdfstamper_bp.route("/pdf_predeterminado/filas")
def pdf_predeterminado_filas():
    """Valores propios (texto/placeholder/fuente/X/Y/tamaño/centrado) del PDF
    predeterminado `nombre`, para rellenar la matriz al elegirlo en el
    desplegable."""
    nombre = request.args.get("nombre", "")
    entrada = PDFS_DISPONIBLES.get(nombre)
    if not entrada:
        return jsonify({"error": f"No existe el PDF predeterminado '{nombre}'"}), 404

    filas_config = entrada.get("filas", {})
    filas = {}
    for i in range(1, MATRIX_FILAS + 1):
        fila = filas_config.get(i, {})
        filas[i] = {
            "texto": fila.get("texto", ""),
            "placeholder": fila.get("placeholder", ""),
            "fuente": fila.get("fuente", ""),
            "x": fila.get("x", 0),
            "y": fila.get("y", 0),
            "tamano": fila.get("tamano", 14),
            "centrado": bool(fila.get("centrado", False)),
        }
    return jsonify({"filas": filas})


@pdfstamper_bp.route("/rejilla", methods=["POST"])
def rejilla():
    if "pdf" not in request.files:
        return jsonify({"error": "Falta el archivo PDF"}), 400

    try:
        pagina = int(request.form.get("pagina", "1")) - 1
    except ValueError:
        return jsonify({"error": "Número de página inválido"}), 400

    pdf_bytes = request.files["pdf"].read()

    puntos = []
    for i in range(1, MATRIX_FILAS + 1):
        texto = request.form.get(f"texto_{i}", "").strip()
        if not texto:
            continue
        try:
            x = float(request.form.get(f"x_{i}", "0"))
            y = float(request.form.get(f"y_{i}", "0"))
        except ValueError:
            continue
        puntos.append({"numero": i, "x": x, "y": y})

    try:
        resultado = generar_rejilla(pdf_bytes, pagina, puntos)
        if request.form.get("solo_pagina"):
            resultado = extraer_pagina(resultado, pagina)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return send_file(
        io.BytesIO(resultado),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="rejilla_calibracion.pdf",
    )


@pdfstamper_bp.route("/generar", methods=["POST"])
def generar():
    if "pdf" not in request.files:
        return jsonify({"error": "Falta el archivo PDF"}), 400

    try:
        pagina = int(request.form.get("pagina", "1")) - 1
    except ValueError:
        return jsonify({"error": "Número de página inválido"}), 400

    color = request.form.get("color", "#000000")
    nombre_pdf_predeterminado = request.form.get("nombre_pdf", "").strip()
    nombre_pdf_subido = request.files["pdf"].filename
    pdf_bytes = request.files["pdf"].read()

    entrada_pdf = PDFS_DISPONIBLES.get(nombre_pdf_predeterminado) if nombre_pdf_predeterminado else None
    filas_predeterminadas_pdf = entrada_pdf.get("filas", {}) if entrada_pdf else FILAS_PREDETERMINADAS_SIN_PDF

    stamps = []
    for i in range(1, MATRIX_FILAS + 1):
        texto = request.form.get(f"texto_{i}", "").strip()
        if not texto:
            continue
        try:
            x = float(request.form.get(f"x_{i}", "0"))
            y = float(request.form.get(f"y_{i}", "0"))
            tamano = float(request.form.get(f"tamano_{i}", "14"))
        except ValueError:
            return jsonify({"error": f"Coordenadas o tamaño inválidos en la fila {i}"}), 400

        fuente_nombre = request.form.get(f"fuente_{i}", "").strip()
        if not fuente_nombre:
            fuente_nombre = filas_predeterminadas_pdf.get(i, {}).get("fuente", "")

        if fuente_nombre:
            try:
                font_bytes = leer_fuente_predeterminada(fuente_nombre)
            except OSError:
                return jsonify({
                    "error": f"No se encontró el archivo de fuente de la fila {i}: {fuente_nombre}"
                }), 400
        else:
            font_bytes = None

        centrado = bool(request.form.get(f"centrado_{i}"))

        stamps.append({
            "texto": texto, "x": x, "y": y, "tamano": tamano,
            "font_bytes": font_bytes, "etiqueta": str(i), "centrado": centrado,
        })

    imagenes_config = entrada_pdf.get("imagenes", IMAGENES_PREDETERMINADAS) if entrada_pdf else IMAGENES_PREDETERMINADAS

    try:
        imagenes = preparar_imagenes(imagenes_config)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not stamps and not imagenes:
        return jsonify({"error": "Agrega texto en al menos una fila de la matriz"}), 400

    try:
        resultado = generar_pdf_con_texto(pdf_bytes, pagina, stamps, color, imagenes)
        if request.form.get("solo_pagina"):
            resultado = extraer_pagina(resultado, pagina)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return send_file(
        io.BytesIO(resultado),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=_nombre_descarga(request.form.get("texto_1", ""), nombre_pdf_subido),
    )
