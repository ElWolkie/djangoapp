# [Django App Fundación UPTYAB]

# [Django App Administrativo]
![Administrativo](https://github.com/ElWolkie/djangoapp/blob/mobile/react-native/media/sacfu_inicio_administrativo.png)

<br />

# [Django App Contable]
![Contable](https://github.com/ElWolkie/djangoapp/blob/mobile/react-native/media/sacfu_inicio_contable.png)

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
$ npm run start:dev # esto genera .env.development con API_BASE_URL y luego levanta

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
```

> Note: Para usar esta aplicación es necesario tener un usuario autenticado para acceder a las pantallas.

<br />

## Navegadores Soportados

En la actualidad, nuestro objetivo oficial es admitir las dos últimas versiones de los siguientes navegadores:

<img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/chrome.png" width="64" height="64"> <img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/firefox.png" width="64" height="64"> <img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/edge.png" width="64" height="64"> <img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/safari.png" width="64" height="64"> <img src="https://s3.amazonaws.com/creativetim_bucket/github/browser/opera.png" width="64" height="64">

<br />