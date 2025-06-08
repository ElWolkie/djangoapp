// Convierte a mayúsculas automáticamente
function activarMayusculasInputs() {
  document.addEventListener('input', function(e) {
    if (e.target.tagName === 'INPUT' && !e.target.type.match(/password|hidden|email/)) {
      e.target.value = e.target.value.toUpperCase();
    }
  });
}

// Valida campos requeridos con SweetAlert2
function highlightInvalidInputs(formSelector) {
  const form = document.querySelector(formSelector);
  if (!form) return;
  let valid = true;
  let firstInvalid = null;
  form.querySelectorAll('input, select, textarea').forEach(input => {
    if (input.type !== "hidden" && input.hasAttribute('data-required') && !input.value.trim()) {
      input.classList.add('is-invalid');
      if (!firstInvalid) firstInvalid = input;
      valid = false;
    } else {
      input.classList.remove('is-invalid');
    }
  });
  if (!valid) {
    Swal.fire({
      title: 'Campos requeridos',
      text: 'Por favor, complete todos los campos obligatorios resaltados en rojo.',
      icon: 'warning',
      confirmButtonText: 'OK',
      customClass: { confirmButton: 'btn btn-warning' },
      buttonsStyling: false,
    }).then(() => {
      if (firstInvalid) firstInvalid.focus();
    });
  }
  return valid;
}
// Llama a esta función al cargar el DOM
document.addEventListener("DOMContentLoaded", function() {
  activarMayusculasInputs();
});