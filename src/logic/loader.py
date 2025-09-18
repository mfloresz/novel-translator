from typing import List
from PyQt6.QtCore import QObject, pyqtSignal
import os
from .database import TranslationDatabase
from .status_manager import STATUS_UNPROCESSED, STATUS_TRANSLATED, get_status_text
from .folder_structure import NovelFolderStructure

class FileLoader(QObject):
    files_loaded = pyqtSignal(list)
    loading_finished = pyqtSignal()
    loading_error = pyqtSignal(str)
    metadata_loaded = pyqtSignal(dict)  # Nueva señal para metadatos

    def __init__(self, lang_manager=None):
        super().__init__()
        self.db = None
        self.lang_manager = lang_manager

    def set_language_manager(self, lang_manager):
        """Set the language manager for status translations."""
        self.lang_manager = lang_manager

    def _get_status_string(self, key, default_text=""):
        """Get a localized status string from the language manager."""
        if self.lang_manager:
            return self.lang_manager.get_string(key, default_text)
        return default_text if default_text else key

    def load_files(self, directory: str) -> None:
        """
        Carga los archivos .txt y verifica su estado de traducción
        """
        try:
            # Asegurar que la estructura de carpetas exista
            NovelFolderStructure.ensure_structure(directory)

            # Inicializar la base de datos
            self.db = TranslationDatabase(directory)

            # Obtener archivos de la carpeta 'translated' (archivos traducidos)
            translated_files = NovelFolderStructure.get_translated_files(directory)

            # Obtener archivos de la carpeta 'originals' (archivos originales)
            original_files = NovelFolderStructure.get_original_files(directory)

            # Crear lista combinada de archivos ordenada alfabéticamente por nombre
            txt_files = []

            # Obtener todos los archivos únicos (translated tienen prioridad)
            all_files = set(translated_files + original_files)

            # Ordenar alfabéticamente por nombre
            sorted_files = sorted(all_files)

            # Para cada archivo, determinar su estado
            for filename in sorted_files:
                if filename in translated_files:
                    # Está en translated, por lo tanto traducido
                    status_code = STATUS_TRANSLATED
                else:
                    # Está solo en originals, verificar DB
                    is_translated = self.db.is_file_translated(filename) if self.db else False
                    status_code = STATUS_TRANSLATED if is_translated else STATUS_UNPROCESSED

                status = get_status_text(status_code, self.lang_manager)
                txt_files.append({
                    'name': filename,
                    'status': status
                })

            if not txt_files:
                self.loading_error.emit("No se encontraron archivos .txt en las carpetas originals o translated")
                return

            # Cargar metadatos del libro si existen
            metadata = self.db.get_book_metadata() if self.db else {"title": "", "author": "", "description": ""}

            # Emitir la lista completa y los metadatos
            self.files_loaded.emit(txt_files)
            self.metadata_loaded.emit(metadata)
            self.loading_finished.emit()

        except Exception as e:
            self.loading_error.emit(f"Error al cargar archivos: {str(e)}")
