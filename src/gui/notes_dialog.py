import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QTextEdit, QPushButton, QMessageBox, QPlainTextEdit,
                              QGroupBox, QFrame)
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
        self.main_window = parent  # Guardar referencia a la ventana principal

        self.init_ui()
        self.load_notes()
        self.load_prompts()

    def init_ui(self):
        """Inicializa la interfaz de usuario del diálogo"""
        self.setWindowTitle(self.lang_manager.get_string("notes_dialog.title", "Notas de la Novela"))
        self.setModal(True)
        self.resize(700, 600)

        layout = QVBoxLayout()

        # Etiqueta de instrucciones
        instructions_label = QLabel(self.lang_manager.get_string("notes_dialog.instructions",
            "Ingrese las notas para esta novela. Estas notas se guardarán en la base de datos del proyecto."))
        instructions_label.setWordWrap(True)
        layout.addWidget(instructions_label)

        # Botones para prompts personalizados
        prompts_layout = QHBoxLayout()
        self.translation_button = QPushButton("Traducción")
        self.refine_button = QPushButton("Refinar")
        self.check_button = QPushButton("Comprobar")

        self.translation_button.clicked.connect(lambda: self.show_prompt_field("translation"))
        self.refine_button.clicked.connect(lambda: self.show_prompt_field("refine"))
        self.check_button.clicked.connect(lambda: self.show_prompt_field("check"))

        prompts_layout.addWidget(QLabel("Prompts:"))
        prompts_layout.addWidget(self.translation_button)
        prompts_layout.addWidget(self.refine_button)
        prompts_layout.addWidget(self.check_button)
        prompts_layout.addStretch()
        layout.addLayout(prompts_layout)

        # Área de texto para las notas
        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText(self.lang_manager.get_string("notes_dialog.placeholder",
            "Escriba aquí las notas sobre la novela..."))
        layout.addWidget(self.notes_text)

        # Campos de texto para prompts (inicialmente ocultos)
        self.translation_group = QGroupBox("Prompt de Traducción")
        translation_layout = QVBoxLayout()
        self.translation_text = QPlainTextEdit()
        self.translation_text.setPlaceholderText("Ingrese el prompt personalizado para traducción...")
        translation_layout.addWidget(self.translation_text)

        translation_buttons_layout = QHBoxLayout()
        self.save_translation_button = QPushButton("Guardar Prompt")
        self.cancel_translation_button = QPushButton("Cancelar")
        self.save_translation_button.clicked.connect(lambda: self.save_prompt("translation"))
        self.cancel_translation_button.clicked.connect(lambda: self.hide_prompt_fields())
        translation_buttons_layout.addStretch()
        translation_buttons_layout.addWidget(self.cancel_translation_button)
        translation_buttons_layout.addWidget(self.save_translation_button)
        translation_layout.addLayout(translation_buttons_layout)
        self.translation_group.setLayout(translation_layout)
        layout.addWidget(self.translation_group)
        self.translation_group.setVisible(False)

        self.refine_group = QGroupBox("Prompt de Refinamiento")
        refine_layout = QVBoxLayout()
        self.refine_text = QPlainTextEdit()
        self.refine_text.setPlaceholderText("Ingrese el prompt personalizado para refinamiento...")
        refine_layout.addWidget(self.refine_text)

        refine_buttons_layout = QHBoxLayout()
        self.save_refine_button = QPushButton("Guardar Prompt")
        self.cancel_refine_button = QPushButton("Cancelar")
        self.save_refine_button.clicked.connect(lambda: self.save_prompt("refine"))
        self.cancel_refine_button.clicked.connect(lambda: self.hide_prompt_fields())
        refine_buttons_layout.addStretch()
        refine_buttons_layout.addWidget(self.cancel_refine_button)
        refine_buttons_layout.addWidget(self.save_refine_button)
        refine_layout.addLayout(refine_buttons_layout)
        self.refine_group.setLayout(refine_layout)
        layout.addWidget(self.refine_group)
        self.refine_group.setVisible(False)

        self.check_group = QGroupBox("Prompt de Comprobación")
        check_layout = QVBoxLayout()
        self.check_text = QPlainTextEdit()
        self.check_text.setPlaceholderText("Ingrese el prompt personalizado para comprobación...")
        check_layout.addWidget(self.check_text)

        check_buttons_layout = QHBoxLayout()
        self.save_check_button = QPushButton("Guardar Prompt")
        self.cancel_check_button = QPushButton("Cancelar")
        self.save_check_button.clicked.connect(lambda: self.save_prompt("check"))
        self.cancel_check_button.clicked.connect(lambda: self.hide_prompt_fields())
        check_buttons_layout.addStretch()
        check_buttons_layout.addWidget(self.cancel_check_button)
        check_buttons_layout.addWidget(self.save_check_button)
        check_layout.addLayout(check_buttons_layout)
        self.check_group.setLayout(check_layout)
        layout.addWidget(self.check_group)
        self.check_group.setVisible(False)

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

    def show_prompt_field(self, prompt_type):
        """Muestra el campo de texto para el tipo de prompt especificado"""
        self.hide_prompt_fields()
        if prompt_type == "translation":
            self.translation_group.setVisible(True)
        elif prompt_type == "refine":
            self.refine_group.setVisible(True)
        elif prompt_type == "check":
            self.check_group.setVisible(True)

    def hide_prompt_fields(self):
        """Oculta todos los campos de prompts"""
        self.translation_group.setVisible(False)
        self.refine_group.setVisible(False)
        self.check_group.setVisible(False)

    def save_prompt(self, prompt_type):
        """Guarda el prompt personalizado en la base de datos"""
        if not self.main_window or not hasattr(self.main_window, 'translate_panel'):
            QMessageBox.warning(self, "Error", "No se puede acceder a la configuración de idiomas.")
            return

        source_lang = self.main_window.translate_panel.source_lang_combo.currentData()
        target_lang = self.main_window.translate_panel.target_lang_combo.currentData()

        if not source_lang or not target_lang:
            QMessageBox.warning(self, "Error", "Debe seleccionar idiomas de origen y destino.")
            return

        content = ""
        if prompt_type == "translation":
            content = self.translation_text.toPlainText().strip()
        elif prompt_type == "refine":
            content = self.refine_text.toPlainText().strip()
        elif prompt_type == "check":
            content = self.check_text.toPlainText().strip()

        if not content:
            QMessageBox.warning(self, "Error", "El prompt no puede estar vacío.")
            return

        success = self.db.save_custom_prompt(source_lang, target_lang, prompt_type, content)
        if success:
            QMessageBox.information(self, "Éxito", f"Prompt de {prompt_type} guardado exitosamente.")
            # Actualizar el directorio temporal con el nuevo prompt
            if hasattr(self.main_window, 'load_custom_prompts_to_temp'):
                self.main_window.load_custom_prompts_to_temp()
            self.hide_prompt_fields()
        else:
            QMessageBox.warning(self, "Error", "Error al guardar el prompt.")

    def load_prompts(self):
        """Carga los prompts personalizados desde la base de datos"""
        if not self.main_window or not hasattr(self.main_window, 'translate_panel'):
            return

        source_lang = self.main_window.translate_panel.source_lang_combo.currentData()
        target_lang = self.main_window.translate_panel.target_lang_combo.currentData()

        if not source_lang or not target_lang:
            return

        self.translation_text.setPlainText(self.db.get_custom_prompt(source_lang, target_lang, "translation"))
        self.refine_text.setPlainText(self.db.get_custom_prompt(source_lang, target_lang, "refine"))
        self.check_text.setPlainText(self.db.get_custom_prompt(source_lang, target_lang, "check"))