from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QRadioButton, QGroupBox,
                           QFormLayout, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from src.logic.functions import get_cover_image, preview_image
from src.logic.database import TranslationDatabase

class CreateEpubPanel(QWidget):
    # Señales para comunicar con la ventana principal
    epub_creation_requested = pyqtSignal(dict)  # Emite los datos para crear el EPUB
    status_message_requested = pyqtSignal(str, int)  # Emite mensaje para barra de estado (mensaje, timeout)
    metadata_saved = pyqtSignal()  # Emite cuando se guardan metadatos para actualizar título de ventana

    def __init__(self):
        super().__init__()
        self.cover_path = None
        self.working_directory = None  # Directorio de trabajo actual
        self.db = None  # Base de datos para metadatos
        self.main_window = None  # Referencia a la ventana principal
        # Note: init_ui() will be called after set_main_window is called

    def set_main_window(self, main_window):
        """Establece la referencia a la ventana principal y inicializa la UI."""
        self.main_window = main_window
        self.init_ui()

    def _get_string(self, key, default_text=""):
        """Get a localized string from the language manager."""
        if self.main_window and hasattr(self.main_window, 'lang_manager'):
            return self.main_window.lang_manager.get_string(key, default_text)
        # If main_window is not set yet, return the default text or key
        return default_text if default_text else key

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()

        # Top section with metadata and cover
        top_layout = QHBoxLayout()

        # Left side - Metadata form
        metadata_layout = QFormLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(self._get_string("create_panel.title_placeholder"))
        self.title_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        metadata_layout.addRow(self._get_string("create_panel.title_label"), self.title_input)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText(self._get_string("create_panel.author_placeholder"))
        self.author_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        metadata_layout.addRow(self._get_string("create_panel.author_label"), self.author_input)

        # Right side - Cover section
        cover_layout = QVBoxLayout()

        # Preview label with 3:4 proportion (165x220)
        self.cover_preview = QLabel()
        self.cover_preview.setFixedSize(165, 220)
        self.cover_preview.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border-radius: 5px;
            }
        """)
        self.cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_preview.setText(self._get_string("create_panel.cover_label"))

        # Cover buttons layout (vertical)
        cover_buttons_layout = QVBoxLayout()
        self.cover_select_button = QPushButton(self._get_string("create_panel.cover_select_button"))
        self.cover_clear_button = QPushButton(self._get_string("create_panel.cover_clear_button"))

        self.cover_select_button.clicked.connect(self.select_cover)
        self.cover_clear_button.clicked.connect(self.clear_cover)

        # Add buttons in vertical order: Select on top, Clear below
        cover_buttons_layout.addWidget(self.cover_select_button)
        cover_buttons_layout.addWidget(self.cover_clear_button)

        # Add cover buttons to cover layout after cover preview
        cover_layout.addWidget(self.cover_preview)
        cover_layout.addLayout(cover_buttons_layout)

        # Add metadata and cover to top layout
        top_layout.addLayout(metadata_layout)
        top_layout.addLayout(cover_layout)

        # Description section
        description_layout = QVBoxLayout()
        description_label = QLabel(self._get_string("create_panel.description_label"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText(self._get_string("create_panel.description_placeholder"))
        # Eliminar el límite de altura para que ocupe todo el espacio disponible
        description_layout.addWidget(description_label)
        description_layout.addWidget(self.description_input)

        # Add description to metadata layout after author
        metadata_layout.addRow(description_label)
        metadata_layout.addRow(self.description_input)

        # Range section
        range_group = QGroupBox(self._get_string("create_panel.range_group"))
        range_layout = QVBoxLayout()

        self.range_all = QRadioButton(self._get_string("create_panel.range_all"))
        self.range_all.setChecked(True)

        range_specific_layout = QHBoxLayout()
        self.range_specific = QRadioButton(self._get_string("create_panel.range_specific"))
        self.range_from_input = QLineEdit()
        self.range_from_input.setPlaceholderText(self._get_string("create_panel.range_from_placeholder"))
        range_to_label = QLabel(self._get_string("create_panel.range_to"))
        self.range_to_input = QLineEdit()
        self.range_to_input.setPlaceholderText(self._get_string("create_panel.range_to_placeholder"))

        # Configurar el layout del rango específico
        range_specific_layout.addWidget(self.range_specific)
        range_specific_layout.addWidget(self.range_from_input)
        range_specific_layout.addWidget(range_to_label)
        range_specific_layout.addWidget(self.range_to_input)

        # Conectar señales para habilitar/deshabilitar inputs
        self.range_all.toggled.connect(self.toggle_range_inputs)
        self.range_specific.toggled.connect(self.toggle_range_inputs)

        range_layout.addWidget(self.range_all)
        range_layout.addLayout(range_specific_layout)
        range_group.setLayout(range_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Save metadata button
        self.save_metadata_button = QPushButton(self._get_string("create_panel.save_metadata_button"))
        self.save_metadata_button.clicked.connect(self.save_metadata)
        self.save_metadata_button.setEnabled(False)  # Deshabilitado hasta tener directorio
        self.save_metadata_button.setToolTip(
            self._get_string("create_panel.save_metadata_button.tooltip")
        )

        # Create button
        self.create_button = QPushButton(self._get_string("create_panel.create_button"))
        self.create_button.clicked.connect(self.request_epub_creation)

        buttons_layout.addWidget(self.save_metadata_button)
        buttons_layout.addWidget(self.create_button)

        # Add all elements to main layout
        main_layout.addLayout(top_layout)
        main_layout.addWidget(range_group)
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        # Inicializar estado de los inputs de rango
        self.toggle_range_inputs()
        
    def select_cover(self):
        """Maneja la selección de la imagen de portada"""
        file_path, pixmap = get_cover_image(self.working_directory)
        if file_path and pixmap:
            self.cover_path = file_path
            preview_image(pixmap, self.cover_preview)

    def clear_cover(self):
        """Limpia la imagen de portada"""
        self.cover_path = None
        self.cover_preview.clear()
        self.cover_preview.setText(self._get_string("create_panel.cover_label"))

    def toggle_range_inputs(self):
        """Habilita/deshabilita los inputs de rango según la selección"""
        enable_inputs = self.range_specific.isChecked()
        self.range_from_input.setEnabled(enable_inputs)
        self.range_to_input.setEnabled(enable_inputs)

    def _set_text_and_show_start(self, line_edit, text):
        """Establece el texto en un QLineEdit y asegura que se muestre el principio del texto"""
        line_edit.setText(text)
        # Mover el cursor al inicio para asegurar que se muestra el principio del texto
        line_edit.setCursorPosition(0)
        # Desplazar el texto para mostrar el inicio
        line_edit.home(False)

    def get_range(self):
        """Obtiene el rango seleccionado"""
        if self.range_all.isChecked():
            return None, None

        try:
            start = int(self.range_from_input.text()) if self.range_from_input.text() else None
            end = int(self.range_to_input.text()) if self.range_to_input.text() else None
            return start, end
        except ValueError:
            return None, None

    def request_epub_creation(self):
        """Recopila los datos y emite la señal para crear el EPUB"""
        start_chapter, end_chapter = self.get_range()

        data = {
            'title': self.title_input.text().strip(),
            'author': self.author_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'cover_path': self.cover_path,
            'start_chapter': start_chapter,
            'end_chapter': end_chapter
        }

        # Emitir señal para solicitar confirmación antes de crear el EPUB
        from src.logic.functions import show_confirmation_dialog
        if show_confirmation_dialog(self._get_string("create_panel.epub_creation.confirmation")):
            self.epub_creation_requested.emit(data)

    def reset_form(self):
        """Reinicia solo la portada y el rango, mantiene título, autor y descripción"""
        # No limpiar título, autor ni descripción - mantener los datos
        # self.title_input.clear()
        # self.author_input.clear()
        # self.description_input.clear()
        self.clear_cover()
        self.range_all.setChecked(True)
        self.range_from_input.clear()
        self.range_to_input.clear()

    def set_working_directory(self, directory):
        """Establece el directorio de trabajo y busca portada automáticamente"""
        self.working_directory = directory
        self.db = TranslationDatabase(directory)
        self.save_metadata_button.setEnabled(True)
        self.auto_load_cover()
        self.load_metadata()

    def load_metadata(self):
        """Carga los metadatos guardados del directorio actual"""
        if not self.db:
            return

        try:
            metadata = self.db.get_book_metadata()
            if metadata.get('title'):
                self._set_text_and_show_start(self.title_input, metadata['title'])
            if metadata.get('author'):
                self._set_text_and_show_start(self.author_input, metadata['author'])
            if metadata.get('description'):
                self.description_input.setPlainText(metadata['description'])
        except Exception as e:
            print(f"Error cargando metadatos: {e}")

    def save_metadata(self):
        """Guarda manualmente los metadatos del libro"""
        if not self.db:
            return

        title = self.title_input.text().strip()
        author = self.author_input.text().strip()
        description = self.description_input.toPlainText().strip()

        if not title and not author and not description:
            from src.logic.functions import show_error_dialog
            show_error_dialog(self._get_string("create_panel.metadata.save_empty"))
            return

        try:
            success = self.db.save_book_metadata(title, author, description)
            if success:
                # Emitir señal para mostrar mensaje en barra de estado
                self.status_message_requested.emit(self._get_string("create_panel.metadata.save_success"), 3000)
                # Emitir señal para actualizar título de ventana
                self.metadata_saved.emit()
            else:
                self.status_message_requested.emit(self._get_string("create_panel.metadata.save_error"), 5000)
        except Exception as e:
            self.status_message_requested.emit(
                self._get_string("create_panel.metadata.save_error_general").format(error=str(e)), 5000)

    def auto_load_cover(self):
        """Busca automáticamente una imagen de portada en el directorio de trabajo"""
        if not self.working_directory:
            return

        import os
        # Patrones comunes de nombres de portada
        cover_patterns = [
            'cover.jpg', 'cover.jpeg', 'cover.png',
            'portada.jpg', 'portada.jpeg', 'portada.png',
            'Cover.jpg', 'Cover.jpeg', 'Cover.png',
            'Portada.jpg', 'Portada.jpeg', 'Portada.png',
            'COVER.jpg', 'COVER.jpeg', 'COVER.png',
            'PORTADA.jpg', 'PORTADA.jpeg', 'PORTADA.png'
        ]

        for pattern in cover_patterns:
            potential_cover = os.path.join(self.working_directory, pattern)
            if os.path.exists(potential_cover):
                try:
                    from PyQt6.QtGui import QPixmap
                    pixmap = QPixmap(potential_cover)
                    if not pixmap.isNull():
                        self.cover_path = potential_cover
                        preview_image(pixmap, self.cover_preview)
                        break
                except Exception:
                    continue

