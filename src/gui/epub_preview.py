import sys
import os
import re
import mistune
from bs4 import BeautifulSoup
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QCheckBox, QGroupBox, QSplitter, QWidget,
                             QTextEdit, QFontComboBox, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.logic.epub_converter import EpubConverter

class EpubPreviewWindow(QDialog):
    """
    Ventana de vista previa para archivos EPUB.
    Permite navegar por los capítulos y ver una comparación lado a lado
    del capítulo original y el resultado renderizado en Markdown.
    """
    
    def __init__(self, epub_path: str, parent=None):
        """
        Inicializa la ventana de vista previa.
        
        Args:
            epub_path (str): Ruta al archivo EPUB
            parent: Widget padre
        """
        super().__init__(parent)
        self.epub_path = epub_path
        self.converter = EpubConverter(epub_path)
        self.chapters = self.converter.get_chapters()
        self.current_chapter_index = 0
        self.options = {
            'add_numbering_to_content': False,
            'add_chapter_titles_to_content': True,
            'replace_css_classes': False
        }
        self.current_font = "Bookerly"  # Fuente por defecto
        self.current_font_size = 11  # Tamaño de fuente por defecto
        
        self.init_ui()
        if self.chapters:
            self.load_chapter(0)
    
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        self.setWindowTitle("Vista Previa de EPUB")
        self.resize(1200, 600)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Layout superior con navegación y opciones
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(5, 2, 5, 2)  # Reducir márgenes verticales del layout superior
        top_layout.setSpacing(15)  # Espaciado horizontal entre elementos
        
        # Botones de navegación
        self.prev_button = QPushButton("<")
        self.next_button = QPushButton(">")
        self.prev_button.clicked.connect(self.prev_chapter)
        self.next_button.clicked.connect(self.next_chapter)
        self.prev_button.setFixedHeight(25)  # Altura fija para botones
        self.next_button.setFixedHeight(25)
        
        # Etiqueta de capítulo actual
        self.chapter_label = QLabel("Capítulo 1 de {}".format(len(self.chapters)))
        
        # Crear etiqueta de opciones
        options_label = QLabel("Opciones:")
        
        # Crear checkboxes y agregarlos directamente al layout superior
        self.numbering_checkbox = QCheckBox("Numeración")
        self.titles_checkbox = QCheckBox("Títulos")
        self.css_checkbox = QCheckBox("CSS")
        
        # Crear menú desplegable de fuentes
        self.font_selector = QFontComboBox()
        self.font_selector.setFixedWidth(120)
        self.font_selector.setCurrentFont(QFont(self.current_font))
        self.font_selector.setToolTip("Seleccionar fuente para la vista previa")
        self.font_selector.currentFontChanged.connect(self.change_font)
        
        # Crear menú desplegable de tamaño de fuente
        self.font_size_selector = QComboBox()
        self.font_size_selector.setFixedWidth(60)
        # Agregar tamaños de fuente comunes
        font_sizes = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "22", "24", "28", "32", "36", "48"]
        self.font_size_selector.addItems(font_sizes)
        self.font_size_selector.setCurrentText(str(self.current_font_size))
        self.font_size_selector.setToolTip("Seleccionar tamaño de fuente para la vista previa")
        self.font_size_selector.currentTextChanged.connect(self.change_font)
        
        # Agregar tooltips explicativos
        self.numbering_checkbox.setToolTip("Añade numeración automática a los párrafos y elementos del contenido")
        self.titles_checkbox.setToolTip("Inserta el título del capítulo al principio del contenido de cada capítulo")
        self.css_checkbox.setToolTip("Sustituye las clases CSS por marcadores de formato simples como **negrita** e *itálica*")
        
        # Establecer valores por defecto
        self.titles_checkbox.setChecked(True)
        
        # Conectar señales
        self.numbering_checkbox.stateChanged.connect(self.update_markdown_preview)
        self.titles_checkbox.stateChanged.connect(self.update_markdown_preview)
        self.css_checkbox.stateChanged.connect(self.update_markdown_preview)
        
        # Agregar widgets al layout superior en orden: botones, etiqueta, opciones
        top_layout.addWidget(self.prev_button)
        top_layout.addWidget(self.chapter_label)
        top_layout.addWidget(self.next_button)
        top_layout.addSpacing(20)  # Espacio entre navegación y opciones
        top_layout.addWidget(options_label)
        top_layout.addSpacing(5)  # Espacio pequeño entre etiqueta y checkboxes
        top_layout.addWidget(self.numbering_checkbox)
        top_layout.addWidget(self.titles_checkbox)
        top_layout.addWidget(self.css_checkbox)
        top_layout.addSpacing(10)  # Espacio entre opciones y selector de fuente
        top_layout.addWidget(QLabel("Fuente:"))
        top_layout.addWidget(self.font_selector)
        top_layout.addWidget(QLabel("Tamaño:"))
        top_layout.addWidget(self.font_size_selector)
        top_layout.addStretch()
        
        # Layout inferior con vistas previas
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Vista del EPUB original (como texto formateado)
        self.epub_view = QTextEdit()
        self.epub_view.setReadOnly(True)
        
        # Vista del Markdown renderizado (como texto formateado)
        self.markdown_view = QTextEdit()
        self.markdown_view.setReadOnly(True)
        
        splitter.addWidget(self.epub_view)
        splitter.addWidget(self.markdown_view)
        
        # Botones inferiores
        buttons_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancelar")
        self.import_button = QPushButton("Importar")
        self.cancel_button.clicked.connect(self.reject)
        self.import_button.clicked.connect(self.accept)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.import_button)
        
        # Agregar layouts al layout principal
        main_layout.addLayout(top_layout)
        main_layout.addWidget(splitter)
        main_layout.addLayout(buttons_layout)
        
        # Configurar el splitter
        splitter.setSizes([600, 600])
    
    def prev_chapter(self):
        """Navega al capítulo anterior."""
        if self.current_chapter_index > 0:
            self.load_chapter(self.current_chapter_index - 1)
    
    def next_chapter(self):
        """Navega al siguiente capítulo."""
        if self.current_chapter_index < len(self.chapters) - 1:
            self.load_chapter(self.current_chapter_index + 1)
    
    def load_chapter(self, index: int):
        """
        Carga un capítulo específico.
        
        Args:
            index (int): Índice del capítulo a cargar
        """
        if 0 <= index < len(self.chapters):
            self.current_chapter_index = index
            chapter = self.chapters[index]
            
            # Actualizar etiqueta
            self.chapter_label.setText(f"Capítulo {index + 1} de {len(self.chapters)}")
            
            # Cargar contenido HTML original
            html_content = self.converter.get_chapter_html(chapter)
            # Mostrar como HTML formateado en QTextEdit
            self.epub_view.setHtml(html_content)
            
            # Actualizar vista previa de Markdown
            self.update_markdown_preview()
            
            # Actualizar estado de botones
            self.prev_button.setEnabled(index > 0)
            self.next_button.setEnabled(index < len(self.chapters) - 1)
    
    def update_markdown_preview(self):
        """Actualiza la vista previa del Markdown."""
        # Obtener opciones actuales
        self.options = {
            'add_numbering_to_content': self.numbering_checkbox.isChecked(),
            'add_chapter_titles_to_content': self.titles_checkbox.isChecked(),
            'replace_css_classes': self.css_checkbox.isChecked()
        }
        
        # Obtener capítulo actual
        if self.chapters:
            chapter = self.chapters[self.current_chapter_index]
            html_content = self.converter.get_chapter_html(chapter)
            
            # Extraer título del capítulo si existe
            chapter_title = self._extract_chapter_title(chapter)
            
            # Convertir HTML a Markdown
            markdown_content = self.converter.convert_html_to_markdown(html_content, self.options, chapter_title)
            
            # Convertir Markdown a HTML usando mistune para la vista previa
            html_preview = mistune.html(markdown_content)
            
            # Aplicar fuente seleccionada al contenido renderizado
            font = self.font_selector.currentFont()
            font_family = font.family()
            font_size = int(self.font_size_selector.currentText())
            font.setPointSize(font_size)
            html_preview = f'<style>body {{ font-family: "{font_family}", serif; font-size: {font_size}px; }}</style>{html_preview}'
            
            self.markdown_view.setHtml(html_preview)
            self.markdown_view.setFont(font)
            
            # Aplicar fuente a la vista del EPUB original también
            self.epub_view.setFont(font)
    
    def change_font(self, font_or_size):
        """
        Cambia la fuente utilizada en las vistas previas.
        
        Args:
            font_or_size: Fuente seleccionada desde QFontComboBox (objeto QFont)
                         o tamaño de fuente desde QComboBox (string)
        """
        # Determinar si el cambio vino del selector de fuente o de tamaño
        if isinstance(font_or_size, QFont):
            # Cambio de fuente
            self.current_font = font_or_size.family()
        else:
            # Cambio de tamaño (font_or_size es un string)
            pass  # No necesitamos hacer nada con el string aquí
        
        # Obtener tamaño de fuente actual
        font_size = int(self.font_size_selector.currentText())
        
        # Crear nueva fuente con tamaño
        new_font = QFont(self.current_font)
        new_font.setPointSize(font_size)
        
        # Aplicar fuente a ambas vistas
        self.epub_view.setFont(new_font)
        
        # Actualizar vista previa de Markdown con la nueva fuente
        self.update_markdown_preview()
    
    def get_import_data(self) -> tuple[str, str, list[tuple[str, str]], dict]:
        """
        Obtiene los datos necesarios para la importación final.
        
        Returns:
            tuple: (título, autor, lista de capítulos, portada)
        """
        # Obtener metadatos del libro
        metadata = self.converter.get_metadata()
        title = metadata.get('title', "Libro Importado")
        author = metadata.get('author', "Autor Desconocido")
        
        # Obtener portada
        cover_image = self.converter.cover_image
        
        # Procesar todos los capítulos
        chapters_data = []
        for i, chapter in enumerate(self.chapters, 1):
            html_content = self.converter.get_chapter_html(chapter)
            # Extraer título del capítulo si existe
            chapter_title = self._extract_chapter_title(chapter)
            markdown_content = self.converter.convert_html_to_markdown(html_content, self.options, chapter_title)
            filename = f"Capítulo {i:03d}.txt"
            chapters_data.append((filename, markdown_content))
            
        return title, author, chapters_data, cover_image
    
    def _extract_chapter_title(self, chapter) -> str:
        """
        Extrae el título del capítulo desde el contenido HTML.
        
        Args:
            chapter: Objeto capítulo de ebooklib
            
        Returns:
            str: Título del capítulo o None si no se encuentra
        """
        try:
            html_content = self.converter.get_chapter_html(chapter)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar títulos en diferentes elementos
            title_elements = [
                soup.find('h1'),
                soup.find('h2'),
                soup.find('h3'),
                soup.find('title')
            ]
            
            for element in title_elements:
                if element and element.get_text().strip():
                    return element.get_text().strip()
            
            # Si no se encuentra un título, usar el nombre del archivo como fallback
            if hasattr(chapter, 'get_name'):
                filename = chapter.get_name()
                if filename:
                    # Remover extensión y limpiar el nombre
                    title = os.path.splitext(filename)[0]
                    title = re.sub(r'^[0-9_\-]+', '', title)  # Remover prefijos numéricos
                    title = title.replace('_', ' ').replace('-', ' ').strip()
                    if title:
                        return title
            
            return None
            
        except Exception as e:
            print(f"Error extrayendo título del capítulo: {e}")
            return None