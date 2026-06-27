#!/usr/bin/env python3
"""
csv_to_yaml.py — Convierte un CSV de propiedades a formato YAML para _data/propiedades.yaml

Uso:
    python3 scripts/csv_to_yaml.py propiedades.csv > _data/propiedades.yaml

Columnas esperadas en el CSV (todas opcionales excepto id, titulo, operacion, tipo, precio, moneda):
  id, titulo, operacion, tipo, precio, moneda, destacada, barrio, partido, direccion,
  lat, lng, ambientes, dormitorios, banos, cochera, superficie_cubierta, superficie_total,
  antiguedad, piso, comodidades (separadas por |), descripcion, fotos (separadas por |),
  foto_portada, estado
"""

import csv, sys, yaml

def parse_bool(val):
    return val.strip().lower() in ('true', 'si', 'sí', '1', 'yes')

def parse_int(val):
    try: return int(val)
    except: return None

def parse_float(val):
    try: return float(val)
    except: return None

def csv_to_propiedades(filepath):
    propiedades = []
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('id', '').strip():
                continue
            p = {}
            # Campos de texto
            for campo in ['id', 'titulo', 'operacion', 'tipo', 'moneda', 'barrio',
                          'partido', 'direccion', 'foto_portada', 'estado', 'descripcion']:
                v = row.get(campo, '').strip()
                if v: p[campo] = v

            # Campos numéricos
            for campo in ['precio', 'ambientes', 'dormitorios', 'banos',
                          'superficie_cubierta', 'superficie_total', 'antiguedad', 'piso']:
                v = parse_int(row.get(campo, ''))
                if v is not None: p[campo] = v

            for campo in ['lat', 'lng']:
                v = parse_float(row.get(campo, ''))
                if v is not None: p[campo] = v

            # Booleanos
            for campo in ['destacada', 'cochera']:
                raw = row.get(campo, '').strip()
                if raw: p[campo] = parse_bool(raw)

            # Listas separadas por |
            for campo in ['comodidades', 'fotos']:
                raw = row.get(campo, '').strip()
                if raw: p[campo] = [x.strip() for x in raw.split('|') if x.strip()]

            propiedades.append(p)
    return propiedades

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/csv_to_yaml.py propiedades.csv", file=sys.stderr)
        sys.exit(1)

    propiedades = csv_to_propiedades(sys.argv[1])
    print(yaml.dump(propiedades, allow_unicode=True, default_flow_style=False, sort_keys=False))
