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
    const r = await fetch('/f76/stats');
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
let pdfFile = null;

async function generar() {
  const apiKey = getApiKey();
  if (!apiKey) { alert('Ingresa tu API key de remove.bg.'); return; }

  const btn      = document.getElementById('btn-gen');
  const status   = document.getElementById('status');
  const dlBtn    = document.getElementById('download-btn');
  const shareBtn = document.getElementById('share-btn');

  btn.disabled = true;
  dlBtn.style.display = 'none';
  shareBtn.style.display = 'none';
  status.className = 'status loading';
  status.innerHTML = '<span class="spinner"></span> Procesando... puede tomar ~20 segundos';

  const form = new FormData();
  form.append('firma',   files.firma);
  form.append('foto',    files.foto);
  form.append('api_key', apiKey);

  try {
    const resp = await fetch('/f76/generar', { method: 'POST', body: form });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: 'Error desconocido' }));
      throw new Error(err.error || 'HTTP ' + resp.status);
    }
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    pdfFile = new File([blob], 'F-76_llenado.pdf', { type: 'application/pdf' });

    status.className = 'status success';
    status.textContent = '✅ PDF generado exitosamente';
    actualizarContador();

    dlBtn.href     = url;
    dlBtn.download = 'F-76_llenado.pdf';
    dlBtn.style.display = 'block';

    if (navigator.canShare && navigator.canShare({ files: [pdfFile] })) {
      shareBtn.style.display = 'block';
    }

    // Guardar la key automáticamente si funcionó
    localStorage.setItem(API_KEY_STORAGE, apiKey);
    document.getElementById('api-saved').style.display = 'block';

  } catch(e) {
    status.className = 'status error';
    status.textContent = '❌ ' + e.message;
  }

  btn.disabled = false;
}

// ── Compartir (sin adjuntar ningún link, solo el archivo) ──
async function compartirPdf() {
  if (!pdfFile) return;
  try {
    await navigator.share({ files: [pdfFile] });
  } catch (e) {
    if (e.name !== 'AbortError') alert('No se pudo compartir: ' + e.message);
  }
}
