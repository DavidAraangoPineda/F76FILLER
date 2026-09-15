"""
Configuración editable de PDF Stamper.
Este es el único archivo pensado para que lo edites vos: cantidad de filas
de la matriz, fuente por defecto y valores precargados por fila. La lógica
de generación de PDF vive en pdf_utils.py y no hace falta tocarla.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cantidad de filas de la matriz de textos que se muestra en el formulario.
MATRIX_FILAS = 5

# Fuente que se usa cuando una fila no indica ninguna en el campo "Fuente".
# Debe ser un archivo .ttf (o .otf con contornos TrueType, no PostScript)
# que esté en esta misma carpeta, o una ruta absoluta.
FUENTE_POR_DEFECTO = "ITCAvantGardeStd-DemiObl.ttf"

# ── Valores predeterminados de la matriz ────────────────────────────────────
# La fila N toma sus valores de FILAS_PREDETERMINADAS[N]. Una fila que no
# aparezca acá (o un campo que falte dentro de ella) usa: texto vacío, X=0,
# Y=0, tamaño=14, fuente FUENTE_POR_DEFECTO, sin centrar. Por ejemplo:
#
#   FILAS_PREDETERMINADAS = {
#       1: {"texto": "Nombre:", "x": 50,  "y": 700, "tamano": 16},
#       2: {"texto": "Fecha:",  "x": 50,  "y": 670, "tamano": 12},
#       5: {"texto": "Firma",   "x": 300, "y": 100, "tamano": 20,
#           "fuente": "ITC-Avant-Garde-Gothic-LT-Demi-Oblique.ttf",
#           "centrado": True},
#   }
#
# "fuente" es el nombre de un archivo .ttf/.otf en esta misma carpeta, o una
# ruta absoluta. Esto es solo el valor por defecto de esa fila: si en el
# formulario escribís otro nombre de archivo en el campo Fuente, ese nombre
# manda por encima de este.
#
# "centrado" (True/False, por defecto False): si es True, X e Y marcan el
# CENTRO del texto — la mitad del texto queda a la izquierda de X y la otra
# mitad a la derecha (ideal para casillas o líneas ya impresas donde tenés
# el punto medio pero no sabés cuánto va a medir el texto). Si es False (o
# no aparece), X e Y son el borde izquierdo, como siempre.
FILAS_PREDETERMINADAS = {
    #    1: {"texto": "* * * Andre Wayne Smit * * *", "x": 299,  "y": 646, "tamano": 36,"fuente": "coronet-mt-bold.ttf","centrado": True},
    #    2: {"texto": "*** A09176885 ***",  "x": 213,  "y": 552, "tamano": 9},
    #    3: {"texto": "* * * South Africa    14 June 1989 * * *",   "x": 238, "y": 521, "tamano": 9},
    #    4: {"texto": "* * * South African * * *",   "x": 183, "y": 491, "tamano": 9},
    #    5: {"texto": "*** PMTS/BFA/24-03-01442 ***",   "x": 362, "y": 491, "tamano": 9},
    #    6: {"texto": "ADADDASDAWWW",   "x": 362, "y": 491, "tamano": 9}
       
       1: {"texto": "* * * Alexis Nicolas Dominguez * * *", "x": 299,  "y": 646, "tamano": 36,"fuente": "coronet-mt-bold.ttf","centrado": True},
       2: {"texto": "*** AAK455790 ***",  "x": 213,  "y": 552, "tamano": 9},
       3: {"texto": "* * * Argentina    20 Sept 2002 * * *",   "x": 238, "y": 521, "tamano": 9},
       4: {"texto": "* * * Argentinian * * *",   "x": 183, "y": 491, "tamano": 9},
       5: {"texto": "*** PMTS/BFA/24-03-01598 ***",   "x": 362, "y": 491, "tamano": 9},
       
       
       
}

# Color de texto que aparece precargado en el formulario (se puede cambiar
# igual desde ahí antes de generar el PDF).
COLOR_POR_DEFECTO = "#000000"

# ── PDFs predeterminados ─────────────────────────────────────────────────
# Lista desplegable de PDFs ya guardados en el proyecto, para elegirlos en
# vez de subirlos a mano cada vez. La clave es el nombre que se ve en el
# formulario; el valor es el archivo (en esta misma carpeta, o ruta
# absoluta). Si la dejás vacía, el desplegable no aparece y el formulario
# queda como antes (solo botón de subir archivo). Por ejemplo:
#
#   PDFS_DISPONIBLES = {
#       "Diploma": "diploma.pdf",
#       "Certificado": "certificado.pdf",
#   }
PDFS_DISPONIBLES = {
    "BFA": "VACIO BFA.pdf",
    "BFF": "VACIO BFF.pdf",
    "BPS": "VACIO BPS.pdf",
    "PSSR": "VACIO PSSR.pdf",
    "SATS": "VACIO SATS.pdf",
    "PRUEBA": "prueba.pdf",

}

# ── Imagen(es) fijas en cada PDF ─────────────────────────────────────────────
# Se agregan SIEMPRE, en todos los PDF que generes o descargues, sin importar
# qué PDF base uses ni qué pongas en la matriz de textos. Cada elemento de la
# lista es un dict con:
#   archivo -> nombre del archivo de imagen (.png/.jpg) en esta misma
#              carpeta, o ruta absoluta.
#   x, y    -> esquina inferior izquierda de la imagen, en puntos (mismo
#              sistema de coordenadas que usás para el texto).
#   ancho, alto -> tamaño en puntos. Opcionales: si dejás uno de los dos,
#              el otro se calcula solo manteniendo la proporción de la
#              imagen; si no ponés ninguno, se usa el tamaño natural de la
#              imagen (1 píxel = 1 punto, casi siempre demasiado grande).
#   pagina  -> en qué página del PDF va (1 = primera). Opcional: si no la
#              ponés, usa la misma página que elegiste en el formulario.
#
# Ejemplo:
#   IMAGENES_PREDETERMINADAS = [
#       {"archivo": "sello.png", "x": 400, "y": 100, "ancho": 120, "alto": 120},
#       {"archivo": "firma.png", "x": 300, "y": 60,  "ancho": 150, "pagina": 1},
#   ]
IMAGENES_PREDETERMINADAS = [
     {"archivo": "qr.png", "x": 60, "y": 145, "ancho": 90, "alto": 90},
]
