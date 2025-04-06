from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QRadioButton, QGroupBox,
                           QMessageBox)
from PyQt6.QtCore import Qt
from src.logic.cleaner import CleanerLogic
from src.logic.functions import show_confirmation_dialog, get_file_range

class CleanPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.cleaner = CleanerLogic()
        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()

        # Text section
        text_layout = QVBoxLayout()
        text_label = QLabel("Texto:")
        self.text_input = QLineEdit()
        text_layout.addWidget(text_label)
        text_layout.addWidget(self.text_input)

        # Añadir campo para texto de reemplazo
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Texto de reemplazo")
        text_layout.addWidget(QLabel("Reemplazar por:"))
        text_layout.addWidget(self.replace_input)

        # Task section
        task_group = QGroupBox("Tarea:")
        task_layout = QVBoxLayout()

        self.task_remove_from_text = QRadioButton("Eliminar a partir del texto")
        self.task_remove_duplicates = QRadioButton("Eliminar duplicados")
        self.task_remove_line = QRadioButton("Eliminar linea")
        self.task_remove_blanks = QRadioButton("Eliminar líneas en blanco múltiples")
        self.task_search_replace = QRadioButton("Buscar y reemplazar")

        task_layout.addWidget(self.task_remove_from_text)
        task_layout.addWidget(self.task_remove_duplicates)
        task_layout.addWidget(self.task_remove_line)
        task_layout.addWidget(self.task_remove_blanks)
        task_layout.addWidget(self.task_search_replace)

        task_group.setLayout(task_layout)

        # Range section
        range_group = QGroupBox("Rango:")
        range_layout = QVBoxLayout()

        self.range_all = QRadioButton("Todos")
        self.range_all.setChecked(True)  # Por defecto seleccionado

        range_from_layout = QHBoxLayout()
        self.range_from = QRadioButton("De:")
        self.range_from_input = QLineEdit()
        range_from_label = QLabel("a:")
        self.range_to_input = QLineEdit()

        range_from_layout.addWidget(self.range_from)
        range_from_layout.addWidget(self.range_from_input)
        range_from_layout.addWidget(range_from_label)
        range_from_layout.addWidget(self.range_to_input)

        range_layout.addWidget(self.range_all)
        range_layout.addLayout(range_from_layout)

        range_group.setLayout(range_layout)

        # Clean button
        self.clean_button = QPushButton("Limpiar")
        self.clean_button.clicked.connect(self.handle_clean)

        # Add all layouts to the main layout
        main_layout.addLayout(text_layout)
        main_layout.addWidget(task_group)
        main_layout.addWidget(range_group)
        main_layout.addWidget(self.clean_button)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def handle_clean(self):
        if not self.main_window.current_directory:
            self.main_window.statusBar().showMessage("Error: Seleccione un directorio primero")
            return

        # Obtener modo de limpieza
        mode = self._get_cleaning_mode()
        if not mode:
            self.main_window.statusBar().showMessage("Error: Seleccione una tarea")
            return

        # Obtener rango
        try:
            start, end = self._get_range()
        except ValueError as e:
            self.main_window.statusBar().showMessage(f"Error: {str(e)}")
            return

        # Confirmar operación
        if not show_confirmation_dialog("Esta operación modificará los archivos originales. ¿Desea continuar?"):
            return

        # Obtener archivos en el rango
        files = get_file_range(self.main_window.chapters_table, start, end)

        # Procesar archivos
        processed, modified = self.cleaner.clean_files(
            self.main_window.current_directory,
            files,
            mode,
            self.text_input.text(),
            self.replace_input.text() if mode == "search_replace" else ""
        )

        self.main_window.statusBar().showMessage(
            f"Proceso completado. Archivos procesados: {processed}, modificados: {modified}"
        )

    def _get_cleaning_mode(self):
        """Determina el modo de limpieza seleccionado"""
        if self.task_remove_from_text.isChecked():
            return "remove_after"
        elif self.task_remove_duplicates.isChecked():
            return "remove_duplicates"
        elif self.task_remove_line.isChecked():
            return "remove_line"
        elif self.task_remove_blanks.isChecked():
            return "remove_multiple_blanks"
        elif self.task_search_replace.isChecked():
            return "search_replace"
        return None

    def _get_range(self):
        """Obtiene el rango de capítulos a procesar"""
        if self.range_all.isChecked():
            return 1, self.main_window.chapters_table.rowCount()

        try:
            start = int(self.range_from_input.text())
            end = int(self.range_to_input.text())

            if start < 1 or end > self.main_window.chapters_table.rowCount():
                raise ValueError("Rango fuera de límites")
            if start > end:
                raise ValueError("El capítulo inicial no puede ser mayor que el final")

            return start, end
        except ValueError:
            raise ValueError("Rango inválido")
