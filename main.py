import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                           QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                           QPushButton, QLabel, QHeaderView, QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics, QPixmap, QIcon
from src.gui.clean import CleanPanel
from src.gui.create import CreateEpubPanel
from src.gui.translate import TranslatePanel
from src.logic.get_path import get_directory
from src.logic.loader import FileLoader
from src.logic.creator import EpubConverterLogic
from src.logic.functions import show_confirmation_dialog
import subprocess

class ElidedLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.full_text = ""
        self.setMinimumWidth(420)
        self.setMaximumWidth(420)

    def setText(self, text):
        self.full_text = text
        self.update_elided_text()

    def update_elided_text(self):
        metrics = QFontMetrics(self.font())
        elided_text = metrics.elidedText(self.full_text, Qt.TextElideMode.ElideLeft, self.width())
        super().setText(elided_text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_elided_text()

class NovelManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_directory = None
        self.setWindowTitle("Novel Manager")
        self.setGeometry(100, 100, 1000, 600)

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

        # Directory section
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Directorio:")
        self.dir_display = ElidedLabel()
        self.nav_button = QPushButton("Navegar")
        self.nav_button.clicked.connect(self.select_directory)

        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_display, stretch=1)
        dir_layout.addWidget(self.nav_button)

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

        # Configurar iconos para las pestañas
        self.set_tab_icons()

        right_layout.addWidget(self.tab_widget)

        # Add both panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # Set initial sizes (left:right ratio roughly 2:1)
        splitter.setSizes([650, 350])

        # Status bar
        self.statusBar().showMessage("Estado: Esperando selección de directorio")

        # Initialize file loader
        self.file_loader = FileLoader()
        self.file_loader.files_loaded.connect(self._add_files_to_table)
        self.file_loader.loading_finished.connect(self._loading_finished)
        self.file_loader.loading_error.connect(self._show_loading_error)

        # Inicializar el convertidor EPUB
        self.epub_converter = EpubConverterLogic()
        self.epub_converter.progress_updated.connect(self.update_status_message)
        self.epub_converter.conversion_finished.connect(self.handle_epub_conversion_finished)

        # Conectar la señal del panel de creación
        self.create_panel.epub_creation_requested.connect(self.handle_epub_creation)

    def set_tab_icons(self):
        """Configurar iconos SVG para las pestañas"""
        try:
            # Rutas de los iconos SVG
            clean_icon_path = "src/gui/icons/clean.svg"
            ebook_icon_path = "src/gui/icons/ebook.svg"
            translate_icon_path = "src/gui/icons/translate.svg"

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
            self.dir_display.setText(self.current_directory)
            self.statusBar().showMessage(f"Directorio seleccionado: {self.current_directory}")
            # Configurar el directorio en el convertidor EPUB
            self.epub_converter.set_directory(directory)
            # Configurar directorio de trabajo en el panel de creación de EPUB
            self.create_panel.set_working_directory(directory)
            self.load_chapters()
            # Cargar los términos personalizados guardados
            self.translate_panel.load_saved_terms()

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
            f"Cargados {total_files} archivos de {self.current_directory}"
        )
        # Actualizar el rango máximo en el panel de traducción
        self.translate_panel.set_chapter_range(total_files)

    def _show_loading_error(self, error_message):
        self.statusBar().showMessage(f"Error: {error_message}")

    def update_file_status(self, filename, new_status):
        """Actualiza el estado de un archivo en la tabla"""
        for row in range(self.chapters_table.rowCount()):
            name_item = self.chapters_table.item(row, 0)
            if name_item and name_item.text() == filename:
                status_item = self.chapters_table.item(row, 1)
                status_item.setText(new_status)
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
            # Reiniciar el formulario
            self.create_panel.reset_form()
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
        api_key = translate_panel.api_input.text().strip()
        if not api_key:
            self.statusBar().showMessage("Error: API key no proporcionada")
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
        translate_panel.translation_manager.translate_files(
            files_to_translate,
            source_lang,
            target_lang,
            api_key,
            self.update_file_status,
            custom_terms,
            segment_size,
            enable_check
        )

def main():
    app = QApplication(sys.argv)
    window = NovelManagerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
