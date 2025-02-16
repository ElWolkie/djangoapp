document.addEventListener("DOMContentLoaded", function() {
    const tipoPersonaForm = document.getElementById("tipoPersonaForm");
    const tipoPersonaSelect = document.getElementById("tipoPersona");
  
    tipoPersonaForm.addEventListener("submit", function(event) {
      event.preventDefault();
  
      const nuevoTipoPersona = document.getElementById("nuevoTipoPersona").value;
      
      // Realizar la solicitud al servidor para guardar el nuevo tipo de persona
      fetch("/ruta-para-guardar-tipo-persona/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ nombre: nuevoTipoPersona })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Agregar la nueva opción al select
          const nuevaOpcion = new Option(nuevoTipoPersona, data.id);
          tipoPersonaSelect.add(nuevaOpcion);
          tipoPersonaSelect.value = data.id;  // Seleccionar la nueva opción
          
          // Cerrar el modal
          document.querySelector('#tipoPersonaModal .btn-close').click();
        } else {
          alert("Error al guardar el nuevo tipo de persona.");
        }
      })
      .catch(error => {
        console.error("Error:", error);
      });
    });
  });
  