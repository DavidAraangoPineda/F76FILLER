"""
Configuración editable de PDF Stamper.
Este es el único archivo pensado para que lo edites vos: cantidad de filas
de la matriz, fuente por defecto y coordenadas de cada PDF. La lógica
de generación de PDF vive en pdf_utils.py y no hace falta tocarla.
"""

import copy
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cantidad de filas de la matriz de textos que se muestra en el formulario.
MATRIX_FILAS = 5

# Fuente que se usa cuando una fila no indica ninguna en el campo "Fuente".
# Debe ser un archivo .ttf (o .otf con contornos TrueType, no PostScript)
# que esté en esta misma carpeta, o una ruta absoluta.
FUENTE_POR_DEFECTO = "ITCAvantGardeStd-DemiObl.ttf"

# ── Coordenadas por PDF ──────────────────────────────────────────────────
# Cada PDF de PDFS_DISPONIBLES (más abajo) tiene SU PROPIA matriz de filas:
# al elegirlo en el desplegable del formulario, Texto/Fuente/X/Y/Tamaño/
# Centrado de cada fila se cargan solos con lo que definas acá.
#
# La fila N de un PDF toma sus valores de su dict en PDFS_DISPONIBLES[...]
# ["filas"][N]. Una fila que no aparezca ahí (o un campo que falte dentro de
# ella) usa: texto vacío, X=0, Y=0, tamaño=14, fuente FUENTE_POR_DEFECTO, sin
# centrar. _FILAS_CERTIFICADO_ESTANDAR (justo abajo) ya es un ejemplo real y
# funcional con "texto" cargado en las 5 filas.
#
# "texto" es el valor real que queda cargado en el campo Texto apenas elegís
# ese PDF — se imprime tal cual si no lo tocás. Usalo para lo que no cambia
# de una vez a otra (un texto fijo de la plantilla, una fecha, una fila que
# casi siempre lleva el mismo valor). Si la fila cambia en cada persona/uso
# (nombre, número de documento...), mejor dejar "texto" vacío o no ponerlo.
#
# "placeholder" es un texto guía que aparece atenuado en el campo Texto pero
# NUNCA se imprime en el PDF; sirve para recordar qué va en esa fila sin
# dejar cargado un valor real. Si la fila tiene "texto", el placeholder no se
# ve (el campo ya tiene ese valor). Podés poner "texto" y "placeholder" a la
# vez: el campo arranca con "texto" cargado, y si lo borrás para escribir
# otra cosa, vuelve a mostrar el placeholder como guía.
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
#
# Ejemplo completo de una fila con todo:
#
#   "filas": {
#       1: {"texto": "Nombre:", "x": 50,  "y": 700, "tamano": 16},
#       2: {"placeholder": "Fecha:",  "x": 50,  "y": 670, "tamano": 12},
#       5: {"texto": "Firma",   "x": 300, "y": 100, "tamano": 20,
#           "fuente": "ITC-Avant-Garde-Gothic-LT-Demi-Oblique.ttf",
#           "centrado": True},
#   }

# Varios PDFs comparten el mismo diseño/plantilla y por lo tanto las mismas
# coordenadas de partida. _copia_filas() te da una copia independiente cada
# vez, así que después podés ajustar las de un PDF puntual (por ejemplo,
# solo el de "SATS") sin que eso mueva las de los demás.
kaka=-90
def _copia_filas(filas):
    return copy.deepcopy(filas)

_FILAS_CERTIFICADO_ESTANDAR = {
    1: {"texto": "* * * Edwin Santos Acevedo * * *", "placeholder": "* * * Nombre Apellido * * *",
        "x": 299, "y": 646, "tamano": 36, "fuente": "coronet-mt-bold.ttf", "centrado": True},
    2: {"texto": "*** 08100085201 ***", "placeholder": "*** Número de documento ***",
        "x": 213, "y": 552, "tamano": 9},
    3: {"texto": "* * * Republica Dominicana  22 Feb 1980 * * *", "placeholder": "* * * Nacionalidad    Fecha de nacimiento * * *",
        "x": 238, "y": 521, "tamano": 9},
    4: {"texto": "* * * Dominican * * *", "placeholder": "* * * Nacionalidad (adjetivo) * * *",
        "x": 183, "y": 491, "tamano": 9},
    5: {"texto": "*** PMTS/BFA/24-03-01598 ***", "placeholder": "*** Número de certificado ***",
        "x": 362, "y": 491, "tamano": 9},
}

# Color de texto que aparece precargado en el formulario (se puede cambiar
# igual desde ahí antes de generar el PDF).
COLOR_POR_DEFECTO = "#000000"

