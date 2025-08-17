import json
import os
from pathlib import Path
from typing import Dict, Any


class LanguageManager:
    """
    Gestor de idiomas para la aplicación Novel Manager.
    Carga y proporciona acceso a los archivos de recursos de idioma.
    """

    def __init__(self, language_code: str = "es_MX"):
        """
        Inicializa el gestor de idiomas.
        
        Args:
            language_code (str): Código del idioma a cargar (ej. "es_MX")
        """
        self.language_code = language_code
        self.strings = {}
        self._load_language_file()

    def _load_language_file(self):
        """
        Carga el archivo de idioma correspondiente.
        """
        try:
            i18n_dir = Path(__file__).parent.parent / 'config' / 'i18n'
            language_file = i18n_dir / f"{self.language_code}.json"
            
            if language_file.exists():
                with open(language_file, 'r', encoding='utf-8') as f:
                    self.strings = json.load(f)
            else:
                print(f"Warning: Language file {language_file} not found")
                self.strings = {}
        except Exception as e:
            print(f"Error loading language file: {e}")
            self.strings = {}

    def get_string(self, key: str, default_text: str = "") -> str:
        """
        Devuelve el texto traducido para una clave dada.
        
        Args:
            key (str): Clave del texto a obtener
            default_text (str): Texto por defecto si la clave no se encuentra
            
        Returns:
            str: Texto traducido o texto por defecto
        """
        return self.strings.get(key, default_text or f"[{key}]")

    @staticmethod
    def get_available_languages() -> Dict[str, str]:
        """
        Lista los idiomas disponibles buscando los archivos .json en el directorio de i18n.
        
        Returns:
            Dict[str, str]: Diccionario con código de idioma como clave y nombre como valor
        """
        languages = {}
        try:
            i18n_dir = Path(__file__).parent.parent / 'config' / 'i18n'
            if i18n_dir.exists():
                for file_path in i18n_dir.glob("*.json"):
                    language_code = file_path.stem  # Nombre del archivo sin extensión
                    # Cargar el nombre del idioma desde el archivo
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lang_data = json.load(f)
                            # Intentar obtener el nombre del idioma del propio archivo
                            # Si no está disponible, usar el código como nombre
                            language_name = lang_data.get("language_name", language_code)
                            languages[language_code] = language_name
                    except Exception:
                        # Si hay un error al cargar el archivo, usar el código como nombre
                        languages[language_code] = language_code
        except Exception as e:
            print(f"Error getting available languages: {e}")
            
        return languages