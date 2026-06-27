#!/usr/bin/env node
/**
 * gen_dummy_photos.js
 * Genera imágenes SVG placeholder para cada foto listada en propiedades/*/data.yaml
 * Las guarda en propiedades/<id>/fotos/<nombre>.jpg (como SVG con extensión jpg — los browsers los renderizan igual)
 * Uso: node scripts/gen_dummy_photos.js
 */

const yaml = require("js-yaml");
const fs = require("fs");
const path = require("path");

const PROP_DIR = path.join(__dirname, "../propiedades");

// Paleta por keyword en nombre de foto
const PALETAS = {
  frente:    { bg: "#c9d4dc", accent: "#7a9bb5", label: "Frente" },
  exterior:  { bg: "#c9d4dc", accent: "#7a9bb5", label: "Exterior" },
  living:    { bg: "#e8ddd0", accent: "#b8987a", label: "Living" },
  comedor:   { bg: "#e8ddd0", accent: "#b8987a", label: "Comedor" },
  cocina:    { bg: "#d8e8d0", accent: "#7aaa6e", label: "Cocina" },
  dormitorio:{ bg: "#ddd0e8", accent: "#9a7ab8", label: "Dormitorio" },
  bano:      { bg: "#d0e4e8", accent: "#5a9aaa", label: "Baño" },
  jardin:    { bg: "#c8e0c0", accent: "#5a9040", label: "Jardín" },
  pileta:    { bg: "#b8d8e8", accent: "#3a7fa0", label: "Pileta" },
  terraza:   { bg: "#e0d8c0", accent: "#a09050", label: "Terraza" },
  balcon:    { bg: "#d8e0e8", accent: "#608090", label: "Balcón" },
  garage:    { bg: "#d0d0d0", accent: "#707070", label: "Garage" },
  cochera:   { bg: "#d0d0d0", accent: "#707070", label: "Cochera" },
  entrada:   { bg: "#dcd8d0", accent: "#908070", label: "Entrada" },
};

const DEFAULT_PALETA = { bg: "#d8d4cc", accent: "#887f70", label: "Foto" };

function getPaleta(filename) {
  const base = filename.toLowerCase().replace(/[^a-z]/g, "");
  for (const [key, val] of Object.entries(PALETAS)) {
    if (base.includes(key.replace(/[^a-z]/g, ""))) return val;
  }
  return { ...DEFAULT_PALETA, label: filename.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ") };
}

function makeSVG(titulo, filename, index, total) {
  const { bg, accent, label } = getPaleta(filename);
  // Líneas decorativas estilo plano arquitectónico simplificado
  return `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="560" viewBox="0 0 800 560">
  <rect width="800" height="560" fill="${bg}"/>
  <!-- Grid sutil -->
  <line x1="0" y1="280" x2="800" y2="280" stroke="${accent}" stroke-width="0.5" opacity="0.3"/>
  <line x1="400" y1="0" x2="400" y2="560" stroke="${accent}" stroke-width="0.5" opacity="0.3"/>
  <line x1="0" y1="140" x2="800" y2="140" stroke="${accent}" stroke-width="0.3" opacity="0.2"/>
  <line x1="0" y1="420" x2="800" y2="420" stroke="${accent}" stroke-width="0.3" opacity="0.2"/>
  <line x1="200" y1="0" x2="200" y2="560" stroke="${accent}" stroke-width="0.3" opacity="0.2"/>
  <line x1="600" y1="0" x2="600" y2="560" stroke="${accent}" stroke-width="0.3" opacity="0.2"/>
  <!-- Marco central decorativo -->
  <rect x="120" y="80" width="560" height="400" fill="none" stroke="${accent}" stroke-width="1.5" opacity="0.4" rx="4"/>
  <rect x="140" y="100" width="520" height="360" fill="none" stroke="${accent}" stroke-width="0.5" opacity="0.25" rx="2"/>
  <!-- Icono central (casa simple) -->
  <polygon points="400,180 480,240 480,340 320,340 320,240" fill="none" stroke="${accent}" stroke-width="2" opacity="0.5"/>
  <polygon points="400,160 500,235 300,235" fill="none" stroke="${accent}" stroke-width="2" opacity="0.5"/>
  <rect x="375" y="295" width="50" height="45" fill="${accent}" opacity="0.25"/>
  <!-- Texto -->
  <text x="400" y="390" font-family="system-ui, sans-serif" font-size="22" font-weight="600"
        fill="${accent}" text-anchor="middle" opacity="0.9">${label}</text>
  <text x="400" y="418" font-family="system-ui, sans-serif" font-size="14"
        fill="${accent}" text-anchor="middle" opacity="0.6">${titulo}</text>
  <text x="400" y="444" font-family="system-ui, sans-serif" font-size="12"
        fill="${accent}" text-anchor="middle" opacity="0.45">${index} / ${total} — imagen de ejemplo</text>
</svg>`;
}

let total = 0;
const propDirs = fs.readdirSync(PROP_DIR, { withFileTypes: true })
  .filter(d => d.isDirectory()).map(d => d.name);

for (const dir of propDirs) {
  const dataFile = path.join(PROP_DIR, dir, "data.yaml");
  if (!fs.existsSync(dataFile)) continue;
  const prop = yaml.load(fs.readFileSync(dataFile, "utf8"));
  const fotosDir = path.join(PROP_DIR, dir, "fotos");
  fs.mkdirSync(fotosDir, { recursive: true });

  const fotos = prop.fotos || [];
  fotos.forEach((filename, i) => {
    const dest = path.join(fotosDir, filename);
    // Solo generar si no existe ya una imagen real
    if (fs.existsSync(dest)) {
      const content = fs.readFileSync(dest);
      // Si ya existe y no es SVG dummy, no pisar
      if (!content.toString().includes("imagen de ejemplo")) return;
    }
    const svg = makeSVG(prop.titulo, filename, i + 1, fotos.length);
    fs.writeFileSync(dest, svg);
    console.log(`  ✓ ${dir}/fotos/${filename}`);
    total++;
  });
}

console.log(`\nGeneradas ${total} imágenes dummy. Reemplazalas con fotos reales cuando las tengas.`);
