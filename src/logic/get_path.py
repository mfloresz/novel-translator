#!/usr/bin/env python3
import os
import sys
import subprocess
import json
from pathlib import Path

def detect_environment():
    """Detecta si estamos en KDE Plasma, GNOME o Windows"""
    if sys.platform == 'win32':
        return 'windows'

    # Para Linux, verificamos las variables de entorno del DE (Desktop Environment)
    desktop_session = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    kde_session = os.environ.get('KDE_FULL_SESSION', '')

    if 'kde' in desktop_session or kde_session:
        return 'kde'
    elif 'gnome' in desktop_session:
        return 'gnome'
    else:
        return 'linux_other'

def get_directory_kde(initial_dir=None):
    """Usa kdialog para seleccionar directorio en KDE Plasma"""
    try:
        dir_to_use = initial_dir or os.path.expanduser('~')
        result = subprocess.run(
            ['kdialog', '--getexistingdirectory', dir_to_use],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_directory_gnome(initial_dir=None):
    """Usa zenity para seleccionar directorio en GNOME"""
    try:
        dir_to_use = initial_dir or os.path.expanduser('~')
        result = subprocess.run(
            ['zenity', '--file-selection', '--directory', '--title=Seleccione un directorio', f'--filename={dir_to_use}'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_directory_windows(initial_dir=None):
    """Usa el diálogo nativo de Windows para seleccionar directorio"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        # No creamos una nueva root si ya existe una
        if not tk._default_root:
            root = tk.Tk()
            root.withdraw()
        dir_to_use = initial_dir or os.path.expanduser('~')
        directory = filedialog.askdirectory(
            title="Seleccionar Directorio",
            initialdir=dir_to_use
        )
        return directory if directory else None
    except ImportError:
        return None

def get_directory_fallback(initial_dir=None):
    """Método de respaldo usando tkinter"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        # No creamos una nueva root si ya existe una
        if not tk._default_root:
            root = tk.Tk()
            root.withdraw()
        dir_to_use = initial_dir or os.path.expanduser('~')
        directory = filedialog.askdirectory(
            title="Seleccionar Directorio",
            initialdir=dir_to_use
        )
        return directory if directory else None
    except ImportError:
        # Último recurso: pedir por consola
        print("\nNo se encontraron herramientas gráficas disponibles.")
        print(f"Por favor ingrese la ruta del directorio (ej. {os.path.expanduser('~')}):")
        return input(">> ").strip()

def get_directory(initial_dir=None):
    """Función principal que selecciona el método apropiado según el entorno"""
    env = detect_environment()

    # Intentar primero con el método específico del entorno
    if env == 'kde':
        directory = get_directory_kde(initial_dir)
    elif env == 'gnome':
        directory = get_directory_gnome(initial_dir)
    elif env == 'windows':
        directory = get_directory_windows(initial_dir)
    else:
        directory = None

    # Si el método específico falla, usar el fallback
    if not directory:
        directory = get_directory_fallback(initial_dir)

    # Validar que el directorio existe y normalizar la ruta a formato POSIX
    if directory and os.path.isdir(directory):
        # os.path.abspath asegura que tenemos una ruta completa antes de la conversión
        # .as_posix() garantiza el uso de '/' como separador en todos los SO
        return Path(os.path.abspath(directory)).as_posix()
    elif directory:
        print(f"Error: El directorio '{directory}' no existe.", file=sys.stderr)
        return None
    else:
        return None



def get_initial_directory():
    """Obtiene el directorio inicial configurado desde el archivo config.json"""
    try:
        config_path = Path(__file__).parent.parent / 'config' / 'config.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                initial_dir = config.get('initial_directory', '')
                if initial_dir and os.path.isdir(initial_dir):
                    return initial_dir
    except Exception as e:
        print(f"Error cargando directorio inicial: {e}")
    
    # Fallback al directorio home del usuario
    return os.path.expanduser('~')

if __name__ == "__main__":
    selected_directory = get_directory()
    if selected_directory:
        print("Directorio seleccionado:", selected_directory)
    else:
        print("No se seleccionó ningún directorio.", file=sys.stderr)
        sys.exit(1)
