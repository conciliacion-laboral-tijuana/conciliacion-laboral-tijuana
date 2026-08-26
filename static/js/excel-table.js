/**
 * ExcelTable — Excel-like interactivity for HTML tables.
 *
 * Usage: new ExcelTable(document.querySelector('table.excel-table'))
 *
 * Features:
 *   - Sort columns (click header)
 *   - Copy cell on click (with toast)
 *   - Search/filter rows
 *   - Row selection (click)
 *   - Column resize (drag header border)
 *   - CSV export
 */
(function () {
  'use strict';

  // ─── Toast helper ────────────────────────────────────────────────────
  function showToast(msg, duration) {
    duration = duration || 2000;
    var t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText =
      'position:fixed;bottom:16px;right:16px;z-index:99999;background:#1e2530;color:#fff;' +
      'padding:8px 14px;border-radius:4px;font-size:12px;box-shadow:0 4px 12px rgba(0,0,0,.25);' +
      'opacity:0;transition:opacity .2s';
    document.body.appendChild(t);
    requestAnimationFrame(function () { t.style.opacity = '1'; });
    setTimeout(function () {
      t.style.opacity = '0';
      setTimeout(function () { t.remove(); }, 200);
    }, duration);
  }

  // ─── CSV helper ──────────────────────────────────────────────────────
  function tableToCSV(table) {
    var rows = [];
    table.querySelectorAll('tr').forEach(function (tr) {
      var cells = [];
      tr.querySelectorAll('th, td').forEach(function (c) {
        var txt = c.textContent.trim().replace(/"/g, '""');
        cells.push('"' + txt + '"');
      });
      rows.push(cells.join(','));
    });
    return rows.join('\n');
  }

  function downloadCSV(csv, filename) {
    var blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename || 'tabla.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  // ─── ExcelTable class ────────────────────────────────────────────────
  function ExcelTable(tableEl) {
    this.table = tableEl;
    this.sortState = {};        // colIndex → 'asc' | 'desc'
    this.selectedRows = new Set();
    this._init();
  }

  ExcelTable.prototype._init = function () {
    this._addToolbar();
    this._enableSort();
    this._enableCopy();
    this._enableSelection();
    this._enableResize();
  };

  // ─── Toolbar: search + CSV export ────────────────────────────────────
  ExcelTable.prototype._addToolbar = function () {
    var self = this;
    var wrapper = this.table.closest('.excel-scroll') || this.table.parentElement;

    var bar = document.createElement('div');
    bar.className = 'excel-toolbar';
    bar.style.cssText =
      'display:flex;align-items:center;gap:8px;padding:4px 8px;border-bottom:1px solid #e8eaed;background:#f8f9fa;';

    // Search input
    var search = document.createElement('input');
    search.type = 'text';
    search.placeholder = '\uD83D\uDD0D Buscar...';
    search.className = 'excel-search';
    search.style.cssText =
      'flex:1;min-width:120px;max-width:260px;padding:3px 8px;font-size:11px;' +
      'border:1px solid #d0d7e0;border-radius:3px;outline:none;';
    search.addEventListener('input', function () { self._filterRows(this.value); });
    bar.appendChild(search);

    // Selected count
    var count = document.createElement('span');
    count.className = 'excel-selected-count';
    count.style.cssText = 'font-size:10px;color:#6b7280;min-width:60px;';
    bar.appendChild(count);
    this._countEl = count;

    // CSV export button
    var csvBtn = document.createElement('button');
    csvBtn.textContent = '\u2B07 CSV';
    csvBtn.title = 'Exportar tabla a CSV';
    csvBtn.style.cssText =
      'padding:3px 8px;font-size:10px;font-weight:600;border:1px solid #b0b5bd;' +
      'border-radius:3px;background:#fff;color:#36404f;cursor:pointer;white-space:nowrap;';
    csvBtn.addEventListener('click', function () {
      var name = (self.table.id || 'tabla') + '.csv';
      downloadCSV(tableToCSV(self.table), name);
      showToast('CSV descargado: ' + name);
    });
    bar.appendChild(csvBtn);

    // Insert before the table inside the scroll wrapper
    if (wrapper.firstChild) {
      wrapper.insertBefore(bar, wrapper.firstChild);
    } else {
      wrapper.prepend(bar);
    }
    this._toolbar = bar;
    this._searchInput = search;
  };

  // ─── Sort ────────────────────────────────────────────────────────────
  ExcelTable.prototype._enableSort = function () {
    var self = this;
    var headers = this.table.querySelectorAll('thead th');
    headers.forEach(function (th, idx) {
      th.style.cursor = 'pointer';
      th.style.userSelect = 'none';
      th.style.position = 'relative';

      // Arrow indicator
      var arrow = document.createElement('span');
      arrow.className = 'sort-arrow';
      arrow.style.cssText = 'margin-left:4px;font-size:9px;color:#9ca3af;';
      th.appendChild(arrow);

      th.addEventListener('click', function (e) {
        // Don't sort if clicking resize handle
        if (e.target.classList.contains('resize-handle')) return;
        self._sortByColumn(idx);
      });
    });
  };

  ExcelTable.prototype._sortByColumn = function (colIdx) {
    var dir = this.sortState[colIdx] === 'asc' ? 'desc' : 'asc';
    this.sortState = {};
    this.sortState[colIdx] = dir;

    var tbody = this.table.querySelector('tbody');
    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));

    // Detect if values are numeric
    var sampleText = rows.length > 0 ? rows[0].children[colIdx]?.textContent.trim() : '';
    var isNumeric = /^[\$\-]?[\d.,]+$/.test(sampleText);

    rows.sort(function (a, b) {
      var av = a.children[colIdx]?.textContent.trim() || '';
      var bv = b.children[colIdx]?.textContent.trim() || '';

      if (isNumeric) {
        av = parseFloat(av.replace(/[\$,%]/g, '').replace(/\./g, '').replace(',', '.')) || 0;
        bv = parseFloat(bv.replace(/[\$,%]/g, '').replace(/\./g, '').replace(',', '.')) || 0;
        return dir === 'asc' ? av - bv : bv - av;
      }
      av = av.toLowerCase();
      bv = bv.toLowerCase();
      if (av < bv) return dir === 'asc' ? -1 : 1;
      if (av > bv) return dir === 'asc' ? 1 : -1;
      return 0;
    });

    rows.forEach(function (r) { tbody.appendChild(r); });

    // Update arrows
    this.table.querySelectorAll('thead th .sort-arrow').forEach(function (el, i) {
      el.textContent = i === colIdx ? (dir === 'asc' ? '\u25B2' : '\u25BC') : '';
    });
  };

  // ─── Copy on click ───────────────────────────────────────────────────
  ExcelTable.prototype._enableCopy = function () {
    var self = this;
    this.table.addEventListener('click', function (e) {
      var td = e.target.closest('td');
      if (!td) return;
      // Don't copy if it's a link
      if (e.target.closest('a')) return;

      var text = td.textContent.trim();
      if (navigator.clipboard && text) {
        navigator.clipboard.writeText(text).then(function () {
          showToast('\u2705 Copiado: ' + (text.length > 40 ? text.substring(0, 40) + '...' : text));
        });
      }

      // Flash effect
      td.style.transition = 'background .15s';
      td.style.background = '#dbeafe';
      setTimeout(function () { td.style.background = ''; }, 300);
    });
  };

  // ─── Row selection ───────────────────────────────────────────────────
  ExcelTable.prototype._enableSelection = function () {
    var self = this;
    this.table.querySelector('tbody').addEventListener('click', function (e) {
      var tr = e.target.closest('tr');
      if (!tr) return;

      // Ctrl/Cmd+click for multi, plain click for single
      if (e.ctrlKey || e.metaKey) {
        if (self.selectedRows.has(tr)) {
          self.selectedRows.delete(tr);
          tr.classList.remove('excel-selected');
        } else {
          self.selectedRows.add(tr);
          tr.classList.add('excel-selected');
        }
      } else {
        self.selectedRows.forEach(function (r) { r.classList.remove('excel-selected'); });
        self.selectedRows.clear();
        self.selectedRows.add(tr);
        tr.classList.add('excel-selected');
      }
      self._updateCount();
    });
  };

  ExcelTable.prototype._updateCount = function () {
    var n = this.selectedRows.size;
    this._countEl.textContent = n > 0 ? n + ' seleccionada' + (n > 1 ? 's' : '') : '';
  };

  // ─── Column resize ───────────────────────────────────────────────────
  ExcelTable.prototype._enableResize = function () {
    var self = this;
    var headers = this.table.querySelectorAll('thead th');

    headers.forEach(function (th, idx) {
      var handle = document.createElement('div');
      handle.className = 'resize-handle';
      handle.style.cssText =
        'position:absolute;right:0;top:0;bottom:0;width:5px;cursor:col-resize;' +
        'background:transparent;z-index:2;';
      handle.addEventListener('mouseover', function () { handle.style.background = '#47505e'; });
      handle.addEventListener('mouseout', function () { handle.style.background = 'transparent'; });
      th.appendChild(handle);
      th.style.position = 'relative';

      var startX, startW;
      handle.addEventListener('mousedown', function (e) {
        e.preventDefault();
        e.stopPropagation();
        startX = e.clientX;
        startW = th.offsetWidth;

        function onMove(ev) {
          var w = Math.max(40, startW + ev.clientX - startX);
          th.style.width = w + 'px';
          th.style.minWidth = w + 'px';
          th.style.maxWidth = w + 'px';
        }
        function onUp() {
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
          document.body.style.cursor = '';
        }
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        document.body.style.cursor = 'col-resize';
      });
    });
  };

  // ─── Search/filter rows ─────────────────────────────────────────────
  ExcelTable.prototype._filterRows = function (query) {
    var q = query.toLowerCase().trim();
    var rows = this.table.querySelectorAll('tbody tr');
    rows.forEach(function (tr) {
      if (!q) {
        tr.style.display = '';
        return;
      }
      var text = tr.textContent.toLowerCase();
      tr.style.display = text.indexOf(q) === -1 ? 'none' : '';
    });
  };

  // ─── Auto-init all .excel-table elements ─────────────────────────────
  function initAll() {
    document.querySelectorAll('table.excel-table').forEach(function (t) {
      if (t._excelInit) return;
      t._excelInit = true;
      new ExcelTable(t);
    });
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  // Expose for manual init
  window.ExcelTable = ExcelTable;
})();
