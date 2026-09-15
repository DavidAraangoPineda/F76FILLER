"""
F-76 Form Filler — vista dentro del proyecto combinado.
Rutas bajo /f76. La lógica de procesamiento vive en f76_utils.py; la
interfaz en templates/f76.html y static/f76/.
"""

import io
import os

from flask import Blueprint, request, send_file, render_template, jsonify

from f76_utils import generar_pdf, obtener_pdf_base

f76_bp = Blueprint("f76", __name__, url_prefix="/f76")

REMOVEBG_API_KEY = os.environ.get("REMOVEBG_API_KEY", "")

# ── Contador de uso ───────────────────────────────────────────────────────────
_api_calls = 0


@f76_bp.route("/")
def index():
    return render_template("f76.html")


@f76_bp.route("/generar", methods=["POST"])
def generar():
    global _api_calls

    # La API key puede venir del env o del cliente
    api_key = request.form.get("api_key", "").strip() or REMOVEBG_API_KEY
    if not api_key:
        return jsonify({"error": "Falta la API key de remove.bg"}), 400

    if not all(k in request.files for k in ["firma", "foto"]):
        return jsonify({"error": "Faltan archivos (firma, foto)"}), 400

    try:
        pdf_bytes = obtener_pdf_base()
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    firma_bytes = request.files["firma"].read()
    foto_bytes  = request.files["foto"].read()

    try:
        resultado = generar_pdf(pdf_bytes, firma_bytes, foto_bytes, api_key)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    _api_calls += 2

    return send_file(
        io.BytesIO(resultado),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="F-76_llenado.pdf",
    )


@f76_bp.route("/stats")
def stats():
    api_key = REMOVEBG_API_KEY
    if not api_key:
        return jsonify({"api_calls": _api_calls, "creditos_restantes": None})
    try:
        import requests as req_lib

        r = req_lib.get(
            "https://api.remove.bg/v1.0/account",
            headers={"X-Api-Key": api_key},
            timeout=10,
        )
        data = r.json()
        attrs    = data.get("data", {}).get("attributes", {})
        creditos = attrs.get("credits", {})
        # remove.bg usa subscription + payg, no "total"
        sub       = creditos.get("subscription", 0) or 0
        payg      = creditos.get("payg", 0) or 0
        restantes = sub + payg
    except Exception:
        restantes = "?"
    return jsonify({"api_calls": _api_calls, "creditos_restantes": restantes})
