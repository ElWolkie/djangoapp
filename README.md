# [Django App Fundación UPTYAB]

![Argon Dashboard Django - Admin Dashboard coded in Django.](https://github.com/ElWolkie/djangoapp/blob/rama-api/media/photo.png)

<br />

## Despliegue Rapido

> Siga los pasos para desplegar este proyecto en su computador.

```bash
$ # Get the code
$ git clone https://github.com/ElWolkie/djangoapp.git
$ cd djangoapp
$
$ # Virtualenv modules installation (Unix based systems)
$ virtualenv env
$ source env/bin/activate #Linux
$ source env/Scripts/activate  #Windows
$
$ # Virtualenv modules installation (Windows based systems)
$ # virtualenv env
$ # .\env\Scripts\activate
$
$ # Install modules - SQLite Storage
$ pip3 install -r requirements.txt
$
$ # Create tables
$ python manage.py makemigrations
$ python manage.py migrate
$
$ # Start the application (development mode)
$ python manage.py runserver # default port 8000
$ python manage.py runserver 0.0.0.0:8000 #Para la app movil
$ npx expo start -c #para correr el entorno Expo en linux mint 

$
$ # Access the web app in browser: http://127.0.0.1:8000/
# python manage.py show_urls  | grep "/api/"  LISTAR LOS ENDPOINTS DE LA API

# CREA LOS GRUPOS EN RAIZ PROYECTO
# python manage.py dumpdata auth.Group --indent 2 > grupos.json

# ACTUALIZA LOS GRUPOS A LOS MAS RECIENTES
# python manage.py dumpdata auth.Group --indent 2 --natural-foreign --exclude contenttypes > grupos.json

# CARGAR GRUPOS EN BD
# python manage.py loaddata grupos.json

# CARGAR PARAMETROS TRIBUTARIOS
# python manage.py create_parametros_tributarios

# LINUX MINT
# sudo apt update
# sudo apt install python3 python3-pip python3-venv -y
# curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
# sudo apt install -y nodejs
# git clone https://github.com/ElWolkie/djangoapp.git
# cd djangoapp
# python3 -m venv env
# source env/bin/activate
# pip install -r requirements.txt
# # Cargar grupos
# python manage.py loaddata grupos.json

# # Crear parámetros tributarios
# python manage.py create_parametros_tributarios
# ip addr show
# python manage.py runserver 0.0.0.0:8000
# sudo ufw allow 8000
# http://192.168.x.x:8000

#####################################################################################################
# PARA EK SERVER: 
# sudo apt update
# sudo apt install nginx -y
# pip install gunicorn
# gunicorn --workers 3 --bind 0.0.0.0:8000 core.wsgi:application
# sudo nano /etc/nginx/sites-available/djangoapp
# server {
#     listen 80;
#     server_name 192.168.x.x; # Reemplaza con la IP de tu máquina

#     location = /favicon.ico { access_log off; log_not_found off; }
#     location /static/ {
#         root /home/stelaringt/djangoapp;
#     }

#     location /media/ {
#         root /home/stelaringt/djangoapp;
#     }

#     location / {
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }
# }
# sudo ln -s /etc/nginx/sites-available/djangoapp /etc/nginx/sites-enabled/
# sudo nginx -t
# sudo systemctl restart nginx
# sudo apt install certbot python3-certbot-nginx -y
# sudo certbot --nginx -d tu-dominio.com
# 
```

> Note: Para usar esta aplicación es necesario tener un usuario autenticado para acceder a las pantallas.


## Code-base structure

The project is coded using a simple and intuitive structure presented bellow:

```bash
< PROJECT ROOT >
   |
   |-- core/                               # Implements app configuration
   |    |-- settings.py                    # Defines Global Settings
   |    |-- wsgi.py                        # Start the app in production
   |    |-- urls.py                        # Define URLs served by all apps/nodes
   |
   |-- apps/
   |    |
   |    |-- home/                          # A simple app that serve HTML files
   |    |    |-- views.py                  # Serve HTML pages for authenticated users
   |    |    |-- urls.py                   # Define some super simple routes  
   |    |
   |    |-- authentication/                # Handles auth routes (login and register)
   |    |    |-- urls.py                   # Define authentication routes  
   |    |    |-- views.py                  # Handles login and registration  
   |    |    |-- forms.py                  # Define auth forms (login and register) 
   |    |
   |    |-- static/
   |    |    |-- <css, JS, images>         # CSS files, Javascripts files
   |    |
   |    |-- templates/                     # Templates used to render pages
   |         |-- includes/                 # HTML chunks and components
   |         |    |-- navigation.html      # Top menu component
   |         |    |-- sidebar.html         # Sidebar component
   |         |    |-- footer.html          # App Footer
   |         |    |-- scripts.html         # Scripts common to all pages
   |         |
   |         |-- layouts/                   # Master pages
   |         |    |-- base-fullscreen.html  # Used by Authentication pages
   |         |    |-- base.html             # Used by common pages
   |         |
   |         |-- accounts/                  # Authentication pages
   |         |    |-- login.html            # Login page
   |         |    |-- register.html         # Register page
   |         |
   |         |-- home/                      # UI Kit Pages
   |              |-- index.html            # Index page
   |              |-- 404-page.html         # 404 page
   |              |-- *.html                # All other pages
   |
   |-- requirements.txt                     # Development modules - SQLite storage
   |
   |-- .env                                 # Inject Configuration via Environment
   |-- manage.py                            # Start the app - Django default start script
   |
   |-- ************************************************************************
```

<br />

> The bootstrap flow

- Django bootstrapper `manage.py` uses `core/settings.py` as the main configuration file
- `core/settings.py` loads the app magic from `.env` file
- Redirect the guest users to Login page
- Unlock the pages served by *app* node for authenticated users

<br />

## Navegadores Soportados

En la actualidad, nuestro objetivo oficial es admitir las dos últimas versiones de los siguientes navegadores:

<img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/chrome.png" width="64" height="64"> <img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/firefox.png" width="64" height="64"> <img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/edge.png" width="64" height="64"> <img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/safari.png" width="64" height="64"> <img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/opera.png" width="64" height="64">

<br />

---
[Argon Dashboard - Django Template](https://www.creative-tim.com/product/argon-dashboard-django) - Provided by [Creative Tim](https://www.creative-tim.com/) and [AppSeed](https://appseed.us)
