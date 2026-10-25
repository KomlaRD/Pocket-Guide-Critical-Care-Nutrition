// RC3.0: use the existing Shiny radio input as the single navigation state.
(function () {
  const mobileQuery = window.matchMedia('(max-width: 767px)');
  function menuSidebar() {
    return document.querySelector('.bslib-sidebar-layout > .sidebar, aside.sidebar, .bslib-sidebar-layout .sidebar');
  }
  function resetMenuScroll() {
    const sidebar = menuSidebar();
    if (!sidebar) return;
    sidebar.scrollTop = 0;
    // Some Shiny/bslib versions put the scrolling surface inside the sidebar.
    sidebar.querySelectorAll('.sidebar-content, .bslib-sidebar-content, .sidebar-inner').forEach(function (el) {
      el.scrollTop = 0;
    });
  }
  function menuToggle() {
    return document.querySelector('.bslib-sidebar-toggle, button[aria-controls*="sidebar"], button[aria-label*="sidebar" i], .sidebar-toggle');
  }
  function openMobileMenu() {
    const toggle = menuToggle();
    if (!toggle) return;
    resetMenuScroll();
    toggle.click();
    // Run after bslib updates the drawer state/layout.
    requestAnimationFrame(resetMenuScroll);
  }
  function navigate(page) {
    const radio = document.querySelector('input[name="page"][value="' + page + '"]');
    if (!radio) return;
    radio.click();
    window.scrollTo({top: 0, behavior: 'instant'});
    // Dismiss a mobile off-canvas sidebar after selecting a destination.
    const sidebar = radio.closest('.sidebar, aside');
    const toggle = menuToggle();
    if (sidebar && toggle && mobileQuery.matches) {
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
  document.addEventListener('DOMContentLoaded', function () {
    labelMenuToggle();
    // Also reset scroll if the native bslib toggle is used instead of bottom Menu.
    document.addEventListener('click', function (event) {
      if (!mobileQuery.matches || event.target.closest('#mobile-nav-menu')) return;
      const toggle = event.target.closest('.bslib-sidebar-toggle, button[aria-controls*="sidebar"], .sidebar-toggle');
      if (toggle && toggle.getAttribute('aria-expanded') !== 'true') {
        resetMenuScroll();
        requestAnimationFrame(resetMenuScroll);
      }
    }, true);
  });
  document.addEventListener('click', function (event) {
    const link = event.target.closest('[data-page]');
    if (link) { event.preventDefault(); navigate(link.dataset.page); return; }
    if (event.target.closest('#mobile-nav-menu')) {
      openMobileMenu();
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
