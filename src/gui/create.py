from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QRadioButton, QGroupBox,
                           QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from src.logic.functions import get_cover_image, preview_image

class CreateEpubPanel(QWidget):
    # Señales para comunicar con la ventana principal
    epub_creation_requested = pyqtSignal(dict)  # Emite los datos para crear el EPUB

    def __init__(self):
        super().__init__()
        self.cover_path = None
        self.working_directory = None  # Directorio de trabajo actual
        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Metadata section
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Ingrese el título del libro")
        form_layout.addRow("Título:", self.title_input)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Ingrese el nombre del autor")
        form_layout.addRow("Autor:", self.author_input)

        # Cover section
        cover_group = QGroupBox("Portada")
        cover_layout = QVBoxLayout()

        # Preview label with fixed size and border
        self.cover_preview = QLabel()
        self.cover_preview.setFixedSize(150, 150)
        self.cover_preview.setStyleSheet("""
            QLabel {
                border: 2px solid #cccccc;
                background-color: #f5f5f5;
                border-radius: 5px;
            }
        """)
        self.cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_preview.setText("Sin imagen")

        # Cover buttons layout
        cover_buttons_layout = QHBoxLayout()
        self.cover_select_button = QPushButton("Seleccionar")
        self.cover_clear_button = QPushButton("Limpiar")

        self.cover_select_button.clicked.connect(self.select_cover)
        self.cover_clear_button.clicked.connect(self.clear_cover)

        cover_buttons_layout.addWidget(self.cover_select_button)
        cover_buttons_layout.addWidget(self.cover_clear_button)

        cover_layout.addWidget(self.cover_preview)
        cover_layout.addLayout(cover_buttons_layout)
        cover_group.setLayout(cover_layout)

        # Range section
        range_group = QGroupBox("Rango de capítulos")
        range_layout = QVBoxLayout()

        self.range_all = QRadioButton("Todos los capítulos")
        self.range_all.setChecked(True)

        range_specific_layout = QHBoxLayout()
        self.range_specific = QRadioButton("Especificar rango:")
        self.range_from_input = QLineEdit()
        self.range_from_input.setPlaceholderText("Desde")
        range_to_label = QLabel("a")
        self.range_to_input = QLineEdit()
        self.range_to_input.setPlaceholderText("Hasta")

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

        # Create button
        self.create_button = QPushButton("Crear EPUB")
        self.create_button.clicked.connect(self.request_epub_creation)

        # Add all elements to main layout
        main_layout.addLayout(form_layout)
        main_layout.addWidget(cover_group)
        main_layout.addWidget(range_group)
        main_layout.addWidget(self.create_button)
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
        self.cover_preview.setText("Sin imagen")

    def toggle_range_inputs(self):
        """Habilita/deshabilita los inputs de rango según la selección"""
        enable_inputs = self.range_specific.isChecked()
        self.range_from_input.setEnabled(enable_inputs)
        self.range_to_input.setEnabled(enable_inputs)

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
            'cover_path': self.cover_path,
            'start_chapter': start_chapter,
            'end_chapter': end_chapter
        }

        self.epub_creation_requested.emit(data)

    def reset_form(self):
        """Reinicia el formulario a su estado inicial"""
        self.title_input.clear()
        self.author_input.clear()
        self.clear_cover()
        self.range_all.setChecked(True)
        self.range_from_input.clear()
        self.range_to_input.clear()

    def set_working_directory(self, directory):
        """Establece el directorio de trabajo y busca portada automáticamente"""
        self.working_directory = directory
        self.auto_load_cover()

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
                        # Mostrar mensaje de confirmación
                        self.show_auto_cover_message(os.path.basename(potential_cover))
                        break
                except Exception:
                    continue

    def show_auto_cover_message(self, filename):
        """Muestra un mensaje temporal indicando que se encontró una portada"""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QFont
        
        # Crear etiqueta temporal
        self.auto_cover_label = QLabel(f"✓ Portada encontrada: {filename}")
        self.auto_cover_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
        """)
        
        # Añadir la etiqueta al layout principal
        layout = self.layout()
        layout.insertWidget(0, self.auto_cover_label)
        
        # Configurar timer para ocultar el mensaje después de 3 segundos
        QTimer.singleShot(3000, self.hide_auto_cover_message)

    def hide_auto_cover_message(self):
        """Oculta el mensaje de portada encontrada"""
        if hasattr(self, 'auto_cover_label'):
            self.auto_cover_label.deleteLater()
            del self.auto_cover_label
