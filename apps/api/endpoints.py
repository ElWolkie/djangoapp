from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.home.models import Personas, Usuarios

@api_view(['GET'])
def verificar_cedula(request):
    """
    Endpoint para verificar cédula
    Parámetros GET:
    - cedula: Cédula a verificar
    Retorna JSON con:
    - existe: boolean (si la cédula existe en Personas)
    - usuario_existe: boolean (si ya tiene usuario asociado)
    """
    cedula = request.GET.get('cedula', '')
    response_data = {
        'existe': False,
        'usuario_existe': False
    }
    
    if len(cedula) >= 6:  # Longitud mínima para buscar
        try:
            persona = Personas.objects.get(cedula=cedula)
            response_data['existe'] = True
            # Verificar si ya tiene usuario
            if Usuarios.objects.filter(idPersona=persona).exists():
                response_data['usuario_existe'] = True
        except Personas.DoesNotExist:
            pass
    
    return Response(response_data)