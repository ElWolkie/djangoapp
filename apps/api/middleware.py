# middleware.py (crea este archivo en tu app)
class DisableCSRFForPublicAPI:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Deshabilitar CSRF para el endpoint de registro público
        if request.path == '/api/registrar_persona/':
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)