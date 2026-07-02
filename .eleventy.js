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
    if (price === undefined || price === null || price === "" || isNaN(Number(price))) {
      return null; // el template decide qué mostrar (ej. "Consultar"/"Ask")
    }
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

  // ================================================================
  // TRADUCCIONES DE SECCIONES
  // ================================================================
  //
  // Diccionario central para traducir los ítems de las 3 secciones.
  // Formato de cada entrada: "texto en español" → "text in english"
  //
  // Los ítems son strings del tipo "Clave: Valor" o "Chip simple".
  // La traducción busca primero el string completo; si no lo encuentra,
  // busca solo la parte de la clave (antes del ":"), y traduce
  // la parte del valor por separado.
  //
  // Para agregar una traducción nueva: agregar una línea al diccionario.
  // Si un ítem no tiene traducción, se muestra en español — sin romper nada.

  const TRADUCCIONES_SECCION = {
    // ---- Características del Inmueble — claves ----
    "Aire Acondicionado":          "Air conditioning",
    "Alarma":                      "Alarm system",
    "Balcón":                      "Balcony",
    "Baulera":                     "Storage room",
    "Calefacción":                 "Heating",
    "Cocina":                      "Kitchen",
    "Comedor":                     "Dining room",
    "Comedor de Diario":           "Breakfast room",
    "Dependencia de Servicio":     "Staff quarters",
    "Disposición":                 "Position",
    "Dormitorio en Suite":         "En-suite bedroom",
    "Escritorio":                  "Study",
    "Gas Natural":                 "Natural gas",
    "Gimnasio":                    "Gym",
    "Hall":                        "Entrance hall",
    "Internet":                    "Internet",
    "Lavadero":                    "Laundry room",
    "Living":                      "Living room",
    "Living Comedor":              "Living/dining room",
    "Luminosidad":                 "Natural light",
    "Master Suite":                "Master suite",
    "Orientación":                 "Orientation",
    "Portones Automaticos":        "Automatic gates",
    "Seguridad Perimetral":        "Perimeter security",
    "Teléfono":                    "Telephone",
    "Terraza":                     "Terrace",
    "Toilette":                    "Powder room",
    "Vestidor":                    "Walk-in closet",
    "Video Cable":                 "Cable TV",
    "Vigilancia":                  "Security",
    "Vigilancia/Encargado":        "Security/Concierge",
    // ---- Características Generales — claves ----
    "Cantidad de Ascensores":      "Elevators",
    "Categoria del Edificio":      "Building category",
    "Estado del Edificio":         "Building condition",
    "Estado del Inmueble":         "Property condition",
    "Tipo de Edificio":            "Building type",
    // ---- Valores comunes ----
    "sí":                          "Yes",
    "Sí":                          "Yes",
    "no":                          "No",
    "No":                          "No",
    "Excelente":                   "Excellent",
    "Muy luminoso":                "Very bright",
    "Muy luminosa":                "Very bright",
    "Primera categoría":           "First class",
    "Torre":                       "Tower",
    "Frente":                      "Front facing",
    "Contrafrente":                "Rear facing",
    "Lateral":                     "Side facing",
    "Amplio Living":               "Spacious living room",
    "Living Intimo":               "Intimate living room",
    "Altillo":                     "Loft",
    "Pileta Climatizada":          "Heated pool",
    "Pileta":                      "Pool",
    "Parrilla":                    "Barbecue",
    "Vestuarios":                  "Changing rooms",
    "Terraza Amplia":              "Large terrace",
    "Estado del Inmueble: A estrenar": "Property condition: Brand new",
  };

  // Filtra las claves que el Resumen ya muestra como campos estructurados
  // (se omiten de caracteristicas_inmueble para no duplicarlas)
  const CLAVES_OMITIR_RESUMEN = new Set([
    "precio", "expensas", "ambientes", "dormitorios",
    "cantidad de dormitorios", "baños", "banos",
    "superficie cubierta", "superficie total",
    "antigüedad", "antiguedad", "cochera", "cocheras", "piso",
  ]);

  /**
   * Traduce un array de ítems de sección al idioma indicado.
   * Cada ítem puede ser "Clave: Valor" o "Chip simple".
   * Si no hay traducción, devuelve el string original.
   */
  eleventyConfig.addFilter("traducirSeccion", (items, lang) => {
    if (!items || !Array.isArray(items)) return [];
    if (lang !== "en") return items;

    return items.map(item => {
      // Traducción directa del string completo
      if (TRADUCCIONES_SECCION[item]) return TRADUCCIONES_SECCION[item];

      // Para ítems "Clave: Valor", traducir clave y valor por separado
      const colonIdx = item.indexOf(":");
      if (colonIdx > -1) {
        const clave = item.slice(0, colonIdx).trim();
        const valor = item.slice(colonIdx + 1).trim();
        const claveEN = TRADUCCIONES_SECCION[clave] || clave;
        const valorEN = TRADUCCIONES_SECCION[valor] || valor;
        return `${claveEN}: ${valorEN}`;
      }

      return item; // sin traducción conocida → devolver en español
    });
  });

  /**
   * Filtra de caracteristicas_inmueble los ítems cuya clave
   * ya está representada en el Resumen (ambientes, dormitorios, etc.)
   */
  eleventyConfig.addFilter("sinDuplicadosResumen", (items) => {
    if (!items || !Array.isArray(items)) return [];
    return items.filter(item => {
      const colonIdx = item.indexOf(":");
      if (colonIdx === -1) return true; // chip simple → siempre incluir
      const clave = item.slice(0, colonIdx).trim().toLowerCase();
      return !CLAVES_OMITIR_RESUMEN.has(clave);
    });
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
