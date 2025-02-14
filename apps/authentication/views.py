from django.shortcuts import render, redirect
from .forms import LoginForm, SignUpForm


def login_view(request):
    form = LoginForm(request.POST or None)
    msg = None

    if request.method == "POST":
        if form.is_valid():
            # Saltamos la lógica de autenticación
            return redirect("index")  # Redirigimos a la página de inicio
        else:
            msg = "Error validando el formulario"

    return render(request, "accounts/login.html", {"form": form, "msg": msg})


def register_user(request):
    msg = None
    success = False

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            msg = 'Usuario creado - por favor <a href="/login">inicia sesión</a>.'
            success = True
        else:
            msg = "El formulario no es válido"
    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form, "msg": msg, "success": success},
    )


def home_view(request):
    return render(request, "home/index.html")
