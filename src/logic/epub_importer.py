import os
import re
from typing import Dict, List, Tuple
from PyQt6.QtCore import QObject, pyqtSignal
from .database import TranslationDatabase

class EpubImporter(QObject):
    progress_updated = pyqtSignal(str)
    import_finished = pyqtSignal(bool, str, str)  # (success, message, directory_path)

    def __init__(self):
        super().__init__()

    def import_epub(self, book_title: str, author: str, chapters_data: List[Tuple[str, str]], cover_image: Dict = None, epub_path: str = None) -> None:
        """
        Importa un archivo EPUB usando datos pre-procesados.
        
        Args:
            book_title (str): Título del libro
            author (str): Autor del libro
            chapters_data (List[Tuple[str, str]]): Lista de tuplas (filename, content) con los capítulos
            cover_image (Dict, optional): Diccionario con información de la portada {'filename': str, 'content': bytes, 'mime_type': str}
            epub_path (str, optional): Ruta al archivo EPUB original (para extraer portada)
        """
        try:
            if not chapters_data:
                self.import_finished.emit(False, "No se encontraron capítulos para importar", "")
                return

            # Crear directorio de trabajo
            if epub_path:
                epub_dir = os.path.dirname(epub_path)
            else:
                # Si no se proporciona la ruta del EPUB, usar el directorio home
                epub_dir = os.path.expanduser('~')
                
            output_dir = os.path.join(epub_dir, self._sanitize_filename(book_title))

            if os.path.exists(output_dir):
                # Si existe, añadir número
                counter = 1
                while os.path.exists(f"{output_dir}_{counter}"):
                    counter += 1
                output_dir = f"{output_dir}_{counter}"

            os.makedirs(output_dir, exist_ok=True)
            self.progress_updated.emit(f"Creando directorio: {output_dir}")

            # Guardar portada si existe
            if cover_image:
                cover_path = os.path.join(output_dir, cover_image['filename'])
                with open(cover_path, 'wb') as f:
                    f.write(cover_image['content'])
                self.progress_updated.emit(f"Portada guardada: {cover_image['filename']}")

            # Guardar capítulos
            for i, (filename, content) in enumerate(chapters_data, 1):
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                self.progress_updated.emit(f"Capítulo {i} guardado")

            # Guardar metadatos en la base de datos
            self._save_book_metadata(output_dir, book_title, author)

            success_msg = f"EPUB importado exitosamente. {len(chapters_data)} capítulos extraídos."
            if cover_image:
                success_msg += " Portada incluida."
            self.import_finished.emit(True, success_msg, output_dir)

        except Exception as e:
            self.import_finished.emit(False, f"Error al importar EPUB: {str(e)}", "")

    def _save_book_metadata(self, output_dir: str, title: str, author: str) -> None:
        """Guarda los metadatos del libro en la base de datos"""
        try:
            db = TranslationDatabase(output_dir)

            if title or author:
                success = db.save_book_metadata(title, author)
                if success:
                    self.progress_updated.emit("Metadatos del libro guardados")
                else:
                    self.progress_updated.emit("Advertencia: No se pudieron guardar los metadatos")
        except Exception as e:
            print(f"Error guardando metadatos: {e}")
            self.progress_updated.emit("Advertencia: Error al guardar metadatos")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitiza un nombre para usar como nombre de directorio"""
        # Remover caracteres no válidos
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')

        # Limitar longitud
        filename = filename[:100].strip()

        # Asegurar que no esté vacío
        if not filename:
            filename = "Libro_Importado"

        return filename
