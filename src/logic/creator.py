import os
import re
from PyQt6.QtCore import QObject, pyqtSignal
try:
    from bs4 import BeautifulSoup
    import pypub
    DEPENDENCIES_OK = True
except ImportError as e:
    DEPENDENCIES_OK = False
    BeautifulSoup = None
    pypub = None
from src.logic.functions import (validate_epub_input, get_epub_files,
                               create_epub_filename, show_error_dialog)

class EpubConverterLogic(QObject):
    # Señales para comunicar el progreso
    progress_updated = pyqtSignal(str)  # Mensaje de progreso
    conversion_finished = pyqtSignal(bool, str)  # (éxito, mensaje)

    def __init__(self):
        super().__init__()
        self.directory = None
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
                - cover_path: Ruta a la imagen de portada
                - start_chapter: Número de capítulo inicial (o None para todos)
                - end_chapter: Número de capítulo final (o None para todos)
            table: QTableWidget con la lista de archivos
        """
        try:
            # Verificar dependencias
            if not DEPENDENCIES_OK:
                error_msg = "Error: Faltan dependencias. Instale: pip install beautifulsoup4 pypub3"
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
            self.progress_updated.emit("Inicializando libro EPUB...")

            # Verificar si hay portada
            cover_path = None
            if data['cover_path'] and os.path.exists(data['cover_path']):
                cover_path = data['cover_path']
                self.progress_updated.emit("Procesando portada...")

            epub = pypub.Epub(data['title'], creator=data['author'], language='es', cover=cover_path)

            # Obtener archivos según rango
            self.progress_updated.emit("Obteniendo lista de archivos...")
            files = get_epub_files(table, data['start_chapter'], data['end_chapter'])

            if not files:
                error_msg = "No se encontraron archivos para procesar"
                self.conversion_finished.emit(False, error_msg)
                return

            # Crear página de título como primer capítulo
            self.progress_updated.emit("Creando página de título...")
            titlepage_html = self._create_titlepage_html(data['title'], data['author'])
            title_chapter = pypub.create_chapter_from_html(titlepage_html.encode('utf-8'), title="Título")
            epub.add_chapter(title_chapter)

            self.progress_updated.emit("Procesando capítulos...")

            # Procesar capítulos
            for i, file_info in enumerate(files):
                self.progress_updated.emit(f"Procesando capítulo {i+1} de {len(files)}: {file_info['name']}")
                chapter_html = self.process_chapter(file_info)
                if chapter_html:
                    chapter_title = self._extract_chapter_title(file_info)
                    chapter = pypub.create_chapter_from_html(chapter_html.encode('utf-8'), title=chapter_title)
                    epub.add_chapter(chapter)
                else:
                    self.progress_updated.emit(f"Advertencia: No se pudo procesar el capítulo {file_info['name']}")

            # Generar nombre y ruta de archivo EPUB
            output_filename = create_epub_filename(data['title'], data['author'])
            output_path = os.path.join(self.directory, output_filename)

            self.progress_updated.emit("Guardando archivo EPUB...")
            epub.create(output_path)

            success_message = f"EPUB creado exitosamente: {output_filename}"
            self.conversion_finished.emit(True, success_message)

        except Exception as e:
            error_message = f"Error al crear EPUB: {str(e)}"
            self.conversion_finished.emit(False, error_message)



    def _extract_chapter_title(self, file_info):
        """Extrae el título del capítulo del archivo"""
        try:
            file_path = os.path.join(self.directory, file_info['name'])
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()

            # Limpiar el título
            title = self._clean_chapter_title(first_line)
            return title if title else f"Capítulo {file_info['chapter']}"
        except Exception as e:
            return f"Capítulo {file_info['chapter']}"

    def process_chapter(self, file_info):
        """Procesa un capítulo individual y retorna HTML"""
        try:
            file_path = os.path.join(self.directory, file_info['name'])
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
            # h1_tag = soup.new_tag('h1')
            #3h1_tag.string = chapter_title
            # body_tag.append(h1_tag)

            # Separar párrafos por dobles saltos de línea y agregar <p>
            paragraphs = [p.strip() for p in chapter_content.split('\n\n') if p.strip()]
            for p in paragraphs:
                formatted_content = self._format_text(p)
                p_tag = soup.new_tag('p')
                # Manejar contenido con HTML de manera simple
                if '<em>' in formatted_content:
                    # Dividir por etiquetas <em> y procesarlas
                    parts = re.split(r'(<em>.*?</em>)', formatted_content)
                    for part in parts:
                        if part.startswith('<em>') and part.endswith('</em>'):
                            # Crear etiqueta em
                            em_tag = soup.new_tag('em')
                            em_tag.string = part[4:-5]  # Extraer contenido entre <em> y </em>
                            p_tag.append(em_tag)
                        elif part:
                            # Agregar texto plano
                            p_tag.append(part)
                else:
                    # Solo texto plano
                    p_tag.string = formatted_content
                body_tag.append(p_tag)

            html_tag.append(body_tag)
            soup.append(html_tag)

            return str(soup)

        except Exception as e:
            self.progress_updated.emit(f"Error al procesar capítulo {file_info['name']}: {str(e)}")
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

    def _format_text(self, text):
        """Convierte formato de texto simple a HTML"""
        # Convertir *texto* a cursiva <em>texto</em>
        # Usar un patrón que capture texto entre asteriscos que no contenga asteriscos
        formatted_text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)



        return formatted_text

    def _create_titlepage_html(self, title, author):
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

        body_tag.append(div_titlepage)
        html_tag.append(body_tag)
        soup.append(html_tag)

        return str(soup)
