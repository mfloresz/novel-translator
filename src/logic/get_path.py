#!/usr/bin/env python3
import os
import sys
import subprocess

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

def get_directory_kde():
    """Usa kdialog para seleccionar directorio en KDE Plasma"""
    try:
        result = subprocess.run(
            ['kdialog', '--getexistingdirectory', os.path.expanduser('~')],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_directory_gnome():
    """Usa zenity para seleccionar directorio en GNOME"""
    try:
        result = subprocess.run(
            ['zenity', '--file-selection', '--directory', '--title=Seleccione un directorio'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_directory_windows():
    """Usa el diálogo nativo de Windows para seleccionar directorio"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        # No creamos una nueva root si ya existe una
        if not tk._default_root:
            root = tk.Tk()
            root.withdraw()
        directory = filedialog.askdirectory(
            title="Seleccionar Directorio",
            initialdir=os.path.expanduser('~')
        )
        return directory if directory else None
    except ImportError:
        return None

def get_directory_fallback():
    """Método de respaldo usando tkinter"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        # No creamos una nueva root si ya existe una
        if not tk._default_root:
            root = tk.Tk()
            root.withdraw()
        directory = filedialog.askdirectory(
            title="Seleccionar Directorio",
            initialdir=os.path.expanduser('~')
        )
        return directory if directory else None
    except ImportError:
        # Último recurso: pedir por consola
        print("\nNo se encontraron herramientas gráficas disponibles.")
        print(f"Por favor ingrese la ruta del directorio (ej. {os.path.expanduser('~')}):")
        return input(">> ").strip()

def get_directory():
    """Función principal que selecciona el método apropiado según el entorno"""
    env = detect_environment()

    # Intentar primero con el método específico del entorno
    if env == 'kde':
        directory = get_directory_kde()
    elif env == 'gnome':
        directory = get_directory_gnome()
    elif env == 'windows':
        directory = get_directory_windows()
    else:
        directory = None

    # Si el método específico falla, usar el fallback
    if not directory:
        directory = get_directory_fallback()

    # Validar que el directorio existe y normalizar la ruta
    if directory and os.path.isdir(directory):
        return os.path.abspath(os.path.normpath(directory))
    elif directory:
        print(f"Error: El directorio '{directory}' no existe.", file=sys.stderr)
        return None
    else:
        return None

if __name__ == "__main__":
    selected_directory = get_directory()
    if selected_directory:
        print("Directorio seleccionado:", selected_directory)
    else:
        print("No se seleccionó ningún directorio.", file=sys.stderr)
        sys.exit(1)
