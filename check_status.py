#!/usr/bin/env python3
"""
Script para verificar el estado de los archivos en un directorio de trabajo
"""

import os
import sys
from pathlib import Path

# Añadir el directorio src al path para poder importar los módulos
sys.path.insert(0, str(Path(__file__).parent))

from src.logic.database import TranslationDatabase

def check_directory_status(directory_path):
    """Verifica el estado de los archivos en un directorio de trabajo"""
    if not os.path.exists(directory_path):
        print(f"Error: El directorio '{directory_path}' no existe")
        return
        
    if not os.path.isdir(directory_path):
        print(f"Error: '{directory_path}' no es un directorio")
        return
        
    print(f"Verificando estado de archivos en: {directory_path}")
    
    try:
        # Inicializar la base de datos
        db = TranslationDatabase(directory_path)
        print("Base de datos inicializada correctamente")
        
        # Obtener todos los archivos .txt del directorio
        txt_files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]
        txt_files.sort()
        
        print(f"\nArchivos .txt encontrados: {len(txt_files)}")
        print("-" * 50)
        
        # Verificar el estado de cada archivo
        for filename in txt_files:
            is_translated = db.is_file_translated(filename)
            status_text = "Traducido" if is_translated else "Sin procesar"
            print(f"{filename:<30} | {status_text}")
            
        # Obtener todos los registros de la base de datos
        print("\n" + "=" * 50)
        print("Registros en la base de datos:")
        print("=" * 50)
        
        import sqlite3
        db_path = os.path.join(directory_path, '.translation_records.db')
        if os.path.exists(db_path):
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT filename, source_lang, target_lang, status FROM translations")
                records = cursor.fetchall()
                
                if records:
                    print(f"{'Archivo':<25} | {'Origen':<10} | {'Destino':<10} | {'Status':<6}")
                    print("-" * 55)
                    for filename, source_lang, target_lang, status in records:
                        print(f"{filename:<25} | {source_lang:<10} | {target_lang:<10} | {status:<6}")
                else:
                    print("No hay registros en la base de datos")
        else:
            print("No se encontró la base de datos")
            
    except Exception as e:
        print(f"Error al verificar el directorio: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python check_status.py <directorio>")
        print("Ejemplo: python check_status.py /ruta/a/tu/directorio/de/trabajo")
        sys.exit(1)
        
    directory_path = sys.argv[1]
    check_directory_status(directory_path)