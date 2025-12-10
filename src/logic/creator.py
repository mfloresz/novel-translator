import os
import re
import json
from PyQt6.QtCore import QObject, pyqtSignal
from src.logic.functions import (validate_epub_input, get_epub_files,
                                create_epub_filename)
from .folder_structure import NovelFolderStructure
from .epub_generator import EpubGenerator, EpubMetadata, ChapterData
from .xml_utils import escape_xml

class EpubConverterLogic(QObject):
    # Señales para comunicar el progreso
    progress_updated = pyqtSignal(str)  # Mensaje de progreso
    conversion_finished = pyqtSignal(bool, str)  # (éxito, mensaje)

    def __init__(self, lang_manager=None):
        super().__init__()
        self.directory = None
        self.lang_manager = lang_manager
        self.epub_generator = EpubGenerator()

    def _get_string(self, key, default_text=""):
        """Obtiene un texto localizado del LanguageManager o usa el texto por defecto."""
        if self.lang_manager:
            return self.lang_manager.get_string(key, default_text)
        return default_text or key

    def set_directory(self, directory):
        """Establece el directorio de trabajo"""
        self.directory = directory

    def create_epub(self, data, table):
        """
        Crea un archivo EPUB con los datos proporcionados usando la nueva estructura.

        Args:
            data (dict): Diccionario con los datos del libro
                - title: Título del libro
                - author: Autor del libro
                - description: Descripción del libro
                - cover_path: Ruta a la imagen de portada
                - start_chapter: Número de capítulo inicial (o None para todos)
                - end_chapter: Número de capítulo final (o None para todos)
                - language: Código de idioma (nuevo)
                - hide_toc: Si ocultar la tabla de contenido (nuevo)
                - patterns: Lista de patrones EPUB (nuevo)
                - collection: Información de colección (opcional)
            table: QTableWidget con la lista de archivos
        """
        try:
            # Validar entradas
            is_valid, error_message = validate_epub_input(
                data['title'], data['author'], self.directory
            )
            if not is_valid:
                self.conversion_finished.emit(False, error_message)
                return

            # Crear instancia de metadatos EPUB
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.initializing", "Inicializando libro EPUB..."))

            # Verificar si hay portada
            cover_path = None
            if data.get('cover_path') and os.path.exists(data['cover_path']):
                # Si la portada no está en el directorio de la novela, copiarla
                novel_cover_path = NovelFolderStructure.copy_cover_to_root(self.directory, data['cover_path'])
                if novel_cover_path:
                    # Usar la ruta absoluta de la portada copiada
                    cover_path = NovelFolderStructure.to_absolute_path(self.directory, novel_cover_path)
                    self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.processing_cover", "Procesando portada..."))
                else:
                    # Si no se pudo copiar, usar la original
                    cover_path = data['cover_path']
            else:
                # Buscar portada en el directorio de la novela
                novel_cover = NovelFolderStructure.find_cover_in_novel(self.directory)
                if novel_cover:
                    cover_path = NovelFolderStructure.to_absolute_path(self.directory, novel_cover)

            # Crear metadatos EPUB
            collection = None
            if data.get('collection'):
                collection = {
                    'name': data['collection'],
                    'type': data.get('collection_type', 'series'),
                    'position': data.get('collection_position', '1')
                }

            metadata = EpubMetadata(
                title=data['title'],
                author=data['author'],
                description=data.get('description', ''),
                language=data.get('language', 'es'),
                cover=cover_path,
                show_toc=not data.get('hide_toc', False),  # Invertido porque hide_toc=True significa show_toc=False
                patterns=data.get('patterns', []),
                collection=collection
            )

            # Obtener archivos según rango
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.getting_files", "Obteniendo lista de archivos..."))
            files = get_epub_files(table, data['start_chapter'], data['end_chapter'])

            if not files:
                error_msg = self._get_string("create_panel.epub_creation.error.no_files", "No se encontraron archivos para procesar")
                self.conversion_finished.emit(False, error_msg)
                return

            # Preparar capítulos
            chapters = []

            # Crear página de título como primer capítulo
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.creating_titlepage", "Creando página de título..."))
            titlepage_html = self.epub_generator.create_title_page_html(
                data['title'], data['author'], data.get('description', '')
            )
            chapters.append(ChapterData("Título", titlepage_html))

            # Procesar capítulos
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.processing_chapters", "Procesando capítulos..."))

            for i, file_info in enumerate(files):
                self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.processing_chapter", "Procesando capítulo {index} de {total}: {name}").format(
                    index=i+1, total=len(files), name=file_info['name']))
                
                chapter_data = self._process_chapter_data(file_info)
                if chapter_data:
                    chapters.append(chapter_data)
                else:
                    self.progress_updated.emit(self._get_string("create_panel.epub_creation.warning.chapter_not_processed", "Advertencia: No se pudo procesar el capítulo {name}").format(
                        name=file_info['name']))

            # Generar archivo EPUB
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.generating_epub", "Generando archivo EPUB..."))
            epub_buffer = self.epub_generator.generate_epub_file(metadata, chapters)

            # Generar nombre y ruta de archivo EPUB
            output_filename = self.epub_generator.generate_epub_filename(data['title'], data['author'])
            output_path = os.path.join(self.directory, output_filename)

            # Guardar archivo EPUB
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.saving", "Guardando archivo EPUB..."))
            with open(output_path, 'wb') as f:
                f.write(epub_buffer)

            success_message = f"{output_filename}"
            self.conversion_finished.emit(True, success_message)

        except Exception as e:
            error_message = self._get_string("create_panel.epub_creation.error.general", "Error al crear EPUB: {error}").format(error=str(e))
            self.conversion_finished.emit(False, error_message)

    def _process_chapter_data(self, file_info):
        """Procesa un archivo de capítulo y retorna ChapterData"""
        try:
            # Leer desde la carpeta 'translated'
            translated_path = NovelFolderStructure.get_translated_path(self.directory)
            file_path = translated_path / file_info['name']

            if not file_path.exists():
                print(f"Archivo traducido no encontrado: {file_path}")
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Obtener título capítulo (primera línea)
            lines = content.split('\n')
            chapter_title = lines[0].strip() if lines else f"Capítulo {file_info['chapter']}"
            chapter_content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''

            # Limpiar el título
            chapter_title = self._clean_chapter_title(chapter_title)
            
            # Si no hay contenido después del título, usar todo el contenido
            if not chapter_content:
                chapter_content = content

            return ChapterData(chapter_title, chapter_content)

        except Exception as e:
            print(f"Error procesando capítulo {file_info['name']}: {e}")
            return None

    def _clean_chapter_title(self, title):
        """Limpia y formatea el título del capítulo"""
        title = title.strip()
        # Remover marcadores markdown
        for marker in ['###', '##', '#', '**']:
            if title.startswith(marker):
                title = title[len(marker):].strip()
            if title.endswith(marker):
                title = title[:-len(marker)].strip()
        return title or "Capítulo sin título"

    def _extract_chapter_title(self, file_info):
        """Extrae el título del capítulo del archivo (método legacy)"""
        try:
            # Leer desde la carpeta 'translated'
            translated_path = NovelFolderStructure.get_translated_path(self.directory)
            file_path = translated_path / file_info['name']

            if not file_path.exists():
                return f"Capítulo {file_info['chapter']}"

            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()

            # Limpiar el título
            title = self._clean_chapter_title(first_line)
            return title if title else f"Capítulo {file_info['chapter']}"
        except Exception:
            return f"Capítulo {file_info['chapter']}"

    def process_chapter(self, file_info):
        """Procesa un capítulo individual y retorna HTML (método legacy)"""
        try:
            # Leer desde la carpeta 'translated'
            translated_path = NovelFolderStructure.get_translated_path(self.directory)
            file_path = translated_path / file_info['name']

            if not file_path.exists():
                print(f"Archivo traducido no encontrado: {file_path}")
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Obtener título capítulo (primera línea)
            lines = content.split('\n')
            chapter_title = lines[0].strip()
            chapter_content = '\n'.join(lines[1:]).strip()

            chapter_title = self._clean_chapter_title(chapter_title)

            # Usar el nuevo procesador de texto
            from .epub_text_processor import EpubTextProcessor
            processor = EpubTextProcessor()
            processed_content = processor.process_chapter_with_python_rules(chapter_content, [])

            html_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{self._escape_xml(chapter_title)}</title>
