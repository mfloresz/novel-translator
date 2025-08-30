@echo off
REM Cambiar al directorio donde está main.py
cd /d "%~dp0"

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Ejecutar la aplicación con pythonw.exe para evitar mostrar la terminal
pythonw main.py