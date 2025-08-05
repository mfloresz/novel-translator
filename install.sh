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

echo "Copiando run_nv.sh..."
cp "$SOURCE_DIR/run_nv.sh" "$INSTALL_DIR/"

# Modificar run_nv.sh para que apunte al nuevo directorio
echo "Actualizando run_nv.sh..."
sed -i "s|cd ~/.local/bin/novel-translator|cd '$INSTALL_DIR'|g" "$INSTALL_DIR/run_nv.sh"

# Dar permisos de ejecución a run_nv.sh
echo "Dando permisos de ejecución a run_nv.sh..."
chmod +x "$INSTALL_DIR/run_nv.sh"

echo "Instalación completada. Los archivos han sido copiados a $INSTALL_DIR"
echo "Para ejecutar la aplicación, use: $INSTALL_DIR/run_nv.sh"