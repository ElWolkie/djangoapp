// sidenav.js (modificado)
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('[data-sidenav-toggle]').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('data-sidenav-target'));
      if (target) target.classList.toggle('show');
      document.body.classList.toggle('sidenav-open');
    });
  });
});