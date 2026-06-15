# F-76 Form Filler — Web App

## Archivos necesarios en el repositorio
- `app.py`
- `requirements.txt`
- `Procfile`
- `F-76_base.pdf` ← el formulario vacío, súbelo también

## Pasos para desplegar (una sola vez)

### 1. Obtener API key de remove.bg
- Ve a https://www.remove.bg/es/dashboard#api-key
- Crea cuenta gratis → copia tu API Key

### 2. Subir a GitHub
- github.com → New repository → nombre `f76-filler`
- Sube los 4 archivos: `app.py`, `requirements.txt`, `Procfile`, `README.md`, `F-76_base.pdf`

### 3. Desplegar en Render
- render.com → New → Web Service → conecta `f76-filler`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Instance Type: **Free**
- En **Environment Variables** agrega:
  - Key: `REMOVEBG_API_KEY`
  - Value: tu API key

### 4. ¡Listo!
Render te da una URL tipo https://f76filler.onrender.com
Ábrela desde cualquier dispositivo.

## Notas
- remove.bg da 50 usos gratis/mes (cada formulario usa 2: firma + foto = 25 formularios)
- Los archivos NO se almacenan en el servidor
- El servidor free de Render se "duerme" tras 15 min sin uso → primera carga puede tardar ~30s
