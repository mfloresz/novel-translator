import os
import re
from typing import Dict, List, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from .database import TranslationDatabase
from .epub_converter import EpubConverter
from bs4 import BeautifulSoup

class EpubImportWorker(QRunnable):
    def __init__(self, importer, book_title, author, epub_path, options):
        super().__init__()
        self.importer = importer
        self.book_title = book_title
        self.author = author
        self.epub_path = epub_path
        self.options = options

    def run(self):
        self.importer.import_epub_threaded(self.book_title, self.author, self.epub_path, self.options)

class EpubImporter(QObject):
    progress_updated = pyqtSignal(str)
    import_finished = pyqtSignal(bool, str, str)  # (success, message, directory_path)

    def __init__(self, lang_manager):
        super().__init__()
        self.lang_manager = lang_manager
        self.thread_pool = QThreadPool()

    def start_import(self, book_title: str, author: str, epub_path: str, options: dict):
        worker = EpubImportWorker(self, book_title, author, epub_path, options)
        self.thread_pool.start(worker)

    def import_epub_threaded(self, book_title: str, author: str, epub_path: str, options: dict):
        try:
            converter = EpubConverter(epub_path)
            chapters = converter.get_chapters()

            if not chapters:
                self.import_finished.emit(False, "No se encontraron capítulos para importar", "")
                return

            epub_dir = os.path.dirname(epub_path)
            output_dir = os.path.join(epub_dir, self._sanitize_filename(book_title))

            if os.path.exists(output_dir):
                counter = 1
                while os.path.exists(f"{output_dir}_{counter}"):
                    counter += 1
                output_dir = f"{output_dir}_{counter}"

            os.makedirs(output_dir, exist_ok=True)
            self.progress_updated.emit(f"Creando directorio: {output_dir}")

            cover_image = converter.cover_image
            if cover_image:
                cover_path = os.path.join(output_dir, cover_image['filename'])
                with open(cover_path, 'wb') as f:
                    f.write(cover_image['content'])
                self.progress_updated.emit(f"Portada guardada: {cover_image['filename']}")

            for i, chapter in enumerate(chapters, 1):
                html_content = converter.get_chapter_html(chapter)
                chapter_title = self._extract_chapter_title(chapter, converter)
                markdown_content = converter.convert_html_to_markdown(html_content, options, chapter_title)
                filename = self.lang_manager.get_string("epub_preview_window.default_chapter_filename").format(i=i)
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                    
                self.progress_updated.emit(f"Capítulo {i} de {len(chapters)} guardado")

            self._save_book_metadata(output_dir, book_title, author)

            success_msg = f"EPUB importado exitosamente. {len(chapters)} capítulos extraídos."
            if cover_image:
                success_msg += " Portada incluida."
            self.import_finished.emit(True, success_msg, output_dir)

        except Exception as e:
            self.import_finished.emit(False, f"Error al importar EPUB: {str(e)}", "")

    def _save_book_metadata(self, output_dir: str, title: str, author: str) -> None:
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
        invalid_chars = '<>:\"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        filename = filename[:100].strip()
        if not filename:
            filename = "Libro_Importado"
        return filename

    def _extract_chapter_title(self, chapter, converter) -> str:
        try:
            html_content = converter.get_chapter_html(chapter)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            title_elements = [
                soup.find('h1'),
                soup.find('h2'),
                soup.find('h3'),
                soup.find('title')
            ]
            
            for element in title_elements:
                if element and element.get_text().strip():
                    return element.get_text().strip()
            
            if hasattr(chapter, 'get_name'):
                filename = chapter.get_name()
                if filename:
                    title = os.path.splitext(filename)[0]
                    title = re.sub(r'^[0-9_\\-]+', '', title)
                    title = title.replace('_', ' ').replace('-', ' ').strip()
                    if title:
                        return title
            
            return None
            
        except Exception as e:
            print(f"Error extrayendo título del capítulo: {e}")
            return None
