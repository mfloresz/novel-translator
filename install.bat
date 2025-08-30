@echo off
REM Script de instalación para novel-translator en Windows

REM Definir variables
set INSTALL_DIR=%USERPROFILE%\novel-translator
set SOURCE_DIR=%~dp0

echo Creando directorio de instalación en %INSTALL_DIR%...
mkdir "%INSTALL_DIR%" 2>nul

REM Copiar archivos necesarios
echo Copiando main.py...
copy "%SOURCE_DIR%main.py" "%INSTALL_DIR%\"

echo Copiando carpeta src...
xcopy "%SOURCE_DIR%src" "%INSTALL_DIR%\src\" /E /I /H /Y

echo Copiando run_nt.bat...
copy "%SOURCE_DIR%run_nt.bat" "%INSTALL_DIR%\"

echo Copiando pyproject.toml...
copy "%SOURCE_DIR%pyproject.toml" "%INSTALL_DIR%\"

echo Copiando create_shortcut.ps1...
copy "%SOURCE_DIR%create_shortcut.ps1" "%INSTALL_DIR%\"

echo Copiando icono...
if not exist "%INSTALL_DIR%\src\gui\icons\" mkdir "%INSTALL_DIR%\src\gui\icons\"
copy "%SOURCE_DIR%src\gui\icons\app.png" "%INSTALL_DIR%\src\gui\icons\"

REM Crear entorno virtual con uv
echo Creando entorno virtual con uv...
cd /d "%INSTALL_DIR%"
uv venv

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Sincronizar dependencias usando pyproject.toml
echo Instalando dependencias con uv sync...
uv sync

REM Crear acceso directo en el escritorio
echo Creando acceso directo en el escritorio...
powershell -ExecutionPolicy Bypass -File "%INSTALL_DIR%\create_shortcut.ps1"

echo Instalación completada. Los archivos han sido copiados a %INSTALL_DIR%
echo Para ejecutar la aplicación, use: %INSTALL_DIR%\run_nt.bat
echo También puede usar el acceso directo creado en su escritorio.