document.addEventListener('DOMContentLoaded', function () {
  const loginForm = document.querySelector('.login-form form');
  const signupForm = document.querySelector('.signup-form form');

  if (loginForm) {
    loginForm.addEventListener('submit', function (event) {
      if (!validateLoginForm()) {
        event.preventDefault(); // Evita que el formulario se envíe si la validación falla
      }
    });
  }

  if (signupForm) {
    signupForm.addEventListener('submit', function (event) {
      if (!validateSignupForm()) {
        event.preventDefault(); // Evita que el formulario se envíe si la validación falla
      }
    });
  }

  function validateLoginForm() {
    const email = loginForm.querySelector('input[name="username"]').value.trim();
    const password = loginForm.querySelector('input[name="password"]').value.trim();

    if (email === '') {
      showAlert('Por favor, ingrese su Correo electrónico.', 'error');
      return false;
    }

    if (password === '') {
      showAlert('Por favor, ingrese su Contraseña.', 'error');
      return false;
    }

    if (!validateEmail(email)) {
      showAlert('Por favor, ingrese un Correo electrónico válido.', 'error');
      return false;
    }

    return true;
  }

  function validateSignupForm() {
    const name = signupForm.querySelector('input[name="name"]').value.trim();
    const email = signupForm.querySelector('input[name="email"]').value.trim();
    const password = signupForm.querySelector('input[name="password"]').value.trim();

    if (name === '') {
      showAlert('Por favor, ingrese su nombre de Usuario.', 'error');
      return false;
    }

    if (email === '') {
      showAlert('Por favor, ingrese su Correo electrónico.', 'error');
      return false;
    }

    if (password === '') {
      showAlert('Por favor, ingrese su Contraseña.', 'error');
      return false;
    }

    if (!validateEmail(email)) {
      showAlert('Por favor, ingrese un Correo electrónico válido.', 'error');
      return false;
    }

    if (password.length < 8) {
      showAlert('La contraseña debe tener al menos 8 caracteres.', 'error');
      return false;
    }

    return true;
  }

  function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  function showAlert(message, type) {
    const alertBox = document.createElement('div');
    alertBox.className = `alert ${type}`;
    alertBox.innerText = message;
    document.body.appendChild(alertBox);
    setTimeout(() => {
      alertBox.remove();
    }, 3000);
  }
});
