import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                           QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                           QPushButton, QLabel, QHeaderView, QSplitter, QDialog,
                           QMenu, QStyle, QWidgetAction)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontMetrics, QPixmap, QIcon, QColor, QPalette, QAction
from PyQt6.QtSvg import QSvgRenderer
from src.gui.clean import CleanPanel
from src.gui.create import CreateEpubPanel
from src.gui.translate import TranslatePanel
from src.gui.settings_gui import SettingsDialog
from src.logic.get_path import get_directory, get_initial_directory
from src.logic.loader import FileLoader
from src.logic.creator import EpubConverterLogic
from src.logic.epub_importer import EpubImporter
from src.logic.functions import show_confirmation_dialog, get_file_range, show_error_dialog
from src.logic.database import TranslationDatabase
from src.logic.session_logger import session_logger
from src.logic.status_manager import get_status_color, get_status_code_from_text
from src.logic.language_manager import LanguageManager
import subprocess

class ElidedLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.full_path = ""
        self.setMinimumWidth(420)
        self.setMaximumWidth(420)
        # Establecer fuente en negrita
        font = self.font()
        font.setBold(True)
        self.setFont(font)
    def setText(self, text):
        self.full_path = text
        self.update_display_text()
    def update_display_text(self):
        if self.full_path:
            # Extraer solo el nombre de la carpeta
            display_text = os.path.basename(self.full_path)
            if not display_text:  # En caso de que termine con /
                display_text = os.path.basename(os.path.dirname(self.full_path))
        else:
            display_text = "Ninguno seleccionado"
        # Aplicar elipsis si es necesario
        metrics = QFontMetrics(self.font())
        elided_text = metrics.elidedText(display_text, Qt.TextElideMode.ElideRight, self.width())
        super().setText(elided_text)
        # Establecer tooltip con la ruta completa
        self.setToolTip(self.full_path if self.full_path else "Seleccione un directorio de trabajo")
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_display_text()

class NovelManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_directory = None
        
        # Initialize language manager
        self.lang_manager = self._init_language_manager()
        
        self.setWindowTitle(self.lang_manager.get_string("main_window.title"))
        self.setGeometry(100, 100, 1000, 580)
        # Establecer ícono de la aplicación
        app_icon_path = "src/gui/icons/app.png"
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))
        # Main central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        # Create a splitter to allow resizing
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        # Left panel contains directory selection and chapters table
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        # Establecer un ancho mínimo para el panel izquierdo
        left_panel.setMinimumWidth(550)
        # Directory section - Solo botones, sin mostrar la ruta
        dir_layout = QHBoxLayout()
        # Botón Abrir
        self.nav_button = QPushButton(self.lang_manager.get_string("main_window.nav_button"))
        self.nav_button.clicked.connect(self.select_directory)
        # Botón Importar EPUB
        self.import_epub_button = QPushButton(self.lang_manager.get_string("main_window.import_epub_button"))
        self.import_epub_button.clicked.connect(self.import_epub)
        # Botón Abrir Directorio
        self.open_dir_button = QPushButton(self.lang_manager.get_string("main_window.open_dir_button"))
        self.open_dir_button.clicked.connect(self.open_working_directory)
        self.open_dir_button.setEnabled(False)  # Deshabilitado hasta seleccionar directorio
        # Botón Actualizar (con ícono)
        self.refresh_button = QPushButton()
        self.refresh_button.clicked.connect(self.refresh_files)
        self.refresh_button.setEnabled(False)  # Deshabilitado hasta seleccionar directorio
        self.refresh_button.setToolTip(self.lang_manager.get_string("main_window.refresh_button.tooltip"))
        # Botón Recientes (con ícono)
        self.recents_button = QPushButton()
        self.recents_button.setToolTip(self.lang_manager.get_string("main_window.recents_button.tooltip"))
        self.recents_button.clicked.connect(self.show_recents_menu)
        # Botón Registro (con ícono)
        self.log_button = QPushButton()
        self.log_button.clicked.connect(self.open_log_file)
        self.log_button.setToolTip(self.lang_manager.get_string("main_window.log_button.tooltip"))
        # Botón Ajustes (con ícono)
        self.settings_button = QPushButton()
        self.settings_button.setToolTip(self.lang_manager.get_string("main_window.settings_button.tooltip"))
        self.settings_button.clicked.connect(self.open_settings)
        # Agregar botones en el orden especificado
        dir_layout.addWidget(self.nav_button)
        dir_layout.addWidget(self.import_epub_button)
        dir_layout.addWidget(self.open_dir_button)
        dir_layout.addWidget(self.refresh_button)
        dir_layout.addWidget(self.recents_button)
        dir_layout.addWidget(self.log_button)
        dir_layout.addWidget(self.settings_button)
        dir_layout.addStretch()  # Empujar botones hacia la izquierda
        # Chapters table
        self.chapters_table = QTableWidget()
        self.chapters_table.setColumnCount(4)
        self.chapters_table.setHorizontalHeaderLabels([
            self.lang_manager.get_string("main_window.chapters_table.column.name"),
            self.lang_manager.get_string("main_window.chapters_table.column.status"),
            self.lang_manager.get_string("main_window.chapters_table.column.open"),
            self.lang_manager.get_string("main_window.chapters_table.column.translate")
        ])
        # Configure the automatic row numbering column
        self.chapters_table.verticalHeader().setVisible(True)
        self.chapters_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.chapters_table.verticalHeader().setDefaultSectionSize(30)
        self.chapters_table.verticalHeader().setMinimumWidth(50)
        # Set header text for the row numbers column
        vertical_header = self.chapters_table.verticalHeader()
        vertical_header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chapters_table.verticalHeader().setStyleSheet("QHeaderView::section { padding: 4px; }")
        vertical_header.setObjectName("Capítulos")
        # Configure column stretching
        self.chapters_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.chapters_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.chapters_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.chapters_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        left_layout.addLayout(dir_layout)
        left_layout.addWidget(self.chapters_table)
        # Right panel contains the tab widget
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        # Create the tab widget for the right side only
        self.tab_widget = QTabWidget()
        # Create individual tab panels with reference to main window
        self.clean_panel = CleanPanel(self)
        self.create_panel = CreateEpubPanel()
        self.create_panel.set_main_window(self)
        self.translate_panel = TranslatePanel(self)  # Modificado para pasar self
        # Add panels to the tab widget
        self.tab_widget.addTab(self.clean_panel, self.lang_manager.get_string("clean_panel.tab_label", "Limpiar"))
        self.tab_widget.addTab(self.create_panel, self.lang_manager.get_string("create_panel.tab_label", "Ebook"))
        self.tab_widget.addTab(self.translate_panel, self.lang_manager.get_string("translate_panel.tab_label", "Traducir"))
        right_layout.addWidget(self.tab_widget)
        # Add both panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        # Set initial sizes (left:right ratio roughly 2:1)
        splitter.setSizes([650, 350])
        # Status bar
        self.statusBar().showMessage(self.lang_manager.get_string("main_window.status.select_directory"))
        # Initialize file loader
        self.file_loader = FileLoader(self.lang_manager)
        self.file_loader.files_loaded.connect(self._add_files_to_table)
        self.file_loader.loading_finished.connect(self._loading_finished)
        self.file_loader.loading_error.connect(self._show_loading_error)
        self.file_loader.metadata_loaded.connect(self._load_book_metadata)
        # Inicializar el convertidor EPUB
        self.epub_converter = EpubConverterLogic()
        self.epub_converter.progress_updated.connect(self.update_status_message)
        self.epub_converter.conversion_finished.connect(self.handle_epub_conversion_finished)
        # Conectar la señal del panel de creación
        self.create_panel.epub_creation_requested.connect(self.handle_epub_creation)
        # Conectar la señal para mostrar mensajes de estado desde create_panel
        self.create_panel.status_message_requested.connect(self.show_status_message)
        # Conectar señal para actualizar título cuando se guardan metadatos
        self.create_panel.metadata_saved.connect(self.update_window_title)
        # Inicializar el importador EPUB
        self.epub_importer = EpubImporter()
        self.epub_importer.progress_updated.connect(self.update_status_message)
        self.epub_importer.import_finished.connect(self.handle_epub_import_finished)
        # Configurar detección de cambios de tema
        self._setup_theme_detection()
        # Configurar iconos para las pestañas y botones (después de configurar detección de tema)
        self.set_tab_icons()
        self.set_button_icons()
        
        # Cargar configuración al iniciar
        self.apply_configuration()

    def _init_language_manager(self):
        """Initialize the language manager with the configured UI language."""
        try:
            config_path = Path(__file__).parent / 'src' / 'config' / 'config.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                ui_language = config.get('ui_language', 'es_MX')
                return LanguageManager(ui_language)
        except Exception as e:
            print(f"Error initializing language manager: {e}")
            # Fallback to Spanish if there's an error
            return LanguageManager('es_MX')

    def closeEvent(self, event):
        """Limpia recursos al cerrar la aplicación"""
        if hasattr(self, '_theme_timer'):
            self._theme_timer.stop()
        # Limpiar el archivo de log de la sesión
        session_logger.cleanup()
        event.accept()

    def _is_dark_theme(self):
        """Detecta si el tema del sistema es oscuro"""
        palette = QApplication.instance().palette()
        background_color = palette.color(QPalette.ColorRole.Window)
        # Si la luminosidad del fondo es baja, es tema oscuro
        luminance = (0.299 * background_color.red() +
                    0.587 * background_color.green() +
                    0.114 * background_color.blue()) / 255
        return luminance < 0.5

    def _setup_theme_detection(self):
        """Configura la detección de cambios de tema usando la señal de QApplication."""
        QApplication.instance().paletteChanged.connect(self._on_palette_changed)
        # Aplicar estilos iniciales basados en el tema actual
        self._on_palette_changed(QApplication.instance().palette())

    def _on_palette_changed(self, palette):
        """Llamado cuando la paleta de la aplicación cambia (tema del sistema)."""
        print("Paleta del sistema cambiada, actualizando estilos...")
        # Actualizar iconos si es necesario (ya lo haces)
        self.set_tab_icons()
        self.set_button_icons()
        # Actualizar colores de estado en la tabla
        self._update_all_status_colors()
        self.statusBar().showMessage("Tema del sistema actualizado", 2000)

        # Actualizar color del texto del encabezado vertical
        text_color = palette.color(QPalette.ColorRole.WindowText)
        self.chapters_table.verticalHeader().setStyleSheet(f"""
            QHeaderView::section {{
                padding: 4px;
                color: {text_color.name()};
            }}
        """)

    def set_tab_icons(self):
        """Configurar iconos SVG para las pestañas según el tema del sistema"""
        try:
            # Rutas de los iconos SVG base (sin sufijo de tema)
            clean_icon_path = "src/gui/icons/clean.svg"
            ebook_icon_path = "src/gui/icons/ebook.svg"
            translate_icon_path = "src/gui/icons/translate.svg"
            # Configurar iconos con coloración automática
            self.tab_widget.setTabIcon(0, self.create_themed_icon(clean_icon_path))
            self.tab_widget.setTabIcon(1, self.create_themed_icon(ebook_icon_path))
            self.tab_widget.setTabIcon(2, self.create_themed_icon(translate_icon_path))
        except Exception as e:
            print(f"Error cargando iconos: {e}")

    def create_themed_icon(self, svg_path, size=24):
        """Crear un icono temático modificando el SVG"""
        if not os.path.exists(svg_path):
            return QIcon()
        try:
            # Leer el contenido del SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            # Obtener el color del texto del sistema
            app_palette = QApplication.palette()
            text_color = app_palette.color(QPalette.ColorRole.WindowText)
            color_hex = text_color.name()  # Formato #RRGGBB
            # Lista de patrones de colores a reemplazar (colores oscuros que se usarían en tema claro)
            dark_patterns = [
                '#000000', '#000', 'fill="black"', "fill='black'",
                '#111111', '#222222', '#333333', '#444444',
                'stroke="#000000"', 'stroke="#000"', 'stroke="black"',
                "stroke='#000000'", "stroke='#000'", "stroke='black'"
            ]
            # Reemplazar todos los patrones oscuros con el color del sistema
            for pattern in dark_patterns:
                if 'fill=' in pattern or 'stroke=' in pattern:
                    # Para atributos fill y stroke, mantener la estructura
                    if 'fill=' in pattern:
                        svg_content = svg_content.replace(pattern, f'fill="{color_hex}"')
                    elif 'stroke=' in pattern:
                        svg_content = svg_content.replace(pattern, f'stroke="{color_hex}"')
                else:
                    # Para valores de color directo
                    svg_content = svg_content.replace(pattern, color_hex)
            # También reemplazar currentColor para compatibilidad
            svg_content = svg_content.replace('currentColor', color_hex)
            # Crear el icono desde el SVG modificado
            svg_bytes = svg_content.encode('utf-8')
            # Usar QSvgRenderer para renderizar el SVG modificado
            renderer = QSvgRenderer(svg_bytes)
            if not renderer.isValid():
                # Fallback: usar el archivo original
                return QIcon(svg_path)
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            from PyQt6.QtGui import QPainter
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return QIcon(pixmap)
        except Exception as e:
            print(f"Error creando icono temático para {svg_path}: {e}")
            # Fallback: cargar el icono sin modificar
            return QIcon(svg_path) if os.path.exists(svg_path) else QIcon()

    def set_button_icons(self):
        """Configurar iconos SVG para los botones según el tema del sistema"""
        try:
            # Rutas de los iconos SVG base (sin sufijo de tema)
            refresh_icon_path = "src/gui/icons/refresh.svg"
            recents_icon_path = "src/gui/icons/recents.svg"
            log_icon_path = "src/gui/icons/log.svg"
            settings_icon_path = "src/gui/icons/settings.svg"
            # Configurar iconos con coloración automática
            self.refresh_button.setIcon(self.create_themed_icon(refresh_icon_path))
            self.recents_button.setIcon(self.create_themed_icon(recents_icon_path))
            self.log_button.setIcon(self.create_themed_icon(log_icon_path))
            self.settings_button.setIcon(self.create_themed_icon(settings_icon_path))
        except Exception as e:
            print(f"Error cargando iconos de botones: {e}")


    def refresh_files(self):
        """Actualiza la lista de archivos del directorio actual"""
        if not self.current_directory:
            self.statusBar().showMessage("Error: No hay directorio seleccionado")
            return
        self.statusBar().showMessage("Actualizando lista de archivos...")
        self.load_chapters()

    def load_chapters(self):
        if not self.current_directory:
            return
        # Clear current table
        self.chapters_table.setRowCount(0)
        # Update status
        self.statusBar().showMessage("Cargando lista de archivos...")
        # Start loading files
        self.file_loader.load_files(self.current_directory)

    def open_file(self, file_path):
        try:
            if sys.platform.startswith('darwin'):  # macOS
                subprocess.run(['open', file_path])
            elif sys.platform.startswith('win32'):  # Windows
                os.startfile(file_path)
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            self.statusBar().showMessage(f"Error al abrir el archivo: {str(e)}")

    def _add_files_to_table(self, files):
        # Preestablecer el número de filas total
        self.chapters_table.setRowCount(len(files))
        for row, file_data in enumerate(files):
            name_item = QTableWidgetItem(file_data['name'])
            status_item = QTableWidgetItem(file_data['status'])
            # Hacer que las celdas no sean editables
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Aplicar color según el estado
            self._apply_status_color(status_item, file_data['status'])
            self.chapters_table.setItem(row, 0, name_item)
            self.chapters_table.setItem(row, 1, status_item)
            # Botón para abrir el archivo
            open_button = QPushButton(self.lang_manager.get_string("main_window.chapters_table.column.open"))
            # Botón para traducir solo este capítulo específico con la configuración actual
            translate_button = QPushButton(self.lang_manager.get_string("main_window.chapters_table.column.translate"))
            file_path = os.path.join(self.current_directory, file_data['name'])
            open_button.clicked.connect(lambda checked, path=file_path: self.open_file(path))
            translate_button.clicked.connect(lambda checked, filename=file_data['name']: self.translate_single_file(filename))
            self.chapters_table.setCellWidget(row, 2, open_button)
            self.chapters_table.setCellWidget(row, 3, translate_button)
            # Set chapter number
            self.chapters_table.setVerticalHeaderItem(
                row,
                QTableWidgetItem(str(row + 1))
            )

    def _loading_finished(self):
        total_files = self.chapters_table.rowCount()
        self.statusBar().showMessage(
            f"Cargados {total_files} archivos de {os.path.basename(self.current_directory)}"
        )
        # Actualizar el rango máximo en el panel de traducción
        self.translate_panel.set_chapter_range(total_files)
        # Aplicar colores de estado a todas las filas
        self._update_all_status_colors()

    def _show_loading_error(self, error_message):
        self.statusBar().showMessage(f"Error: {error_message}")

    def _load_book_metadata(self, metadata):
        """Carga los metadatos del libro en el panel de creación de EPUB"""
        if metadata.get('title') or metadata.get('author'):
            # Los metadatos se cargan automáticamente cuando se establece el directorio
            # en el panel de creación, no necesitamos hacer nada adicional aquí
            pass

    def update_file_status(self, filename, new_status):
        """Actualiza el estado de un archivo en la tabla"""
        for row in range(self.chapters_table.rowCount()):
            name_item = self.chapters_table.item(row, 0)
            if name_item and name_item.text() == filename:
                status_item = self.chapters_table.item(row, 1)
                if status_item:
                    status_item.setText(new_status)
                    # Aplicar color según el nuevo estado
                    self._apply_status_color(status_item, new_status)
                break

    def handle_epub_creation(self, data):
        """
        Maneja la solicitud de creación de EPUB.
        """
        if not self.current_directory:
            self.statusBar().showMessage(
                self.lang_manager.get_string("create_panel.epub_creation.error.no_directory"))
            return
        # Validar el rango de capítulos si se especificó
        if data['start_chapter'] is not None and data['end_chapter'] is not None:
            total_chapters = self.chapters_table.rowCount()
            if data['start_chapter'] < 1 or data['end_chapter'] > total_chapters:
                self.statusBar().showMessage(
                    self.lang_manager.get_string("create_panel.epub_creation.error.invalid_range").format(
                        max_chapters=total_chapters))
                return
            if data['start_chapter'] > data['end_chapter']:
                self.statusBar().showMessage(
                    self.lang_manager.get_string("create_panel.epub_creation.error.range_order"))
                return
        # Obtener archivos en el rango
        files = get_file_range(self.chapters_table, data['start_chapter'], data['end_chapter'])
        # Iniciar la creación del EPUB
        self.epub_converter.set_directory(self.current_directory)
        self.epub_converter.create_epub(data, self.chapters_table)

    def update_status_message(self, message):
        """Actualiza la barra de estado y fuerza el procesamiento de eventos"""
        self.statusBar().showMessage(message)
        QApplication.processEvents()  # Forzar actualización de UI

    def handle_epub_conversion_finished(self, success, message):
        """
        Maneja la finalización de la conversión a EPUB.
        """
        if success:
            # Mostrar mensaje de éxito
            self.statusBar().showMessage(
                self.lang_manager.get_string("create_panel.epub_creation.success") + ": " + message, 5000)
            # No reiniciar el formulario - mantener datos
        else:
            # Mostrar mensaje de error
            self.statusBar().showMessage(
                self.lang_manager.get_string("create_panel.epub_creation.error").format(error=message))
        QApplication.processEvents()  # Forzar actualización de UI

    def handle_single_translation_completed(self):
        """
        Maneja la finalización de la traducción de un solo archivo.
        """
        # Restaurar el estado de los botones
        self.translate_panel.translate_button.setEnabled(True)
        self.translate_panel.stop_button.setEnabled(False)
        # Desconectar la señal para evitar múltiples conexiones
        self.translate_panel.translation_manager.all_translations_completed.disconnect(self.handle_single_translation_completed)
        # Actualizar mensaje de estado
        self.statusBar().showMessage("Traducción completada", 5000)

    def _apply_status_color(self, status_item, status):
        """Aplica color al item de estado según su valor, usando la paleta del sistema."""
        # Convertir texto a código (para compatibilidad con valores existentes)
        status_code = get_status_code_from_text(status)
        
        # Obtener color específico para el código de estado
        color_rgb = get_status_color(status_code)
        
        if color_rgb:
            # Aplicar color específico
            status_item.setForeground(QColor(*color_rgb))
        else:
            # Usar color de texto predeterminado del sistema
            palette = QApplication.instance().palette()
            status_item.setForeground(palette.color(QPalette.ColorRole.Text))

    def _update_all_status_colors(self):
        """Actualiza los colores de estado de todas las filas en la tabla"""
        for row in range(self.chapters_table.rowCount()):
            status_item = self.chapters_table.item(row, 1)
            if status_item:
                status = status_item.text()
                self._apply_status_color(status_item, status)

    def translate_single_file(self, filename):
        """
        Traduce un único archivo usando la configuración actual de la pestaña de traducción.
        Esta función es llamada cuando se hace clic en el botón "Traducir" de la tabla de capítulos.
        """
        if not self.current_directory:
            self.statusBar().showMessage("Error: Seleccione un directorio primero")
            return
        # Obtener configuración de la pestaña de traducción
        translate_panel = self.translate_panel
        # Obtener API key
        api_key = translate_panel.get_current_api_key()
        if not api_key:
            self.statusBar().showMessage("Error: API key no configurada. Use el botón de configuración.")
            return
        # Obtener proveedor y modelo
        provider = next(
            (k for k, v in translate_panel.models_config.items()
             if v['name'] == translate_panel.provider_combo.currentText()),
            None
        )
        model = next(
            (k for k, v in translate_panel.models_config[provider]['models'].items()
             if v['name'] == translate_panel.model_combo.currentText()),
            None
        )
        # Obtener idiomas (códigos)
        source_lang = translate_panel.source_lang_combo.currentData()
        target_lang = translate_panel.target_lang_combo.currentData()

        if not source_lang or not target_lang or source_lang == target_lang:
            self.statusBar().showMessage("Error: Los idiomas de origen y destino deben ser diferentes y estar seleccionados")
            return
        # Obtener términos personalizados
        custom_terms = translate_panel.terms_input.toPlainText().strip()
        # Obtener configuración de segmentación
        segment_size = None
        if translate_panel.segment_checkbox.isChecked():
            try:
                segment_size = int(translate_panel.segment_size_input.text() or 5000)
                if segment_size <= 0:
                    segment_size = 5000
            except ValueError:
                self.statusBar().showMessage("Error: El tamaño de segmentación debe ser un número")
                return
        # Obtener estado de la comprobación
        enable_check = translate_panel.check_translation_checkbox.isChecked()
        # Obtener estado del refinamiento
        enable_refine = translate_panel.refine_translation_checkbox.isChecked()
        # Confirmar la operación
        
        if not show_confirmation_dialog(
            f"Se traducirá el archivo '{filename}'.\n¿Desea continuar?"
        ):
            return
        # Preparar el administrador de traducción
        translate_panel.translation_manager.initialize(
            self.current_directory,
            provider,
            model
        )
        # Configurar UI
        self.statusBar().showMessage(f"Traduciendo {filename}...")
        translate_panel.translate_button.setEnabled(False)
        translate_panel.stop_button.setEnabled(True)
        # Crear la lista con un solo archivo
        files_to_translate = [{
            'name': filename,
            'row': None  # No necesitamos la fila aquí
        }]
        # Conectar señal para restaurar botones cuando termine la traducción
        translate_panel.translation_manager.all_translations_completed.connect(self.handle_single_translation_completed)
        # Iniciar traducción
        self.translate_panel.translation_manager.translate_files(
            files_to_translate,
            source_lang,
            target_lang,
            api_key,
            self.update_file_status,
            custom_terms,
            segment_size,
            enable_check,
            enable_refine
        )

    def import_epub(self):
        """Maneja la importación de archivos EPUB usando la nueva ventana de vista previa"""
        from PyQt6.QtWidgets import QFileDialog
        from src.gui.epub_preview import EpubPreviewWindow
        
        # Abrir diálogo para seleccionar archivo EPUB
        # Usar el directorio home como directorio inicial, igual que en get_directory()
        initial_dir = os.path.expanduser('~')
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo EPUB",
            initial_dir,
            "Archivos EPUB (*.epub);;Todos los archivos (*.*)"
        )
        if not file_path:
            return
            
        # Mostrar ventana de vista previa
        preview_dialog = EpubPreviewWindow(file_path, self)
        if preview_dialog.exec() == QDialog.DialogCode.Accepted:
            # Obtener datos de importación de la ventana de vista previa
            book_title, author, chapters_data, cover_image = preview_dialog.get_import_data()
            
            # Iniciar la importación
            self.statusBar().showMessage("Importando EPUB...")
            self.import_epub_button.setEnabled(False)
            self.nav_button.setEnabled(False)
            self.epub_importer.import_epub(book_title, author, chapters_data, cover_image, file_path)
        else:
            # Usuario canceló la operación
            return

    def handle_epub_import_finished(self, success, message, directory_path):
        """Maneja la finalización de la importación de EPUB"""
        # Restaurar botones
        self.import_epub_button.setEnabled(True)
        self.nav_button.setEnabled(True)
        if success:
            # Limpiar campos de descripción y términos personalizados antes de establecer el nuevo directorio
            self.create_panel.description_input.clear()
            self.translate_panel.terms_input.clear()
            # Agregar al historial de recientes
            self.add_recent(directory_path)
            # Establecer automáticamente el directorio importado como directorio de trabajo
            self.current_directory = directory_path
            # Configurar el directorio en el convertidor EPUB
            self.epub_converter.set_directory(directory_path)
            # Configurar directorio de trabajo en el panel de creación de EPUB
            self.create_panel.set_working_directory(directory_path)
            # Configurar directorio de trabajo en el panel de traducción
            self.translate_panel.set_working_directory(directory_path)
            # Habilitar botones
            self.refresh_button.setEnabled(True)
            self.open_dir_button.setEnabled(True)
            # Actualizar título de la ventana
            self.update_window_title()
            self.load_chapters()
            # Mostrar mensaje de éxito
            self.statusBar().showMessage(message, 5000)
        else:
            # Mostrar mensaje de error
            self.statusBar().showMessage(f"Error: {message}")
            
            show_error_dialog(message, "Error al importar EPUB")

    def show_status_message(self, message, timeout=0):
        """Muestra un mensaje en la barra de estado"""
        self.statusBar().showMessage(message, timeout)

    def update_window_title(self):
        """Actualiza el título de la ventana basado en los metadatos de la base de datos"""
        if not self.current_directory:
            self.setWindowTitle("Novel Translator")
            return
        try:
            # Crear instancia de base de datos para obtener metadatos
            db = TranslationDatabase(self.current_directory)
            metadata = db.get_book_metadata()
            # Usar el título si existe, sino usar el nombre de la carpeta
            if metadata.get('title') and metadata['title'].strip():
                title = metadata['title'].strip()
                self.setWindowTitle(f"Novel Translator - {title}")
            else:
                folder_name = os.path.basename(self.current_directory)
                self.setWindowTitle(f"Novel Translator - {folder_name}")
        except Exception as e:
            # En caso de error, usar el nombre de la carpeta
            folder_name = os.path.basename(self.current_directory)
            self.setWindowTitle(f"Novel Translator - {folder_name}")

    def open_working_directory(self):
        """Abre el directorio de trabajo actual en el explorador de archivos"""
        if not self.current_directory:
            self.statusBar().showMessage("Error: No hay directorio de trabajo seleccionado")
            return
        try:
            import platform
            system = platform.system()
            if system == "Windows":
                os.startfile(self.current_directory)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", self.current_directory])
            else:  # Linux y otros Unix
                subprocess.run(["xdg-open", self.current_directory])
            self.statusBar().showMessage(f"Abriendo directorio: {os.path.basename(self.current_directory)}", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error al abrir directorio: {str(e)}")

    def open_log_file(self):
        """Abre el archivo de log de la sesión con el programa predeterminado"""
        log_path = session_logger.get_log_path()
        if not log_path or not os.path.exists(log_path):
            self.statusBar().showMessage("No se encontró el archivo de registro de la sesión")
            return
        try:
            import platform
            system = platform.system()
            if system == "Windows":
                os.startfile(log_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", log_path])
            else:  # Linux y otros Unix
                subprocess.run(["xdg-open", log_path])
            #self.statusBar().showMessage("Abriendo archivo de registro...", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error al abrir archivo de registro: {str(e)}")

    def open_settings(self):
        """Abre el diálogo de configuración"""
        try:
            dialog = SettingsDialog(self)
            dialog.finished.connect(self.translate_panel.update_preset_terms_button_state)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # La configuración se guardó, actualizar la aplicación
                self.apply_configuration()
                self.statusBar().showMessage(self.lang_manager.get_string("main_window.settings_updated"), 3000)
        except Exception as e:
            self.statusBar().showMessage(self.lang_manager.get_string("main_window.settings_open_error").format(error=str(e)))

    def apply_configuration(self):
        """Aplica la configuración guardada a los componentes de la aplicación"""
        try:
            config_path = Path(__file__).parent / 'src' / 'config' / 'config.json'
            languages_path = Path(__file__).parent / 'src' / 'config' / 'languages.json'
            
            # Cargar configuración principal
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Cargar mapeo de idiomas
                languages_mapping = {}
                if languages_path.exists():
                    with open(languages_path, 'r', encoding='utf-8') as f:
                        languages_mapping = json.load(f)
                
                # Aplicar configuración al panel de traducción
                if hasattr(self, 'translate_panel'):
                    self._apply_translate_panel_config(config, languages_mapping)
                    
        except Exception as e:
            print(f"Error aplicando configuración: {e}")

    def _apply_translate_panel_config(self, config, languages_mapping=None):
        """Aplica la configuración específica al panel de traducción"""
        try:
            # Aplicar proveedor y modelo
            provider = config.get('provider', '')
            model = config.get('model', '')
            
            if provider and hasattr(self.translate_panel, 'provider_combo'):
                # Encontrar índice del proveedor usando itemData
                provider_index = -1
                for i in range(self.translate_panel.provider_combo.count()):
                    if self.translate_panel.provider_combo.itemData(i) == provider:
                        provider_index = i
                        break
                
                # Si no se encuentra por itemData, buscar por texto (fallback)
                if provider_index == -1:
                    for i in range(self.translate_panel.provider_combo.count()):
                        if self.translate_panel.provider_combo.itemText(i) == provider:
                            provider_index = i
                            break
                
                if provider_index >= 0:
                    self.translate_panel.provider_combo.setCurrentIndex(provider_index)
                    # Actualizar modelos
                    self.translate_panel.update_models()
                    
                    # Seleccionar modelo
                    if model and hasattr(self.translate_panel, 'model_combo'):
                        model_index = -1
                        for i in range(self.translate_panel.model_combo.count()):
                            if self.translate_panel.model_combo.itemData(i) == model:
                                model_index = i
                                break
                        
                        # Si no se encuentra por itemData, buscar por texto (fallback)
                        if model_index == -1:
                            for i in range(self.translate_panel.model_combo.count()):
                                if self.translate_panel.model_combo.itemText(i) == model:
                                    model_index = i
                                    break
                        
                        if model_index >= 0:
                            self.translate_panel.model_combo.setCurrentIndex(model_index)
            
            # Aplicar idiomas usando el mapeo de languages.json
            source_lang_gui = config.get('source_language', '')
            target_lang_gui = config.get('target_language', '')
            
            # Aplicar idioma de origen
            if source_lang_gui and hasattr(self.translate_panel, 'source_lang_combo'):
                source_index = -1
                for i in range(self.translate_panel.source_lang_combo.count()):
                    if self.translate_panel.source_lang_combo.itemData(i) == source_lang_gui:
                        source_index = i
                        break
                
                # Si no se encuentra por itemData, buscar por texto (fallback)
                if source_index == -1:
                    for i in range(self.translate_panel.source_lang_combo.count()):
                        if self.translate_panel.source_lang_combo.itemText(i) == source_lang_gui:
                            source_index = i
                            break
                
                if source_index >= 0:
                    self.translate_panel.source_lang_combo.setCurrentIndex(source_index)
            
            # Aplicar idioma de destino
            if target_lang_gui and hasattr(self.translate_panel, 'target_lang_combo'):
                target_index = -1
                for i in range(self.translate_panel.target_lang_combo.count()):
                    if self.translate_panel.target_lang_combo.itemData(i) == target_lang_gui:
                        target_index = i
                        break
                
                # Si no se encuentra por itemData, buscar por texto (fallback)
                if target_index == -1:
                    for i in range(self.translate_panel.target_lang_combo.count()):
                        if self.translate_panel.target_lang_combo.itemText(i) == target_lang_gui:
                            target_index = i
                            break
                
                if target_index >= 0:
                    self.translate_panel.target_lang_combo.setCurrentIndex(target_index)
                    
        except Exception as e:
            print(f"Error aplicando configuración al panel de traducción: {e}")

    def get_recents_file_path(self):
        """Obtiene la ruta del archivo JSON de carpetas recientes"""
        return Path(__file__).parent / 'src' / 'config' / 'recents.json'

    def load_recents(self):
        """Carga las carpetas recientes desde el archivo JSON"""
        try:
            recents_file = self.get_recents_file_path()
            if recents_file.exists():
                with open(recents_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Asegurar que todas las rutas cargadas estén normalizadas
                    return [Path(p).as_posix() for p in data.get('recientes', [])]
            return []
        except Exception as e:
            print(f"Error al cargar carpetas recientes: {e}")
            return []

    def save_recents(self, recents_list):
        """Guarda las carpetas recientes en el archivo JSON"""
        try:
            recents_file = self.get_recents_file_path()
            # Las rutas ya deberían estar normalizadas antes de llegar aquí
            data = {"recientes": recents_list}
            with open(recents_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar carpetas recientes: {e}")

    def add_recent(self, directory_path):
        """Agrega una carpeta al historial de recientes, normalizando la ruta"""
        if not directory_path:
            return

        # Normalizar la ruta entrante a formato POSIX para consistencia
        normalized_path = Path(directory_path).as_posix()

        # Cargar lista actual (ya viene normalizada desde load_recents)
        recents = self.load_recents()

        # Eliminar la ruta si ya existe para moverla al principio
        recents = [p for p in recents if p != normalized_path]

        # Agregar la nueva ruta normalizada al principio
        recents.insert(0, normalized_path)

        # Limitar a 10 elementos
        recents = recents[:10]

        # Guardar actualizado
        self.save_recents(recents)

    def remove_recent(self, directory_path):
        """Elimina una carpeta específica del historial de recientes"""
        # Normalizar la ruta a eliminar para asegurar la coincidencia
        normalized_path_to_remove = Path(directory_path).as_posix()
        
        recents = self.load_recents()
        if normalized_path_to_remove in recents:
            recents.remove(normalized_path_to_remove)
            self.save_recents(recents)

    def remove_recent_and_update_menu(self, directory_path):
        """Elimina una carpeta del historial y actualiza el menú"""
        # La normalización se maneja dentro de remove_recent
        self.remove_recent(directory_path)
        
        # Obtener el nombre de la carpeta para el mensaje
        folder_name = os.path.basename(directory_path)
        if not folder_name:  # En caso de que termine con /
            folder_name = os.path.basename(os.path.dirname(directory_path))
        
        # Mostrar mensaje de confirmación
        self.statusBar().showMessage(f"Eliminado '{folder_name}' del historial de carpetas recientes", 3000)
        
        # El menú se cerrará automáticamente, no es necesario reabrirlo aquí.

    def show_recents_menu(self):
        """Muestra el menú desplegable de carpetas recientes"""
        menu = QMenu(self)
        
        # Cargar carpetas recientes (ya vienen normalizadas)
        recents = self.load_recents()
        
        if not recents:
            action = QAction("No hay carpetas recientes", self)
            action.setEnabled(False)
            menu.addAction(action)
        else:
            for recent_path in recents:
                widget_item = QWidget()
                layout = QHBoxLayout(widget_item)
                layout.setContentsMargins(5, 2, 5, 2)
                layout.setSpacing(5)
                
                folder_name = os.path.basename(recent_path)
                if not folder_name:
                    folder_name = os.path.basename(os.path.dirname(recent_path))
                
                label = QLabel(folder_name)
                label.setToolTip(recent_path)
                
                remove_button = QPushButton("×")
                remove_button.setFixedSize(20, 20)
                remove_button.setToolTip(f"Eliminar {folder_name} del historial")
                remove_button.setStyleSheet("""
                    QPushButton { border: 1px solid #ccc; border-radius: 3px; background-color: #f0f0f0; font-weight: bold; }
                    QPushButton:hover { background-color: #ff6b6b; border-color: #ff5252; }
                """)
                
                remove_button.clicked.connect(lambda checked, path=recent_path, menu=menu: (menu.close(), self.remove_recent_and_update_menu(path)))
                
                # Usar una clase o función para capturar la ruta correctamente en el lambda
                def create_mouse_release_event(path):
                    return lambda event: (menu.close(), self.select_recent_directory(path))
                
                label.mouseReleaseEvent = create_mouse_release_event(recent_path)
                
                layout.addWidget(label)
                layout.addWidget(remove_button)
                layout.addStretch()
                
                menu_action = QWidgetAction(self)
                menu_action.setDefaultWidget(widget_item)
                menu.addAction(menu_action)
        
        button_rect = self.recents_button.rect()
        pos = self.recents_button.mapToGlobal(button_rect.bottomLeft())
        menu.exec(pos)

    def select_recent_directory(self, directory_path):
        """Establece una carpeta reciente como directorio de trabajo actual"""
        # Normalizar la ruta por si acaso viene de una versión antigua del recents.json
        normalized_path = Path(directory_path).as_posix()

        if os.path.exists(normalized_path) and os.path.isdir(normalized_path):
            self.add_recent(normalized_path)  # add_recent se encarga de la lógica de duplicados
            self.current_directory = normalized_path
            self.statusBar().showMessage(f"Directorio de trabajo: {os.path.basename(self.current_directory)}")
            
            self.epub_converter.set_directory(normalized_path)
            self.create_panel.set_working_directory(normalized_path)
            self.translate_panel.set_working_directory(normalized_path)
            
            self.refresh_button.setEnabled(True)
            self.open_dir_button.setEnabled(True)
            
            self.update_window_title()
            self.load_chapters()
        else:
            self.statusBar().showMessage(f"Error: La carpeta no existe: {directory_path}")
            self.remove_recent(directory_path)

    def select_directory(self):
        # Obtener el directorio inicial configurado
        initial_dir = get_initial_directory()
        directory = get_directory(initial_dir)
        if directory:
            # Agregar al historial de recientes
            self.add_recent(directory)
            self.current_directory = directory
            self.statusBar().showMessage(f"Directorio de trabajo: {os.path.basename(self.current_directory)}")
            # Configurar el directorio en el convertidor EPUB
            self.epub_converter.set_directory(directory)
            # Configurar directorio de trabajo en el panel de creación de EPUB
            self.create_panel.set_working_directory(directory)
            # Configurar directorio de trabajo en el panel de traducción
            self.translate_panel.set_working_directory(directory)
            # Habilitar botones
            self.refresh_button.setEnabled(True)
            self.open_dir_button.setEnabled(True)
            # Actualizar título de la ventana
            self.update_window_title()
            self.load_chapters()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = NovelManagerApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)