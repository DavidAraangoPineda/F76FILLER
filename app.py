"""
F-76 Form Filler — Web App
Flask backend para desplegar en Render.com
"""

import io
import os
import time
import uuid
from flask import Flask, request, send_file, render_template_string, jsonify, abort
from PIL import Image
import requests as req_lib

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

REMOVEBG_API_KEY = os.environ.get("REMOVEBG_API_KEY", "")

# ── Contador de uso ───────────────────────────────────────────────────────────
_api_calls = 0

# ── Caché de PDFs generados (para descarga directa vía URL real) ──────────────
_PDF_CACHE_TTL = 5 * 60  # segundos
_pdf_cache = {}  # token -> (bytes, timestamp)

def _limpiar_pdf_cache():
    ahora = time.time()
    vencidos = [tok for tok, (_, ts) in _pdf_cache.items() if ahora - ts > _PDF_CACHE_TTL]
    for tok in vencidos:
        _pdf_cache.pop(tok, None)

# ── PDF base ──────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PDF_PATH = os.path.join(_BASE_DIR, "F-76_base.pdf")

def obtener_pdf_base() -> bytes:
    if os.path.exists(_PDF_PATH):
        with open(_PDF_PATH, "rb") as f:
            return f.read()
    raise FileNotFoundError("No se encontró F-76_base.pdf en el servidor.")

# ── Procesamiento ─────────────────────────────────────────────────────────────

def quitar_fondo_api(imagen_bytes: bytes, api_key: str) -> bytes:
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

# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>F-76 Form Filler</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

  :root {
    --navy: #0f2040;
    --blue: #1a56db;
    --sky: #e8f0fe;
    --white: #ffffff;
    --gray: #6b7280;
    --light: #f8fafc;
    --border: #dde3ed;
    --success: #16a34a;
    --error: #dc2626;
    --warn: #d97706;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--light);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px 48px;
  }

  header { text-align: center; margin-bottom: 32px; }
  .flag  { font-size: 36px; margin-bottom: 8px; }

  h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 26px;
    color: var(--navy);
    letter-spacing: -0.5px;
  }

  .subtitle { font-size: 13px; color: var(--gray); margin-top: 4px; font-weight: 300; }

  .card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px 24px;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 4px 24px rgba(15,32,64,0.07);
  }

  .field { margin-bottom: 18px; }

  .field label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--navy);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 8px;
  }

  /* Campo API key */
  .api-row {
    display: flex;
    align-items: center;
    gap: 8px;
    border: 1.5px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
    background: var(--light);
    transition: border-color 0.2s;
  }
  .api-row:focus-within { border-color: var(--blue); }
  .api-row input {
    flex: 1;
    border: none;
    background: transparent;
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    color: var(--navy);
    outline: none;
  }
  .api-row button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
    padding: 2px 4px;
    color: var(--gray);
    transition: color 0.2s;
  }
  .api-row button:hover { color: var(--navy); }
  .api-saved {
    font-size: 11px;
    color: var(--success);
    margin-top: 4px;
    display: none;
  }

  .file-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1.5px dashed var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    cursor: pointer;
    transition: all 0.2s;
    background: var(--light);
  }

  .file-btn:active { background: var(--sky); }
  .file-btn .icon  { font-size: 22px; flex-shrink: 0; }
  .file-btn .text  { flex: 1; min-width: 0; }
  .file-btn .label { font-size: 13px; font-weight: 500; color: var(--navy); }
  .file-btn .hint  {
    font-size: 11px; color: var(--gray);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .file-btn.selected { border-color: var(--blue); border-style: solid; background: var(--sky); }
  .file-btn.selected .hint { color: var(--blue); }

  input[type="file"] { display: none; }

  .divider { height: 1px; background: var(--border); margin: 20px 0; }

  .btn-generate {
    width: 100%;
    padding: 15px;
    background: var(--navy);
    color: var(--white);
    font-family: 'DM Sans', sans-serif;
    font-size: 15px;
    font-weight: 600;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    transition: background 0.2s, transform 0.1s;
    letter-spacing: 0.2px;
  }
  .btn-generate:active   { transform: scale(0.98); }
  .btn-generate:disabled { background: #94a3b8; cursor: not-allowed; }

  .status {
    margin-top: 16px;
    padding: 12px 14px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    display: none;
    text-align: center;
  }
  .status.loading { display: block; background: var(--sky);  color: var(--blue);    }
  .status.success { display: block; background: #f0fdf4;     color: var(--success); }
  .status.error   { display: block; background: #fef2f2;     color: var(--error);   }

  .spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid var(--blue);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .download-btn {
    display: block;
    margin-top: 12px;
    padding: 13px;
    background: var(--success);
    color: white;
    text-align: center;
    border-radius: 12px;
    font-weight: 600;
    font-size: 15px;
    text-decoration: none;
    transition: opacity 0.2s;
  }
  .download-btn:active { opacity: 0.85; }

  .footer  { margin-top: 28px; font-size: 11px; color: #94a3b8; text-align: center; }
  .counter { margin-top: 10px; font-size: 12px; color: var(--gray); text-align: center; }
  .counter span { font-weight: 600; color: var(--navy); }
  .counter span.warn { color: var(--warn); }
</style>
</head>
<body>

<header>
  <div class="flag">🇵🇦</div>
  <h1>F-76 Form Filler</h1>
  <p class="subtitle">Autoridad Marítima de Panamá</p>
</header>

<div class="card">

  <!-- API Key -->
  <div class="field">
    <label>🔑 API Key remove.bg</label>
    <div class="api-row">
      <input type="password" id="api-key-input" placeholder="Pega tu API key aquí"
             oninput="onApiKeyChange()">
      <button onclick="toggleApiVis()" title="Mostrar/ocultar">👁️</button>
      <button onclick="guardarApiKey()" title="Guardar">💾</button>
    </div>
    <div class="api-saved" id="api-saved">✅ API key guardada en este dispositivo</div>
  </div>

  <!-- Firma -->
  <div class="field">
    <label>✍️ Imagen de la firma</label>
    <div class="file-btn" id="btn-firma" onclick="document.getElementById('input-firma').click()">
      <span class="icon">🖊️</span>
      <div class="text">
        <div class="label">Seleccionar firma</div>
        <div class="hint" id="hint-firma">JPG, PNG o HEIC</div>
      </div>
    </div>
    <input type="file" id="input-firma" accept="image/*" onchange="setFile(this,'firma')">
  </div>

  <!-- Foto -->
  <div class="field">
    <label>🖼️ Foto del marino</label>
    <div class="file-btn" id="btn-foto" onclick="document.getElementById('input-foto').click()">
      <span class="icon">👤</span>
      <div class="text">
        <div class="label">Seleccionar foto</div>
        <div class="hint" id="hint-foto">JPG, PNG o HEIC</div>
      </div>
    </div>
    <input type="file" id="input-foto" accept="image/*" onchange="setFile(this,'foto')">
  </div>

  <div class="divider"></div>

  <button class="btn-generate" id="btn-gen" onclick="generar()" disabled>
    Generar PDF
  </button>

  <div class="status" id="status"></div>
  <a class="download-btn" id="download-btn" style="display:none">⬇️ Descargar PDF</a>

</div>

<p class="footer">Los archivos se procesan de forma segura y no se almacenan.</p>
<p class="counter">Créditos remove.bg restantes: <span id="api-count">—</span></p>

<script>
const API_KEY_STORAGE = 'removebg_api_key';
const files = { firma: null, foto: null };

// ── Al cargar la página, restaurar API key guardada ──
window.addEventListener('load', () => {
  const saved = localStorage.getItem(API_KEY_STORAGE);
  if (saved) {
    document.getElementById('api-key-input').value = saved;
    document.getElementById('api-saved').style.display = 'block';
  }
  actualizarContador();
  checkReady();
});

function onApiKeyChange() {
  // Si el usuario edita, ocultar el mensaje de "guardada"
  document.getElementById('api-saved').style.display = 'none';
  checkReady();
}

function guardarApiKey() {
  const val = document.getElementById('api-key-input').value.trim();
  if (!val) { alert('Ingresa una API key primero.'); return; }
  localStorage.setItem(API_KEY_STORAGE, val);
  const msg = document.getElementById('api-saved');
  msg.style.display = 'block';
  msg.textContent = '✅ API key guardada en este dispositivo';
}

function toggleApiVis() {
  const inp = document.getElementById('api-key-input');
  inp.type = inp.type === 'password' ? 'text' : 'password';
}

function getApiKey() {
  return document.getElementById('api-key-input').value.trim();
}

// ── Archivos ──
function setFile(input, key) {
  const file = input.files[0];
  if (!file) return;
  files[key] = file;
  document.getElementById('hint-' + key).textContent = file.name;
  document.getElementById('btn-'  + key).classList.add('selected');
  checkReady();
}

function checkReady() {
  document.getElementById('btn-gen').disabled =
    !(files.firma && files.foto && getApiKey());
}

// ── Contador créditos ──
async function actualizarContador() {
  try {
    const r = await fetch('/stats');
    const d = await r.json();
    const el = document.getElementById('api-count');
    if (d.creditos_restantes !== null && d.creditos_restantes !== '?') {
      el.textContent = d.creditos_restantes;
      el.className = d.creditos_restantes < 10 ? 'warn' : '';
    } else {
      el.textContent = '—';
    }
  } catch(_) {}
}

// ── Generar ──
async function generar() {
  const apiKey = getApiKey();
  if (!apiKey) { alert('Ingresa tu API key de remove.bg.'); return; }

  const btn    = document.getElementById('btn-gen');
  const status = document.getElementById('status');
  const dlBtn  = document.getElementById('download-btn');

  btn.disabled = true;
  dlBtn.style.display = 'none';
  status.className = 'status loading';
  status.innerHTML = '<span class="spinner"></span> Procesando... puede tomar ~20 segundos';

  const form = new FormData();
  form.append('firma',   files.firma);
  form.append('foto',    files.foto);
  form.append('api_key', apiKey);

  try {
    const resp = await fetch('/generar', { method: 'POST', body: form });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: 'Error desconocido' }));
      throw new Error(err.error || 'HTTP ' + resp.status);
    }
    const data = await resp.json();

    status.className = 'status success';
    status.textContent = '✅ PDF generado exitosamente';
    actualizarContador();

    dlBtn.href     = '/descargar/' + data.token;
    dlBtn.download = 'F-76_llenado.pdf';
    dlBtn.style.display = 'block';

    // Guardar la key automáticamente si funcionó
    localStorage.setItem(API_KEY_STORAGE, apiKey);
    document.getElementById('api-saved').style.display = 'block';

  } catch(e) {
    status.className = 'status error';
    status.textContent = '❌ ' + e.message;
  }

  btn.disabled = false;
}
</script>
</body>
</html>
"""

# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/generar", methods=["POST"])
def generar():
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

    global _api_calls
    _api_calls += 2

    _limpiar_pdf_cache()
    token = uuid.uuid4().hex
    _pdf_cache[token] = (resultado, time.time())

    return jsonify({"token": token})

@app.route("/descargar/<token>")
def descargar(token):
    entrada = _pdf_cache.get(token)
    if entrada is None:
        abort(404)
    pdf_bytes, _ = entrada
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name="F-76_llenado.pdf",
    )

@app.route("/stats")
def stats():
    api_key = REMOVEBG_API_KEY
    if not api_key:
        return jsonify({"api_calls": _api_calls, "creditos_restantes": None})
    try:
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
