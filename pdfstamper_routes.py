"""
PDF Stamper — vista dentro del proyecto combinado.
Rutas bajo /pdfstamper. Para editar valores por defecto usá config.py; la
lógica de generación de PDF vive en pdf_utils.py; la interfaz en
templates/pdfstamper.html y static/pdfstamper/.
"""

import datetime
import io
import os
import re
import unicodedata
import zipfile

from flask import Blueprint, request, send_file, render_template, jsonify

from config import (
    COLOR_POR_DEFECTO,
    FILAS_PREDETERMINADAS_SIN_PDF,
    IMAGENES_PREDETERMINADAS,
    MATRIX_FILAS,
    MOVIL_CAMPOS,
    MOVIL_DIGITOS_NUMERO,
    MOVIL_EXCLUIR,
    MOVIL_FILA_POR_DOCUMENTO,
    MOVIL_LUGAR_LARGO,
    MOVIL_MESES,
    MOVIL_NUMEROS_EJEMPLO,
    MOVIL_PLANTILLA_POR_DOCUMENTO,
    MOVIL_PLANTILLAS_COMUNES,
    MOVIL_SEPARACION_CORTA,
    MOVIL_SEPARACION_LARGA,
    PAISES,
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


# ── Versión celular ───────────────────────────────────────────────────────────

def _codigo_pdf(nombre: str) -> str:
    return PDFS_DISPONIBLES[nombre].get("codigo", nombre)


def _pdfs_movil() -> dict:
    return {n: e for n, e in PDFS_DISPONIBLES.items() if n not in MOVIL_EXCLUIR}


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)).lower()


def _paises_movil() -> list:
    """[{lugar, nacionalidad}] ordenado alfabéticamente por el nombre que se
    imprime (español si el país lo tiene, inglés si no)."""
    paises = [{"lugar": es or en, "nacionalidad": nac} for en, es, nac in PAISES]
    return sorted(paises, key=lambda p: _sin_acentos(p["lugar"]))


def _formatear_fecha(iso: str) -> str:
    """'1989-06-14' -> '14 June 1989' (meses según MOVIL_MESES)."""
    try:
        fecha = datetime.date.fromisoformat(iso)
    except ValueError:
        raise ValueError("Fecha de nacimiento inválida")
    if fecha > datetime.date.today() or fecha.year < 1900:
        raise ValueError("Fecha de nacimiento fuera de rango")
    return f"{fecha.day} {MOVIL_MESES[fecha.month]} {fecha.year}"


@pdfstamper_bp.route("/movil")
def movil():
    return render_template(
        "pdfstamper_movil.html",
        campos=MOVIL_CAMPOS,
        paises=_paises_movil(),
        hoy=datetime.date.today().isoformat(),
        documentos=[
            {
                "nombre": n,
                "codigo": _codigo_pdf(n),
                "ejemplo": MOVIL_NUMEROS_EJEMPLO.get(n, "0" * MOVIL_DIGITOS_NUMERO),
            }
            for n in _pdfs_movil()
        ],
        digitos=MOVIL_DIGITOS_NUMERO,
    )


def _generar_documento_movil(nombre: str, comunes: dict, numero: str):
    """Genera el PDF `nombre` con los datos comunes y el número de su fila
    propia. Devuelve (nombre_de_archivo, bytes)."""
    entrada = PDFS_DISPONIBLES[nombre]
    filas_config = entrada.get("filas", {})

    espacios = MOVIL_SEPARACION_LARGA if len(comunes["pais"]) > MOVIL_LUGAR_LARGO else MOVIL_SEPARACION_CORTA
    valores = {**comunes, "separacion": " " * espacios}
    textos = {i: plantilla.format(**valores) for i, plantilla in MOVIL_PLANTILLAS_COMUNES.items()}
    textos[MOVIL_FILA_POR_DOCUMENTO] = MOVIL_PLANTILLA_POR_DOCUMENTO.format(
        codigo=_codigo_pdf(nombre), numero=numero
    )

    stamps = []
    for i in range(1, MATRIX_FILAS + 1):
        texto = textos.get(i, "").strip()
        if not texto:
            continue
        fila = filas_config.get(i, {})
        fuente = fila.get("fuente", "")
        stamps.append({
            "texto": texto,
            "x": float(fila.get("x", 0)),
            "y": float(fila.get("y", 0)),
            "tamano": float(fila.get("tamano", 14)),
            "font_bytes": leer_fuente_predeterminada(fuente) if fuente else None,
            "etiqueta": str(i),
            "centrado": bool(fila.get("centrado", False)),
        })

    imagenes = preparar_imagenes(entrada.get("imagenes", IMAGENES_PREDETERMINADAS))
    pdf_bytes = leer_pdf_predeterminado(entrada["archivo"])
    resultado = generar_pdf_con_texto(pdf_bytes, 0, stamps, COLOR_POR_DEFECTO, imagenes)
    return _nombre_descarga(textos.get(1, ""), f"{nombre}.pdf"), resultado


@pdfstamper_bp.route("/movil/generar", methods=["POST"])
def movil_generar():
    """Recibe los datos comunes, los documentos elegidos (`docs`, repetido) y
    `numero_<NOMBRE>` por cada uno. Con `zip=1` devuelve un ZIP con todos; si
    no, exige un solo documento y devuelve ese PDF."""
    comunes = {}
    for id_campo, etiqueta in MOVIL_CAMPOS:
        valor = re.sub(r"\s+", " ", request.form.get(id_campo, "")).strip()
        if not valor:
            return jsonify({"error": f"Falta el campo: {etiqueta}"}), 400
        comunes[id_campo] = valor

    try:
        comunes["fecha_nacimiento"] = _formatear_fecha(comunes["fecha_nacimiento"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    docs = request.form.getlist("docs")
    disponibles = _pdfs_movil()
    if not docs:
        return jsonify({"error": "Elegí al menos un documento"}), 400
    for nombre in docs:
        if nombre not in disponibles:
            return jsonify({"error": f"Documento desconocido: {nombre}"}), 400

    numeros = {}
    for nombre in docs:
        numero = request.form.get(f"numero_{nombre}", "").strip()
        if not (numero.isascii() and numero.isdigit() and len(numero) == MOVIL_DIGITOS_NUMERO):
            return jsonify({
                "error": f"{nombre}: el número debe tener exactamente {MOVIL_DIGITOS_NUMERO} dígitos"
            }), 400
        numeros[nombre] = numero

    es_zip = bool(request.form.get("zip"))
    if not es_zip and len(docs) != 1:
        return jsonify({"error": "Para descargar un PDF suelto elegí un solo documento"}), 400

    try:
        resultados = [_generar_documento_movil(n, comunes, numeros[n]) for n in docs]
    except (OSError, ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400

    if not es_zip:
        nombre_archivo, contenido = resultados[0]
        return send_file(io.BytesIO(contenido), mimetype="application/pdf",
                         as_attachment=True, download_name=nombre_archivo)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre_archivo, contenido in resultados:
            z.writestr(nombre_archivo, contenido)
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name="documentos.zip")
