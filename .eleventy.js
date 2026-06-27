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
