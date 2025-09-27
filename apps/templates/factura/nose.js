document.addEventListener('DOMContentLoaded', function () {
    const formPago = document.getElementById('formPago');

    // Validación del formulario al enviar
    formPago.addEventListener('submit', function(event) {
        if (!validarFormularioCompleto()) {
            event.preventDefault();
            event.stopPropagation();
            // Mostrar mensajes de error en todos los campos inválidos
            const camposInvalidos = formPago.querySelectorAll('.is-invalid');
            camposInvalidos.forEach(campo => campo.reportValidity());
        } else {
            event.preventDefault();
            enviarFormulario(formPago);
        }
    });

    function validarFormularioCompleto() {
        // Implementa tu lógica de validación aquí
        // Retorna true si el formulario es válido, false si no
        // Ejemplo básico:
        let valido = true;
        const campos = formPago.querySelectorAll('input, select, textarea');
        campos.forEach(campo => {
            if (!campo.checkValidity()) {
                campo.classList.add('is-invalid');
                valido = false;
            } else {
                campo.classList.remove('is-invalid');
            }
        });
        return valido;
    }

    function enviarFormulario(form) {
        const formData = new FormData(form);
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
        .then(response => {
            if (!response.ok) throw new Error('Error en la respuesta del servidor');
            return response.json();
        })
        .then(data => manejarRespuestaServidor(data))
        .catch(error => mostrarErrorInesperado(error));
    }

    function manejarRespuestaServidor(data) {
        if (data.success) {
            mostrarMensajeExito(data);
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error al registrar el pago',
                text: data.message || 'Ocurrió un error inesperado.',
                confirmButtonText: 'Aceptar',
                confirmButtonColor: '#dc3545',
            });
        }
    }

    function mostrarErrorInesperado(error) {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error inesperado',
            text: 'Ocurrió un error al procesar la solicitud.',
            confirmButtonText: 'Aceptar',
            confirmButtonColor: '#dc3545',
        });
    }

    function mostrarMensajeExito(data) {
        if (data.factura_generada && data.factura_id) {
            window.location.href = data.redirect_url;
        } else if (data.message && data.message.includes('La nota ha sido pagada en su totalidad')) {
            Swal.fire({
                icon: 'success',
                title: 'Pago registrado exitosamente',
                html: `
                    <p><strong>ID Pago:</strong> ${data.pago.idPago}</p>
                    <p><strong>Nota:</strong> ${data.pago.idNota}</p>
                    <p><strong>Monto:</strong> ${data.pago.monto}</p>
                    <p><strong>Fecha de Pago:</strong> ${data.pago.fechaPago}</p>
                    <p><strong>Forma de Pago:</strong> ${data.pago.formaPago}</p>
                    <p><strong>Referencia:</strong> ${data.pago.referencia || 'N/A'}</p>
                    <p class="text-success">${data.message}</p>
                `,
                showCancelButton: true,
                confirmButtonText: 'Generar Factura',
                confirmButtonColor: '#28a745',
                cancelButtonText: 'Volver a Pagos',
                cancelButtonColor: '#6c757d',
                allowOutsideClick: false,
                allowEscapeKey: false,
                allowEnterKey: false
            }).then(result => {
                if (result.isConfirmed) {
                    const notaId = document.getElementById('idNota').value;
                    window.location.href = `/factura/facturas/nueva/${notaId}/`;
                } else if (result.dismiss === Swal.DismissReason.cancel) {
                    window.location.href = "/factura/pagos/";
                }
            });
        } else {
            Swal.fire({
                icon: 'warning',
                title: 'Pago registrado exitosamente',
                html: `
                    <p><strong>ID Pago:</strong> ${data.pago.idPago}</p>
                    <p><strong>Nota:</strong> ${data.pago.idNota}</p>
                    <p><strong>Monto:</strong> ${data.pago.monto}</p>
                    <p><strong>Fecha de Pago:</strong> ${data.pago.fechaPago}</p>
                    <p><strong>Forma de Pago:</strong> ${data.pago.formaPago}</p>
                    <p><strong>Referencia:</strong> ${data.pago.referencia || 'N/A'}</p>
                    <p class="text-danger">${data.message}</p>
                `,
                confirmButtonText: 'Realizar otro pago',
                confirmButtonColor: '#ffc107',
                allowOutsideClick: false,
                allowEscapeKey: false,
                allowEnterKey: false
            }).then(() => {
                window.location.href = data.redirect_url;
            });
        }
    }
});
