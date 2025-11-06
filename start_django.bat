@echo off

REM Navegar al directorio del proyecto
cd /d %~dp0

REM Activar el entorno virtual
call env\Scripts\activate

REM Iniciar el servidor
start python manage.py runserver

REM Abrir el navegador
start http://127.0.0.1:8000