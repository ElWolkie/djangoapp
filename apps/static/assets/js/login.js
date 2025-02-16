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
      alert('Por favor, ingresa tu correo electrónico.');
      return false;
    }

    if (password === '') {
      alert('Por favor, ingresa tu contraseña.');
      return false;
    }

    if (!validateEmail(email)) {
      alert('Por favor, ingresa un correo electrónico válido.');
      return false;
    }

    return true;
  }

  function validateSignupForm() {
    const name = signupForm.querySelector('input[type="text"]').value.trim();
    const email = signupForm.querySelector('input[type="email"]').value.trim();
    const password = signupForm.querySelector('input[type="password"]').value.trim();

    if (name === '') {
      alert('Por favor, ingresa tu nombre.');
      return false;
    }

    if (email === '') {
      alert('Por favor, ingresa tu correo electrónico.');
      return false;
    }

    if (password === '') {
      alert('Por favor, ingresa tu contraseña.');
      return false;
    }

    if (!validateEmail(email)) {
      alert('Por favor, ingresa un correo electrónico válido.');
      return false;
    }

    if (password.length < 8) {
      alert('La contraseña debe tener al menos 8 caracteres.');
      return false;
    }

    return true;
  }

  function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
});