#!/bin/bash

# Script de instalación para novel-translator

# Definir variables
INSTALL_DIR="$HOME/.local/bin/novel-translator"
SOURCE_DIR="$(pwd)"

# Crear directorio de instalación si no existe
echo "Creando directorio de instalación en $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Copiar archivos necesarios
echo "Copiando main.py..."
cp "$SOURCE_DIR/main.py" "$INSTALL_DIR/"

echo "Copiando carpeta src..."
cp -r "$SOURCE_DIR/src" "$INSTALL_DIR/"

echo "Copiando run_nt.sh..."
cp "$SOURCE_DIR/run_nt.sh" "$INSTALL_DIR/"

# Dar permisos de ejecución a run_nt.sh
echo "Dando permisos de ejecución a run_nt.sh..."
chmod +x "$INSTALL_DIR/run_nt.sh"

echo "Instalación completada. Los archivos han sido copiados a $INSTALL_DIR"
echo "Para ejecutar la aplicación, use: $INSTALL_DIR/run_nt.sh"