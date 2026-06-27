#!/usr/bin/env python3
"""
descargar_fotos_alvear.py
Descarga las 22 fotos en tamaño completo de la propiedad
alvear-libertad-barrio-norte y elimina los bordes blancos laterales.

Dependencias:
    pip install Pillow

Uso:
    python3 descargar_fotos_alvear.py
"""

import urllib.request
import os
import time
from PIL import Image
import numpy as np

DEST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "propiedades", "alvear-libertad-barrio-norte"
)
os.makedirs(DEST, exist_ok=True)

REFERER = (
    "https://abgapropiedades.com/propiedades/"
    "marcelo-t-de-alvear-y-libertad-barrio-norte-capital-federal/"
)

FOTOS = [
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador2.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador3.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador4.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador5.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador6.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador7.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador8.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador9.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador10.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador11.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador12.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador13.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador14.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador15.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador16.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador17.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador18.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador19.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador20.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertador21.jpg",
    "https://abgapropiedades.com/wp-content/uploads/2020/03/alvear-y-libertadorxx22.jpg",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": REFERER,
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

WHITE_THRESHOLD = 245  # píxeles con todos los canales > este valor = blanco


def trim_white_borders(img: Image.Image) -> Image.Image:
    """Elimina bordes blancos uniformes en los 4 lados."""
    arr = np.array(img.convert("RGB"))
    is_white_col = np.all(arr > WHITE_THRESHOLD, axis=(0, 2))
    is_white_row = np.all(arr > WHITE_THRESHOLD, axis=(1, 2))

    non_white_cols = np.where(~is_white_col)[0]
    non_white_rows = np.where(~is_white_row)[0]

    if len(non_white_cols) == 0 or len(non_white_rows) == 0:
        return img  # imagen completamente blanca, devolver original

    left   = non_white_cols[0]
    right  = non_white_cols[-1]
    top    = non_white_rows[0]
    bottom = non_white_rows[-1] + 1

    trimmed = img.crop((left, top, right, bottom))
    removed = (left, img.size[0] - right, top, img.size[1] - bottom)
    if any(r > 0 for r in removed):
        print(f"    recortado: izq={removed[0]}px der={removed[1]}px "
              f"arr={removed[2]}px abj={removed[3]}px → {trimmed.size[0]}×{trimmed.size[1]}")
    return trimmed


ok = fail = 0

for url in FOTOS:
    filename = os.path.basename(url)
    dest_path = os.path.join(DEST, filename)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 5000:
        print(f"  ya existe: {filename}")
        ok += 1
        continue

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()

        if len(data) < 2000:
            print(f"  SKIP (respuesta muy chica): {filename}")
            fail += 1
            continue

        # Abrir, recortar bordes, guardar
        from io import BytesIO
        img = Image.open(BytesIO(data))
        img_trimmed = trim_white_borders(img)
        img_trimmed.save(dest_path, "JPEG", quality=92, optimize=True)

        kb_orig = len(data) // 1024
        kb_new  = os.path.getsize(dest_path) // 1024
        print(f"  OK {kb_orig}KB → {kb_new}KB: {filename}")
        ok += 1
        time.sleep(0.4)

    except Exception as e:
        print(f"  FAIL: {filename} — {e}")
        fail += 1

print(f"\nResultado: {ok} descargadas, {fail} fallidas")
print(f"Destino:   {DEST}")
