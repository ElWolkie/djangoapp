# backup/middleware.py
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class SessionCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Solo aplicar a usuarios autenticados
        if request.user.is_authenticated:
            self.ensure_single_session(request)
            
        return response
    
    def ensure_single_session(self, request):
        """Asegura que solo haya una sesión activa por usuario"""
        try:
            current_session_key = request.session.session_key
            if not current_session_key:
                return
            
            # Obtener el ID del usuario
            user_id = self.get_user_id(request.user)
            if not user_id:
                logger.warning(f"No se pudo obtener el ID del usuario: {request.user}")
                return
            
            # Buscar sesiones del mismo usuario
            user_sessions = Session.objects.filter(
                expire_date__gte=timezone.now()
            )
            
            sessions_to_delete = []
            for session in user_sessions.exclude(session_key=current_session_key):
                session_data = self.get_session_data(session)
                if session_data and str(user_id) == str(session_data.get('_auth_user_id')):
                    sessions_to_delete.append(session.session_key)
            
            # Eliminar sesiones duplicadas
            if sessions_to_delete:
                Session.objects.filter(session_key__in=sessions_to_delete).delete()
                logger.info(f"Eliminadas {len(sessions_to_delete)} sesiones duplicadas para el usuario {user_id}")
                
        except Exception as e:
            logger.error(f"Error en SessionCleanupMiddleware: {str(e)}", exc_info=True)
    
    def get_user_id(self, user):
        """Obtiene el ID del usuario de manera segura"""
        try:
            # Probar diferentes atributos comunes para el ID
            for attr in ['id', 'pk', 'idUsuario', 'codigo', 'user_id']:
                if hasattr(user, attr):
                    value = getattr(user, attr)
                    if value is not None:
                        return value
            
            # Si es un modelo de Django, intentar obtener la pk
            if hasattr(user, '_meta'):
                return user.pk
                
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener user ID: {str(e)}")
            return None
    
    def get_session_data(self, session):
        """Obtiene los datos de la sesión de manera segura"""
        try:
            return session.get_decoded()
        except Exception as e:
            logger.error(f"Error al decodificar sesión {session.session_key}: {str(e)}")
            return None

    def cleanup_old_sessions(self):
        """Limpia sesiones expiradas (puede ser llamado desde un cron job)"""
        try:
            expired_count = Session.objects.filter(
                expire_date__lt=timezone.now()
            ).delete()[0]
            
            if expired_count > 0:
                logger.info(f"Limpieza automática: {expired_count} sesiones expiradas eliminadas")
                
        except Exception as e:
            logger.error(f"Error en limpieza de sesiones expiradas: {str(e)}")