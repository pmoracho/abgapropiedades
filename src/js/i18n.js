/**
 * i18n.js — Traducción client-side para ES/EN
 *
 * Estrategia:
 * 1. Lee strings desde el JSON embebido en la página (inyectado por Eleventy)
 * 2. Detecta idioma preferido: localStorage → navigator.language → 'es'
 * 3. Aplica traducciones a todos los [data-i18n] del DOM
 * 4. Expone window.setLang() para el selector manual
 */

(function () {
  const STORAGE_KEY = "lang";
  const SUPPORTED = ["es", "en"];

  // --- Carga de strings ---
  let i18nData = {};
  try {
    const el = document.getElementById("i18n-data");
    if (el) i18nData = JSON.parse(el.textContent);
  } catch (e) {
    console.warn("[i18n] No se pudo parsear i18n-data", e);
  }

  function t(lang, key) {
    return (i18nData[lang] && i18nData[lang][key]) || (i18nData["es"] && i18nData["es"][key]) || key;
  }

  // --- Detección de idioma ---
  function detectLang() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED.includes(stored)) return stored;

    const nav = (navigator.language || navigator.userLanguage || "es").toLowerCase();
    // Español: es, es-ar, es-mx, etc.
    if (nav.startsWith("es")) return "es";
    // Inglés: en, en-us, en-gb, etc.
    if (nav.startsWith("en")) return "en";
    return "es";
  }

  // --- Aplicar idioma al DOM ---
  function applyLang(lang) {
    document.documentElement.setAttribute("lang", lang);
    localStorage.setItem(STORAGE_KEY, lang);

    // Actualizar botones del selector
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("lang-btn--active", btn.dataset.lang === lang);
    });

    // Traducir elementos con data-i18n (textContent)
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      const val = t(lang, key);
      if (val && val !== key) el.textContent = val;
    });

    // Traducir placeholders con data-i18n-placeholder
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.dataset.i18nPlaceholder;
      const val = t(lang, key);
      if (val && val !== key) el.placeholder = val;
    });

    // Títulos de propiedades con data-titulo-es / data-titulo-en
    document.querySelectorAll("[data-titulo-es]").forEach((el) => {
      const val = lang === "en" ? el.dataset.tituloEn : el.dataset.tituloEs;
      if (val) el.textContent = val;
    });

    // Detalles extra del Resumen (clave/valor del scraper sin campo
    // estructurado propio): data-clave-es/en + data-valor-es/en
    document.querySelectorAll(".resumen-detalles-extra .detalle-item").forEach((el) => {
      const dt = el.querySelector("dt");
      const dd = el.querySelector("dd");
      const clave = lang === "en" ? el.dataset.claveEn : el.dataset.claveEs;
      const valor = lang === "en" ? el.dataset.valorEn : el.dataset.valorEs;
      if (dt && clave) dt.textContent = clave;
      if (dd && valor) dd.textContent = valor;
    });

    // Tagline del sitio (hero, footer) con data-tagline-es / data-tagline-en
    document.querySelectorAll("[data-tagline-es]").forEach((el) => {
      const val = lang === "en" ? el.dataset.taglineEn : el.dataset.taglineEs;
      if (val) el.textContent = val;
    });

    // Descripciones con data-desc-es / data-desc-en
    document.querySelectorAll("[data-desc-es]").forEach((el) => {
      const val = lang === "en" ? el.dataset.descEn : el.dataset.descEs;
      if (val) el.textContent = val;
    });

    // Comodidades con data-comodidades-es / data-comodidades-en
    document.querySelectorAll("[data-comodidades-es]").forEach((ul) => {      try {
        const list = JSON.parse(
          lang === "en" ? ul.dataset.comodidadesEn : ul.dataset.comodidadesEs
        );
        if (Array.isArray(list)) {
          ul.innerHTML = list.map((item) => `<li>${item}</li>`).join("");
        }
      } catch (_) {}
    });

    // Actualizar el link de Google Maps con texto traducido
    document.querySelectorAll(".mapa-abrir").forEach((a) => {
      a.textContent =
        lang === "en" ? "Open in Google Maps ↗" : "Abrir en Google Maps ↗";
    });

    // Disparar evento para que main.js pueda reaccionar si necesita
    document.dispatchEvent(new CustomEvent("langchange", { detail: { lang } }));
  }

  // --- API pública ---
  window.setLang = function (lang) {
    if (!SUPPORTED.includes(lang)) return;
    applyLang(lang);
  };

  window.getLang = function () {
    return localStorage.getItem(STORAGE_KEY) || detectLang();
  };

  // --- Init: aplicar al cargar ---
  const initialLang = detectLang();
  // Aplicar inmediatamente (antes del DOMContentLoaded para evitar flash)
  // Usamos DOMContentLoaded porque el script se carga en <head>-end
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => applyLang(initialLang));
  } else {
    applyLang(initialLang);
  }
})();
