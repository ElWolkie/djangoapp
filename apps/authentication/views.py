# apps/authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status

# Vista de inicio de sesión con JWT
class CustomTokenObtainPairView(TokenObtainPairView):
    # Añade estas líneas para deshabilitar las verificaciones de CSRF
    authentication_classes = []  # Desactiva autenticaciones por defecto
    permission_classes = []     # Desactiva permisos

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return Response({
            'access': response.data['access'],
            'refresh': response.data['refresh']
        })

# Vista de inicio de sesión tradicional (si es necesario)
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')  # Redirigir al home después de un inicio de sesión exitoso
        else:
            return render(request, "accounts/login.html", {"error": "Credenciales incorrectas."})
    else:
        return render(request, "accounts/login.html")

# Vista de registro (si es necesario)
def register_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            return render(request, "accounts/register.html", {"error": "Este correo ya está registrado."})

        user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
        user.save()

        login(request, user)
        return redirect('home')
    else:
        return render(request, "accounts/register.html")

# Vista de cierre de sesión
def logout_view(request):
    logout(request)
    return redirect('login')