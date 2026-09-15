const files = { pdf: null };

function setFile(input, key) {
  const file = input.files[0];
  if (!file) return;
  files[key] = file;
  document.getElementById('hint-' + key).textContent = file.name;
  document.getElementById('btn-'  + key).classList.add('selected');
  checkReady();
  programarVistaPrevia();
}

async function seleccionarPdfPredeterminado(select) {
  const nombre = select.value;
  if (!nombre) return;

  try {
    const resp = await fetch('/pdfstamper/pdf_predeterminado?nombre=' + encodeURIComponent(nombre));
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: 'No se pudo cargar el PDF predeterminado.' }));
      alert(err.error || 'No se pudo cargar el PDF predeterminado.');
      select.value = '';
      return;
    }
    const blob = await resp.blob();
    files.pdf = new File([blob], nombre + '.pdf', { type: 'application/pdf' });
    const hint = document.getElementById('hint-pdf');
    if (hint) hint.textContent = nombre;
    const btn = document.getElementById('btn-pdf');
    if (btn) btn.classList.add('selected');
    checkReady();
    programarVistaPrevia();
  } catch (e) {
    alert('Error cargando el PDF predeterminado: ' + e.message);
    select.value = '';
  }
}

function filasConTexto() {
  return Array.from(document.querySelectorAll('.m-texto'))
    .filter(inp => inp.value.trim())
    .map(inp => inp.dataset.row);
}

function checkReady() {
  const pdfListo = !!files.pdf;
  document.getElementById('btn-grid').disabled = !pdfListo;
  document.getElementById('btn-gen').disabled = !(pdfListo && filasConTexto().length > 0);
}

function setStatus(clase, html) {
  const status = document.getElementById('status');
  status.className = 'status ' + clase;
  status.innerHTML = html;
}

function nombreDesdeContentDisposition(resp, nombrePorDefecto) {
  const cd = resp.headers.get('Content-Disposition') || '';
  let m = cd.match(/filename\*=UTF-8''([^;]+)/i);
  if (m) return decodeURIComponent(m[1]);
  m = cd.match(/filename="([^"]+)"/i);
  if (m) return m[1];
  return nombrePorDefecto;
}

async function descargarBlob(resp, nombrePorDefecto) {
  const nombreArchivo = nombreDesdeContentDisposition(resp, nombrePorDefecto);
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const dlBtn = document.getElementById('download-btn');
  dlBtn.href = url;
  dlBtn.download = nombreArchivo;
  dlBtn.style.display = 'block';
}

function agregarFilasAlForm(form, filas, incluirFuentesYTamano) {
  filas.forEach(row => {
    form.append('texto_' + row, document.querySelector(`.m-texto[data-row="${row}"]`).value);
    form.append('x_' + row, document.querySelector(`.m-x[data-row="${row}"]`).value || '0');
    form.append('y_' + row, document.querySelector(`.m-y[data-row="${row}"]`).value || '0');
    if (incluirFuentesYTamano) {
      form.append('tamano_' + row, document.querySelector(`.m-tamano[data-row="${row}"]`).value || '14');
      form.append('fuente_' + row, document.querySelector(`.m-fuente[data-row="${row}"]`).value || '');
      form.append('centrado_' + row, document.querySelector(`.m-centrado[data-row="${row}"]`).checked ? '1' : '');
    }
  });
}

async function generarRejilla() {
  if (!files.pdf) return;
  const btnGrid = document.getElementById('btn-grid');
  const btnGen  = document.getElementById('btn-gen');
  btnGrid.disabled = true;
  btnGen.disabled = true;
  document.getElementById('download-btn').style.display = 'none';
  setStatus('loading', '<span class="spinner"></span> Generando rejilla...');

  const form = new FormData();
  form.append('pdf', files.pdf);
  form.append('pagina', document.getElementById('pagina').value || '1');
  agregarFilasAlForm(form, filasConTexto(), false);

  try {
    const resp = await fetch('/pdfstamper/rejilla', { method: 'POST', body: form });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: 'Error desconocido' }));
      throw new Error(err.error || 'HTTP ' + resp.status);
    }
    await descargarBlob(resp, 'rejilla_calibracion.pdf');
    setStatus('success', '✅ Rejilla descargada. Cada punto de color es una fila de tu matriz.');
  } catch (e) {
    setStatus('error', '❌ ' + e.message);
  }
  checkReady();
}

