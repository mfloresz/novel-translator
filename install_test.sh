#!/bin/bash

# Script de instalación para novel-translator

# Definir variables
INSTALL_DIR="$HOME/.local/bin/novel-translator"
SOURCE_DIR="$(pwd)"

# Crear directorio de instalación si no existe
echo "Creando directorio de instalación en $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Crear directorio temporal para copia de seguridad de archivos
TEMP_DIR="/tmp/novel-translator-backup"
mkdir -p "$TEMP_DIR"

# Hacer copia de seguridad de archivos que no deben ser reemplazados si existen
echo "Haciendo copia de seguridad de archivos que no deben ser reemplazados..."
if [ -f "$INSTALL_DIR/src/config/config.json" ]; then
    cp "$INSTALL_DIR/src/config/config.json" "$TEMP_DIR/"
fi

if [ -f "$INSTALL_DIR/src/config/recents.json" ]; then
    cp "$INSTALL_DIR/src/config/recents.json" "$TEMP_DIR/"
fi

if [ -f "$INSTALL_DIR/src/config/prompts/en-US_es-MX/preset_terms.json" ]; then
    cp "$INSTALL_DIR/src/config/prompts/en-US_es-MX/preset_terms.json" "$TEMP_DIR/"
fi

# Copiar archivos necesarios
echo "Copiando main.py..."
cp "$SOURCE_DIR/main.py" "$INSTALL_DIR/"

echo "Copiando carpeta src..."
cp -r "$SOURCE_DIR/src" "$INSTALL_DIR/"

# Restaurar archivos de la copia de seguridad si existían
echo "Restaurando archivos que no deben ser reemplazados..."
if [ -f "$TEMP_DIR/config.json" ]; then
    cp "$TEMP_DIR/config.json" "$INSTALL_DIR/src/config/"
fi

if [ -f "$TEMP_DIR/recents.json" ]; then
    cp "$TEMP_DIR/recents.json" "$INSTALL_DIR/src/config/"
fi

if [ -f "$TEMP_DIR/preset_terms.json" ]; then
    mkdir -p "$INSTALL_DIR/src/config/prompts/en-US_es-MX/"
    cp "$TEMP_DIR/preset_terms.json" "$INSTALL_DIR/src/config/prompts/en-US_es-MX/"
fi

# Limpiar directorio temporal
rm -rf "$TEMP_DIR"

echo "Copiando run_nt.sh..."
cp "$SOURCE_DIR/run_nt.sh" "$INSTALL_DIR/"

# Dar permisos de ejecución a run_nt.sh
echo "Dando permisos de ejecución a run_nt.sh..."
chmod +x "$INSTALL_DIR/run_nt.sh"

echo "Instalación completada. Los archivos han sido copiados a $INSTALL_DIR"
echo "Para ejecutar la aplicación, use: $INSTALL_DIR/run_nt.sh"