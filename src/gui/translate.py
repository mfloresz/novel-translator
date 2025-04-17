import requests
import time
import json
import os
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QGroupBox, QComboBox,
                           QSpinBox, QFormLayout, QPlainTextEdit, QRadioButton)
from PyQt6.QtCore import Qt
from dotenv import load_dotenv
from src.logic.translation_manager import TranslationManager
from src.logic.functions import show_confirmation_dialog

class TranslatePanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.translation_manager = TranslationManager()

        # Cargar variables de entorno desde .env en la carpeta padre
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)

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

        # Language selection - now in one line
        lang_layout = QHBoxLayout()
        self.source_lang_combo = QComboBox()
        self.target_lang_combo = QComboBox()

        # Populate language combos
        languages = list(self.translation_manager.get_supported_languages().keys())
        self.source_lang_combo.addItems(languages)
        self.target_lang_combo.addItems(languages)

        lang_layout.addWidget(QLabel("Idioma Origen:"))
        lang_layout.addWidget(self.source_lang_combo)
        lang_layout.addWidget(QLabel("Idioma Destino:"))
        lang_layout.addWidget(self.target_lang_combo)

        form_layout.addRow(lang_layout)

        # Text segmentation options
        segmentation_layout = QHBoxLayout()
        self.segment_checkbox = QRadioButton("Segmentar texto (caracteres)")
        self.segment_size_input = QLineEdit()
        self.segment_size_input.setPlaceholderText("Caracteres por segmento")
        self.segment_size_input.setEnabled(False)
        self.segment_size_input.setText("5000")  # Valor por defecto

        segmentation_layout.addWidget(self.segment_checkbox)
        segmentation_layout.addWidget(self.segment_size_input)
        segmentation_layout.addStretch()

        form_layout.addRow(segmentation_layout)

        # Custom Terms section
        terms_group = QGroupBox("Términos Personalizados")
        terms_layout = QVBoxLayout()

        # Instrucciones para los términos
        terms_instructions = QLabel(
            "Ingrese los términos y sus traducciones (uno por línea)"
        )
        terms_instructions.setWordWrap(True)
        terms_layout.addWidget(terms_instructions)

        # Campo para los términos personalizados
        self.terms_input = QPlainTextEdit()
        self.terms_input.setMinimumHeight(100)
        terms_layout.addWidget(self.terms_input)

        terms_group.setLayout(terms_layout)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(terms_group)

        # Chapter range group
        range_group = QGroupBox("Rango de Capítulos")
        range_layout = QHBoxLayout()

        # Start chapter input
        self.start_chapter_spin = QLineEdit()
        self.start_chapter_spin.setPlaceholderText("Desde")
        range_layout.addWidget(QLabel("Capítulo Inicio:"))
        range_layout.addWidget(self.start_chapter_spin)

        # End chapter input
        self.end_chapter_spin = QLineEdit()
        self.end_chapter_spin.setPlaceholderText("Hasta")
        range_layout.addWidget(QLabel("Capítulo Fin:"))
        range_layout.addWidget(self.end_chapter_spin)

        range_group.setLayout(range_layout)
        main_layout.addWidget(range_group)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Translate button
        self.translate_button = QPushButton("Traducir")
        self.translate_button.setEnabled(True)

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

        # Conectar cambios en los inputs de rango
        self.start_chapter_spin.textChanged.connect(self.adjust_chapter_range)
        self.end_chapter_spin.textChanged.connect(self.adjust_chapter_range)

        # Conectar el checkbox de segmentación
        self.segment_checkbox.toggled.connect(self.segment_size_input.setEnabled)

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

            # Conectar señal de cambio de proveedor para API key
            self.provider_combo.currentTextChanged.connect(self.update_provider_api_key)

            # Cargar modelos iniciales
            self.update_models()

            # Establecer la API key inicial si existe
            self.update_provider_api_key()

        except Exception as e:
            print(f"Error cargando modelos: {e}")

    def update_provider_api_key(self):
        """Actualiza la API key según el proveedor seleccionado"""
        try:
            provider_key = next(
                (k for k, v in self.models_config.items()
                 if v['name'] == self.provider_combo.currentText()),
                None
            )

            if provider_key:
                # Construir el nombre de la variable de entorno (ej: GEMINI_API_KEY)
                env_var_name = f"{provider_key.upper()}_API_KEY"
                api_key = os.getenv(env_var_name, "")
                self.api_input.setText(api_key)
        except Exception as e:
            print(f"Error actualizando API key: {e}")

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

    def set_chapter_range(self, max_chapters):
        """Configura el rango máximo de capítulos"""
        self.start_chapter_spin.setText("1")
        self.end_chapter_spin.setText(str(max_chapters))

    def adjust_chapter_range(self):
        """Ajusta los valores de los inputs para mantener un rango válido"""
        try:
            start_value = int(self.start_chapter_spin.text())
            end_value = int(self.end_chapter_spin.text())
            if start_value > end_value:
                self.end_chapter_spin.setText(self.start_chapter_spin.text())
        except ValueError:
            pass

    def load_saved_terms(self):
        """Carga los términos guardados cuando se selecciona un directorio"""
        if self.main_window.current_directory:
                # Siempre reinicializar con el nuevo directorio
                self.translation_manager.initialize(self.main_window.current_directory)
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
        try:
            start_chapter = int(self.start_chapter_spin.text())
            end_chapter = int(self.end_chapter_spin.text())
        except ValueError:
            self.main_window.statusBar().showMessage("Error: Los valores de rango deben ser números")
            return

        # Obtener términos personalizados
        custom_terms = self.terms_input.toPlainText().strip()

        # Obtener configuración de segmentación
        segment_size = None  # None = no segmentar
        if self.segment_checkbox.isChecked():
            try:
                segment_size = int(self.segment_size_input.text() or 5000)  # Usa 5000 si está vacío
                if segment_size <= 0:
                    segment_size = 5000  # Valor por defecto si es negativo
            except ValueError:
                self.main_window.statusBar().showMessage("Error: El tamaño debe ser un número positivo")
                return

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
            custom_terms,
            segment_size
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
        self.main_window.statusBar().showMessage("Traducción completada", 5000)

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
