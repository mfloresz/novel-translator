import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import os
from typing import List, Dict, Tuple

class EpubConverter:
    """
    Clase para convertir archivos EPUB a diferentes formatos.
    Esta clase maneja la lectura del EPUB y la conversión de HTML a Markdown.
    """
    
    def __init__(self, epub_path: str):
        """
        Inicializa el convertidor con la ruta al archivo EPUB.

        Args:
            epub_path (str): Ruta al archivo EPUB
        """
        self.epub_path = epub_path
        try:
            self.book = epub.read_epub(epub_path)
        except Exception as e:
            raise ValueError(f"Error al leer el archivo EPUB: {str(e)}. Verifique que el archivo no esté corrupto o en un formato incompatible.")
        self.chapters = self._get_chapters()
        self.metadata = self._get_metadata()
        self.cover_image = self._get_cover_image()
    
    @property
    def cover_image(self):
        """Propiedad para acceder a la portada del libro"""
        return self._cover_image
    
    @cover_image.setter
    def cover_image(self, value):
        """Setter para la portada del libro"""
        self._cover_image = value
        
    def _get_chapters(self) -> List:
        """
        Obtiene la lista de capítulos del EPUB ordenados por número de capítulo.

        Returns:
            List: Lista de capítulos ordenados (objetos ebooklib)
        """
        chapters = []
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                chapters.append(item)

        # Ordenar capítulos por número de capítulo
        def get_chapter_number(chapter):
            """Extrae el número de capítulo del nombre del archivo o del contenido"""
            try:
                # Método 1: Extraer número del nombre del archivo (ej: chapter10.html)
                name = chapter.get_name().lower()
                match = re.search(r'chapter(\d+)', name)
                if match:
                    return int(match.group(1))

                # Método 2: Extraer número del contenido HTML (si el nombre no tiene número)
                html_content = chapter.get_content().decode('utf-8')
                soup = BeautifulSoup(html_content, 'html.parser')

                # Buscar en títulos (h1, h2, etc.)
                for tag in ['h1', 'h2', 'h3']:
                    title = soup.find(tag)
                    if title:
                        text = title.get_text().lower()
                        match = re.search(r'chapter\s*(\d+)', text)
                        if match:
                            return int(match.group(1))

                # Método 3: Usar el orden original si no se encuentra número
                return float('inf')  # Poner al final si no tiene número

            except Exception:
                return float('inf')  # Poner al final si hay error

        # Ordenar por número de capítulo
        chapters.sort(key=get_chapter_number)
        return chapters
    
    def _get_metadata(self) -> Dict:
        """
        Obtiene los metadatos del libro.

        Returns:
            Dict: Diccionario con los metadatos del libro
        """
        metadata = {}

        try:
            # Obtener título
            title = self.book.get_metadata('DC', 'title')
            if title:
                metadata['title'] = title[0][0]
            else:
                metadata['title'] = "Libro Sin Título"

            # Obtener autor
            creator = self.book.get_metadata('DC', 'creator')
            if creator:
                metadata['author'] = creator[0][0]
            else:
                metadata['author'] = "Autor Desconocido"
        except Exception as e:
            print(f"Error obteniendo metadatos: {e}")
            metadata['title'] = "Libro Sin Título"
            metadata['author'] = "Autor Desconocido"

        return metadata
    
    def _get_cover_image(self) -> Dict:
        """
        Obtiene la portada del EPUB.

        Returns:
            Dict: Diccionario con información de la portada {'filename': str, 'content': bytes, 'mime_type': str} o None
        """
        try:
            # Método 1: Buscar portada por metadato cover
            cover_meta = self.book.get_metadata('DC', 'cover')
            if cover_meta:
                cover_id = cover_meta[0][0]
                # Buscar el item por ID
                for item in self.book.get_items():
                    if item.get_name() == cover_id or item.get_id() == cover_id:
                        try:
                            return {
                                'filename': f"cover{os.path.splitext(item.get_name())[1]}",
                                'content': item.get_content(),
                                'mime_type': getattr(item, 'media_type', None) or 'image/jpeg'
                            }
                        except Exception:
                            continue

            # Método 2: Buscar items de tipo portada directamente
            for item in self.book.get_items():
                if item.get_type() == ebooklib.ITEM_COVER:
                    try:
                        return {
                            'filename': f"cover{os.path.splitext(item.get_name())[1]}",
                            'content': item.get_content(),
                            'mime_type': getattr(item, 'media_type', None) or 'image/jpeg'
                        }
                    except Exception:
                        continue

            # Método 3: Buscar imágenes que podrían ser portadas
            for item in self.book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    # Verificar si el nombre sugiere que es una portada
                    name = item.get_name().lower()
                    if any(keyword in name for keyword in ['cover', 'portada', 'front', 'titlepage']):
                        try:
                            return {
                                'filename': f"cover{os.path.splitext(item.get_name())[1]}",
                                'content': item.get_content(),
                                'mime_type': getattr(item, 'media_type', None) or 'image/jpeg'
                            }
                        except Exception:
                            continue

            return None

        except Exception as e:
            print(f"Error extrayendo portada: {e}")
            return None
    
    def get_chapters(self) -> List:
        """
        Retorna la lista de capítulos.
        
        Returns:
            List: Lista de capítulos
        """
        return self.chapters
    
    def get_metadata(self) -> Dict:
        """
        Retorna los metadatos del libro.
        
        Returns:
            Dict: Diccionario con los metadatos del libro
        """
        return self.metadata
    
    def get_chapter_html(self, chapter) -> str:
        """
        Obtiene el contenido HTML de un capítulo.

        Args:
            chapter: Objeto capítulo de ebooklib

        Returns:
            str: Contenido HTML del capítulo
        """
        try:
            content = chapter.get_content()
            return content.decode('utf-8')
        except Exception as e:
            print(f"Error obteniendo contenido HTML del capítulo: {e}")
            return "<html><body><p>Error al cargar el capítulo</p></body></html>"
    
    def convert_html_to_markdown(self, html_content: str, options: dict = None, chapter_title: str = None) -> str:
        """
        Convierte contenido HTML a formato Markdown.
        
        Args:
            html_content (str): Contenido HTML a convertir
            options (dict): Opciones de conversión
            chapter_title (str, optional): Título del capítulo actual
            
        Returns:
            str: Contenido en formato Markdown
        """
        if not html_content:
            return ""
            
        if options is None:
            options = {
                'add_numbering_to_content': False,
                'add_chapter_titles_to_content': True,
                'replace_css_classes': False
            }
            
        # Parsear HTML con BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remover scripts y estilos
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
            
        # Procesar el contenido del body
        body = soup.find('body') or soup
        
        # Procesar el contenido de forma recursiva
        markdown_content = self._process_element(body, options)
        
        # Asegurar que los elementos de bloque estén separados por saltos de línea
        # Reemplazar cualquier texto que vaya seguido de un elemento de bloque (sin salto de línea)
        # con un salto de línea doble
        result = re.sub(r'([^\n]+)(?=\n+[^\n])', r'\1\n\n', markdown_content)
        
        # Limpieza final
        result = re.sub(r'\n{3,}', '\n\n', result).strip()
        
        # Aplicar opciones adicionales
        result = self._apply_conversion_options(result, options, chapter_title)
        
        return result

    def _process_element(self, element, options: dict = None) -> str:
        """
        Procesa un elemento y sus hijos de forma recursiva.
        
        Args:
            element: Elemento HTML a procesar
            options (dict): Opciones de conversión
        """
        if options is None:
            options = {
                'add_numbering_to_content': False,
                'replace_css_classes': False
            }
        
        if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']:
            # Estos elementos deben estar separados por doble salto de línea
            return self._element_to_markdown(element, options) + '\n\n'
        
        if element.name == 'li':
            return "• " + self._element_to_markdown(element, options) + '\n'
        
        # Para otros elementos (como divs), procesar sus hijos
        content = []
        for child in element.children:
            if isinstance(child, str):
                # Si es un string, procesar saltos de línea
                text = child
                if text.strip():
                    # Reemplazar saltos de línea simples con dobles saltos de línea para que markdown los reconozca
                    text = re.sub(r'\n(?!\n)', '\n\n', text)
                    content.append(text)
            else:
                # Si es una etiqueta, procesarla recursivamente
                processed = self._process_element(child, options)
                if processed:
                    # Añadir separación entre elementos hermanos significativos
                    if content and content[-1].strip() and processed.strip():
                        content.append('\n\n')
                    content.append(processed)
        
        # Unir contenido
        result = "".join(content)
        
        # Limpiar espacios múltiples pero conservar los saltos de línea
        result = re.sub(r'(?<!\n) {2,}(?!\n)', ' ', result)
        
        return result.strip()

    def _element_to_markdown(self, element, options: dict = None) -> str:
        """
        Convierte un elemento HTML individual a formato Markdown.
        
        Args:
            element: Elemento HTML a convertir
            options (dict): Opciones de conversión
        """
        if options is None:
            options = {'replace_css_classes': False}
        
        # Procesar negritas
        for tag in element.find_all(['strong', 'b']):
            tag.insert_before('**')
            tag.insert_after('**')
            tag.unwrap()
            
        # Procesar cursivas
        for tag in element.find_all(['em', 'i']):
            tag.insert_before('*')
            tag.insert_after('*')
            tag.unwrap()
            
        # Procesar saltos de línea
        for br in element.find_all("br"):
            br.replace_with("\n")
        
        # Extraer texto preservando saltos de línea
        text_parts = []
        for child in element.children:
            if isinstance(child, str):
                # Si es un string, añadirlo directamente
                text_parts.append(child)
            else:
                # Si es una etiqueta, procesarla recursivamente
                text_parts.append(self._element_to_markdown(child, options))
        
        # Unir todas las partes
        text = "".join(text_parts)
        
        # Limpiar espacios múltiples pero conservar saltos de línea
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Convertir saltos de línea simples a dobles saltos de línea (párrafos)
        text = re.sub(r'\n(?!\n)', '\n\n', text)
        
        # Convertir saltos de línea múltiples a saltos dobles (párrafos)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Limpiar comillas dobles al principio y final si son las únicas cosas en la línea
        text = re.sub(r'^\s*"\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def _apply_conversion_options(self, content: str, options: dict, chapter_title: str = None) -> str:
        """
        Aplica las opciones adicionales de conversión al contenido.
        
        Args:
            content (str): Contenido en formato Markdown
            options (dict): Opciones de conversión
            chapter_title (str, optional): Título del capítulo actual
            
        Returns:
            str: Contenido con opciones aplicadas
        """
        result = content
        
        # Aplicar título del capítulo si está habilitado
        if options.get('add_chapter_titles_to_content', False) and chapter_title:
            result = f"# {chapter_title}\n\n{result}"
        
        # Aplicar numeración si está habilitada
        if options.get('add_numbering_to_content', False):
            result = self._add_numbering_to_content(result)
        
        return result
    
    def _add_numbering_to_content(self, content: str) -> str:
        """
        Añade numeración automática a los elementos del contenido.
        
        Args:
            content (str): Contenido en formato Markdown
            
        Returns:
            str: Contenido con numeración aplicada
        """
        lines = content.split('\n')
        numbered_lines = []
        paragraph_number = 1
        list_number = 1
        
        for line in lines:
            # Contar párrafos (líneas no vacías)
            if line.strip():
                # Si es un encabezado, no numerarlo
                if line.startswith('# '):
                    numbered_lines.append(line)
                # Si es una lista, numerarla
                elif line.strip().startswith('• '):
                    numbered_line = f"{list_number}. {line.strip()[2:]}"
                    numbered_lines.append(numbered_line)
                    list_number += 1
                # Si es un párrafo normal, numerarlo
                elif line.strip():
                    numbered_line = f"{paragraph_number}. {line.strip()}"
                    numbered_lines.append(numbered_line)
                    paragraph_number += 1
                # Si es una línea vacía, mantenerla
                else:
                    numbered_lines.append(line)
            else:
                numbered_lines.append(line)
        
        return '\n'.join(numbered_lines)