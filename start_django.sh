#!/bin/bash

# Navegar al directorio del proyecto
#RUTA GENERICA
cd /home/stelaringt/djangoapp
# Activar el entorno virtual
#RUTA GENERICA
# source env/bin/activate
##RUTA PERSONALIZADA
source /home/stelaringt/djangoapp/venv/bin/activate
# Iniciar el servidor
python manage.py runserver 0.0.0.0:8000 &

# Esperar a que el servidor esté corriendo
while ! nc -z localhost 8000; do
  sleep 1
done

# Abrir el navegador
xdg-open http://127.0.0.1:8000/


# COMANDO PARA DETENER EL SERVIDOR EN CASOS DE EMERGENCIA
# pkill -f "python manage.py runserver"