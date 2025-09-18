import os
import re
import json
import html
from PyQt6.QtCore import QObject, pyqtSignal
try:
    from bs4 import BeautifulSoup
    import pypub
    DEPENDENCIES_OK = True
except ImportError:
    DEPENDENCIES_OK = False
    BeautifulSoup = None
    pypub = None
from src.logic.functions import (validate_epub_input, get_epub_files,
                                create_epub_filename)
from .folder_structure import NovelFolderStructure

class EpubConverterLogic(QObject):
    # Señales para comunicar el progreso
    progress_updated = pyqtSignal(str)  # Mensaje de progreso
    conversion_finished = pyqtSignal(bool, str)  # (éxito, mensaje)

    def __init__(self, lang_manager=None):
        super().__init__()
        self.directory = None
        self.lang_manager = lang_manager
        self.default_css = '''
            body {
                font-family: "Libre Baskerville", Georgia, serif;
                line-height: 1.6;
                margin: 1em auto;
                max-width: 40em;
                padding: 0 1em;
                text-align: justify;
            }
            h1 {
                text-align: center;
                font-size: 2em;
                margin: 1em 0;
                page-break-before: always;
            }
            p {
                text-indent: 1.5em;
                margin: 0;
                text-align: justify;
            }
            img {
                max-width: 100%;
                height: auto;
                display: block;
                margin: 1em auto;
            }
            .titlepage {
                text-align: center;
                page-break-after: always;
            }
            .cover {
                text-align: center;
                page-break-after: always;
            }
        '''

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
        Crea un archivo EPUB con los datos proporcionados.

        Args:
            data (dict): Diccionario con los datos del libro
                - title: Título del libro
                - author: Autor del libro
                - description: Descripción del libro
                - cover_path: Ruta a la imagen de portada
                - start_chapter: Número de capítulo inicial (o None para todos)
                - end_chapter: Número de capítulo final (o None para todos)
            table: QTableWidget con la lista de archivos
        """
        try:
            # Verificar dependencias
            if not DEPENDENCIES_OK:
                error_msg = self._get_string("create_panel.epub_creation.error.dependencies", "Error: Faltan dependencias. Instale: pip install beautifulsoup4 pypub3")
                self.conversion_finished.emit(False, error_msg)
                return

            # Validar entradas
            is_valid, error_message = validate_epub_input(
                data['title'], data['author'], self.directory
            )
            if not is_valid:
                self.conversion_finished.emit(False, error_message)
                return

            # Crear instancia de Epub
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.initializing", "Inicializando libro EPUB..."))

            # Verificar si hay portada
            cover_path = None
            if data['cover_path'] and os.path.exists(data['cover_path']):
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

            epub = pypub.Epub(data['title'], creator=data['author'], language='es', cover=cover_path)

            # Obtener archivos según rango
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.getting_files", "Obteniendo lista de archivos..."))
            files = get_epub_files(table, data['start_chapter'], data['end_chapter'])

            if not files:
                error_msg = self._get_string("create_panel.epub_creation.error.no_files", "No se encontraron archivos para procesar")
                self.conversion_finished.emit(False, error_msg)
                return

            # Crear página de título como primer capítulo
            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.creating_titlepage", "Creando página de título..."))
            titlepage_html = self._create_titlepage_html(data['title'], data['author'], data.get('description', ''))
            title_chapter = pypub.create_chapter_from_html(titlepage_html.encode('utf-8'), title="Título")
            epub.add_chapter(title_chapter)

            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.processing_chapters", "Procesando capítulos..."))

            # Procesar capítulos
            for i, file_info in enumerate(files):
                self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.processing_chapter", "Procesando capítulo {index} de {total}: {name}").format(
                    index=i+1, total=len(files), name=file_info['name']))
                chapter_html = self.process_chapter(file_info)
                if chapter_html:
                    chapter_title = self._extract_chapter_title(file_info)
                    chapter = pypub.create_chapter_from_html(chapter_html.encode('utf-8'), title=chapter_title)
                    epub.add_chapter(chapter)
                else:
                    self.progress_updated.emit(self._get_string("create_panel.epub_creation.warning.chapter_not_processed", "Advertencia: No se pudo procesar el capítulo {name}").format(
                        name=file_info['name']))

            # Generar nombre y ruta de archivo EPUB
            output_filename = create_epub_filename(data['title'], data['author'])
            output_path = os.path.join(self.directory, output_filename)

            self.progress_updated.emit(self._get_string("create_panel.epub_creation.progress.saving", "Guardando archivo EPUB..."))
            epub.create(output_path)

            success_message = f"{output_filename}"
            self.conversion_finished.emit(True, success_message)

        except Exception as e:
            error_message = self._get_string("create_panel.epub_creation.error.general", "Error al crear EPUB: {error}").format(error=str(e))
            self.conversion_finished.emit(False, error_message)

    def _extract_chapter_title(self, file_info):
        """Extrae el título del capítulo del archivo"""
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
        """Procesa un capítulo individual y retorna HTML"""
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

            # Construir contenido HTML con BeautifulSoup
            soup = BeautifulSoup('', 'html.parser')
            html_tag = soup.new_tag('html')

            head_tag = soup.new_tag('head')
            title_tag = soup.new_tag('title')
            title_tag.string = chapter_title
            head_tag.append(title_tag)

            # Añadir CSS inline
            style_tag = soup.new_tag('style')
            style_tag.string = self.default_css
            head_tag.append(style_tag)

            html_tag.append(head_tag)

            body_tag = soup.new_tag('body')

            # Separar párrafos por dobles saltos de línea y agregar <p>
            paragraphs = [p.strip() for p in chapter_content.split('\n\n') if p.strip()]
            for paragraph_text in paragraphs:
                # Procesar cada línea del párrafo
                lines_in_paragraph = [line.strip() for line in paragraph_text.split('\n') if line.strip()]
                formatted_text = ' '.join(lines_in_paragraph)

                # Aplicar formato de texto (negritas, cursivas)
                formatted_text = self._format_text(formatted_text)

                # Crear párrafo HTML
                p_tag = soup.new_tag('p')

                # Usar BeautifulSoup para parsear el HTML formateado
                formatted_soup = BeautifulSoup(formatted_text, 'html.parser')
                p_tag.extend(formatted_soup.contents)

                body_tag.append(p_tag)

            html_tag.append(body_tag)
            soup.append(html_tag)

            return str(soup)

        except Exception:
            return None

    def _clean_chapter_title(self, title):
        """Limpia y formatea el título del capítulo"""
        title = title.strip()
        for marker in ['###', '##', '#', '**']:
            if title.startswith(marker):
                title = title[len(marker):].strip()
            if title.endswith(marker):
                title = title[:-len(marker)].strip()
        return title

    def _escape_html_content(self, text):
        """
        Escapa caracteres HTML especiales que podrían ser interpretados incorrectamente
        por BeautifulSoup como etiquetas HTML cuando no deberían serlo.
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
        result = ""
        last_end = 0

        for match in valid_tags:
            start, end = match.span()
            # Escapar el texto antes de la etiqueta válida
            before_tag = formatted_text[last_end:start]
            if before_tag:
                result += html.escape(before_tag)
            # Agregar la etiqueta válida sin escapar
            result += match.group()
            last_end = end

        # Escapar el texto después de la última etiqueta válida
        after_last_tag = formatted_text[last_end:]
        if after_last_tag:
            result += html.escape(after_last_tag)

        return result

    def _apply_text_formatting(self, text):
        """Aplica solo las reglas de formato de texto sin escapar HTML."""
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
        escapando adecuadamente los caracteres HTML especiales.
        """
        return self._escape_html_content(text)

    def _create_titlepage_html(self, title, author, description=""):
        """Crea HTML para la página de título"""
        soup = BeautifulSoup('', 'html.parser')
        html_tag = soup.new_tag('html')

        head_tag = soup.new_tag('head')
        title_tag = soup.new_tag('title')
        title_tag.string = 'Página de Título'
        head_tag.append(title_tag)

        # Añadir CSS inline
        style_tag = soup.new_tag('style')
        style_tag.string = self.default_css
        head_tag.append(style_tag)

        html_tag.append(head_tag)

        body_tag = soup.new_tag('body')
        div_titlepage = soup.new_tag('div', attrs={'class': 'titlepage'})

        h1_title = soup.new_tag('h1')
        h1_title.string = title
        div_titlepage.append(h1_title)

        p_author = soup.new_tag('p')
        p_author.string = f"por {author}"
        div_titlepage.append(p_author)

        # Agregar descripción si está disponible
        if description.strip():
            # Separar párrafos por dobles saltos de línea
            paragraphs = [p.strip() for p in description.split('\n\n') if p.strip()]
            for paragraph_text in paragraphs:
                # Procesar cada línea del párrafo
                lines_in_paragraph = [line.strip() for line in paragraph_text.split('\n') if line.strip()]
                formatted_text = ' '.join(lines_in_paragraph)

                # Aplicar formato de texto (negritas, cursivas)
                formatted_text = self._format_text(formatted_text)

                # Crear párrafo HTML
                p_description = soup.new_tag('p')

                # Usar BeautifulSoup para parsear el HTML formateado
                formatted_soup = BeautifulSoup(formatted_text, 'html.parser')
                p_description.extend(formatted_soup.contents)

                div_titlepage.append(p_description)

        body_tag.append(div_titlepage)
        html_tag.append(body_tag)
        soup.append(html_tag)

        return str(soup)