# ── PDFs predeterminados ─────────────────────────────────────────────────
# Lista desplegable de PDFs ya guardados en el proyecto, para elegirlos en
# vez de subirlos a mano cada vez. La clave es el nombre que se ve en el
# formulario. El valor es un dict con:
#   archivo  -> el PDF (en esta misma carpeta, o ruta absoluta).
#   filas    -> (opcional) las coordenadas propias de este PDF, con el mismo
#               formato que se explica arriba. Si falta, todas las filas
#               arrancan en X=0, Y=0 (sin calibrar todavía).
#   imagenes -> (opcional) reemplaza, solo para este PDF, la lista global
#               IMAGENES_PREDETERMINADAS de más abajo. Útil si el sello/QR
#               va en otro lugar en este PDF puntual.
#
# Si dejás PDFS_DISPONIBLES vacío ({}), el desplegable no aparece y el
# formulario queda con el botón de "subir archivo" de siempre.
PDFS_DISPONIBLES = {
    "BFA": {
        "archivo": "VACIO BFA.pdf",
        "filas": _copia_filas(_FILAS_CERTIFICADO_ESTANDAR),
    },
    "BFF": {
        "archivo": "VACIO BFF.pdf",
        "filas": _copia_filas(_FILAS_CERTIFICADO_ESTANDAR),
    },
    "BPS": {
        "archivo": "VACIO BPS.pdf",
        "filas": _copia_filas(_FILAS_CERTIFICADO_ESTANDAR),
    },
    "PSSR": {
        "archivo": "VACIO PSSR.pdf",
        "filas": _copia_filas(_FILAS_CERTIFICADO_ESTANDAR),
    },
    "SATS": {
        "archivo": "VACIO SATS.pdf",
        "filas": _copia_filas(_FILAS_CERTIFICADO_ESTANDAR),
    },
    # CMT y CMHBT arrancan con las coordenadas estándar como punto de partida,
    # pero escritas acá mismo (no con _copia_filas) para que sea directo
    # cambiar cada X/Y a mano una vez que calibres este diseño con "Generar
    # rejilla de calibración" — tocar estos números no afecta a ningún otro
    # PDF.
    "CMT": {
        "archivo": "VACOP CMT.pdf",
        "filas": {
                    1: {"texto": "* * * Alexis Nicolas Dominguez * * *", "placeholder": "* * * Nombre Apellido * * *",
                        "x": 308, "y": 568, "tamano": 36, "fuente": "coronet-mt-bold.ttf", "centrado": True},
                    2: {"texto": "*** AAK455790 ***", "placeholder": "*** Número de documento ***",
                        "x": 216.5, "y": 473.2, "tamano": 9},
                    3: {"texto": "* * * El Salvador    31 July 1991 * * *", "placeholder": "* * * Nacionalidad    Fecha de nacimiento * * *",
                        "x": 246, "y": 443, "tamano": 9},
                    4: {"texto": "* * * Argentinian * * *", "placeholder": "* * * Nacionalidad (adjetivo) * * *",
                        "x": 191, "y": 412.5, "tamano": 9},
                    5: {"texto": "*** PMTS/BFA/24-03-01598 ***", "placeholder": "*** Número de certificado ***",
                        "x": 368, "y": 412.5, "tamano": 9},
                },
                "imagenes": [
                 {"archivo": "qr.png", "x": 70, "y": 70, "ancho": 90, "alto": 90},
                                    ],
    },
    

    "CMHBT": {
        "archivo": "VACIO CMHBT.pdf",
        "filas": {
            1: {"texto": "* * * Alexis Nicolas Dominguez * * *", "placeholder": "* * * Nombre Apellido * * *",
                "x": 308, "y": 568, "tamano": 36, "fuente": "coronet-mt-bold.ttf", "centrado": True},
            2: {"texto": "*** AAK455790 ***", "placeholder": "*** Número de documento ***",
                "x": 216, "y": 456, "tamano": 9},
            3: {"texto": "* * * El Salvador    31 July 1991 * * *", "placeholder": "* * * Nacionalidad    Fecha de nacimiento * * *",
                "x": 246, "y": 426, "tamano": 9},
            4: {"texto": "* * * Argentinian * * *", "placeholder": "* * * Nacionalidad (adjetivo) * * *",
                "x": 191, "y": 396, "tamano": 9},
            5: {"texto": "*** PMTS/BFA/24-03-01598 ***", "placeholder": "*** Número de certificado ***",
                "x": 368, "y": 396, "tamano": 9},
        },
        "imagenes": [
         {"archivo": "qr.png", "x": 70, "y": 70, "ancho": 90, "alto": 90},
                            ],
    },
}

# ── Coordenadas por PDF cuando no hay desplegable ───────────────────────────
# Solo se usa si PDFS_DISPONIBLES queda vacío (formulario en modo "subir
# archivo"). Mismo formato que "filas" de cada PDF arriba.
FILAS_PREDETERMINADAS_SIN_PDF = {}

# ── Imagen(es) fijas en cada PDF ─────────────────────────────────────────────
# Se agregan en todos los PDF que generes o descargues, salvo que el PDF
# elegido defina su propia lista "imagenes" en PDFS_DISPONIBLES (ahí manda la
# suya, no esta — como en el ejemplo de "PRUEBA" arriba). Cada elemento de la
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
IMAGENES_PREDETERMINADAS = [
     {"archivo": "qr.png", "x": 60, "y": 145, "ancho": 90, "alto": 90},
]


