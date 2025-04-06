import requests
import time
import json
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QGroupBox, QComboBox,
                           QSpinBox, QFormLayout, QPlainTextEdit)
from PyQt6.QtCore import Qt
from src.logic.translation_manager import TranslationManager
from src.logic.functions import show_confirmation_dialog

class TranslatePanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.translation_manager = TranslationManager()
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()

        # API Key section
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Ingrese su API key")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("API Key:", self.api_input)

        # Provider and Model selection
        provider_layout = QHBoxLayout()
        self.provider_combo = QComboBox()
        self.model_combo = QComboBox()

        provider_layout.addWidget(QLabel("Proveedor:"))
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addWidget(QLabel("Modelo:"))
        provider_layout.addWidget(self.model_combo)

        form_layout.addRow(provider_layout)

        # Language selection
        languages = list(self.translation_manager.get_supported_languages().keys())

        # Source Language ComboBox
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(languages)
        form_layout.addRow("Idioma Origen:", self.source_lang_combo)

        # Target Language ComboBox
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(languages)
        form_layout.addRow("Idioma Destino:", self.target_lang_combo)

        # Custom Terms section
        terms_group = QGroupBox("Términos Personalizados")
        terms_layout = QVBoxLayout()

        # Instrucciones para los términos
        terms_instructions = QLabel(
            "Ingrese los términos y sus traducciones (uno por línea)\n"
            "Formato: Término → Traducción"
        )
        terms_instructions.setWordWrap(True)
        terms_layout.addWidget(terms_instructions)

        # Campo para los términos personalizados
        self.terms_input = QPlainTextEdit()
        self.terms_input.setPlaceholderText("Ejemplo:\nBirth Chart → Carta Natal")
        self.terms_input.setMinimumHeight(100)
        terms_layout.addWidget(self.terms_input)

        terms_group.setLayout(terms_layout)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(terms_group)

        # Chapter range group
        range_group = QGroupBox("Rango de Capítulos")
        range_layout = QFormLayout()

        # Start chapter SpinBox
        self.start_chapter_spin = QSpinBox()
        self.start_chapter_spin.setMinimum(1)
        self.start_chapter_spin.setMaximum(9999)
        range_layout.addRow("Capítulo Inicio:", self.start_chapter_spin)

        # End chapter SpinBox
        self.end_chapter_spin = QSpinBox()
        self.end_chapter_spin.setMinimum(1)
        self.end_chapter_spin.setMaximum(9999)
        range_layout.addRow("Capítulo Fin:", self.end_chapter_spin)

        range_group.setLayout(range_layout)
        main_layout.addWidget(range_group)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Translate button
        self.translate_button = QPushButton("Traducir")

        # Stop button
        self.stop_button = QPushButton("Detener")
        self.stop_button.setEnabled(False)

        buttons_layout.addWidget(self.translate_button)
        buttons_layout.addWidget(self.stop_button)

        # Add all layouts to main layout
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        # Cargar proveedores y modelos
        self.load_translation_models()

    def load_translation_models(self):
        """Carga los proveedores y modelos desde el JSON"""
        try:
            models_path = Path(__file__).parent.parent / 'logic' / 'translation_models.json'
            with open(models_path, 'r') as f:
                self.models_config = json.load(f)

            # Cargar proveedores
            self.provider_combo.clear()
            self.provider_combo.addItems([config['name'] for config in self.models_config.values()])

            # Conectar señal de cambio de proveedor
            self.provider_combo.currentTextChanged.connect(self.update_models)

            # Cargar modelos iniciales
            self.update_models()
        except Exception as e:
            print(f"Error cargando modelos: {e}")

    def update_models(self):
        """Actualiza la lista de modelos según el proveedor seleccionado"""
        try:
            provider = next(
                (k for k, v in self.models_config.items()
                 if v['name'] == self.provider_combo.currentText()),
                None
            )

            if provider:
                self.model_combo.clear()
                models = self.models_config[provider]['models']
                self.model_combo.addItems([m['name'] for m in models.values()])
        except Exception as e:
            print(f"Error actualizando modelos: {e}")

    def connect_signals(self):
        """Conecta las señales de los widgets con sus slots correspondientes"""
        self.translate_button.clicked.connect(self.start_translation)
        self.stop_button.clicked.connect(self.stop_translation)

        # Conectar señales del TranslationManager
        self.translation_manager.progress_updated.connect(self.update_progress)
        self.translation_manager.translation_completed.connect(self.handle_translation_completed)
        self.translation_manager.all_translations_completed.connect(self.handle_all_completed)
        self.translation_manager.error_occurred.connect(self.handle_error)

        # Conectar cambios en los SpinBox
        self.start_chapter_spin.valueChanged.connect(self.adjust_chapter_range)
        self.end_chapter_spin.valueChanged.connect(self.adjust_chapter_range)

    def set_chapter_range(self, max_chapters):
        """Configura el rango máximo de capítulos"""
        self.start_chapter_spin.setMaximum(max_chapters)
        self.end_chapter_spin.setMaximum(max_chapters)
        self.end_chapter_spin.setValue(max_chapters)

    def adjust_chapter_range(self):
        """Ajusta los valores de los SpinBox para mantener un rango válido"""
        if self.start_chapter_spin.value() > self.end_chapter_spin.value():
            self.end_chapter_spin.setValue(self.start_chapter_spin.value())

    def load_saved_terms(self):
        """Carga los términos guardados cuando se selecciona un directorio"""
        if self.main_window.current_directory:
            # Inicializa el translation_manager con el directorio actual si no está inicializado
            if not self.translation_manager.working_directory:
                self.translation_manager.initialize(self.main_window.current_directory)

            # Obtiene los términos guardados
            saved_terms = self.translation_manager.get_custom_terms()
            if saved_terms:
                self.terms_input.setPlainText(saved_terms)

    def start_translation(self):
        """Inicia el proceso de traducción"""
        if not self.main_window.current_directory:
            self.main_window.statusBar().showMessage("Error: Seleccione un directorio primero")
            return

        # Validar API key
        api_key = self.api_input.text().strip()
        if not api_key:
            self.main_window.statusBar().showMessage("Error: API key no proporcionada")
            return

        # Obtener proveedor y modelo seleccionados
        provider = next(
            (k for k, v in self.models_config.items()
             if v['name'] == self.provider_combo.currentText()),
            None
        )
        model = next(
            (k for k, v in self.models_config[provider]['models'].items()
             if v['name'] == self.model_combo.currentText()),
            None
        )

        # Obtener idiomas seleccionados
        source_lang = self.source_lang_combo.currentText()
        target_lang = self.target_lang_combo.currentText()

        if source_lang == target_lang:
            self.main_window.statusBar().showMessage("Error: Los idiomas de origen y destino no pueden ser iguales")
            return

        # Obtener rango de capítulos
        start_chapter = self.start_chapter_spin.value()
        end_chapter = self.end_chapter_spin.value()

        # Obtener términos personalizados
        custom_terms = self.terms_input.toPlainText().strip()

        # Confirmar la operación
        if not show_confirmation_dialog(
            "Esta operación modificará los archivos originales.\n"
            "¿Desea continuar con la traducción?"
        ):
            return

        # Preparar traducción
        self.translation_manager.initialize(
            self.main_window.current_directory,
            provider,
            model
        )

        # Obtener archivos del rango seleccionado
        files_to_translate = []
        for row in range(start_chapter - 1, end_chapter):
            name_item = self.main_window.chapters_table.item(row, 0)
            if name_item:
                files_to_translate.append({
                    'name': name_item.text(),
                    'row': row
                })

        if not files_to_translate:
            self.main_window.statusBar().showMessage("Error: No hay archivos para traducir en el rango seleccionado")
            return

        # Configurar UI para traducción
        self.translate_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Iniciar traducción
        self.translation_manager.translate_files(
            files_to_translate,
            source_lang,
            target_lang,
            api_key,
            self.update_file_status,
            custom_terms
        )

    def stop_translation(self):
        """Detiene el proceso de traducción"""
        self.translation_manager.stop_translation()
        self.stop_button.setEnabled(False)
        self.main_window.statusBar().showMessage("Deteniendo traducción...")

    def update_progress(self, message):
        """Actualiza la barra de estado con el progreso"""
        self.main_window.statusBar().showMessage(message)

    def handle_translation_completed(self, filename, success):
        """Maneja la finalización de la traducción de un archivo"""
        if success:
            self.update_file_status(filename, "Traducido")
        else:
            self.update_file_status(filename, "Error")

    def handle_all_completed(self):
        """Maneja la finalización de todas las traducciones"""
        self.translate_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def handle_error(self, error_message):
        """Maneja los errores durante la traducción"""
        self.main_window.statusBar().showMessage(f"Error: {error_message}")

    def update_file_status(self, filename, status):
        """Actualiza el estado de un archivo en la tabla"""
        for row in range(self.main_window.chapters_table.rowCount()):
            name_item = self.main_window.chapters_table.item(row, 0)
            if name_item and name_item.text() == filename:
                status_item = self.main_window.chapters_table.item(row, 1)
                if status_item:
                    status_item.setText(status)
                break
