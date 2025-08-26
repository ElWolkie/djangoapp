from django.urls import path
from apps.authentication.views import CustomTokenObtainPairView
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('token/', csrf_exempt(CustomTokenObtainPairView.as_view()), name='token_obtain_pair'),
]
