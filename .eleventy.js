const yaml = require("js-yaml");
const fs = require("fs");
const path = require("path");

// Convierte _data/*.yaml a JSON (excepto los leídos por JS loaders)
function syncYamlToJson(dataDir) {
  const skip = new Set(["propiedades"]);
  fs.readdirSync(dataDir)
    .filter(f => f.endsWith(".yaml"))
    .forEach(file => {
      const name = path.basename(file, ".yaml");
      if (skip.has(name)) return;
      const data = yaml.load(fs.readFileSync(path.join(dataDir, file), "utf8"));
      fs.writeFileSync(
        path.join(dataDir, file.replace(".yaml", ".json")),
        JSON.stringify(data, null, 2)
      );
    });
}
syncYamlToJson(path.join(__dirname, "_data"));

module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/css");
  eleventyConfig.addPassthroughCopy("src/js");
  eleventyConfig.addPassthroughCopy("src/img");
  // Copiar el directorio unificado de propiedades (data.yaml ignorado, solo fotos)
  eleventyConfig.addPassthroughCopy({ "propiedades": "propiedades" });

  // ---- Filtros ----
  eleventyConfig.addFilter("formatPrice", (price, currency) => {
    const symbol = currency === "USD" ? "USD " : "$ ";
    return symbol + Number(price).toLocaleString("es-AR");
  });

  eleventyConfig.addFilter("operacionLabel", (op, lang) => {
    const labels = {
      es: { venta: "En venta", alquiler: "En alquiler", "alquiler-temporario": "Alq. temporario" },
      en: { venta: "For sale", alquiler: "For rent", "alquiler-temporario": "Short-term" },
    };
    return (labels[lang] || labels.es)[op] || op;
  });

  eleventyConfig.addFilter("tipoLabel", (tipo, lang) => {
    const labels = {
      es: { casa: "Casa", departamento: "Dpto.", ph: "PH", local: "Local", terreno: "Terreno", oficina: "Oficina" },
      en: { casa: "House", departamento: "Apt.", ph: "PH", local: "Commercial", terreno: "Land", oficina: "Office" },
    };
    return (labels[lang] || labels.es)[tipo] || tipo;
  });

  // ---- Resumen dinámico de la ficha de propiedad ----
  //
  // Combina campos estructurados (prop.precio, prop.ambientes, etc.) con
  // cualquier dato extra que venga en secciones["CARACTERÍSTICAS INMUEBLE"]
  // del scraper, SIN duplicar lo que ya está cubierto por un campo
  // estructurado. Las claves del scraper vienen en mayúsculas con acentos
  // (p.ej. "ORIENTACIÓN", "DEPENDENCIA DE SERVICIO") — se normalizan para
  // poder filtrarlas contra el set de claves ya cubiertas.

  function normalizeKey(str) {
    return str
      .toUpperCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // quitar acentos
      .trim();
  }

  // Claves del scraper que ya están representadas por un campo estructurado
  // (precio, expensas, ambientes, dormitorios, baños, m² cubiertos/totales,
  // antigüedad). Si el scraper trae alguna de estas, se descarta para no
  // duplicar el dato en el Resumen.
  const CLAVES_CUBIERTAS = new Set([
    "PRECIO", "EXPENSAS",
    "AMBIENTES",
    "DORMITORIOS", "CANTIDAD DE DORMITORIOS",
    "BANOS", "BAÑOS",
    "SUPERFICIE CUBIERTA", "SUPERFICIE TOTAL",
    "ANTIGUEDAD", "ANTIGÜEDAD",
    "COCHERA", "COCHERAS",
    "PISO",
  ]);

  // Traducciones EN para claves del scraper que no tienen campo estructurado
  // propio. Si una clave nueva aparece y no está acá, se muestra tal cual
  // viene (en español) — agregar la traducción aquí cuando se detecte.
  const TRADUCCION_CLAVE_EN = {
    "ORIENTACIÓN": "Orientation",
    "DISPOSICIÓN": "Position",
    "LUMINOSIDAD": "Natural light",
    "MASTER SUITE": "Master suite",
    "VESTIDOR": "Walk-in closet",
    "HALL": "Entrance hall",
    "LIVING COMEDOR": "Living/dining room",
    "ESCRITORIO": "Study",
    "TOILETTE": "Powder room",
    "COCINA": "Kitchen",
    "COMEDOR DE DIARIO": "Breakfast room",
    "DEPENDENCIA DE SERVICIO": "Staff quarters",
    "LAVADERO": "Laundry room",
    "DORMITORIO EN SUITE": "En-suite bedroom",
    "CATEGORIA DEL EDIFICIO": "Building category",
    "TIPO DE EDIFICIO": "Building type",
    "ESTADO DEL EDIFICIO": "Building condition",
  };

  const TRADUCCION_VALOR_EN = {
    "sí": "Yes", "si": "Yes", "no": "No",
    "frente": "Front", "contrafrente": "Back", "lateral": "Side",
    "excelente": "Excellent", "muy luminosa": "Very bright",
    "muy luminoso": "Very bright", "primera categoría": "First class",
  };

function toTitleCase(str) {
    // Nota: \b en JS no reconoce bien los límites alrededor de vocales
    // acentuadas (ej. "ORIENTACIÓN" → "OrientacióN" con \b\w). Separamos
    // por espacios y capitalizamos cada palabra completa en su lugar.
    return str
      .toLowerCase()
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }

  eleventyConfig.addFilter("resumenExtra", (prop) => {
    const secciones = prop.secciones || {};
    // Buscar la sección de características del inmueble por nombre conocido
    const caract = secciones["CARACTERÍSTICAS INMUEBLE"] || secciones["CARACTERISTICAS INMUEBLE"];
    if (!caract || !caract.detalles) return [];

    const cubiertas = new Set([...CLAVES_CUBIERTAS]);
    const extra = [];
    for (const [claveOriginal, valor] of Object.entries(caract.detalles)) {
      const normalizada = normalizeKey(claveOriginal);
      if (cubiertas.has(normalizada)) continue;
      extra.push({
        clave: toTitleCase(claveOriginal),
        clave_en: TRADUCCION_CLAVE_EN[claveOriginal] || toTitleCase(claveOriginal),
        valor: valor,
        valor_en: TRADUCCION_VALOR_EN[String(valor).toLowerCase()] || valor,
      });
    }
    return extra;
  });

  return {
    dir: {
      input: "src",
      output: "_site",
      data: "../_data",
      includes: "_includes",
      layouts: "_layouts",
    },
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
  };
};
