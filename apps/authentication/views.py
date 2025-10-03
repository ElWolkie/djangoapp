# apps/authentication/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework.response import Response

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    authentication_classes = []   # ya no usamos SessionAuthentication
    permission_classes = []       # AllowAny implícito

    def dispatch(self, request, *args, **kwargs):
        # desactiva internamente el chequeo de CSRF
        request._dont_enforce_csrf_checks = True
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return Response({
            'access':  response.data['access'],
            'refresh': response.data['refresh'],
            'user_id': request.user.idUsuario if hasattr(request, 'user') else None,
            'idPersona': response.data.get('idPersona'),
        })
