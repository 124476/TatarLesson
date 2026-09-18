// static_dev/js/toast.js
(function () {
  'use strict';

  window.showToast = function (message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `app-toast app-toast-${type}`;

    const icon = type === 'success' ? 'check-circle-fill'
               : type === 'error' ? 'x-circle-fill'
               : 'info-circle-fill';

    toast.innerHTML = `<i class="bi bi-${icon}"></i><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  };

  window.getCookie = function (name) {
    for (let c of document.cookie.split(';')) {
      c = c.trim();
      if (c.startsWith(name + '=')) return decodeURIComponent(c.slice(name.length + 1));
    }
    return '';
  };
})();