</head>
<body>
  <h1>{self._escape_xml(chapter_title)}</h1>
  {processed_content}
</body>
</html>'''

            return html_content

        except Exception:
            return None

    def _escape_xml(self, text):
        """Escapa caracteres XML"""
        return escape_xml(text)

    def _apply_text_formatting(self, text):
        """Aplica solo las reglas de formato de texto sin escapar HTML (método legacy)"""
        try:
            # Construir la ruta al archivo de reglas JSON
            rules_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'markdown_rules.json')

            with open(rules_path, 'r', encoding='utf-8') as f:
                rules = json.load(f)

            # Aplicar cada regla en un orden específico si es necesario
            rule_order = ["bold", "italic", "italic_quotes", "line_break"]
            for key in rule_order:
                if key in rules:
                    rule = rules[key]
                    text = re.sub(rule['pattern'], rule['replacement'], text)

            return text
        except (FileNotFoundError, json.JSONDecodeError):
            return text

    def _format_text(self, text):
        """
        Convierte formato de texto simple a HTML usando reglas de un JSON,
        escapando adecuadamente los caracteres HTML especiales (método legacy).
        """
        return self._escape_html_content(text)

    def _escape_html_content(self, text):
        """
        Escapa caracteres HTML especiales que podrían ser interpretados incorrectamente
        por BeautifulSoup como etiquetas HTML cuando no deberían serlo (método legacy).
        """
        # Primero, aplicar formato de texto para generar HTML válido
        formatted_text = self._apply_text_formatting(text)

        # Patrón para detectar etiquetas HTML válidas comunes
        html_tag_pattern = r'<(/?)([biu]|strong|em|br|p|h[1-6])\b[^>]*>'

        # Encontrar todas las etiquetas HTML válidas
        valid_tags = list(re.finditer(html_tag_pattern, formatted_text, re.IGNORECASE))

        if not valid_tags:
            # Si no hay etiquetas HTML válidas, escapar todos los < y >
            return html.escape(formatted_text)

        # Si hay etiquetas válidas, solo escapar < y > que no sean parte de ellas
        import html as html_module
        result = ""
        last_end = 0

        for match in valid_tags:
            start, end = match.span()
            # Escapar el texto antes de la etiqueta válida
            before_tag = formatted_text[last_end:start]
            if before_tag:
                result += html_module.escape(before_tag)
            # Agregar la etiqueta válida sin escapar
            result += match.group()
            last_end = end

        # Escapar el texto después de la última etiqueta válida
        after_last_tag = formatted_text[last_end:]
        if after_last_tag:
            result += html_module.escape(after_last_tag)

        return result

    def _create_titlepage_html(self, title, author, description=""):
        """Crea HTML para la página de título (método legacy)"""
        return self.epub_generator.create_title_page_html(title, author, description)