async function generar() {
  if (!files.pdf) return;
  const filas = filasConTexto();
  if (filas.length === 0) { alert('Escribe texto en al menos una fila de la matriz.'); return; }

  const btnGrid = document.getElementById('btn-grid');
  const btnGen  = document.getElementById('btn-gen');
  btnGrid.disabled = true;
  btnGen.disabled = true;
  document.getElementById('download-btn').style.display = 'none';
  setStatus('loading', '<span class="spinner"></span> Generando PDF...');

  const form = new FormData();
  form.append('pdf', files.pdf);
  form.append('pagina', document.getElementById('pagina').value || '1');
  form.append('color', document.getElementById('color').value || '#000000');
  agregarFilasAlForm(form, filas, true);

  try {
    const resp = await fetch('/pdfstamper/generar', { method: 'POST', body: form });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: 'Error desconocido' }));
      throw new Error(err.error || 'HTTP ' + resp.status);
    }
    await descargarBlob(resp, 'documento_con_texto.pdf');
    setStatus('success', '✅ PDF descargado exitosamente');
  } catch (e) {
    setStatus('error', '❌ ' + e.message);
  }
  checkReady();
}

// ── Vista previa en vivo ─────────────────────────────────────────────────

let vistaActual = 'pdf'; // 'pdf' | 'grid'
let previewUrlActual = null;
let previewDebounce = null;
let previewSeq = 0;

function cambiarVista(vista) {
  vistaActual = vista;
  document.getElementById('tab-pdf').classList.toggle('active', vista === 'pdf');
  document.getElementById('tab-grid').classList.toggle('active', vista === 'grid');
  actualizarVistaPrevia();
}

function programarVistaPrevia() {
  clearTimeout(previewDebounce);
  previewDebounce = setTimeout(actualizarVistaPrevia, 500);
}

async function actualizarVistaPrevia() {
  const frame = document.getElementById('preview-frame');
  const placeholder = document.getElementById('preview-placeholder');
  const filas = filasConTexto();
  const miSeq = ++previewSeq;

  if (!files.pdf || filas.length === 0) {
    frame.style.display = 'none';
    placeholder.style.display = 'flex';
    placeholder.textContent = 'Subí un PDF y escribí texto en alguna fila para ver la vista previa acá. Se actualiza sola con cada cambio.';
    return;
  }

  const form = new FormData();
  form.append('pdf', files.pdf);
  form.append('pagina', document.getElementById('pagina').value || '1');
  form.append('solo_pagina', '1');

  let url;
  if (vistaActual === 'pdf') {
    form.append('color', document.getElementById('color').value || '#000000');
    agregarFilasAlForm(form, filas, true);
    url = '/pdfstamper/generar';
  } else {
    agregarFilasAlForm(form, filas, false);
    url = '/pdfstamper/rejilla';
  }

  placeholder.style.display = 'flex';
  placeholder.textContent = 'Generando vista previa...';

  try {
    const resp = await fetch(url, { method: 'POST', body: form });
    if (miSeq !== previewSeq) return; // llegó una respuesta vieja, hay una más nueva en camino
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: 'Error desconocido' }));
      placeholder.textContent = '❌ ' + (err.error || 'No se pudo generar la vista previa.');
      frame.style.display = 'none';
      return;
    }
    const blob = await resp.blob();
    if (miSeq !== previewSeq) return;
    const nuevaUrl = URL.createObjectURL(blob);
    if (previewUrlActual) URL.revokeObjectURL(previewUrlActual);
    previewUrlActual = nuevaUrl;
    frame.src = nuevaUrl + '#toolbar=0&navpanes=0&view=FitH';
    frame.style.display = 'block';
    placeholder.style.display = 'none';
  } catch (e) {
    if (miSeq !== previewSeq) return;
    placeholder.textContent = '❌ ' + e.message;
    frame.style.display = 'none';
  }
}

document.addEventListener('input', (e) => {
  if (e.target.matches('.m-texto, .m-fuente, .m-x, .m-y, .m-tamano, .m-centrado, #pagina, #color')) {
    checkReady();
    programarVistaPrevia();
  }
});

document.addEventListener('DOMContentLoaded', () => {
  checkReady();
  actualizarVistaPrevia();
});
