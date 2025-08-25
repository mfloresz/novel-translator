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
    
    def __init__(self, epub_path: str, lang_manager, parent=None):
        """
        Inicializa la ventana de vista previa.
        
        Args:
            epub_path (str): Ruta al archivo EPUB
            lang_manager: Gestor de idiomas
            parent: Widget padre
        """
        super().__init__(parent)
        self.epub_path = epub_path
        self.lang_manager = lang_manager
        self.converter = EpubConverter(epub_path)
        self.chapters = self.converter.get_chapters()
        self.current_chapter_index = 0
        self.options = {
            'add_numbering_to_content': False,
            'add_chapter_titles_to_content': True,
            'replace_css_classes': False
        }
        self.current_font = "Bookerly"
        self.current_font_size = 11
        
        self.init_ui()
        if self.chapters:
            self.load_chapter(0)
    
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        self.setWindowTitle(self.lang_manager.get_string("epub_preview_window.title"))
        self.resize(1200, 600)
        
        main_layout = QVBoxLayout(self)
        
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(5, 2, 5, 2)
        top_layout.setSpacing(15)
        
        self.prev_button = QPushButton("<")
        self.next_button = QPushButton(">")
        self.prev_button.clicked.connect(self.prev_chapter)
        self.next_button.clicked.connect(self.next_chapter)
        self.prev_button.setFixedHeight(25)
        self.next_button.setFixedHeight(25)
        
        self.chapter_label = QLabel()
        
        options_label = QLabel(self.lang_manager.get_string("epub_preview_window.options_label"))
        
        self.numbering_checkbox = QCheckBox(self.lang_manager.get_string("epub_preview_window.numbering_checkbox"))
        self.titles_checkbox = QCheckBox(self.lang_manager.get_string("epub_preview_window.titles_checkbox"))
        self.css_checkbox = QCheckBox(self.lang_manager.get_string("epub_preview_window.css_checkbox"))
        
        self.font_selector = QFontComboBox()
        self.font_selector.setFixedWidth(120)
        self.font_selector.setCurrentFont(QFont(self.current_font))
        self.font_selector.setToolTip(self.lang_manager.get_string("epub_preview_window.font_selector_tooltip"))
        self.font_selector.currentFontChanged.connect(self.change_font)
        
        self.font_size_selector = QComboBox()
        self.font_size_selector.setFixedWidth(60)
        font_sizes = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "22", "24", "28", "32", "36", "48"]
        self.font_size_selector.addItems(font_sizes)
        self.font_size_selector.setCurrentText(str(self.current_font_size))
        self.font_size_selector.setToolTip(self.lang_manager.get_string("epub_preview_window.font_size_selector_tooltip"))
        self.font_size_selector.currentTextChanged.connect(self.change_font)
        
        self.numbering_checkbox.setToolTip(self.lang_manager.get_string("epub_preview_window.numbering_tooltip"))
        self.titles_checkbox.setToolTip(self.lang_manager.get_string("epub_preview_window.titles_tooltip"))
        self.css_checkbox.setToolTip(self.lang_manager.get_string("epub_preview_window.css_tooltip"))
        
        self.titles_checkbox.setChecked(True)
        
        self.numbering_checkbox.stateChanged.connect(self.update_markdown_preview)
        self.titles_checkbox.stateChanged.connect(self.update_markdown_preview)
        self.css_checkbox.stateChanged.connect(self.update_markdown_preview)
        
        top_layout.addWidget(self.prev_button)
        top_layout.addWidget(self.chapter_label)
        top_layout.addWidget(self.next_button)
        top_layout.addSpacing(20)
        top_layout.addWidget(options_label)
        top_layout.addSpacing(5)
        top_layout.addWidget(self.numbering_checkbox)
        top_layout.addWidget(self.titles_checkbox)
        top_layout.addWidget(self.css_checkbox)
        top_layout.addSpacing(10)
        top_layout.addWidget(QLabel(self.lang_manager.get_string("epub_preview_window.font_label")))
        top_layout.addWidget(self.font_selector)
        top_layout.addWidget(QLabel(self.lang_manager.get_string("epub_preview_window.font_size_label")))
        top_layout.addWidget(self.font_size_selector)
        top_layout.addStretch()
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.epub_view = QTextEdit()
        self.epub_view.setReadOnly(True)
        
        self.markdown_view = QTextEdit()
        self.markdown_view.setReadOnly(True)
        
        splitter.addWidget(self.epub_view)
        splitter.addWidget(self.markdown_view)
        
        buttons_layout = QHBoxLayout()
        self.cancel_button = QPushButton(self.lang_manager.get_string("epub_preview_window.cancel_button"))
        self.import_button = QPushButton(self.lang_manager.get_string("epub_preview_window.import_button"))
        self.cancel_button.clicked.connect(self.reject)
        self.import_button.clicked.connect(self.accept)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.import_button)
        
        main_layout.addLayout(top_layout)
        main_layout.addWidget(splitter)
        main_layout.addLayout(buttons_layout)
        
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
            
            self.chapter_label.setText(
                self.lang_manager.get_string("epub_preview_window.chapter_label").format(
                    index=index + 1, total=len(self.chapters)
                )
            )
            
            html_content = self.converter.get_chapter_html(chapter)
            self.epub_view.setHtml(html_content)
            
            self.update_markdown_preview()
            
            self.prev_button.setEnabled(index > 0)
            self.next_button.setEnabled(index < len(self.chapters) - 1)
    
    def update_markdown_preview(self):
        """Actualiza la vista previa del Markdown."""
        self.options = {
            'add_numbering_to_content': self.numbering_checkbox.isChecked(),
            'add_chapter_titles_to_content': self.titles_checkbox.isChecked(),
            'replace_css_classes': self.css_checkbox.isChecked()
        }
        
        if self.chapters:
            chapter = self.chapters[self.current_chapter_index]
            html_content = self.converter.get_chapter_html(chapter)
            
            chapter_title = self._extract_chapter_title(chapter)
            
            markdown_content = self.converter.convert_html_to_markdown(html_content, self.options, chapter_title)
            
            html_preview = mistune.html(markdown_content)
            
            font = self.font_selector.currentFont()
            font_family = font.family()
            font_size = int(self.font_size_selector.currentText())
            font.setPointSize(font_size)
            html_preview = f'<style>body {{ font-family: "{font_family}", serif; font-size: {font_size}px; }}</style>{html_preview}'
            
            self.markdown_view.setHtml(html_preview)
            self.markdown_view.setFont(font)
            
            self.epub_view.setFont(font)
    
    def change_font(self, font_or_size):
        """
        Cambia la fuente utilizada en las vistas previas.
        
        Args:
            font_or_size: Fuente seleccionada desde QFontComboBox (objeto QFont)
                         o tamaño de fuente desde QComboBox (string)
        """
        if isinstance(font_or_size, QFont):
            self.current_font = font_or_size.family()
        
        font_size = int(self.font_size_selector.currentText())
        
        new_font = QFont(self.current_font)
        new_font.setPointSize(font_size)
        
        self.epub_view.setFont(new_font)
        
        self.update_markdown_preview()
    
    def get_import_options(self) -> tuple[str, str, dict]:
        """
        Obtiene las opciones de importación seleccionadas por el usuario.
        
        Returns:
            tuple: (título, autor, opciones)
        """
        metadata = self.converter.get_metadata()
        title = metadata.get('title', self.lang_manager.get_string("epub_preview_window.default_book_title"))
        author = metadata.get('author', self.lang_manager.get_string("epub_preview_window.default_author"))
        
        self.options = {
            'add_numbering_to_content': self.numbering_checkbox.isChecked(),
            'add_chapter_titles_to_content': self.titles_checkbox.isChecked(),
            'replace_css_classes': self.css_checkbox.isChecked()
        }
        
        return title, author, self.options
    
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
                    title = re.sub(r'^[0-9_\-]+', '', title)
                    title = title.replace('_', ' ').replace('-', ' ').strip()
                    if title:
                        return title
            
            return None
            
        except Exception as e:
            print(f"Error extrayendo título del capítulo: {e}")
            return None
