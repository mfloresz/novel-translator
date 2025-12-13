import zipfile
import os
import re
from typing import List, Dict, Optional
from datetime import datetime
import base64
from .xml_utils import escape_xml

class EpubMetadata:
    """Clase para metadatos del EPUB"""
    def __init__(self, title="", author="", description="", language="es", 
                 cover=None, show_toc=True, patterns=None, collection=None):
        self.title = title
        self.author = author
        self.description = description
        self.language = language
        self.cover = cover
        self.show_toc = show_toc
        self.patterns = patterns or []
        self.collection = collection
        self.publisher = "Tomo App"  # Como solicita el usuario

class ChapterData:
    """Clase para datos de capítulo"""
    def __init__(self, title="", content=""):
        self.title = title
        self.content = content

class EpubGenerator:
    """Generador de archivos EPUB replicando la funcionalidad del proyecto Vue"""
    
    def __init__(self):
        self.default_css = """/* Reset and base styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: "Libre Baskerville", "Times New Roman", serif;
  font-size: 1em;
  line-height: 1.6;
  margin: 0 auto;
  max-width: 100%;
  padding: 0;
  text-align: justify;
  color: #333;
  background: #fff;
}

/* Headings */
h1 {
  font-size: 1.5em;
  font-weight: bold;
  text-align: center;
  margin: 2em 0 1em 0;
  page-break-before: always;
  line-height: 1.2;
}

h2 {
  font-size: 1.25em;
  font-weight: bold;
  margin: 1.5em 0 0.5em 0;
  text-align: left;
}

h3 {
  font-size: 1.1em;
  font-weight: bold;
  margin: 1.25em 0 0.5em 0;
  text-align: left;
}

/* Paragraphs */
p {
  text-indent: 1.5em;
  margin: 0 0 1em 0;
  text-align: justify;
  orphans: 2;
  widows: 2;
}

p:first-of-type {
  text-indent: 0;
}

/* Images */
img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1em auto;
  border-radius: 4px;
}

/* Special pages */
.titlepage {
  text-align: center;
  page-break-after: always;
  padding: 2em 1em;
}

.cover {
  text-align: center;
  page-break-after: always;
  padding: 2em 1em;
}

/* Separators */
hr {
  margin: 2em auto;
  border: none;
  border-top: 1px solid #666;
  width: 50%;
  page-break-after: avoid;
}

/* Quotes and emphasis */
blockquote {
  margin: 1em 2em;
  font-style: italic;
  border-left: 4px solid #ccc;
  padding-left: 1em;
}

em, i {
  font-style: italic;
}

strong, b {
  font-weight: bold;
}

/* Lists */
ul, ol {
  margin: 1em 0;
  padding-left: 2em;
}

li {
  margin-bottom: 0.5em;
}

/* Code and preformatted text */
code {
  font-family: "Courier New", monospace;
  background: #f5f5f5;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 0.9em;
}

pre {
  font-family: "Courier New", monospace;
        # Aplicar procesamiento de texto usando el procesador existente
        # La importación se hace localmente para evitar problemas circulares
        try:
            from .epub_text_processor import EpubTextProcessor
            processor = EpubTextProcessor()
            processed_content = processor.process_chapter_with_python_rules(content, patterns)
        except ImportError:

            # Fallback si no está disponible el procesador
            processed_content = f'<p>{self._escape_xml(content)}</p>'
  background: #f5f5f5;
  padding: 1em;
  border-radius: 4px;
  margin: 1em 0;
  overflow-x: auto;
  white-space: pre-wrap;
}

/* Links */
a {
  color: #0066cc;
  text-decoration: underline;
}

/* Tables */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
}

th, td {
  border: 1px solid #ccc;
  padding: 0.5em;
  text-align: left;
}

th {
  background: #f5f5f5;
  font-weight: bold;
}

/* Page breaks */
.page-break {
  page-break-before: always;
}

/* Print-specific styles */
@media print {
  body {
    font-size: 12pt;
  }

  h1 {
    font-size: 18pt;
  }

  p {
    text-indent: 1.5em;
  }
}"""

    def generate_epub_file(self, metadata: EpubMetadata, chapters: List[ChapterData]) -> bytes:
        """
        Genera un archivo EPUB usando zipfile nativo de Python
        """
        import io
        
        # Crear buffer en memoria para el ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
            # Crear estructura de directorios
            epub_dir = 'EPUB'
            meta_dir = 'META-INF'
            
            # Agregar portada si existe
            if metadata.cover and os.path.exists(metadata.cover):
                try:
                    with open(metadata.cover, 'rb') as cover_file:
                        epub_zip.writestr(f'{epub_dir}/cover.jpg', cover_file.read())
                except Exception as e:
                    print(f"Advertencia: No se pudo agregar la portada: {e}")
            
            # Generar contenido de archivos
            container_xml, content_opf, toc_ncx, toc_xhtml = self._generate_epub_structure(metadata, chapters)
            
            # META-INF/container.xml
            epub_zip.writestr(f'{meta_dir}/container.xml', container_xml)
            
            # EPUB/content.opf
            epub_zip.writestr(f'{epub_dir}/content.opf', content_opf)
            
            # EPUB/toc.ncx (para compatibilidad con lectores antiguos)
            epub_zip.writestr(f'{epub_dir}/toc.ncx', toc_ncx)
            
            # EPUB/toc.xhtml (navegación EPUB3)
            epub_zip.writestr(f'{epub_dir}/toc.xhtml', toc_xhtml)
            
            # EPUB/css/styles.css
            epub_zip.writestr(f'{epub_dir}/css/styles.css', self.default_css)
            
            # Generar capítulos HTML
            for i, chapter in enumerate(chapters):
                filename = f'chapter{i + 1}.xhtml'
                html_content = self._generate_chapter_html(chapter.title, chapter.content, metadata.patterns)
                epub_zip.writestr(f'{epub_dir}/{filename}', html_content)
        
        return zip_buffer.getvalue()

    def _generate_epub_structure(self, metadata: EpubMetadata, chapters: List[ChapterData]):
        """Genera la estructura XML del EPUB"""
        book_id = f"book-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now().isoformat()
        
        # META-INF/container.xml
        container_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
        
        # EPUB/content.opf
        content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
  <package version="3.0" xml:lang="{metadata.language}" xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
      <dc:identifier id="book-id">{book_id}</dc:identifier>
      <dc:title>{self._escape_xml(metadata.title)}</dc:title>
      <dc:creator>{self._escape_xml(metadata.author)}</dc:creator>
      <dc:publisher>{metadata.publisher}</dc:publisher>
      <dc:language>{metadata.language}</dc:language>
      <dc:date>{now.split('T')[0]}</dc:date>
      <meta property="dcterms:modified">{now}</meta>'''
        
        if metadata.description:
            # Convertir saltos de línea a entidades XML para preservar en metadatos
            escaped_desc = self._escape_xml(metadata.description).replace('\n', '&#10;')
            content_opf += f'''
      <dc:description>{escaped_desc}</dc:description>'''
        
        # Agregar metadatos de serie/colección
        if metadata.collection:
            content_opf += f'''
      <meta property="belongs-to-collection" id="collection">{self._escape_xml(metadata.collection['name'])}</meta>
      <meta refines="#collection" property="collection-type">{metadata.collection['type']}</meta>
      <meta refines="#collection" property="group-position">{metadata.collection['position']}</meta>'''
        
        content_opf += f'''
    </metadata>
    <manifest>
      <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>
      <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
      <item id="css" href="css/styles.css" media-type="text/css"/>'''
        
        if metadata.cover:
            content_opf += '''
      <item id="cover" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>'''
        
        # Agregar capítulos al manifest
        for i in range(len(chapters)):
            content_opf += f'''
      <item id="chapter{i + 1}" href="chapter{i + 1}.xhtml" media-type="application/xhtml+xml"/>'''
        
        content_opf += f'''
    </manifest>
    <spine{" toc=\"ncx\"" if metadata.show_toc else ""}>'''
        
        if metadata.cover:
            content_opf += '''
      <itemref idref="cover"/>'''
        
        if metadata.show_toc:
            content_opf += '''
      <itemref idref="toc"/>'''
        
        # Agregar referencias a capítulos
        for i in range(len(chapters)):
            content_opf += f'''
      <itemref idref="chapter{i + 1}"/>'''
        
        content_opf += '''
  </spine>
