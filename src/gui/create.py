from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QRadioButton, QGroupBox,
                           QFormLayout, QTextEdit, QComboBox, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox, QToolButton,
                           QMenu, QWidgetAction, QFrame, QVBoxLayout as QVBoxLayoutWidget,
                           QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QIntValidator, QIcon, QPixmap, QAction
from src.logic.functions import get_cover_image, preview_image
from src.logic.database import TranslationDatabase
import re

class EpubPattern:
    """Clase para representar un patrón EPUB"""
    def __init__(self, pattern="", action="center"):
        self.pattern = pattern
        self.action = action  # 'center', 'separator', 'italic'
        self.id = None

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
        self.epub_patterns = []  # Lista de patrones EPUB
        self.default_patterns = self._get_default_patterns()
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

    def _get_default_patterns(self):
        """Obtiene los patrones por defecto basados en Vue"""
        return [
            {"pattern": r"^\*\*\*$", "action": "center", "description": "Centrar separador ***"},
            {"pattern": r"^\-\-\-$", "action": "center", "description": "Centrar separador ---"},
            {"pattern": r"^===+$", "action": "separator", "description": "Línea con iguales"},
            {"pattern": r"^\*\*[^*]+\*\*$", "action": "center", "description": "Texto en negrita centrado"},
        ]

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        # Create container widget for scroll area
        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

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

        # Nuevo: Campo de idioma
        self.language_input = QLineEdit()
        self.language_input.setPlaceholderText("ej: es, en, fr")
        self.language_input.setMaxLength(5)  # Permitir códigos como 'en-US'
        self.language_input.setToolTip("Código de idioma de dos letras (ej: es para español, en para inglés, fr para francés)")
        metadata_layout.addRow("Idioma:", self.language_input)

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

        # Collection section
        collection_group = QGroupBox(self._get_string("create_panel.collection_group"))
        collection_layout = QVBoxLayout()

        # Radio button to enable/disable collection fields
        self.collection_enabled = QRadioButton(self._get_string("create_panel.collection_enabled"))
        self.collection_enabled.setChecked(False)

        # Collection input
        self.collection_input = QLineEdit()
        self.collection_input.setPlaceholderText(self._get_string("create_panel.collection_placeholder"))
        self.collection_input.setEnabled(False)

        # Type and position layout (horizontal)
        type_position_layout = QHBoxLayout()

        # Type dropdown
        self.collection_type_dropdown = QComboBox()
        self.collection_type_dropdown.addItems([
            self._get_string("create_panel.collection_type_series"),
            self._get_string("create_panel.collection_type_set")
        ])
        self.collection_type_dropdown.setEnabled(False)

        # Position input (numbers only)
        self.collection_position_input = QLineEdit()
        self.collection_position_input.setPlaceholderText(self._get_string("create_panel.collection_position_placeholder"))
        self.collection_position_input.setValidator(QIntValidator())
        self.collection_position_input.setEnabled(False)
        self.collection_position_input.setFixedWidth(80)  # Fixed width for position input

        # Add type and position to horizontal layout
        type_position_layout.addWidget(self.collection_type_dropdown)
        type_position_layout.addWidget(self.collection_position_input)

        # Connect signal to enable/disable collection fields
        self.collection_enabled.toggled.connect(self.toggle_collection_fields)

        # Add widgets to collection layout
        collection_layout.addWidget(self.collection_enabled)
        collection_layout.addWidget(self.collection_input)
        collection_layout.addLayout(type_position_layout)
        collection_group.setLayout(collection_layout)

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

        # Nuevo: Sección para ocultar/mostrar tabla de contenido
        toc_group = QGroupBox("Configuración EPUB")
        toc_layout = QVBoxLayout()
        
        # Radio button para ocultar tabla de contenido (activado por defecto)
        self.hide_toc = QRadioButton("Ocultar Tabla de Contenido")
        self.hide_toc.setChecked(True)  # Activado por defecto como solicita el usuario
        
        toc_layout.addWidget(self.hide_toc)
        toc_group.setLayout(toc_layout)

        # Nuevo: Sección de patrones EPUB
        patterns_group = QGroupBox("Patrones de Formateo")
        patterns_layout = QVBoxLayout()

        # Botón para agregar patrón
        self.add_pattern_button = QPushButton("Agregar Patrón")
        self.add_pattern_button.clicked.connect(self.add_pattern)
        patterns_layout.addWidget(self.add_pattern_button)

        # Tabla de patrones
        self.patterns_table = QTableWidget()
        self.patterns_table.setColumnCount(3)
        self.patterns_table.setHorizontalHeaderLabels(["Patrón (Regex)", "Acción", "Acciones"])
        header = self.patterns_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.patterns_table.setAlternatingRowColors(True)
        self.patterns_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.patterns_table.customContextMenuRequested.connect(self.show_pattern_context_menu)
        patterns_layout.addWidget(self.patterns_table)

        # Sección de patrones recomendados
        default_patterns_layout = QVBoxLayout()
        default_label = QLabel("Patrones Recomendados:")
        default_patterns_layout.addWidget(default_label)

        # Botones para patrones por defecto
        for pattern_info in self.default_patterns:
            pattern_button = QPushButton(f"Agregar: {pattern_info['description']}")
            pattern_button.setToolTip(f"Patrón: {pattern_info['pattern']}")
            pattern_button.clicked.connect(lambda checked, p=pattern_info: self.add_default_pattern(p))
            default_patterns_layout.addWidget(pattern_button)

        patterns_layout.addLayout(default_patterns_layout)
        patterns_group.setLayout(patterns_layout)

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

        # Add all elements to scroll layout
        scroll_layout.addLayout(top_layout)
        scroll_layout.addWidget(range_group)
        scroll_layout.addWidget(collection_group)
        scroll_layout.addWidget(toc_group)  # Nueva sección
        scroll_layout.addWidget(patterns_group)  # Nueva sección
        scroll_layout.addStretch()

        # Set scroll area widget and add to main layout
        scroll_area.setWidget(scroll_container)
        main_layout.addWidget(scroll_area)
        
        # Add buttons layout below scroll area (always visible)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        # Inicializar estado de los inputs de rango
        self.toggle_range_inputs()
        # Inicializar estado de los inputs de colección
        self.toggle_collection_fields()
        # Inicializar tabla de patrones
        self.refresh_patterns_table()
        
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

    def toggle_collection_fields(self):
        """Habilita/deshabilita los campos de colección según la selección"""
        enable_fields = self.collection_enabled.isChecked()
        self.collection_input.setEnabled(enable_fields)
        self.collection_type_dropdown.setEnabled(enable_fields)
        self.collection_position_input.setEnabled(enable_fields)

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
            'end_chapter': end_chapter,
            'language': self.language_input.text().strip() or 'es',  # Nuevo campo
            'hide_toc': self.hide_toc.isChecked(),  # Nuevo campo
            'patterns': [vars(pattern) for pattern in self.epub_patterns]  # Nuevo campo
        }

        # Add collection data if enabled
        if self.collection_enabled.isChecked():
            data['collection'] = self.collection_input.text().strip()
            data['collection_type'] = self.collection_type_dropdown.currentText()
            data['collection_position'] = self.collection_position_input.text().strip()

        # Emitir señal para solicitar confirmación antes de crear el EPUB
        from src.logic.functions import show_confirmation_dialog
        if show_confirmation_dialog(self._get_string("create_panel.epub_creation.confirmation"), parent=self.main_window):
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
        # Limpiar patrones
        self.epub_patterns.clear()
        self.refresh_patterns_table()

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

    # Métodos para gestión de patrones EPUB
    def refresh_patterns_table(self):
        """Actualiza la tabla de patrones"""
        self.patterns_table.setRowCount(len(self.epub_patterns))
        
        for row, pattern in enumerate(self.epub_patterns):
            # Patrón
            self.patterns_table.setItem(row, 0, QTableWidgetItem(pattern.pattern))
            
            # Acción
            action_text = {"center": "Centrar", "separator": "Separador", "italic": "Cursiva"}[pattern.action]
            self.patterns_table.setItem(row, 1, QTableWidgetItem(action_text))
            
            # Acciones (botones)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 2, 5, 2)
            
            # Botón editar
            edit_btn = QToolButton()
            edit_btn.setText("Editar")
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_pattern(r))
            actions_layout.addWidget(edit_btn)
            
            # Botón eliminar
            delete_btn = QToolButton()
            delete_btn.setText("Eliminar")
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_pattern(r))
            actions_layout.addWidget(delete_btn)
            
            self.patterns_table.setCellWidget(row, 2, actions_widget)

    def add_pattern(self):
        """Abre diálogo para agregar nuevo patrón"""
        dialog = PatternEditDialog(self)
        if dialog.exec() == PatternEditDialog.DialogCode.Accepted:
            pattern_data = dialog.get_pattern_data()
            if pattern_data:
                new_pattern = EpubPattern(pattern_data['pattern'], pattern_data['action'])
                self.epub_patterns.append(new_pattern)
                self.refresh_patterns_table()

    def edit_pattern(self, row):
        """Edita un patrón existente"""
        print(f"edit_pattern llamado con row={row}")
        if 0 <= row < len(self.epub_patterns):
            pattern = self.epub_patterns[row]
            print(f"Patrón actual: {pattern.pattern}, acción: {pattern.action}")
            dialog = PatternEditDialog(self, pattern)
            if dialog.exec() == QMessageBox.StandardButton.Ok:
                pattern_data = dialog.get_pattern_data()
                print(f"Datos del diálogo: {pattern_data}")
                if pattern_data:
                    try:
                        pattern.pattern = pattern_data['pattern']
                        pattern.action = pattern_data['action']
                        print(f"Patrón actualizado: {pattern.pattern}, acción: {pattern.action}")

                        # Actualizar la tabla directamente sin recrear todos los widgets
                        if self.patterns_table.item(row, 0):
                            self.patterns_table.item(row, 0).setText(pattern.pattern)
                            print(f"Celda patrón actualizada: {pattern.pattern}")
                        else:
                            print(f"ERROR: No se encontró item en fila {row}, columna 0")

                        action_text = {"center": "Centrar", "separator": "Separador", "italic": "Cursiva"}[pattern.action]
                        if self.patterns_table.item(row, 1):
                            self.patterns_table.item(row, 1).setText(action_text)
                            print(f"Celda acción actualizada: {action_text}")
                        else:
                            print(f"ERROR: No se encontró item en fila {row}, columna 1")
                    except Exception as e:
                        print(f"ERROR en edit_pattern: {str(e)}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("ERROR: pattern_data es None")
            else:
                print("Diálogo cancelado")
        else:
            print(f"ERROR: Índice de fila inválido {row}, longitud de patrones: {len(self.epub_patterns)}")

    def delete_pattern(self, row):
        """Elimina un patrón"""
        if 0 <= row < len(self.epub_patterns):
            reply = QMessageBox.question(self, 'Confirmar eliminación', 
                                       '¿Está seguro de que desea eliminar este patrón?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                del self.epub_patterns[row]
                self.refresh_patterns_table()

    def add_default_pattern(self, pattern_info):
        """Agrega un patrón por defecto"""
        new_pattern = EpubPattern(pattern_info['pattern'], pattern_info['action'])
        self.epub_patterns.append(new_pattern)
        self.refresh_patterns_table()

    def show_pattern_context_menu(self, position):
        """Muestra menú contextual para la tabla de patrones"""
        item = self.patterns_table.itemAt(position)
        if item is not None:
            row = item.row()
            if 0 <= row < len(self.epub_patterns):
                menu = QMenu(self)
                
                edit_action = QAction("Editar", self)
                edit_action.triggered.connect(lambda: self.edit_pattern(row))
                menu.addAction(edit_action)
                
                delete_action = QAction("Eliminar", self)
                delete_action.triggered.connect(lambda: self.delete_pattern(row))
                menu.addAction(delete_action)
                
                menu.exec(self.patterns_table.mapToGlobal(position))


class PatternEditDialog(QMessageBox):
    """Diálogo para editar patrones EPUB"""
    
    def __init__(self, parent, pattern=None):
        super().__init__(parent)
        self.pattern = pattern
        self.setWindowTitle("Agregar Patrón" if pattern is None else "Editar Patrón")
        self.setIcon(QMessageBox.Icon.Question)
        
        # Crear layout personalizado
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Ej: ^\\*\\*\\*$")
        
        self.action_combo = QComboBox()
        self.action_combo.addItems(["center", "separator", "italic"])
        
        # Layout para los campos
        layout = QVBoxLayoutWidget()
        
        # Campo patrón
        pattern_label = QLabel("Patrón (Regex):")
        layout.addWidget(pattern_label)
        layout.addWidget(self.pattern_input)
        
        # Tooltip
        tooltip_label = QLabel("Use expresiones regulares. Ejemplo: ^\\*\\*\\*$ para líneas que solo contengan ***")
        tooltip_label.setWordWrap(True)
        tooltip_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(tooltip_label)
        
        # Campo acción
        action_label = QLabel("Acción:")
        layout.addWidget(action_label)
        layout.addWidget(self.action_combo)
        
        # Configurar diálogo
        self.layout().addLayout(layout, 1, 1, 1, 3)
        
        # Botones
        self.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        # Si hay patrón existente, cargar datos
        if pattern:
            self.pattern_input.setText(pattern.pattern)
            self.action_combo.setCurrentText(pattern.action)

    def get_pattern_data(self):
        """Obtiene los datos del patrón del diálogo"""
        pattern = self.pattern_input.text().strip()
        action = self.action_combo.currentText()
        
        print(f"get_pattern_data llamado - patrón: '{pattern}', acción: '{action}'")
        
        if not pattern:
            print("ERROR: Patrón vacío")
            QMessageBox.warning(self, "Error", "El patrón no puede estar vacío")
            return None
            
        # Validar regex
        try:
            print(f"Intentando compilar regex: {pattern}")
            re.compile(pattern)
            print("Regex compilado exitosamente")
        except re.error as e:
            print(f"ERROR en regex: {str(e)}")
            QMessageBox.warning(self, "Error", f"Patrón regex inválido: {str(e)}")
            return None
            
        print(f"Devolviendo datos válidos: pattern='{pattern}', action='{action}'")
        return {'pattern': pattern, 'action': action}
