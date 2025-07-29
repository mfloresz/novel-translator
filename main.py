import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                           QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                           QPushButton, QLabel, QHeaderView, QSplitter)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontMetrics, QPixmap, QIcon, QColor, QPalette
from src.gui.clean import CleanPanel
from src.gui.create import CreateEpubPanel
from src.gui.translate import TranslatePanel
from src.logic.get_path import get_directory
from src.logic.loader import FileLoader
from src.logic.creator import EpubConverterLogic
from src.logic.epub_importer import EpubImporter
from src.logic.functions import show_confirmation_dialog, show_import_confirmation_dialog
from src.logic.database import TranslationDatabase
from src.logic.session_logger import session_logger
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
        self.setWindowTitle("Novel Translator")
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
        self.nav_button = QPushButton("Navegar")
        self.nav_button.clicked.connect(self.select_directory)

        # Añadir botón de importar EPUB
        self.import_epub_button = QPushButton("Importar EPUB")
        self.import_epub_button.clicked.connect(self.import_epub)

        # Añadir botón de actualizar
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh_files)
        self.refresh_button.setEnabled(False)  # Deshabilitado hasta seleccionar directorio

        # Añadir botón para abrir directorio
        self.open_dir_button = QPushButton("Abrir Directorio")
        self.open_dir_button.clicked.connect(self.open_working_directory)
        self.open_dir_button.setEnabled(False)  # Deshabilitado hasta seleccionar directorio

        # Añadir botón para abrir registro
        self.log_button = QPushButton("Registro")
        self.log_button.clicked.connect(self.open_log_file)

        dir_layout.addWidget(self.nav_button)
        dir_layout.addWidget(self.import_epub_button)
        dir_layout.addWidget(self.refresh_button)
        dir_layout.addWidget(self.open_dir_button)
        dir_layout.addWidget(self.log_button)
        dir_layout.addStretch()  # Empujar botones hacia la izquierda

        # Chapters table
        self.chapters_table = QTableWidget()
        self.chapters_table.setColumnCount(4)
        self.chapters_table.setHorizontalHeaderLabels(["Nombre", "Estado", "Abrir", "Traducir"])

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
        self.translate_panel = TranslatePanel(self)  # Modificado para pasar self

        # Add panels to the tab widget
        self.tab_widget.addTab(self.clean_panel, "Limpiar")
        self.tab_widget.addTab(self.create_panel, "Ebook")
        self.tab_widget.addTab(self.translate_panel, "Traducir")

        right_layout.addWidget(self.tab_widget)

        # Add both panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # Set initial sizes (left:right ratio roughly 2:1)
        splitter.setSizes([650, 350])

        # Status bar
        self.statusBar().showMessage("Estado: Seleccione un directorio de trabajo o importe un EPUB")

        # Initialize file loader
        self.file_loader = FileLoader()
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

        # Configurar iconos para las pestañas (después de configurar detección de tema)
        self.set_tab_icons()

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
        """Configura la detección de cambios de tema"""
        self._current_theme_dark = self._is_dark_theme()

        # Timer para verificar cambios de tema periódicamente
        self._theme_timer = QTimer()
        self._theme_timer.timeout.connect(self._check_theme_change)
        self._theme_timer.start(2000)  # Verificar cada 2 segundos (más eficiente)

    def _check_theme_change(self):
        """Verifica si el tema ha cambiado y actualiza los iconos si es necesario"""
        current_dark = self._is_dark_theme()
        if current_dark != self._current_theme_dark:
            self._current_theme_dark = current_dark
            self.set_tab_icons()
            self._update_all_status_colors()
            self.statusBar().showMessage("Tema del sistema actualizado", 2000)

    def set_tab_icons(self):
        """Configurar iconos SVG para las pestañas según el tema del sistema"""
        try:
            # Determinar sufijo del icono según el tema
            icon_suffix = "-light.svg" if self._is_dark_theme() else "-dark.svg"

            # Rutas de los iconos SVG
            clean_icon_path = f"src/gui/icons/clean{icon_suffix}"
            ebook_icon_path = f"src/gui/icons/ebook{icon_suffix}"
            translate_icon_path = f"src/gui/icons/translate{icon_suffix}"

            # Configurar icono para la pestaña "Limpiar" (índice 0)
            if os.path.exists(clean_icon_path):
                self.tab_widget.setTabIcon(0, QIcon(clean_icon_path))

            # Configurar icono para la pestaña "Ebook" (índice 1)
            if os.path.exists(ebook_icon_path):
                self.tab_widget.setTabIcon(1, QIcon(ebook_icon_path))

            # Configurar icono para la pestaña "Traducir" (índice 2)
            if os.path.exists(translate_icon_path):
                self.tab_widget.setTabIcon(2, QIcon(translate_icon_path))

        except Exception as e:
            print(f"Error cargando iconos: {e}")

    def select_directory(self):
        directory = get_directory()
        if directory:
            self.current_directory = directory
            self.statusBar().showMessage(f"Directorio de trabajo: {os.path.basename(self.current_directory)}")
            # Configurar el directorio en el convertidor EPUB
            self.epub_converter.set_directory(directory)
            # Configurar directorio de trabajo en el panel de creación de EPUB
            self.create_panel.set_working_directory(directory)
            # Habilitar botones
            self.refresh_button.setEnabled(True)
            self.open_dir_button.setEnabled(True)
            # Actualizar título de la ventana
            self.update_window_title()
            self.load_chapters()
            # Cargar los términos personalizados guardados
            self.translate_panel.load_saved_terms()

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
            open_button = QPushButton("Abrir")
            # Botón para traducir solo este capítulo específico con la configuración actual
            translate_button = QPushButton("Traducir")
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
            self.statusBar().showMessage("Error: Seleccione un directorio de trabajo primero")
            return

        # Validar el rango de capítulos si se especificó
        if data['start_chapter'] is not None and data['end_chapter'] is not None:
            total_chapters = self.chapters_table.rowCount()
            if data['start_chapter'] < 1 or data['end_chapter'] > total_chapters:
                self.statusBar().showMessage(
                    f"Error: El rango debe estar entre 1 y {total_chapters}"
                )
                return
            if data['start_chapter'] > data['end_chapter']:
                self.statusBar().showMessage(
                    "Error: El capítulo inicial no puede ser mayor que el final"
                )
                return

        # Confirmar la operación
        if not show_confirmation_dialog(
            "¿Desea proceder con la creación del EPUB?\n"
            "Esto puede tomar varios segundos dependiendo del número de capítulos."
        ):
            return

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
            self.statusBar().showMessage(message, 5000)
            # No reiniciar el formulario - mantener datos
        else:
            # Mostrar mensaje de error
            self.statusBar().showMessage(f"Error: {message}")
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
        """Aplica color al item de estado según su valor"""
        if status == "Error":
            status_item.setForeground(QColor(165, 42, 42))  # Rojo oscuro más legible
        elif status == "Traducido":
            status_item.setForeground(QColor(34, 139, 34))  # Verde oscuro más legible
        else:
            # Para "Sin procesar" u otros estados, usar color de texto del sistema
            palette = QApplication.instance().palette()
            system_text_color = palette.color(QPalette.ColorRole.Text)
            status_item.setForeground(system_text_color)

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

        # Obtener idiomas
        source_lang = translate_panel.source_lang_combo.currentText()
        target_lang = translate_panel.target_lang_combo.currentText()

        if source_lang == target_lang:
            self.statusBar().showMessage("Error: Los idiomas de origen y destino no pueden ser iguales")
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

        # Confirmar la operación
        from src.logic.functions import show_confirmation_dialog
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
            enable_check
        )

    def import_epub(self):
        """Maneja la importación de archivos EPUB"""
        from PyQt6.QtWidgets import QFileDialog

        # Abrir diálogo para seleccionar archivo EPUB
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo EPUB",
            "",
            "Archivos EPUB (*.epub);;Todos los archivos (*.*)"
        )

        if not file_path:
            return

        # La carpeta se creará en la misma ubicación que el EPUB
        epub_dir = os.path.dirname(file_path)

        # Confirmar la importación con opciones
        accepted, options = show_import_confirmation_dialog(
            os.path.basename(file_path),
            epub_dir,
            self
        )

        if not accepted:
            return

        # Iniciar la importación
        self.statusBar().showMessage("Importando EPUB...")
        self.import_epub_button.setEnabled(False)
        self.nav_button.setEnabled(False)

        self.epub_importer.import_epub(file_path, options)

    def handle_epub_import_finished(self, success, message, directory_path):
        """Maneja la finalización de la importación de EPUB"""
        # Restaurar botones
        self.import_epub_button.setEnabled(True)
        self.nav_button.setEnabled(True)

        if success:
            # Establecer automáticamente el directorio importado como directorio de trabajo
            self.current_directory = directory_path

            # Configurar el directorio en el convertidor EPUB
            self.epub_converter.set_directory(directory_path)

            # Configurar directorio de trabajo en el panel de creación de EPUB
            self.create_panel.set_working_directory(directory_path)

            # Habilitar botones
            self.refresh_button.setEnabled(True)
            self.open_dir_button.setEnabled(True)

            # Actualizar título de la ventana
            self.update_window_title()

            # Cargar los archivos
            self.load_chapters()

            # Cargar los términos personalizados guardados
            self.translate_panel.load_saved_terms()

            # Mostrar mensaje de éxito
            self.statusBar().showMessage(message, 5000)
        else:
            # Mostrar mensaje de error
            self.statusBar().showMessage(f"Error: {message}")
            from src.logic.functions import show_error_dialog
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

            self.statusBar().showMessage("Abriendo archivo de registro...", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error al abrir archivo de registro: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = NovelManagerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
