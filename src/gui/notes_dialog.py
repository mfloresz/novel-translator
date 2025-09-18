import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QTextEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from src.logic.database import TranslationDatabase

class NotesDialog(QDialog):
    """
    Diálogo para editar las notas de la novela.
    Permite leer y modificar el campo 'notes' de la tabla book_metadata.
    """

    def __init__(self, directory, lang_manager, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.lang_manager = lang_manager
        self.db = TranslationDatabase(directory)

        self.init_ui()
        self.load_notes()

    def init_ui(self):
        """Inicializa la interfaz de usuario del diálogo"""
        self.setWindowTitle(self.lang_manager.get_string("notes_dialog.title", "Notas de la Novela"))
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout()

        # Etiqueta de instrucciones
        instructions_label = QLabel(self.lang_manager.get_string("notes_dialog.instructions",
            "Ingrese las notas para esta novela. Estas notas se guardarán en la base de datos del proyecto."))
        instructions_label.setWordWrap(True)
        layout.addWidget(instructions_label)

        # Área de texto para las notas
        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText(self.lang_manager.get_string("notes_dialog.placeholder",
            "Escriba aquí las notas sobre la novela..."))
        layout.addWidget(self.notes_text)

        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.save_button = QPushButton(self.lang_manager.get_string("notes_dialog.save_button", "Guardar"))
        self.save_button.clicked.connect(self.save_notes)
        buttons_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton(self.lang_manager.get_string("notes_dialog.cancel_button", "Cancelar"))
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def load_notes(self):
        """Carga las notas existentes desde la base de datos"""
        try:
            metadata = self.db.get_book_metadata()
            notes = metadata.get('notes', '')
            self.notes_text.setPlainText(notes)
        except Exception as e:
            QMessageBox.warning(self,
                self.lang_manager.get_string("error_dialog.title", "Error"),
                self.lang_manager.get_string("notes_dialog.load_error", "Error al cargar las notas: {error}").format(error=str(e)))

    def save_notes(self):
        """Guarda las notas en la base de datos"""
        try:
            notes = self.notes_text.toPlainText().strip()

            # Obtener metadatos existentes para preservar otros campos
            metadata = self.db.get_book_metadata()

            # Guardar metadatos con las nuevas notas
            success = self.db.save_book_metadata(
                title=metadata.get('title', ''),
                author=metadata.get('author', ''),
                description=metadata.get('description', ''),
                notes=notes
            )

            if success:
                QMessageBox.information(self,
                    self.lang_manager.get_string("success_dialog.title", "Éxito"),
                    self.lang_manager.get_string("notes_dialog.save_success", "Notas guardadas exitosamente."))
                self.accept()
            else:
                QMessageBox.warning(self,
                    self.lang_manager.get_string("error_dialog.title", "Error"),
                    self.lang_manager.get_string("notes_dialog.save_error", "Error al guardar las notas."))

        except Exception as e:
            QMessageBox.critical(self,
                self.lang_manager.get_string("error_dialog.title", "Error"),
                self.lang_manager.get_string("notes_dialog.save_error_general", "Error al guardar las notas: {error}").format(error=str(e)))

    def get_notes(self):
        """Retorna las notas actuales"""
        return self.notes_text.toPlainText().strip()