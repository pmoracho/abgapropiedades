# Inmobiliaria Estática — Eleventy

Sitio de propiedades inmobiliarias 100% estático, generado con [Eleventy (11ty)](https://www.11ty.dev/).
Ultrarrápido, SEO-friendly, cero base de datos.

---

## Estructura del proyecto

```
├── _data/
│   ├── propiedades.yaml   ← TUS PROPIEDADES (editar aquí)
│   └── site.yaml          ← config global: nombre, colores, contacto
├── photos/
│   └── casa-olivos-001/   ← fotos de cada propiedad (carpeta = id)
│       ├── frente.jpg
│       └── ...
├── src/
│   ├── _layouts/          ← layout base HTML
│   ├── _includes/         ← header, footer, card de propiedad
│   ├── propiedades/       ← template de ficha individual
│   ├── css/main.css
│   ├── js/main.js
│   ├── index.njk          ← listado + buscador
│   └── contacto.njk
├── .eleventy.js
├── netlify.toml
└── package.json
```

---

## Cómo administrar propiedades

### Opción A — editar el YAML directamente

Abrí `_data/propiedades.yaml` en cualquier editor y agregá/editá entradas.
Cada propiedad es un bloque que empieza con `- id:`.

### Opción B — desde Excel o CSV

1. Usá la plantilla `propiedades-plantilla.xlsx` (o `propiedades-plantilla.csv`).
2. Completá una fila por propiedad.
3. Exportá como CSV y convertí a YAML con:
   ```bash
   python3 scripts/csv_to_yaml.py propiedades.csv > _data/propiedades.yaml
   ```

### Agregar fotos

Creá una carpeta en `photos/` con el mismo nombre que el `id` de la propiedad:

```
photos/
└── casa-olivos-001/
    ├── frente.jpg       ← foto de portada (referenciada en foto_portada)
    ├── living.jpg
    └── jardin.jpg
```

Las imágenes se recomiendan en formato JPEG, ancho 1200–1600px, optimizadas (< 300KB).

---

## Desarrollo local

```bash
# Instalar dependencias (primera vez)
npm install

# Servidor de desarrollo con hot reload
npm start
# → http://localhost:8080

# Build completo (con índice de búsqueda Pagefind)
npm run build:search
```

---

## Deploy en Netlify

1. Subí el proyecto a GitHub.
2. En [Netlify](https://netlify.com): **Add new site → Import from Git**.
3. Build command: `npm run build:search`
4. Publish directory: `_site`
5. ¡Listo! Cada push al repo actualiza el sitio automáticamente.

### Formulario de contacto

- Si usás **Netlify Forms**: reemplazá el `action` del form con `netlify` y agregá el atributo `netlify` al `<form>`. Los mensajes llegan a tu panel de Netlify.
- Si usás **Formspree**: creá una cuenta en [formspree.io](https://formspree.io), copiá tu Form ID y reemplazá `TU_FORM_ID` en los templates.

---

## Personalización

### Colores y nombre del sitio

Editá `_data/site.yaml`:

```yaml
nombre: "Tu Inmobiliaria"
colores:
  primario: "#1a3a5c"   ← color principal (header, botones)
  acento: "#c8a96e"     ← color de acento (dorado, verde, etc.)
```

### Tipografías

Las fuentes se definen en `src/_layouts/base.njk` (Google Fonts) y en `src/css/main.css`.
Actualmente usa `DM Serif Display` para títulos e `Inter` para cuerpo de texto.

---

## Buscador Pagefind

Pagefind indexa todo el contenido HTML al momento del build y genera un motor de búsqueda
en el cliente en ~8KB de JS. No requiere servidor ni API.

Después de correr `npm run build:search`, el índice queda en `_site/pagefind/`.

---

## Checklist de SEO

- [x] `<title>` y `<meta description>` únicos por página
- [x] Open Graph tags (og:title, og:image, og:description)
- [x] `<link rel="canonical">`
- [x] `lang="es"` en el HTML
- [x] Imágenes con `alt` descriptivo
- [x] `loading="lazy"` en imágenes secundarias
- [x] URLs limpias (`/propiedades/casa-olivos-001/`)
- [ ] Agregar `sitemap.xml` (plugin `@11ty/eleventy-plugin-sitemap`)
- [ ] Agregar `robots.txt`
- [ ] Schema.org RealEstateListing (opcional pero recomendado)
