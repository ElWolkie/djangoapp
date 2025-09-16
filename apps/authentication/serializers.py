from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from apps.home.models import Usuarios

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        id_persona = attrs.get("idPersona")
        password   = attrs.get("password")

        if id_persona is None or password is None:
            raise AuthenticationFailed("Se requieren idPersona y contraseña")

        try:
            user = Usuarios.objects.get(idPersona=id_persona)
        except Usuarios.DoesNotExist:
            raise AuthenticationFailed("Usuario no encontrado")

        if not user.check_password(password):
            raise AuthenticationFailed("Contraseña incorrecta")

        if not user.is_active:
            raise AuthenticationFailed("Usuario inactivo")

        refresh = RefreshToken.for_user(user)  

        return {
            "refresh": str(refresh),
            "access":  str(refresh.access_token),
            # aquí puedes usar el claim que quieras
            "user_id": user.idUsuario,
            "idPersona": user.idPersona,
        }

    @classmethod
    def get_token(cls, user):
        # Aunque no lo uses en validate, es bueno dejarlo
        token = RefreshToken.for_user(user)
        token['idPersona']  = user.idPersona
        token['user_id']    = user.idUsuario
        return token
