"""
Herramientas — Web App
Combina dos proyectos como vistas separadas del mismo servidor Flask:
  - /pdfstamper  → PDF Stamper (rutas en pdfstamper_routes.py)
  - /f76         → F-76 Form Filler (rutas en f76_routes.py)
Este archivo solo arma el Flask app y registra los Blueprints; la lógica de
cada herramienta vive en sus propios archivos.
"""

import os

from flask import Flask, render_template

from pdfstamper_routes import pdfstamper_bp
from f76_routes import f76_bp

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

app.register_blueprint(pdfstamper_bp)
app.register_blueprint(f76_bp)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # debug=True activa el recargador automático: al guardar cualquier .py
    # el servidor se reinicia solo. Este bloque no se ejecuta en producción
    # (Render usa gunicorn vía Procfile), así que es seguro dejarlo prendido.
    app.run(host="0.0.0.0", port=port, debug=True)
