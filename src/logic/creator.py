import os
from ebooklib import epub
from PyQt6.QtCore import QObject, pyqtSignal
from src.logic.functions import (validate_epub_input, get_epub_files,
                               create_epub_filename, show_error_dialog)

class EpubConverterLogic(QObject):
    # Señales para comunicar el progreso
    progress_updated = pyqtSignal(str)  # Mensaje de progreso
    conversion_finished = pyqtSignal(bool, str)  # (éxito, mensaje)

    def __init__(self):
        super().__init__()
        self.directory = None
        self.default_css = '''@charset "UTF-8";

        body {
            font-family: serif;
            line-height: 1.6;
            margin: 1em auto;
            max-width: 40em;
            padding: 0 1em;
            text-align: justify;
        }
        h1 {
            text-align: center;
            font-size: 1.5em;
            margin: 1em 0;
            page-break-before: always;
        }
        p {
            text-indent: 1.5em;
            margin: 0 0 0.5em 0;
            text-align: justify;
        }
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
        }
        .cover {
            width: 100%;
            height: 100%;
            text-align: center;
        }
        .cover img {
            max-height: 100%;
            max-width: 100%;
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
            # Validar entradas
            is_valid, error_message = validate_epub_input(
                data['title'], data['author'], self.directory
            )
            if not is_valid:
                self.conversion_finished.emit(False, error_message)
                return

            # Crear el libro
            book = epub.EpubBook()

            # Configurar metadatos
            book.set_identifier(f'id_{hash(data["title"])}')
            book.set_title(data['title'])
            book.set_language('es')
            book.add_author(data['author'])

            # Añadir CSS
            style = epub.EpubItem(
                uid="style_default",
                file_name="style/default.css",
                media_type="text/css",
                content=self.default_css
            )
            book.add_item(style)

            # Procesar portada si existe
            has_cover = False
            if data['cover_path'] and os.path.exists(data['cover_path']):
                self.progress_updated.emit("Procesando portada...")
                has_cover = self.add_cover(book, data['cover_path'])

            # Obtener archivos según el rango especificado
            self.progress_updated.emit("Obteniendo lista de archivos...")
            files = get_epub_files(table, data['start_chapter'], data['end_chapter'])

            if not files:
                self.conversion_finished.emit(False, "No se encontraron archivos para procesar")
                return

            # Procesar capítulos
            chapters = []
            spine = ['nav'] if not has_cover else ['cover', 'nav']

            self.progress_updated.emit("Procesando capítulos...")
            for file_info in files:
                chapter = self.process_chapter(book, file_info)
                if chapter:
                    chapters.append(chapter)
                    spine.append(chapter)

            # Configurar la estructura del libro
            self.progress_updated.emit("Finalizando estructura del libro...")
            book.toc = tuple(chapters)
            book.add_item(epub.EpubNcx())
            nav = epub.EpubNav()
            book.add_item(nav)
            book.spine = spine

            # Generar nombre de archivo y guardar
            output_filename = create_epub_filename(data['title'])
            output_path = os.path.join(self.directory, output_filename)

            self.progress_updated.emit("Guardando archivo EPUB...")
            epub.write_epub(output_path, book, {})

            success_message = f"EPUB creado exitosamente: {output_filename}"
            self.conversion_finished.emit(True, success_message)

        except Exception as e:
            error_message = f"Error al crear EPUB: {str(e)}"
            self.conversion_finished.emit(False, error_message)

    def add_cover(self, book, cover_path):
        """Añade la portada al libro"""
        try:
            # Leer la imagen
            with open(cover_path, 'rb') as file:
                cover_image = file.read()

            # Determinar el tipo de imagen basado en la extensión
            ext = os.path.splitext(cover_path)[1].lower()
            if ext == '.jpg' or ext == '.jpeg':
                image_type = "image/jpeg"
            elif ext == '.png':
                image_type = "image/png"
            elif ext == '.gif':
                image_type = "image/gif"
            else:
                image_type = "image/jpeg"  # Por defecto

            # Crear el item de la portada
            cover_img = epub.EpubImage(
                uid='cover-image',
                file_name='images/cover' + ext,  # Mantener la extensión original
                media_type=image_type,
                content=cover_image
            )
            book.add_item(cover_img)

            # Configurar como portada
            book.set_cover('images/cover' + ext, cover_image)

            # Crear la página de portada
            cover_page = epub.EpubHtml(
                title='Cover',
                file_name='cover.xhtml',
                lang='es'
            )
            cover_page.content = f'''<?xml version='1.0' encoding='utf-8'?>
                <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="es">
                <head>
                    <title>Cover</title>
                    <link rel="stylesheet" href="style/default.css" type="text/css"/>
                </head>
                <body>
                    <div class="cover">
                        <img src="images/cover{ext}" alt="cover"/>
                    </div>
                </body>
                </html>
            '''
            book.add_item(cover_page)
            return True

        except Exception as e:
            show_error_dialog(f"Error al procesar la portada: {str(e)}")
            return False

    def process_chapter(self, book, file_info):
        """Procesa un capítulo individual"""
        try:
            file_path = os.path.join(self.directory, file_info['name'])
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Obtener el título del capítulo (primera línea)
            lines = content.split('\n')
            chapter_title = lines[0].strip()
            chapter_content = '\n'.join(lines[1:]).strip()

            # Limpiar el título del capítulo
            chapter_title = self._clean_chapter_title(chapter_title)

            # Crear el capítulo
            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f'chapter_{file_info["chapter"]}.xhtml',
                lang='es'
            )

            # Crear el contenido HTML correctamente formateado
            chapter.content = f'''<?xml version='1.0' encoding='utf-8'?>
            <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="es">
            <head>
                <title>{chapter_title}</title>
                <link rel="stylesheet" type="text/css" href="style/default.css"/>
            </head>
            <body>
                <h1>{chapter_title}</h1>
                {''.join(f'<p>{p.strip()}</p>' for p in chapter_content.split('\n\n') if p.strip())}
            </body>
            </html>
            '''

            book.add_item(chapter)
            return chapter

        except Exception as e:
            self.progress_updated.emit(f"Error al procesar capítulo {file_info['name']}: {str(e)}")
            return None

    def _clean_chapter_title(self, title):
        """Limpia y formatea el título del capítulo"""
        # Remover marcadores Markdown comunes
        title = title.strip()
        for marker in ['##', '#', '**']:
            if title.startswith(marker):
                title = title[len(marker):].strip()
            if title.endswith(marker):
                title = title[:-len(marker)].strip()

        return title
