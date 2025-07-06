import os
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import re
from PyQt6.QtCore import QObject, pyqtSignal
from .database import TranslationDatabase

class EpubImporter(QObject):
    progress_updated = pyqtSignal(str)
    import_finished = pyqtSignal(bool, str, str)  # (success, message, directory_path)

    def __init__(self):
        super().__init__()
        self.namespaces = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'container': 'urn:oasis:names:tc:opendocument:xmlns:container'
        }

    def import_epub(self, epub_path: str, options: dict = None) -> None:
        """
        Importa un archivo EPUB y lo convierte a estructura de archivos TXT.

        Args:
            epub_path: Ruta al archivo EPUB
            options: Diccionario con opciones de importación
                - add_numbering_to_content: Si True, añade numeración automática al contenido
                - add_chapter_titles_to_content: Si True, inserta títulos de capítulos en el contenido
        """
        if options is None:
            options = {'add_numbering_to_content': False, 'add_chapter_titles_to_content': True}
        try:
            # Validar archivo EPUB
            if not self._validate_epub(epub_path):
                self.import_finished.emit(False, "El archivo no es un EPUB válido", "")
                return

            self.progress_updated.emit("Leyendo estructura del EPUB...")

            # Extraer metadatos y estructura
            with zipfile.ZipFile(epub_path, 'r') as epub_zip:
                metadata = self._extract_metadata(epub_zip)
                if not metadata:
                    self.import_finished.emit(False, "No se pudieron extraer los metadatos del EPUB", "")
                    return

                # Crear directorio de trabajo en la misma ubicación del EPUB
                epub_dir = os.path.dirname(epub_path)
                book_title = self._sanitize_filename(metadata['title'])
                output_dir = os.path.join(epub_dir, book_title)

                if os.path.exists(output_dir):
                    # Si existe, añadir número
                    counter = 1
                    while os.path.exists(f"{output_dir}_{counter}"):
                        counter += 1
                    output_dir = f"{output_dir}_{counter}"

                os.makedirs(output_dir, exist_ok=True)
                self.progress_updated.emit(f"Creando directorio: {output_dir}")

                # Extraer capítulos
                chapters = self._extract_chapters(epub_zip, metadata)
                if not chapters:
                    self.import_finished.emit(False, "No se encontraron capítulos en el EPUB", "")
                    return

                # Convertir capítulos a TXT
                self._convert_chapters_to_txt(chapters, output_dir, options)

                # Extraer portada
                self._extract_cover(epub_zip, metadata, output_dir)

                # Guardar metadatos en la base de datos
                self._save_book_metadata(output_dir, metadata)

                success_msg = f"EPUB importado exitosamente. {len(chapters)} capítulos extraídos."
                self.import_finished.emit(True, success_msg, output_dir)

        except Exception as e:
            self.import_finished.emit(False, f"Error al importar EPUB: {str(e)}", "")

    def _save_book_metadata(self, output_dir: str, metadata: Dict) -> None:
        """Guarda los metadatos del libro en la base de datos"""
        try:
            db = TranslationDatabase(output_dir)
            title = metadata.get('title', '')
            author = metadata.get('author', '')

            if title or author:
                success = db.save_book_metadata(title, author)
                if success:
                    self.progress_updated.emit("Metadatos del libro guardados")
                else:
                    self.progress_updated.emit("Advertencia: No se pudieron guardar los metadatos")
        except Exception as e:
            print(f"Error guardando metadatos: {e}")
            self.progress_updated.emit("Advertencia: Error al guardar metadatos")

    def _validate_epub(self, epub_path: str) -> bool:
        """Valida que el archivo sea un EPUB válido"""
        try:
            if not epub_path.lower().endswith('.epub'):
                return False

            with zipfile.ZipFile(epub_path, 'r') as epub_zip:
                # Verificar que tenga la estructura básica
                files = epub_zip.namelist()
                return 'META-INF/container.xml' in files and any(f.endswith('.opf') for f in files)
        except:
            return False

    def _extract_metadata(self, epub_zip: zipfile.ZipFile) -> Optional[Dict]:
        """Extrae metadatos y estructura del EPUB"""
        try:
            # Leer container.xml para encontrar el archivo OPF
            container_content = epub_zip.read('META-INF/container.xml')
            container_root = ET.fromstring(container_content)

            opf_element = container_root.find('.//container:rootfile', self.namespaces)
            if opf_element is None:
                print("No se encontró el elemento rootfile")
                return None
            opf_path = opf_element.get('full-path')

            if opf_path is None:
                print("No se encontró la ruta del archivo OPF")
                return None

            # Leer archivo OPF
            opf_content = epub_zip.read(opf_path)
            opf_root = ET.fromstring(opf_content)

            # Extraer metadatos básicos
            title = self._get_text(opf_root.find('.//dc:title', self.namespaces), 'Libro Sin Título')
            author = self._get_text(opf_root.find('.//dc:creator', self.namespaces), 'Autor Desconocido')

            # Extraer orden de capítulos del spine
            spine_items = []
            spine = opf_root.find('.//opf:spine', self.namespaces)
            if spine is not None:
                for itemref in spine.findall('opf:itemref', self.namespaces):
                    idref = itemref.get('idref')
                    spine_items.append(idref)

            # Mapear IDs a archivos del manifest
            manifest_map = {}
            manifest = opf_root.find('.//opf:manifest', self.namespaces)
            if manifest is not None:
                for item in manifest.findall('opf:item', self.namespaces):
                    item_id = item.get('id')
                    href = item.get('href')
                    media_type = item.get('media-type')
                    manifest_map[item_id] = {'href': href, 'media-type': media_type}

            # Buscar portada
            cover_id = None
            for meta in opf_root.findall('.//opf:meta', self.namespaces):
                if meta.get('name') == 'cover':
                    cover_id = meta.get('content')
                    break

            return {
                'title': title,
                'author': author,
                'opf_path': opf_path,
                'spine_items': spine_items,
                'manifest_map': manifest_map,
                'cover_id': cover_id,
                'opf_dir': os.path.dirname(opf_path) if opf_path else ""
            }

        except Exception as e:
            print(f"Error extrayendo metadatos: {e}")
            return None

    def _extract_chapters(self, epub_zip: zipfile.ZipFile, metadata: Dict) -> List[Dict]:
        """Extrae los capítulos en orden del spine"""
        chapters = []
        opf_dir = metadata['opf_dir']

        for i, spine_id in enumerate(metadata['spine_items'], 1):
            if spine_id in metadata['manifest_map']:
                item_info = metadata['manifest_map'][spine_id]

                # Solo procesar archivos HTML/XHTML
                if item_info['media-type'] in ['application/xhtml+xml', 'text/html']:
                    file_path = item_info['href']

                    # Resolver ruta relativa al directorio OPF
                    if opf_dir:
                        file_path = f"{opf_dir}/{file_path}"

                    try:
                        content = epub_zip.read(file_path).decode('utf-8')

                        # Extraer título del capítulo del HTML
                        chapter_title = self._extract_chapter_title_from_html(content)

                        chapters.append({
                            'number': i,
                            'content': content,
                            'original_path': file_path,
                            'title': chapter_title
                        })
                        self.progress_updated.emit(f"Procesando capítulo {i}...")
                    except Exception as e:
                        print(f"Error leyendo capítulo {file_path}: {e}")
                        continue

        return chapters

    def _convert_chapters_to_txt(self, chapters: List[Dict], output_dir: str, options: dict) -> None:
        """Convierte capítulos HTML a archivos TXT numerados"""
        for chapter in chapters:
            try:
                # Parsear HTML con BeautifulSoup
                soup = BeautifulSoup(chapter['content'], 'html.parser')

                # Remover scripts y estilos
                for script in soup(["script", "style"]):
                    script.decompose()

                # Extraer texto respetando la estructura de párrafos
                text = self._extract_structured_text(soup)

                # Manejar contenido según opciones
                chapter_title = chapter.get('title', '').strip()

                # Construir contenido según las opciones seleccionadas
                content_parts = []

                # Opción 1: Añadir numeración automática al contenido
                if options.get('add_numbering_to_content', False):
                    content_parts.append(f"Capítulo {chapter['number']:03d}")

                # Opción 2: Añadir título del capítulo al contenido
                if options.get('add_chapter_titles_to_content', True):
                    if chapter_title and not text.startswith(chapter_title):
                        content_parts.append(chapter_title)

                # Construir el contenido final
                if content_parts:
                    # Unir las partes del encabezado
                    header = " - ".join(content_parts) if len(content_parts) > 1 else content_parts[0]
                    text = f"{header}\n\n{text}"

                # Generar nombre de archivo (siempre usa numeración para evitar conflictos)
                filename = f"Capítulo {chapter['number']:03d}.txt"

                filepath = os.path.join(output_dir, filename)

                # Guardar archivo
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)

                self.progress_updated.emit(f"Capítulo {chapter['number']} convertido a TXT")

            except Exception as e:
                print(f"Error convirtiendo capítulo {chapter['number']}: {e}")

    def _extract_cover(self, epub_zip: zipfile.ZipFile, metadata: Dict, output_dir: str) -> None:
        """Extrae la imagen de portada si existe"""
        try:
            cover_id = metadata.get('cover_id')
            if not cover_id:
                return

            manifest_map = metadata['manifest_map']
            if cover_id not in manifest_map:
                return

            cover_info = manifest_map[cover_id]
            cover_path = cover_info['href']

            # Resolver ruta relativa
            opf_dir = metadata['opf_dir']
            if opf_dir:
                cover_path = f"{opf_dir}/{cover_path}"

            # Extraer imagen
            cover_data = epub_zip.read(cover_path)

            # Determinar extensión
            media_type = cover_info['media-type']
            ext_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/bmp': '.bmp',
                'image/webp': '.webp'
            }

            extension = ext_map.get(media_type, '.jpg')
            cover_filename = f"cover{extension}"
            cover_filepath = os.path.join(output_dir, cover_filename)

            with open(cover_filepath, 'wb') as f:
                f.write(cover_data)

            self.progress_updated.emit("Portada extraída")

        except Exception as e:
            print(f"Error extrayendo portada: {e}")

    def _extract_structured_text(self, soup: BeautifulSoup) -> str:
        """Extrae texto respetando la estructura de párrafos y elementos de bloque"""
        # Remover elementos no deseados
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        # Procesar diferentes tipos de elementos
        result_parts = []

        # Buscar el contenido principal (body o contenedor principal)
        main_content = soup.find('body') or soup

        # Procesar cada elemento de forma secuencial
        try:
            elements = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'blockquote', 'li'])
            for element in elements:
                if hasattr(element, 'get_text') and hasattr(element, 'name'):
                    text = element.get_text().strip()
                    if text:
                        # Los encabezados y párrafos se separan con doble salto
                        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote']:
                            result_parts.append(text)
                        elif element.name == 'div':
                            # Solo añadir divs si contienen texto directo
                            try:
                                direct_text = ''.join([str(t) for t in element.find_all(text=True, recursive=False)]).strip()
                                if direct_text:
                                    result_parts.append(text)
                            except:
                                result_parts.append(text)
                        elif element.name == 'li':
                            result_parts.append(f"• {text}")
        except Exception as e:
            print(f"Error procesando elementos: {e}")

        # Si no se encontró contenido estructurado, usar método de respaldo
        if not result_parts:
            text = soup.get_text()
            # Limpiar espacios múltiples
            text = re.sub(r'[ \t]+', ' ', text)
            # Dividir por saltos de línea y limpiar
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n\n'.join(lines)

        # Unir con doble salto de línea
        result = '\n\n'.join(result_parts)

        # Normalizar espacios en cada línea
        lines = result.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = re.sub(r'[ \t]+', ' ', line.strip())
            cleaned_lines.append(cleaned_line)

        result = '\n'.join(cleaned_lines)

        # Limpiar saltos múltiples y espacios al inicio/final
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = result.strip()

        return result

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

    def _extract_chapter_title_from_html(self, html_content: str) -> str:
        """Extrae el título del capítulo del contenido HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Buscar título en el elemento title del HTML
            title_elem = soup.find('title')
            if title_elem and title_elem.get_text().strip():
                title = title_elem.get_text().strip()
                title = re.sub(r'\s+', ' ', title)
                if 5 <= len(title) <= 200:
                    return title

            # Buscar en encabezados por orden de importancia
            for tag_name in ['h1', 'h2', 'h3']:
                heading = soup.find(tag_name)
                if heading and heading.get_text().strip():
                    title = heading.get_text().strip()
                    title = re.sub(r'\s+', ' ', title)
                    if 5 <= len(title) <= 150:
                        return title

            # Buscar en elementos con clases relacionadas con títulos
            for class_pattern in ['title', 'chapter', 'heading']:
                element = soup.find(attrs={'class': re.compile(class_pattern, re.I)})
                if element and element.get_text().strip():
                    title = element.get_text().strip()
                    title = re.sub(r'\s+', ' ', title)
                    if 5 <= len(title) <= 150:
                        return title

            return ""

        except Exception:
            return ""

    def _sanitize_filename_for_file(self, filename: str) -> str:
        """Sanitiza un nombre para usar como nombre de archivo"""
        # Remover caracteres no válidos
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')

        # Reemplazar espacios múltiples con uno solo
        filename = ' '.join(filename.split())

        # Limitar longitud
        filename = filename[:100].strip()

        # Asegurar que no esté vacío
        if not filename:
            filename = "Capitulo_Sin_Titulo"

        return filename

    def _get_text(self, element, default: str = "") -> str:
        """Obtiene texto de un elemento XML o retorna valor por defecto"""
        if element is not None and element.text:
            return element.text.strip()
        return default
