from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm

# Vista de inicio
def home_view(request):
    return render(request, "home/index.html")

def login_view(request):
    if request.method == "POST":
        # Verificar si es un inicio de sesión o un registro
        if 'name' in request.POST:  # Esto indica que el usuario está registrándose
            # Registro de usuario
            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")

            # Validar si el usuario ya existe
            if User.objects.filter(email=email).exists():
                return render(request, "accounts/login.html", {"error": "Este correo ya está registrado."})

            # Crear un nuevo usuario
            user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
            user.save()

            # Redirigir al home después del registro
            login(request, user)
            return redirect('/home/')  # O a donde quieras redirigir después del registro

        else:  # Esto indica que el usuario está intentando iniciar sesión
            # Intentar iniciar sesión
            username = request.POST.get("username")
            password = request.POST.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('/home/')  # Redirigir al home después de un inicio de sesión exitoso
            else:
                # Si el usuario no es válido, mostrar un error
                return render(request, "accounts/login.html", {"error": "Credenciales incorrectas."})

    else:
        return render(request, "accounts/login.html")  # Si no es un POST, simplemente renderiza el formulario
    
def logout_view(request):
    logout(request)  # Esto cierra la sesión
    return redirect('login')