</package>'''
        
        # EPUB/toc.ncx (NCX para compatibilidad)
        toc_ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xml:lang="{metadata.language}" xmlns="http://www.daisy.org/z3986/2005/ncx/">
  <head>
    <meta name="dtb:uid" content="{book_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{self._escape_xml(metadata.title)}</text>
  </docTitle>
  <navMap>'''
        
        play_order = 1
        
        if metadata.cover:
            toc_ncx += f'''
    <navPoint id="nav0" playOrder="{play_order}">
      <navLabel>
        <text>Portada</text>
      </navLabel>
      <content src="cover.jpg"/>
    </navPoint>'''
            play_order += 1
        
        if metadata.show_toc:
            toc_ncx += f'''
    <navPoint id="toc" playOrder="{play_order}">
      <navLabel>
        <text>Table of Contents</text>
      </navLabel>
      <content src="toc.xhtml"/>
    </navPoint>'''
            play_order += 1
        
        for i, chapter in enumerate(chapters):
            toc_ncx += f'''
    <navPoint id="nav{i + 1}" playOrder="{play_order}">
      <navLabel>
        <text>{self._escape_xml(chapter.title)}</text>
      </navLabel>
      <content src="chapter{i + 1}.xhtml"/>
    </navPoint>'''
            play_order += 1
        
        toc_ncx += '''
  </navMap>
</ncx>'''
        
        # EPUB/toc.xhtml (navegación EPUB3)
        toc_xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head>
    <title>{self._escape_xml(metadata.title)}</title>
  </head>
  <body>
    <nav epub:type="toc">
      <h1>Table of Contents</h1>
      <ol>'''
        
        if metadata.cover:
            toc_xhtml += '''
        <li><a href="cover.jpg">Portada</a></li>'''
        
        for i, chapter in enumerate(chapters):
            toc_xhtml += f'''
        <li><a href="chapter{i + 1}.xhtml">{self._escape_xml(chapter.title)}</a></li>'''
        
        toc_xhtml += '''
      </ol>
    </nav>
  </body>
