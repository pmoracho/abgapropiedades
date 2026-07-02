#!/usr/bin/env python3
"""
scrape_propiedad.py
====================
Script genérico para scrapear una propiedad de abgapropiedades.com:
  - Descarga las imágenes en tamaño completo
  - Elimina bordes blancos (incluidos artefactos JPEG en el borde)
  - Genera un data.yaml listo para el sitio Eleventy

Dependencias:
    pip install requests beautifulsoup4 Pillow pyyaml

Uso:
    python3 scrape_propiedad.py <URL>

Ejemplo:
    python3 scrape_propiedad.py \\
        https://abgapropiedades.com/propiedades/marcelo-t-de-alvear-y-libertad-barrio-norte-capital-federal/
"""

import sys
import os
import re
import time
import unicodedata
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np


# ── Configuración ────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
}

IMG_HEADERS = {
    **HEADERS,
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

MIN_BORDER_PX   = 2     # ignorar bordes menores a este ancho (evita falsos positivos)
JPEG_QUALITY    = 92
REQUEST_DELAY   = 0.4   # segundos entre descargas


# ── Helpers generales ─────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80]


def decode_qp(text: str) -> str:
    """
    Decodifica quoted-printable (=XX, =\\n) típico de emails/HTML.

    IMPORTANTE: los caracteres acentuados en UTF-8 ocupan 2-3 bytes
    (p.ej. 'Í' = 0xC3 0x8D = "=C3=8D"). Si se decodifica cada =XX por
    separado, cada byte falla al decodificarse individualmente como UTF-8.
    Por eso agrupamos secuencias consecutivas de =XX y las decodificamos
    como un bloque de bytes.
    """
    text = re.sub(r"=\r?\n", "", text)  # soft line breaks primero

    def repl(m):
        hex_str = m.group(0)
        try:
            byte_vals = bytes.fromhex(hex_str.replace("=", ""))
            return byte_vals.decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return hex_str  # dejar sin tocar si no es decodificable

    return re.sub(r"(?:=[0-9A-Fa-f]{2})+", repl, text)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── Extracción de datos ───────────────────────────────────────────────────────

def fetch_page(url: str) -> BeautifulSoup:
    print(f"  Descargando página: {url}")
    headers = {**HEADERS, "Referer": url}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    html = decode_qp(r.text)
    return BeautifulSoup(html, "html.parser"), html


def extract_images(soup: BeautifulSoup, html: str, base_url: str) -> list[str]:
    """
    Busca URLs de imágenes en tamaño completo (sin sufijo -WxH).
    Estrategia: recolecta todas las URLs de imágenes,
    reconstruye la versión full-size eliminando el sufijo de tamaño,
    y devuelve solo las que son únicas y parecen de la propiedad.
    """
    found = set()
    excluded = set()  # URLs de imágenes de widgets/relacionadas

    # 1. src y data-src de <img>
    # Excluir imágenes en tags con clase woocommerce_thumbnail (propiedades relacionadas)
    for tag in soup.find_all("img"):
        tag_class = " ".join(tag.get("class", []))
        is_woo = "woocommerce_thumbnail" in tag_class or "woocommerce-thumbnail" in tag_class
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            val = tag.get(attr, "")
            if not val:
                continue
            full_url = urljoin(base_url, val)
            # Reconstruir URL sin sufijo de tamaño para trackear la versión full
            full_base = re.sub(r"-\d+x\d+(\.[a-z]+)$", r"\1", full_url, flags=re.I)
            if is_woo:
                excluded.add(full_base)
            else:
                found.add(full_url)

    # 2. srcset
    for tag in soup.find_all(attrs={"srcset": True}):
        for part in tag["srcset"].split(","):
            url_part = part.strip().split()[0]
            found.add(urljoin(base_url, url_part))

    # 3. href de <a> que apunten a imágenes
    for tag in soup.find_all("a", href=True):
        if re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", tag["href"], re.I):
            found.add(urljoin(base_url, tag["href"]))

    # 4. Regex directo sobre HTML crudo (para JS inline, etc.)
    raw_imgs = re.findall(
        r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
        html, re.I
    )
    found.update(raw_imgs)

    # Filtrar por dominio de origen y excluir logos/icons/etc.
    domain = urlparse(base_url).netloc
    relevant = set()
    skip_patterns = re.compile(
        r"/(logo|icon|favicon|thumb-placeholder|loading|spinner|avatar|"
        r"wp-includes|plugins/|themes/[^u])",
        re.I
    )
    for u in found:
        if domain not in u:
            continue
        if skip_patterns.search(u):
            continue
        if "uploads" not in u.lower():
            continue
        full = re.sub(r"-\d+x\d+(\.[a-z]+)$", r"\1", u, flags=re.I)
        # Skip if this image was flagged as a woocommerce widget thumbnail
        if full in excluded:
            continue
        relevant.add(full)

    # Para cada URL con sufijo de tamaño, generar la versión full
    full_versions = set()
    for u in relevant:
        # Quitar sufijo tipo -800x600 o -600x450
        full = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", u)
        full_versions.add(full)

    # Ordenar: primero las que no tienen sufijo de tamaño, luego alfabéticamente
    result = sorted(
        full_versions,
        key=lambda u: (bool(re.search(r"-\d+x\d+\.", u)), u)
    )
    return result


def _title_es(text: str) -> str:
    """Title-case en español: no capitaliza preposiciones/artículos cortos."""
    NO_CAP = {"de", "del", "la", "las", "el", "los", "y", "o", "en", "a", "con"}
    words = text.lower().split()
    return " ".join(
        w if (i > 0 and w in NO_CAP) else w.capitalize()
        for i, w in enumerate(words)
    )


def extract_feature_sections(html: str) -> dict:
    """
    Extrae las 3 secciones de características de la página y las devuelve
    como listas planas de strings. Los ítems con ":" mantienen el formato
    "Clave: Valor" (title-case); los sin ":" se devuelven capitalizados.

    Mapeo de títulos de ABGA → claves del data.yaml:
      CARACTERÍSTICAS INMUEBLE  → caracteristicas_inmueble
      SERVICIOS GENERALES       → servicios_generales
      CARACTERÍSTICAS GENERALES → caracteristicas_generales

    Cualquier sección no reconocida se ignora (evita basura del scraper).
    Devuelve: { "caracteristicas_inmueble": [...], "servicios_generales": [...], ... }
    """
    # Mapeo de nombres de ABGA a claves YAML
    TITULO_MAP = {
        "CARACTERÍSTICAS INMUEBLE":  "caracteristicas_inmueble",
        "CARACTERISTICAS INMUEBLE":  "caracteristicas_inmueble",
        "SERVICIOS GENERALES":       "servicios_generales",
        "CARACTERÍSTICAS GENERALES": "caracteristicas_generales",
        "CARACTERISTICAS GENERALES": "caracteristicas_generales",
    }

    # Claves que ya están representadas en campos estructurados del data.yaml
    # (precio, ambientes, dormitorios, etc.) — se omiten de la sección para
    # evitar duplicarlos en el Resumen
    CLAVES_OMITIR = {
        "PRECIO", "EXPENSAS", "AMBIENTES", "DORMITORIOS",
        "CANTIDAD DE DORMITORIOS", "BAÑOS", "BANOS",
        "SUPERFICIE CUBIERTA", "SUPERFICIE TOTAL",
        "ANTIGÜEDAD", "ANTIGÜEDAD", "COCHERA", "COCHERAS", "PISO",
    }

    result = {}
    pattern = re.compile(
        r'<span style="color:\s*#55afb4">([^<]+)</span></p>\s*<ul>(.*?)</ul>',
        re.S | re.I
    )

    for raw_title, ul_content in pattern.findall(html):
        titulo = clean_text(raw_title).upper().strip()
        clave_yaml = TITULO_MAP.get(titulo)
        if not clave_yaml:
            continue  # ignorar secciones no reconocidas

        li_items = re.findall(r"<li>(.*?)</li>", ul_content, re.S)
        items = []
        for li in li_items:
            text = clean_text(re.sub(r"<[^>]+>", "", li)).strip()
            if not text:
                continue

            # Detectar par "CLAVE: valor"
            m = re.match(r"^([A-ZÁÉÍÓÚÑÜ0-9 /._-]{2,40}):\s*(.+)$", text)
            if m:
                clave  = m.group(1).strip()
                valor  = m.group(2).strip()
                # Omitir claves ya cubiertas por campos estructurados
                clave_norm = clave.upper().strip()
                if clave_norm in CLAVES_OMITIR:
                    continue
                # Guardar como "Clave: Valor" (title-case en la clave)
                items.append(f"{_title_es(clave)}: {valor}")
            else:
                # Ítem simple — capitalizar con _title_es
                items.append(_title_es(text))

        if items:
            result[clave_yaml] = items

    return result


def resolve_maps_shortlink(short_url: str) -> tuple:
    """
    Expande un link corto de Google Maps (goo.gl/maps/... o maps.app.goo.gl/...)
    siguiendo la redirección, y extrae lat/lng de la URL final.
    Devuelve (lat, lng) o (None, None) si no se pudo resolver.
    """
    try:
        r = requests.get(short_url, headers=HEADERS, timeout=15, allow_redirects=True)
        final_url = r.url
        for pattern in [
            r"@(-?\d+\.\d+),(-?\d+\.\d+)",
            r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
            r"q=(-?\d+\.\d+),(-?\d+\.\d+)",
        ]:
            m = re.search(pattern, final_url)
            if m:
                return float(m.group(1)), float(m.group(2))
        # A veces las coords están en el HTML de la página final, no en la URL
        for pattern in [
            r"@(-?\d+\.\d+),(-?\d+\.\d+)",
            r"\"lat\":\s*(-?\d+\.\d+).*?\"lng\":\s*(-?\d+\.\d+)",
        ]:
            m = re.search(pattern, r.text, re.S)
            if m:
                return float(m.group(1)), float(m.group(2))
    except Exception as e:
        print(f"    (no se pudo resolver el link de Maps: {e})")
    return None, None


def extract_property_data(soup: BeautifulSoup, html: str, url: str) -> dict:
    """Extrae metadatos de la propiedad de la página."""
    data = {}
    raw = clean_text(soup.get_text(" "))

    # Título: og:title o h1
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        data["titulo"] = clean_text(og_title["content"].split("|")[0].split("-")[0])
    else:
        h1 = soup.find("h1")
        if h1:
            data["titulo"] = clean_text(h1.get_text())

    # URL canónica / slug
    data["_source_url"] = url
    slug_from_url = url.rstrip("/").split("/")[-1]
    data["id"] = slugify(slug_from_url)

    # Precio y moneda
    price_match = re.search(
        r"(?:PRECIO|Precio)[:\s]*(?P<cur>USD|U\$S|ARS|\$)\s*(?P<val>[\d.,]+)",
        raw, re.I
    )
    if price_match:
        cur = price_match.group("cur").upper()
        data["moneda"] = "USD" if "USD" in cur or "U$S" in cur else "ARS"
        val_str = price_match.group("val").replace(".", "").replace(",", "")
        try:
            data["precio"] = int(val_str)
        except ValueError:
            data["precio"] = val_str

    # Expensas
    exp_match = re.search(r"EXPENSAS[:\s]*\$\s*([\d.,]+)", raw, re.I)
    if exp_match:
        try:
            data["expensas"] = int(exp_match.group(1).replace(".", "").replace(",", ""))
            data["expensas_moneda"] = "ARS"
        except ValueError:
            pass

    # Superficies
    for label, key in [
        (r"SUPERFICIE TOTAL", "superficie_total"),
        (r"SUPERFICIE CUBIERTA", "superficie_cubierta"),
    ]:
        m = re.search(label + r"[:\s]*([\d.,]+)\s*m", raw, re.I)
        if m:
            try:
                data[key] = int(m.group(1).replace(".", "").replace(",", ""))
            except ValueError:
                pass

    # Ambientes / dormitorios / baños
    for label, key in [
        (r"AMBIENTES", "ambientes"),
        (r"DORMITORIOS", "dormitorios"),
        (r"BA[ÑN]OS?", "banos"),
        (r"COCHERAS?", "cochera_count"),
    ]:
        m = re.search(label + r"[:\s]*(\d+)", raw, re.I)
        if m:
            try:
                val = int(m.group(1))
                if key == "cochera_count":
                    data["cochera"] = val > 0
                else:
                    data[key] = val
            except ValueError:
                pass

    # Operación
    op_map = {
        "venta": "venta", "sale": "venta",
        "alquiler": "alquiler", "rent": "alquiler",
        "temporario": "alquiler-temporario", "temporal": "alquiler-temporario",
    }
    for kw, op in op_map.items():
        if kw in raw.lower() or kw in url.lower():
            data["operacion"] = op
            break
    if "operacion" not in data:
        data["operacion"] = "venta"

    # Tipo
    tipo_map = {
        "departamento": "departamento", "depto": "departamento", "piso": "departamento",
        "casa": "casa", "chalet": "casa",
        r"\bph\b": "ph",
        "local": "local", "comercial": "local",
        "terreno": "terreno", "lote": "terreno",
        "oficina": "oficina",
    }
    data["tipo"] = "departamento"  # default
    for kw, tipo in tipo_map.items():
        if re.search(kw, raw.lower()) or re.search(kw, url.lower()):
            data["tipo"] = tipo
            break

    # Ubicación: extraer del texto o de og:description
    # Parse location from raw HTML for cleaner extraction
    ubicacion_html = re.search(
        r"UBICACION[:\s]*</span><b>([^<]+)</b>,\s*([^<]+),\s*([^<]+?)</p>",
        html, re.I
    )
    if ubicacion_html:
        calle   = clean_text(ubicacion_html.group(1))
        barrio  = clean_text(ubicacion_html.group(2))
        partido = clean_text(ubicacion_html.group(3))
        data["direccion"] = f"{calle}, {barrio}, {partido}"
        data["barrio"]    = barrio
        data["partido"]   = partido
    else:
        ubicacion_match = re.search(
            r"UBICACI[OÓ]N[:\s]*([^\n<]{10,120})", raw, re.I
        )
        if ubicacion_match:
            loc = clean_text(ubicacion_match.group(1).split("Inicio")[0])
            parts = [p.strip() for p in re.split(r",\s*", loc)]
            data["direccion"] = loc
            if len(parts) >= 2:
                data["barrio"]  = parts[-2] if len(parts) >= 3 else parts[0]
                data["partido"] = parts[-1]

    # Coordenadas de Google Maps
    for pattern in [
        r"maps\.google\.com/maps\?q=(-?\d+\.\d+),(-?\d+\.\d+)",
        r"@(-?\d+\.\d+),(-?\d+\.\d+)",
        r"\"lat\":\s*(-?\d+\.\d+).*?\"lng\":\s*(-?\d+\.\d+)",
        r"(-3[0-9]\.\d{4,}),\s*(-5[0-9]\.\d{4,})",   # Argentina bounding box
    ]:
        m = re.search(pattern, html, re.S)
        if m:
            try:
                data["lat"] = float(m.group(1))
                data["lng"] = float(m.group(2))
                break
            except (ValueError, IndexError):
                pass

    # Google Maps short link
    gmap = re.search(r"https?://goo\.gl/maps/[^\s\"'<>]+", html)
    if gmap and "lat" not in data:
        data["_maps_url"] = gmap.group(0)
        # Intentar resolver el shortlink a coordenadas reales
        lat, lng = resolve_maps_shortlink(data["_maps_url"])
        if lat is not None:
            data["lat"] = lat
            data["lng"] = lng
            print(f"    ✓ Coordenadas resueltas desde shortlink: {lat}, {lng}")

    # Secciones de características/servicios/instalaciones (genérico)
    data["_secciones"] = extract_feature_sections(html)

    # Descripción: bloque de texto largo después de "DESCRIPCIÓN"
    desc_match = re.search(
        r"DESCRIPCI[OÓ]N\s*([A-ZÁÉÍÓÚÑ][^<]{200,3000}?)(?=ENVIANOS|MANDANOS|CONTACT|$)",
        raw, re.I | re.S
    )
    if desc_match:
        desc = clean_text(desc_match.group(1))
        # Limpiar ruido al final
        desc = re.split(r"(ENVIANOS|MANDANOS|Email|Teléfono)", desc)[0].strip()
        data["descripcion"] = desc

    # 1. Campo WooCommerce (más confiable)
    sku_tag = soup.find("span", class_="sku")
    if sku_tag:
        data["sku"] = clean_text(sku_tag.get_text())

    # 2. Fallback: patrón en texto
    if "sku" not in data:
        m = re.search(r'\bSKU:\s*([A-Z0-9][A-Z0-9_-]{1,20})', raw, re.I)
        if m:
            data["sku"] = m.group(1).strip()

    return data


def build_yaml(prop: dict, fotos: list[str], prop_dir: str) -> dict:
    """Arma el dict final para el data.yaml."""
    foto_names = [os.path.basename(f) for f in fotos]

    doc = {
        "id":         prop.get("id", "propiedad-sin-id"),
        "titulo":     prop.get("titulo", "Sin título"),
        "titulo_en":  "",   # completar manualmente
        "operacion":  prop.get("operacion", "venta"),
        "tipo":       prop.get("tipo", "departamento"),
        "destacada":  False,
        "estado":     "activa",
    }

    if "precio" in prop:
        doc["precio"] = prop["precio"]
        doc["moneda"] = prop.get("moneda", "USD")

    if "expensas" in prop:
        doc["expensas"] = prop["expensas"]
        doc["expensas_moneda"] = prop.get("expensas_moneda", "ARS")

    for k in ("barrio", "partido", "direccion"):
        if k in prop:
            doc[k] = prop[k]

    for k in ("lat", "lng"):
        if k in prop:
            doc[k] = prop[k]

    if "_maps_url" in prop and "lat" not in prop:
        doc["_maps_url_pendiente"] = prop["_maps_url"]

    for k in ("ambientes", "dormitorios", "banos", "superficie_cubierta",
              "superficie_total", "cochera"):
        if k in prop:
            doc[k] = prop[k]

    if "descripcion" in prop:
        doc["descripcion"] = prop["descripcion"]
        doc["descripcion_en"] = ""   # completar manualmente

    # Secciones como listas planas (nueva estructura)
    secciones = prop.get("_secciones", {})
    for clave in ("caracteristicas_inmueble", "servicios_generales", "caracteristicas_generales"):
        if clave in secciones and secciones[clave]:
            doc[clave] = secciones[clave]

    if foto_names:
        doc["fotos"]        = foto_names
        doc["foto_portada"] = foto_names[0]

    if "sku" in prop:
        doc["sku"] = prop["sku"]

    return doc


# ── Procesamiento de imágenes ─────────────────────────────────────────────────

def trim_white_borders(img: Image.Image) -> tuple[Image.Image, dict]:
    """
    Elimina bordes uniformes y claros (blancos, cremas, grises claros).

    Algoritmo de varianza+brillo:
      Una columna/fila es "borde" si:
        (a) varianza < VAR_THRESH  → color uniforme (no es contenido)
        (b) mean     >= MEAN_THRESH → es claro (descarta marcos oscuros)

    Esto captura tanto blancos puros (255) como artefactos JPEG (~250)
    y franjas de paredes/marcos claros sin afectar contenido oscuro.
    """
    arr = np.array(img.convert("RGB")).astype(np.float32)
    H, W = arr.shape[:2]

    VAR_THRESH  = 80   # varianza máxima para considerar columna/fila uniforme
    MEAN_THRESH = 200  # brillo mínimo (evita recortar marcos oscuros)

    def is_border_col(c):
        col = arr[:, c, :]
        return col.var() < VAR_THRESH and col.mean() >= MEAN_THRESH

    def is_border_row(r):
        row = arr[r, :, :]
        return row.var() < VAR_THRESH and row.mean() >= MEAN_THRESH

    left = 0
    while left < W and is_border_col(left):
        left += 1

    right = W - 1
    while right > left and is_border_col(right):
        right -= 1
    right += 1

    top = 0
    while top < H and is_border_row(top):
        top += 1

    bottom = H - 1
    while bottom > top and is_border_row(bottom):
        bottom -= 1
    bottom += 1

    removed = {
        "left":   left,
        "right":  W - right,
        "top":    top,
        "bottom": H - bottom,
    }

    if any(v >= MIN_BORDER_PX for v in removed.values()):
        img = img.crop((left, top, right, bottom))

    return img, removed


def download_and_trim(url: str, dest_path: str, referer: str) -> bool:
    """Descarga una imagen, recorta bordes blancos y guarda."""
    headers = {**IMG_HEADERS, "Referer": referer}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200 or len(r.content) < 2000:
            print(f"    ✗ HTTP {r.status_code}, {len(r.content)} bytes")
            return False

        img = Image.open(BytesIO(r.content))
        orig_size = img.size
        img_rgb = img.convert("RGB")
        trimmed, removed = trim_white_borders(img_rgb)

        trimmed.save(dest_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

        trim_info = ", ".join(f"{k}={v}px" for k, v in removed.items() if v >= MIN_BORDER_PX)
        size_info = f"{orig_size[0]}×{orig_size[1]} → {trimmed.size[0]}×{trimmed.size[1]}"
        print(f"    ✓ {size_info}" + (f" [{trim_info}]" if trim_info else ""))
        return True

    except Exception as e:
        print(f"    ✗ {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scrape_propiedad.py <URL>")
        print("Ej:  python3 scrape_propiedad.py https://abgapropiedades.com/propiedades/mi-propiedad/")
        sys.exit(1)

    url = sys.argv[1].rstrip("/") + "/"
    domain = urlparse(url).netloc

    print(f"\n{'='*60}")
    print(f"  scrape_propiedad.py")
    print(f"  URL: {url}")
    print(f"{'='*60}\n")

    # 1. Descargar y parsear página
    print("[ 1/4 ] Descargando página...")
    try:
        soup, html = fetch_page(url)
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # 2. Extraer datos
    print("[ 2/4 ] Extrayendo datos de la propiedad...")
    prop = extract_property_data(soup, html, url)
    prop_id = prop.get("id", slugify(prop.get("titulo", "propiedad")))
    print(f"  ID:      {prop_id}")
    print(f"  Título:  {prop.get('titulo', '—')}")
    print(f"  Precio:  {prop.get('moneda','')} {prop.get('precio','—')}")
    print(f"  Tipo:    {prop.get('tipo','—')} / {prop.get('operacion','—')}")
    print(f"  Loc:     {prop.get('direccion','—')}")
    if "lat" in prop:
        print(f"  Coords:  {prop['lat']}, {prop['lng']}")
    elif "_maps_url" in prop:
        print(f"  Maps URL: {prop['_maps_url']} (no se pudo resolver automáticamente)")

    secciones = prop.get("_secciones", {})
    if secciones:
        print(f"  Secciones encontradas: {', '.join(secciones.keys())}")

    # 3. Encontrar imágenes
    print("\n[ 3/4 ] Buscando imágenes...")
    img_urls = extract_images(soup, html, url)
    print(f"  {len(img_urls)} imágenes encontradas")

    # Crear directorio de destino
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dest_dir = os.path.join(script_dir, "propiedades", prop_id)
    os.makedirs(dest_dir, exist_ok=True)

    # 4. Descargar y recortar
    print(f"\n[ 4/4 ] Descargando y recortando bordes blancos → {dest_dir}/")
    downloaded = []
    for img_url in img_urls:
        filename = os.path.basename(urlparse(img_url).path)
        dest_path = os.path.join(dest_dir, filename)

        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 2000:
            print(f"  → {filename} (ya existe)")
            downloaded.append(img_url)
            continue

        print(f"  → {filename}")
        ok = download_and_trim(img_url, dest_path, referer=url)
        if ok:
            downloaded.append(img_url)
        time.sleep(REQUEST_DELAY)

    print(f"\n  Descargadas: {len(downloaded)}/{len(img_urls)}")

    # 5. Generar data.yaml
    yaml_data = build_yaml(prop, downloaded, dest_dir)
    yaml_path = os.path.join(dest_dir, "data.yaml")

    # Representar strings multilínea con literal block scalar (|)
    class LiteralStr(str):
        pass

    def literal_representer(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(LiteralStr, literal_representer)
    yaml.add_representer(str, literal_representer)

    if "descripcion" in yaml_data:
        yaml_data["descripcion"] = LiteralStr(yaml_data["descripcion"])

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False,
                  sort_keys=False, width=80)

    print(f"\n{'='*60}")
    print(f"  ✓ data.yaml generado: {yaml_path}")
    print(f"  ✓ {len(downloaded)} imágenes en: {dest_dir}/")
    print(f"\n  Próximos pasos:")
    print(f"    1. Revisá {yaml_path} y completá:")
    print(f"       - titulo_en, descripcion_en, comodidades / comodidades_en")
    if "_maps_url_pendiente" in yaml_data:
        print(f"       - lat/lng (abrí {yaml_data['_maps_url_pendiente']})")
    print(f"    2. Corré: npm run build")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()