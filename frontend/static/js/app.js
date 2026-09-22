(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('app', function () {
      return {
        open: false,
        loading: false,
        error: null
      };
    });
  });

  //ცენტრალური toast: `window.dispatchEvent(new CustomEvent('bina:toast', { detail: { message, type } }))`
  document.addEventListener('DOMContentLoaded', function () {
    const region = document.getElementById('toast-region');
    if (!region) return;

    const TYPE_CLASS = {
      success: 'border-[var(--secondary)] text-[var(--secondary)]',
      error: 'border-[var(--danger)] text-[var(--danger)]',
      info: 'border-[var(--border)] text-[var(--text-primary)]'
    };

    window.addEventListener('bina:toast', function (event) {
      const detail = event.detail || {};
      const message = String(detail.message || '');
      if (!message) return;
      const type = TYPE_CLASS[detail.type] ? detail.type : 'info';

      const toast = document.createElement('div');
      toast.setAttribute('role', 'status');
      toast.className = 'pointer-events-auto mb-2 rounded-[var(--radius-md)] border bg-[var(--surface)] px-4 py-3 text-sm font-medium shadow-[var(--shadow-lg)] ' + TYPE_CLASS[type];
      toast.textContent = message;

      region.appendChild(toast);
      window.setTimeout(function () {
        toast.remove();
      }, 3000);
    });
  });
}());
