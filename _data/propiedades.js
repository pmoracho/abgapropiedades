// _data/propiedades.js
// Lee automáticamente todos los archivos propiedades/*/data.yaml
// Al agregar una nueva carpeta con su data.yaml, aparece sola en el sitio.

const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

module.exports = function () {
  const base = path.join(__dirname, "..", "propiedades");

  if (!fs.existsSync(base)) return [];

  return fs
    .readdirSync(base)
    .filter((entry) => {
      const dataFile = path.join(base, entry, "data.yaml");
      return fs.statSync(path.join(base, entry)).isDirectory() && fs.existsSync(dataFile);
    })
    .map((entry) => {
      const raw = fs.readFileSync(path.join(base, entry, "data.yaml"), "utf8");
      return yaml.load(raw);
    })
    .filter((p) => p && p.id); // descartar entradas rotas
};
