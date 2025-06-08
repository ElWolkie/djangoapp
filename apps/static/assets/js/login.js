document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.getElementById('loginForm');
  const cedulaInput = document.getElementById('cedulaInput');
  const passwordInput = document.getElementById('passwordInput');
  const submitBtn = document.getElementById('submitBtn');

  if (loginForm) {
    loginForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      submitBtn.disabled = true;
      submitBtn.textContent = 'Verificando...';
      
      const cedula = cedulaInput.value.trim();
      const password = passwordInput.value.trim();
      
      // Validación básica
      if (!cedula) {
        showError('Por favor ingrese su cédula');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Entrar';
        return;
      }
      
      if (!password) {
        showError('Por favor ingrese su contraseña');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Entrar';
        return;
      }
      
      try {
        const response = await fetch('/login/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: `cedula=${encodeURIComponent(cedula)}&password=${encodeURIComponent(password)}`
        });
        
        if (response.redirected) {
          window.location.href = response.url; // Redirige al dashboard
        } else {
          const data = await response.json();
          if (data.error) {
            showError(data.error);
          }
        }
      } catch (error) {
        showError('Error de conexión con el servidor');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Entrar';
      }
    });
  }
  
  function showError(message) {
    // Eliminar mensajes anteriores
    const oldAlerts = document.querySelectorAll('.alert-messages .alert');
    oldAlerts.forEach(alert => alert.remove());
    
    // Crear nuevo mensaje
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-error';
    alertDiv.textContent = message;
    
    const alertContainer = document.querySelector('.alert-messages') || document.createElement('div');
    if (!document.querySelector('.alert-messages')) {
      alertContainer.className = 'alert-messages';
      loginForm.insertBefore(alertContainer, loginForm.querySelector('.button'));
    }
    
    alertContainer.prepend(alertDiv);
    
    // Scroll al mensaje
    alertDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  
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
});