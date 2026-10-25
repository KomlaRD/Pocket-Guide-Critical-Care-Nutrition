// RC3.0: use the existing Shiny radio input as the single navigation state.
(function () {
  function navigate(page) {
    const radio = document.querySelector('input[name="page"][value="' + page + '"]');
    if (!radio) return;
    radio.click();
    window.scrollTo({top: 0, behavior: 'instant'});
    // Dismiss a mobile off-canvas sidebar after selecting a destination.
    const sidebar = radio.closest('.sidebar, aside');
    const toggle = document.querySelector('.bslib-sidebar-toggle, button[aria-controls*="sidebar"], button[aria-label*="sidebar" i], .sidebar-toggle');
    if (sidebar && toggle && window.matchMedia('(max-width: 767px)').matches) {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      if (expanded) toggle.click();
    }
  }
  function labelMenuToggle() {
    const toggle=document.querySelector('.bslib-sidebar-toggle, button[aria-controls*="sidebar"], .sidebar-toggle');
    if (toggle) {
      toggle.setAttribute('aria-label', 'Open or close navigation menu');
      toggle.setAttribute('title', 'Menu — browse all sections');
      toggle.classList.add('pg-menu-toggle');
    }
  }
  document.addEventListener('DOMContentLoaded', labelMenuToggle);
  document.addEventListener('click', function (event) {
    const link = event.target.closest('[data-page]');
    if (link) { event.preventDefault(); navigate(link.dataset.page); return; }
    if (event.target.closest('#mobile-nav-menu')) {
      const toggle = document.querySelector('.bslib-sidebar-toggle, button[aria-controls*="sidebar"], button[aria-label*="sidebar" i], .sidebar-toggle');
      if (toggle) toggle.click();
    }
  });
  document.addEventListener('change', function (event) {
    if (event.target.matches('input[name="page"]')) {
      document.querySelectorAll('.mobile-nav-item[data-page]').forEach(function (link) {
        if (link.dataset.page === event.target.value) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      });
    }
  });
})();
