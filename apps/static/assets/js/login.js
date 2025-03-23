// Función para obtener el valor de una cookie (ámbito global)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

document.addEventListener('DOMContentLoaded', function () {
  const loginForm = document.querySelector('.login-form form');
  const signupForm = document.querySelector('.signup-form form');

  if (loginForm) {
    loginForm.addEventListener('submit', function (event) {
      event.preventDefault();

      if (!validateLoginForm()) return;

      const email = loginForm.querySelector('input[name="username"]').value.trim();
      const password = loginForm.querySelector('input[name="password"]').value.trim();

      // --- Zona modificada ---
      fetch('/auth/api/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',  // Solo este header es necesario
        },
        body: JSON.stringify({
            username: email,
            password: password
        })
    })
      .then(response => {
        // Verificamos si la respuesta es exitosa
        if (!response.ok) {
          throw new Error(`Error HTTP: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log('Respuesta completa del servidor:', data); // Debug
        // Dentro del .then(data => ...)
          if (data.access) {
            localStorage.setItem('access_token', data.access);
            console.log('Token almacenado:', localStorage.getItem('access_token')); 
            
            // Verifica manualmente el token en consola
            window.location.href = '/index/';  // Redirige SIN setTimeout
          }
      })
      .catch(error => {
        console.error('Error completo:', error);
        showAlert('Error de conexión: ' + error.message, 'error');
      });
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