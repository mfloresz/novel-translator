from typing import List
from PyQt6.QtCore import QObject, pyqtSignal
import os
from .database import TranslationDatabase

class FileLoader(QObject):
    files_loaded = pyqtSignal(list)
    loading_finished = pyqtSignal()
    loading_error = pyqtSignal(str)
    metadata_loaded = pyqtSignal(dict)  # Nueva señal para metadatos

    def __init__(self):
        super().__init__()
        self.db = None

    def load_files(self, directory: str) -> None:
        """
        Carga los archivos .txt y verifica su estado de traducción
        """
        try:
            # Inicializar la base de datos
            self.db = TranslationDatabase(directory)

            # Obtener y ordenar la lista de archivos .txt
            txt_files = []
            for f in sorted(os.listdir(directory)):
                if f.endswith('.txt'):
                    # Verificar si el archivo está traducido
                    status = 'Traducido' if self.db.is_file_translated(f) else 'Sin procesar'
                    txt_files.append({
                        'name': f,
                        'status': status
                    })

            if not txt_files:
                self.loading_error.emit("No se encontraron archivos .txt en el directorio")
                return

            # Cargar metadatos del libro si existen
            metadata = self.db.get_book_metadata()
            
            # Emitir la lista completa y los metadatos
            self.files_loaded.emit(txt_files)
            self.metadata_loaded.emit(metadata)
            self.loading_finished.emit()

        except Exception as e:
            self.loading_error.emit(f"Error al cargar archivos: {str(e)}")
