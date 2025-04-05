from django.contrib.auth.backends import ModelBackend
from .models import Usuarios, Personas

class CedulaBackend(ModelBackend):
    def authenticate(self, request, idPersona=None, password=None, **kwargs):
        try:
            # Buscar usuario por idPersona
            user = Usuarios.objects.get(idPersona=idPersona)
            if user.check_password(password):
                return user
            return None
        except Usuarios.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Usuarios.objects.get(pk=user_id)
        except Usuarios.DoesNotExist:
            return None