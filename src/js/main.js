/* main.js — filtros del listado e inicialización de Pagefind */

// ---- Pagefind (buscador fulltext) ----
// Se inicializa sólo en la página de inicio donde existe el elemento
window.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('search') && window.PagefindUI) {
    new PagefindUI({
      element: '#search',
      showSubResults: false,
      resetStyles: false,
      translations: {
        placeholder: 'Buscar propiedades...',
        zero_results: 'Sin resultados para "[QUERY]"',
        many_results: '[COUNT] propiedades encontradas',
        one_result: '1 propiedad encontrada',
        alt_search: 'No hay resultados. Intentá con "[DIFFERENT_TERM]"',
        search_label: 'Buscar',
        filters_label: 'Filtros',
      }
    });
  }
});

// ---- Filtros por select ----
(function () {
  const grid = document.getElementById('grid-propiedades');
  const gridVacio = document.getElementById('grid-vacio');
  const contador = document.getElementById('contador');
  if (!grid) return;

  const tarjetas = Array.from(grid.querySelectorAll('.prop-card'));

  function aplicarFiltros() {
    const operacion = document.getElementById('f-operacion')?.value || '';
    const tipo = document.getElementById('f-tipo')?.value || '';
    const ambientesMin = parseInt(document.getElementById('f-ambientes')?.value || '0', 10);

    let visibles = 0;
    tarjetas.forEach(card => {
      const ok =
        (!operacion || card.dataset.operacion === operacion) &&
        (!tipo || card.dataset.tipo === tipo) &&
        (!ambientesMin || parseInt(card.dataset.ambientes, 10) >= ambientesMin);

      card.style.display = ok ? '' : 'none';
      if (ok) visibles++;
    });

    if (gridVacio) gridVacio.classList.toggle('hidden', visibles > 0);
    if (contador) {
      contador.textContent = visibles === tarjetas.length
        ? `${tarjetas.length} propiedades`
        : `${visibles} de ${tarjetas.length} propiedades`;
    }
  }

  ['f-operacion', 'f-tipo', 'f-ambientes'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', aplicarFiltros);
  });

  // Inicializar contador
  aplicarFiltros();
})();

// Exponer limpiarFiltros al scope global (llamado desde el botón HTML)
window.limpiarFiltros = function () {
  ['f-operacion', 'f-tipo', 'f-ambientes'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.querySelectorAll('.prop-card').forEach(c => c.style.display = '');
  document.getElementById('grid-vacio')?.classList.add('hidden');
  const t = document.querySelectorAll('.prop-card').length;
  const c = document.getElementById('contador');
  if (c) c.textContent = `${t} propiedades`;
};
