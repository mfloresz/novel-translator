@echo off
setlocal

:: Activa el entorno virtual
call .venv\Scripts\activate.bat

:: Ejecuta el script principal
python main.py

:: Elimina todas las carpetas __pycache__ dentro de 'src'
for /d /r "src" %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
    )
)

:: Desactiva el entorno virtual
deactivate

endlocal
