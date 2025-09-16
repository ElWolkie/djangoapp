import threading
from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()

class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Almacena usuario e IP en hilo local
        _thread_locals.user = getattr(request, 'user', None)
        _thread_locals.ip = request.META.get('REMOTE_ADDR')
    
    def process_response(self, request, response):
        # Limpiar al finalizar la petición
        if hasattr(_thread_locals, 'user'):
            del _thread_locals.user
        if hasattr(_thread_locals, 'ip'):
            del _thread_locals.ip
        return response

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def get_current_ip():
    return getattr(_thread_locals, 'ip', None)