</html>'''
        
        return container_xml, content_opf, toc_ncx, toc_xhtml

    def _generate_chapter_html(self, title: str, content: str, patterns: List[Dict]) -> str:
        """Genera HTML completo de un capítulo incluyendo título y estructura"""
        # Aplicar procesamiento de texto (esto será implementado en el procesador de texto)
        from .epub_text_processor import EpubTextProcessor
        processor = EpubTextProcessor()
        processed_content = processor.process_chapter_content(content, patterns)
        
        return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{self._escape_xml(title)}</title>
</head>
<body>
  <h1>{self._escape_xml(title)}</h1>
  {processed_content}
</body>
</html>'''

    def _escape_xml(self, unsafe: str) -> str:
        """Escapa caracteres XML"""
        return escape_xml(unsafe)

    def create_title_page_html(self, title: str, author: str, description: str = "") -> str:
        """Crea HTML para la página de título"""
        html = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{self._escape_xml(title)}</title>
</head>
<body>
  <div class="titlepage">
    <h1>{self._escape_xml(title)}</h1>
    <p>por {self._escape_xml(author)}</p>'''

        if description:
            # Convertir saltos de línea a <br> para preservar párrafos en HTML
            escaped_desc = self._escape_xml(description).replace('\n', '<br>')
            html += f'''
    <p>{escaped_desc}</p>'''

        html += '''
  </div>
</body>
</html>'''

        return html

    def generate_epub_filename(self, title: str, author: str) -> str:
        """Genera nombre de archivo seguro para el EPUB"""
        import re
        clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title).replace(' ', '_')
        clean_author = re.sub(r'[^a-zA-Z0-9\s]', '', author).replace(' ', '_')
        return f"{clean_title}_{clean_author}.epub"