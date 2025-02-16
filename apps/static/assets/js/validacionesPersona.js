document.addEventListener("DOMContentLoaded", function() {
  // Validar cedula solo números
  document.getElementById("cedula").addEventListener("input", function() {
    this.value = this.value.replace(/\D/g, '');
  });

  // Validar nombres sin números y caracteres especiales
  document.getElementById("nombres").addEventListener("input", function() {
    this.value = this.value.replace(/[^a-zA-Z\s]/g, '');
  });

  // Validar apellidos sin números y caracteres especiales
  document.getElementById("apellidos").addEventListener("input", function() {
    this.value = this.value.replace(/[^a-zA-Z\s]/g, '');
  });

  // Validar teléfono en formato 0412-000-0000
  document.getElementById("telefono").addEventListener("input", function() {
    let value = this.value.replace(/\D/g, '');
    if (value.length > 4) {
      value = value.substring(0, 4) + '-' + value.substring(4, 7) + '-' + value.substring(7, 11);
    }
    this.value = value;
  });
});
