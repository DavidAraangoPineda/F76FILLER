const BASE = '/pdfstamper/movil/generar';
let generados = []; // [{doc, nombre, blob}]

function alternarDoc(cb) {
  const wrap = document.getElementById('num-wrap-' + cb.value);
  wrap.hidden = !cb.checked;
  if (cb.checked) document.getElementById('num-' + cb.value).focus();
}

// Lugar de nacimiento: lista o "escribir a mano". El valor final va en el
// input oculto #pais; la nacionalidad se rellena sola (y sigue editable).
function sincronizarPais() {
  const sel = document.getElementById('pais-sel');
  const manual = sel.value === '__manual__';
  document.getElementById('pais').value = manual
    ? document.getElementById('pais-manual').value
    : sel.value;
}

function elegirPais() {
  const sel = document.getElementById('pais-sel');
  const manual = sel.value === '__manual__';
  const campoManual = document.getElementById('pais-manual');
  campoManual.hidden = !manual;
  campoManual.required = manual;
  if (manual) campoManual.focus();
  else document.getElementById('nacionalidad').value = sel.selectedOptions[0].dataset.nac || '';
  sincronizarPais();
}

function setStatus(clase, texto) {
  const s = document.getElementById('status');
  s.className = 'status ' + clase;
  s.textContent = texto;
}

function docsElegidos() {
  return Array.from(document.querySelectorAll('.doc-cb:checked')).map(cb => cb.value);
}

function formData(docs, zip) {
  const fd = new FormData(document.getElementById('form'));
  docs.forEach(d => {
    fd.append('docs', d);
    fd.append('numero_' + d, document.getElementById('num-' + d).value.trim());
  });
  if (zip) fd.append('zip', '1');
  return fd;
}

function validar(docs) {
  if (docs.length === 0) return 'Elegí al menos un documento.';
  for (const d of docs) {
    if (!new RegExp('^[0-9]{' + DIGITOS + '}$').test(document.getElementById('num-' + d).value.trim()))
      return d + ': escribí los ' + DIGITOS + ' números.';
  }
  return null;
}

function nombreArchivo(resp, porDefecto) {
  const cd = resp.headers.get('Content-Disposition') || '';
  let m = cd.match(/filename\*=UTF-8''([^;]+)/i);
  if (m) return decodeURIComponent(m[1]);
  m = cd.match(/filename="([^"]+)"/i);
  return m ? m[1] : porDefecto;
}

async function pedir(docs, zip) {
  const resp = await fetch(BASE, { method: 'POST', body: formData(docs, zip) });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: 'Error desconocido' }));
    throw new Error(err.error || 'HTTP ' + resp.status);
  }
  return { blob: await resp.blob(), nombre: nombreArchivo(resp, zip ? 'documentos.zip' : 'documento.pdf') };
}

function guardar(blob, nombre) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nombre;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

async function generar(ev) {
  ev.preventDefault();
  sincronizarPais();
  const form = document.getElementById('form');
  if (!form.reportValidity()) return false;
  const docs = docsElegidos();
  const error = validar(docs);
  if (error) { setStatus('error', '❌ ' + error); return false; }

  const btn = document.getElementById('btn-gen');
  btn.disabled = true;
  document.getElementById('resultados').hidden = true;
  setStatus('loading', 'Generando ' + docs.length + ' documento(s)...');
  try {
    generados = [];
    for (const d of docs) {
      const { blob, nombre } = await pedir([d], false);
      generados.push({ doc: d, nombre, blob });
    }
    mostrarResultados();
    setStatus('success', '✅ Listo: ' + generados.length + ' documento(s) generados');
  } catch (e) {
    setStatus('error', '❌ ' + e.message);
  }
  btn.disabled = false;
  return false;
}

function mostrarResultados() {
  const lista = document.getElementById('lista');
  lista.innerHTML = '';
  generados.forEach((g) => {
    const fila = document.createElement('div');
    fila.className = 'res';
    const nombre = document.createElement('span');
    nombre.className = 'nombre';
    nombre.textContent = g.doc;
    nombre.title = g.nombre;
    const bajar = document.createElement('a');
    bajar.textContent = '⬇️ PDF';
    bajar.href = '#';
    bajar.onclick = (e) => { e.preventDefault(); guardar(g.blob, g.nombre); };
    fila.append(nombre, bajar);

    const archivo = new File([g.blob], g.nombre, { type: 'application/pdf' });
    if (navigator.canShare && navigator.canShare({ files: [archivo] })) {
      const compartir = document.createElement('button');
      compartir.type = 'button';
      compartir.textContent = '📤';
      compartir.onclick = async () => {
        try { await navigator.share({ files: [archivo] }); }
        catch (e) { if (e.name !== 'AbortError') alert('No se pudo compartir: ' + e.message); }
      };
      fila.append(compartir);
    }
    lista.append(fila);
  });
  document.getElementById('resultados').hidden = false;
}

async function descargarZip() {
  const btn = document.getElementById('btn-zip');
  btn.disabled = true;
  try {
    const { blob, nombre } = await pedir(generados.map(g => g.doc), true);
    guardar(blob, nombre);
  } catch (e) {
    setStatus('error', '❌ ' + e.message);
  }
  btn.disabled = false;
}
