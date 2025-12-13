import requests
import time
import json
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QGroupBox, QComboBox,
                           QSpinBox, QFormLayout, QPlainTextEdit, QRadioButton,
                           QCheckBox, QDialog, QMessageBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
from dotenv import load_dotenv
from src.logic.translation_manager import TranslationManager
from src.logic.database import TranslationDatabase
from src.logic.functions import show_confirmation_dialog, load_preset_terms
from src.logic.status_manager import STATUS_TRANSLATED, STATUS_ERROR, STATUS_PROCESSING, get_status_text
from src.gui.prompt_refine_settings import PromptRefineSettingsDialog

class PresetTermsDialog(QDialog):
    def __init__(self, source_lang, target_lang, parent=None):
        super().__init__(parent)
        self.selected_term = None
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.main_window = parent.main_window if parent else None
        self.init_ui()
        self.load_preset_terms()

    def _get_string(self, key, default_text=""):
        """Get a localized string from the language manager."""
        if self.main_window and hasattr(self.main_window, 'lang_manager'):
            return self.main_window.lang_manager.get_string(key, default_text)
        return default_text or key

    def init_ui(self):
        self.setWindowTitle(self._get_string("translate_panel.preset_terms_dialog.title"))
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout()

        # Instrucciones
        instructions = QLabel(self._get_string("translate_panel.preset_terms_dialog.instructions"))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Lista de términos
        self.terms_list = QListWidget()
        self.terms_list.itemDoubleClicked.connect(self.on_term_double_clicked)
        layout.addWidget(self.terms_list)

        # Botones
        buttons_layout = QHBoxLayout()
        self.cancel_button = QPushButton(self._get_string("translate_panel.preset_terms_dialog.cancel_button"))
        self.add_button = QPushButton(self._get_string("translate_panel.preset_terms_dialog.add_button"))

        self.cancel_button.clicked.connect(self.reject)
        self.add_button.clicked.connect(self.add_selected_term)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.add_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def load_preset_terms(self):
        """Carga los términos predefinidos desde el archivo JSON específico del par de idiomas"""
        try:
            terms = load_preset_terms(self.source_lang, self.target_lang)
            self.terms_list.clear()
            for term in terms:
                item = QListWidgetItem(term)
                self.terms_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, self._get_string("error_dialog.title"), 
                              self._get_string("translate_panel.preset_terms_dialog.load_error").format(error=str(e)))

    def on_term_double_clicked(self, item):
        """Maneja el doble clic en un término"""
        self.selected_term = item.text()
        self.accept()

    def add_selected_term(self):
        """Agrega el término seleccionado"""
        current_item = self.terms_list.currentItem()
        if current_item:
            self.selected_term = current_item.text()
            self.accept()
        else:
            QMessageBox.information(self, self._get_string("information_dialog.title", "Información"), 
                                  self._get_string("translate_panel.preset_terms_dialog.no_selection"))

    def get_selected_term(self):
        """Retorna el término seleccionado"""
        return self.selected_term

class ApiKeyConfigDialog(QDialog):
    def __init__(self, provider_name, current_api_key="", parent=None):
        super().__init__(parent)
        self.provider_name = provider_name
        self.api_key = current_api_key
        self.main_window = parent.main_window if parent else None
        self.init_ui()

    def _get_string(self, key, default_text=""):
        """Get a localized string from the language manager."""
        if self.main_window and hasattr(self.main_window, 'lang_manager'):
            return self.main_window.lang_manager.get_string(key, default_text)
        return default_text or key

    def init_ui(self):
        self.setWindowTitle(self._get_string("translate_panel.api_key_dialog.title").format(provider=self.provider_name))
        self.setModal(True)
        self.resize(400, 150)

        layout = QVBoxLayout()

        # Información
        info_label = QLabel(self._get_string("translate_panel.api_key_dialog.info"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Campo API Key
        form_layout = QFormLayout()
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText(self._get_string("translate_panel.api_key_dialog.api_key_placeholder"))
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_input.setText(self.api_key)
        form_layout.addRow(self._get_string("translate_panel.api_key_dialog.api_key_label"), self.api_input)
        layout.addLayout(form_layout)

        # Botones
        buttons_layout = QHBoxLayout()

        self.ok_button = QPushButton(self._get_string("translate_panel.api_key_dialog.ok_button"))
        self.cancel_button = QPushButton(self._get_string("translate_panel.api_key_dialog.cancel_button"))

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.ok_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def get_api_key(self):
        return self.api_input.text().strip()

class RangeTranslationDialog(QDialog):
    def __init__(self, translated_count, total_count, parent=None):
        super().__init__(parent)
        self.translated_count = translated_count
        self.total_count = total_count
        self.main_window = parent.main_window if parent else None
        self.result_choice = False  # False = omitir, True = volver a traducir
        self.init_ui()

    def _get_string(self, key, default_text=""):
        """Get a localized string from the language manager."""
        if self.main_window and hasattr(self.main_window, 'lang_manager'):
            return self.main_window.lang_manager.get_string(key, default_text)
        return default_text or key

    def init_ui(self):
        self.setWindowTitle(self._get_string("translate_panel.range_translation_dialog.title", "Capítulos ya traducidos"))
        self.setModal(True)
        self.resize(450, 100)

        layout = QVBoxLayout()

        # Mensaje informativo
        message = self._get_string(
            "translate_panel.range_translation_dialog.message",
            "Se encontraron {translated} capítulos ya traducidos de {total} en el rango seleccionado. ¿Qué desea hacer?"
        ).format(translated=self.translated_count, total=self.total_count)

        info_label = QLabel(message)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Espacio
        #layout.addStretch()

        # Botones
        buttons_layout = QHBoxLayout()

        self.omit_button = QPushButton(self._get_string("translate_panel.range_translation_dialog.omit_button", "Omitir"))
        self.retranslate_button = QPushButton(self._get_string("translate_panel.range_translation_dialog.retranslate_button", "Volver a traducir"))

        self.omit_button.clicked.connect(self.on_omit)
        self.retranslate_button.clicked.connect(self.on_retranslate)

        buttons_layout.addWidget(self.omit_button)
        buttons_layout.addWidget(self.retranslate_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def on_omit(self):
        """El usuario elige omitir los capítulos ya traducidos"""
        self.result_choice = False
        self.accept()

    def on_retranslate(self):
        """El usuario elige volver a traducir todos los capítulos"""
        self.result_choice = True
        self.accept()

    def get_result(self):
        """Retorna True si elige volver a traducir, False si omite"""
        return self.result_choice

class TranslatePanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.translation_manager = TranslationManager(main_window.lang_manager)
        self.working_directory = None
        self.session_check_refine_settings = None
        self.segmentation_config = None
        self.session_segmentation = None

        # Variable para almacenar API keys temporales
        self.temp_api_keys = {}

        # Crear directorio temporal para prompts de la sesión
        self._temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_prompts_path = Path(self._temp_dir_obj.name)
        self.translation_manager.update_temp_prompts_path(self.temp_prompts_path)

        # Cargar variables de entorno desde .env en la carpeta padre
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)

        # Cargar configuración por defecto
        self.default_config = self._load_default_config()
        self.segmentation_config = self.default_config.get("auto_segmentation", {"enabled": False, "threshold": 10000, "segment_size": 5000})
        self.timeout_config = self.default_config.get("timeout", 120)

        self.init_ui()
        self.connect_signals()

    def _get_string(self, key, default_text=""):
        """Get a localized string from the language manager."""
        if hasattr(self.main_window, 'lang_manager'):
            return self.main_window.lang_manager.get_string(key, default_text)
        return default_text or key

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Provider and Model selection
        provider_layout = QHBoxLayout()
        self.provider_combo = QComboBox()
        self.config_button = QPushButton("⚙")
        self.config_button.setToolTip(self._get_string("translate_panel.api_key_dialog.title").format(provider=""))
        self.config_button.setMaximumWidth(30)
        self.config_button.clicked.connect(self.configure_api_key)
        self.model_combo = QComboBox()

        provider_layout.addWidget(QLabel(self._get_string("translate_panel.provider_label")))
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addWidget(self.config_button)
        provider_layout.addWidget(QLabel(self._get_string("translate_panel.model_label")))
        provider_layout.addWidget(self.model_combo)

        form_layout.addRow(provider_layout)

        # Language selection - now in one line
        lang_layout = QHBoxLayout()
        self.source_lang_combo = QComboBox()
        self.target_lang_combo = QComboBox()

        # Populate language combos
        language_mapping = self.translation_manager.get_supported_languages()
        self.source_lang_combo.clear()
        self.target_lang_combo.clear()

        if language_mapping:
            sorted_languages = sorted(language_mapping.items(), key=lambda x: (x[0] != 'auto', x[1]))
            for code, name in sorted_languages:
                self.source_lang_combo.addItem(name, userData=code)
                self.target_lang_combo.addItem(name, userData=code)

        lang_layout.addWidget(QLabel(self._get_string("translate_panel.source_language_label")))
        lang_layout.addWidget(self.source_lang_combo)
        lang_layout.addWidget(QLabel(self._get_string("translate_panel.target_language_label")))
        lang_layout.addWidget(self.target_lang_combo)

        form_layout.addRow(lang_layout)

        # Combined layout for segmentation and translation options
        options_layout = QHBoxLayout()

        # Auto segmentation option
        self.enable_auto_segmentation_radio = QRadioButton(self._get_string("translate_panel.enable_auto_segmentation"))
        self.enable_auto_segmentation_radio.setToolTip(self._get_string("translate_panel.enable_auto_segmentation.tooltip"))

        options_layout.addWidget(self.enable_auto_segmentation_radio)

        # Add separator
        options_layout.addWidget(QLabel("Traducción:"))

        # Checkbox for enabling translation check
        self.check_translation_checkbox = QCheckBox(self._get_string("translate_panel.check_translation_checkbox"))
        self.check_translation_checkbox.setToolTip(self._get_string("translate_panel.check_translation_checkbox.tooltip"))
        self.check_translation_checkbox.setChecked(True)  # Por defecto está habilitado

        # Checkbox for translation refinement
        self.refine_translation_checkbox = QCheckBox(self._get_string("translate_panel.refine_translation_checkbox"))
        self.refine_translation_checkbox.setToolTip(self._get_string("translate_panel.refine_translation_checkbox.tooltip"))

        self.check_refine_settings_button = QPushButton("⚙")
        self.check_refine_settings_button.setToolTip(self._get_string("translate_panel.check_refine_settings_button.tooltip"))
        self.check_refine_settings_button.setMaximumWidth(30)

        options_layout.addWidget(self.check_translation_checkbox)
        options_layout.addWidget(self.refine_translation_checkbox)
        options_layout.addWidget(self.check_refine_settings_button)
        options_layout.addStretch()

        form_layout.addRow(options_layout)

        # Custom Terms section
        terms_group = QGroupBox(self._get_string("translate_panel.terms_group"))
        terms_layout = QVBoxLayout()

        # Instrucciones para los términos con botones
        terms_header_layout = QHBoxLayout()

        terms_instructions = QLabel(self._get_string("translate_panel.terms_instructions"))
        terms_instructions.setWordWrap(True)
        terms_header_layout.addWidget(terms_instructions)

        # Botón para guardar términos personalizados
        self.save_terms_btn = QPushButton()
        self.save_terms_btn.setMaximumWidth(30)
        self.save_terms_btn.setToolTip(self._get_string("translate_panel.save_terms_button.tooltip", "Guardar términos personalizados"))
        self.save_terms_btn.clicked.connect(self.save_custom_terms)
        terms_header_layout.addWidget(self.save_terms_btn)

        # Botón para copiar símbolo →
        self.copy_arrow_btn = QPushButton(self._get_string("translate_panel.copy_arrow_button"))
        self.copy_arrow_btn.setMaximumWidth(30)
        self.copy_arrow_btn.setToolTip(self._get_string("translate_panel.copy_arrow_button.tooltip"))
        self.copy_arrow_btn.clicked.connect(self.copy_arrow_symbol)
        terms_header_layout.addWidget(self.copy_arrow_btn)

        # Botón para mostrar términos predefinidos
        self.preset_terms_btn = QPushButton(self._get_string("translate_panel.preset_terms_button"))
        self.preset_terms_btn.setMaximumWidth(30)
        self.preset_terms_btn.setToolTip(self._get_string("translate_panel.preset_terms_button.tooltip"))
        self.preset_terms_btn.clicked.connect(self.show_preset_terms)
        terms_header_layout.addWidget(self.preset_terms_btn)

        terms_layout.addLayout(terms_header_layout)

        # Campo para los términos personalizados
        self.terms_input = QPlainTextEdit()
        self.terms_input.setMinimumHeight(100)
        terms_layout.addWidget(self.terms_input)

        terms_group.setLayout(terms_layout)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(terms_group)

        # Chapter range group
        range_group = QGroupBox(self._get_string("translate_panel.range_group"))
        range_layout = QHBoxLayout()

        # Start chapter input
        self.start_chapter_spin = QLineEdit()
        self.start_chapter_spin.setPlaceholderText(self._get_string("translate_panel.range_start_placeholder"))
        range_layout.addWidget(QLabel(self._get_string("translate_panel.range_start_label")))
        range_layout.addWidget(self.start_chapter_spin)

        # End chapter input
        self.end_chapter_spin = QLineEdit()
        self.end_chapter_spin.setPlaceholderText(self._get_string("translate_panel.range_end_placeholder"))
        range_layout.addWidget(QLabel(self._get_string("translate_panel.range_end_label")))
        range_layout.addWidget(self.end_chapter_spin)

        range_group.setLayout(range_layout)
        main_layout.addWidget(range_group)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Translate button
        self.translate_button = QPushButton(self._get_string("translate_panel.translate_button"))
        self.translate_button.setEnabled(True)

        # Stop button
        self.stop_button = QPushButton(self._get_string("translate_panel.stop_button"))
        self.stop_button.setEnabled(False)

        buttons_layout.addWidget(self.translate_button)
        buttons_layout.addWidget(self.stop_button)

        # Add all layouts to main layout
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        # Cargar proveedores y modelos
        self.load_translation_models()

        # Cargar valores por defecto de la configuración
        self._load_default_values()

        # Comentar estas líneas para permitir escritura libre
        # self.start_chapter_spin.textChanged.connect(self.adjust_chapter_range)
        # self.end_chapter_spin.textChanged.connect(self.adjust_chapter_range)

        # No hay conexión necesaria para el radio button de autosegmentación

        # Configurar iconos para las pestañas y botones (después de configurar detección de tema)
        self.set_terms_button_icons()

    def _load_default_config(self) -> Dict:
        """Carga la configuración por defecto desde config.json"""
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'config.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración por defecto: {e}")

        # Valores por defecto si no se puede cargar el archivo
        return {
            "provider": "chutes",
            "model": "mistral-3.2",
            "source_language": "Inglés",
            "target_language": "Español (MX)"
        }

    def load_translation_models(self):
        """Carga los proveedores y modelos desde el JSON"""
        try:
            models_path = Path(__file__).parent.parent / 'config' / 'translation_models.json'
            with open(models_path, 'r') as f:
                self.models_config = json.load(f)

            # Cargar proveedores
            self.provider_combo.clear()
            for key, config in self.models_config.items():
                self.provider_combo.addItem(config['name'], userData=key)

            # Conectar señal de cambio de proveedor
            self.provider_combo.currentTextChanged.connect(self.update_models)

            # Cargar modelos iniciales
            self.update_models()

        except Exception as e:
            print(f"Error cargando modelos: {e}")

    def _load_default_values(self):
        """Carga los valores por defecto de la configuración en los controles"""
        try:
            # Establecer proveedor por defecto
            default_provider = self.default_config.get('provider', '')
            provider_index = -1
            for i in range(self.provider_combo.count()):
                if self.provider_combo.itemData(i) == default_provider:
                    provider_index = i
                    break

            if provider_index >= 0:
                self.provider_combo.setCurrentIndex(provider_index)
                # Actualizar modelos después de seleccionar el proveedor
                self.update_models()

                # Establecer modelo por defecto
                default_model = self.default_config.get('model', '')
                model_index = -1
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemData(i) == default_model:
                        model_index = i
                        break

                if model_index >= 0:
                    self.model_combo.setCurrentIndex(model_index)

            # Establecer idiomas por defecto
            default_source = self.default_config.get('source_language', '')
            source_index = -1
            for i in range(self.source_lang_combo.count()):
                if self.source_lang_combo.itemData(i) == default_source:
                    source_index = i
                    break

            if source_index >= 0:
                self.source_lang_combo.setCurrentIndex(source_index)

            default_target = self.default_config.get('target_language', '')
            target_index = -1
            for i in range(self.target_lang_combo.count()):
                if self.target_lang_combo.itemData(i) == default_target:
                    target_index = i
                    break

            if target_index >= 0:
                self.target_lang_combo.setCurrentIndex(target_index)

            # Actualizar estado del botón de términos predefinidos
            self.update_preset_terms_button_state()

        except Exception as e:
            print(f"Error cargando valores por defecto: {e}")

    def configure_api_key(self):
        """Abre el diálogo de configuración de API Key"""
        provider_key = self.provider_combo.currentData()
        provider_name = self.provider_combo.currentText()

        # Si por alguna razón currentData() devuelve None, buscar por nombre como fallback
        if provider_key is None:
            provider_key = next(
                (k for k, v in self.models_config.items()
                 if v['name'] == provider_name),
                None
            )

        if not provider_name:
            return

        # Obtener API key actual (temporal o del .env)
        current_api_key = self.get_current_api_key()

        dialog = ApiKeyConfigDialog(provider_name, current_api_key, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_api_key = dialog.get_api_key()
            if new_api_key:
                # Guardar API key temporal para el proveedor actual
                if provider_key:
                    self.temp_api_keys[provider_key] = new_api_key
                    self.main_window.statusBar().showMessage(f"API Key configurada temporalmente para {provider_name}", 3000)

    def get_current_api_key(self):
        """Obtiene la API key actual (temporal o del .env)"""
        provider_key = self.provider_combo.currentData()

        # Si por alguna razón currentData() devuelve None, buscar por nombre como fallback
        if provider_key is None:
            provider_key = next(
                (k for k, v in self.models_config.items()
                 if v['name'] == self.provider_combo.currentText()),
                None
            )

        if provider_key:
            # Priorizar API key temporal si existe
            if provider_key in self.temp_api_keys:
                return self.temp_api_keys[provider_key]
            else:
                # Usar del .env si no hay temporal
                env_var_name = f"{provider_key.upper()}_API_KEY"
                return os.getenv(env_var_name, "")

        return ""

    def update_models(self):
        """Actualiza la lista de modelos según el proveedor seleccionado"""
        try:
            provider = self.provider_combo.currentData()

            # Si por alguna razón currentData() devuelve None, buscar por nombre como fallback
            if provider is None:
                provider = next(
                    (k for k, v in self.models_config.items()
                     if v['name'] == self.provider_combo.currentText()),
                    None
                )

            if provider:
                self.model_combo.clear()
                # Encontrar la clave del proveedor
                provider_key = next(
                    (k for k, v in self.models_config.items()
                     if v['name'] == self.provider_combo.currentText()),
                    None
                )
                if provider_key:
                    models = self.models_config[provider_key]['models']
                    for key, model in models.items():
                        self.model_combo.addItem(model['name'], userData=key)
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

        # Conectar cambio de idioma a la actualización del botón de términos
        self.source_lang_combo.currentIndexChanged.connect(self.update_preset_terms_button_state)
        self.target_lang_combo.currentIndexChanged.connect(self.update_preset_terms_button_state)
        self.check_refine_settings_button.clicked.connect(self.open_check_refine_settings)

    def open_check_refine_settings(self):
        """Abre el diálogo de configuración para prompts, comprobación y refinado."""
        current_settings = self.session_check_refine_settings or self.default_config.get("check_refine_settings")
        source_lang = self.source_lang_combo.currentData()
        target_lang = self.target_lang_combo.currentData()

        dialog = PromptRefineSettingsDialog(
            parent=self,
            current_settings=current_settings,
            models_config=self.models_config,
            source_lang=source_lang,
            target_lang=target_lang,
            temp_prompts_path=self.temp_prompts_path,  # Pasar la ruta temporal
            enabled_auto_segmentation=self.enable_auto_segmentation_radio.isChecked()
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session_check_refine_settings = dialog.get_settings()
            self.session_segmentation = self.session_check_refine_settings.get("auto_segmentation", None)
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.check_refine_settings_saved_session", "Configuración guardada"), 3000)

    def update_preset_terms_button_state(self):
        """
        Habilita o deshabilita el botón de términos predefinidos basado en si
        existen términos para el par de idiomas seleccionado.
        """
        source_lang = self.source_lang_combo.currentData()
        target_lang = self.target_lang_combo.currentData()

        if source_lang and target_lang:
            terms = load_preset_terms(source_lang, target_lang)
            self.preset_terms_btn.setEnabled(bool(terms))
        else:
            self.preset_terms_btn.setEnabled(False)

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
        if self.working_directory:
            self.translation_manager.initialize(self.working_directory)
            saved_terms = self.translation_manager.get_custom_terms()
            if saved_terms:
                self.terms_input.setPlainText(saved_terms)

    def start_translation(self):
        """Inicia el proceso de traducción"""
        if not self.main_window.current_directory:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.error.no_directory"))
            return

        # Validar API key
        api_key = self.get_current_api_key()
        if not api_key:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.error.no_api_key"))
            return

        # Obtener proveedor y modelo seleccionados
        provider = self.provider_combo.currentData()

        # Si por alguna razón currentData() devuelve None, buscar por nombre como fallback
        if provider is None:
            provider = next(
                (k for k, v in self.models_config.items()
                 if v['name'] == self.provider_combo.currentText()),
                None
            )

        if not provider:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.error.no_provider"))
            return

        model = self.model_combo.currentData()

        # Si por alguna razón currentData() devuelve None, buscar por nombre como fallback
        if model is None:
            model = next(
                (k for k, v in self.models_config[provider]['models'].items()
                 if v['name'] == self.model_combo.currentText()),
                None
            )

        if not model:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.error.no_model"))
            return

        # Obtener idiomas seleccionados (códigos)
        source_lang = self.source_lang_combo.currentData()
        target_lang = self.target_lang_combo.currentData()

        if not source_lang or not target_lang or source_lang == target_lang:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.error.same_languages"))
            return

        # Obtener rango de capítulos
        try:
            start_chapter = int(self.start_chapter_spin.text())
            end_chapter = int(self.end_chapter_spin.text())
        except ValueError:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.error.invalid_range"))
            return

        # Obtener términos personalizados
        custom_terms = self.terms_input.toPlainText().strip()

        # Obtener configuración de segmentación efectiva
        segment_size = None
        effective_segmentation = None
        if self.enable_auto_segmentation_radio.isChecked():
            if self.session_segmentation:
                effective_segmentation = self.session_segmentation
            else:
                # Usar configuración por defecto con enabled=True
                effective_segmentation = {**self.segmentation_config, "enabled": True}
        else:
            effective_segmentation = None

        # Obtener estado de la comprobación
        enable_check = self.check_translation_checkbox.isChecked()

        # Obtener estado del refinamiento
        enable_refine = self.refine_translation_checkbox.isChecked()

        # Obtener la configuración de comprobación y refinado
        check_refine_settings = self.session_check_refine_settings or self.default_config.get("check_refine_settings")

        # Preparar traducción
        self.translation_manager.initialize(
            self.main_window.current_directory,
            provider,
            model
        )

        # Guardar la posición actual de scroll
        scroll_position = self.main_window.chapters_table.verticalScrollBar().value()

        # Obtener archivos del rango seleccionado
        files_to_translate = []
        for row in range(start_chapter - 1, end_chapter):
            name_item = self.main_window.chapters_table.item(row, 0)
            if name_item:
                files_to_translate.append({
                    'name': name_item.text(),
                    'row': row
                })

        # Restaurar la posición de scroll
        self.main_window.chapters_table.verticalScrollBar().setValue(scroll_position)

        if not files_to_translate:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.error.no_files"))
            return

        # Verificar si hay capítulos ya traducidos en el rango
        db = TranslationDatabase(self.main_window.current_directory)
        translated_count = 0
        for file_info in files_to_translate:
            if db.is_file_translated(file_info['name']):
                translated_count += 1

        allow_retranslation = False
        if translated_count > 0:
            # Mostrar diálogo para preguntar qué hacer con los capítulos ya traducidos
            dialog = RangeTranslationDialog(translated_count, len(files_to_translate), self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                allow_retranslation = dialog.get_result()
                if not allow_retranslation:
                    # Filtrar la lista para omitir los ya traducidos
                    files_to_translate = [
                        file_info for file_info in files_to_translate
                        if not db.is_file_translated(file_info['name'])
                    ]
                    if not files_to_translate:
                        self.main_window.statusBar().showMessage(
                            self._get_string("translate_panel.range_translation.all_already_translated", "Todos los capítulos en el rango ya están traducidos"))
                        return
            else:
                # Usuario canceló la operación
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
            segment_size,
            enable_check,   # <-- Pasar parámetro para habilitar comprobación
            enable_refine,  # <-- Pasar parámetro para habilitar refinamiento
            check_refine_settings, # <-- Pasar la configuración de comprobación/refinado
            temp_api_keys=self.temp_api_keys,  # <-- Pasar las API keys temporales
            allow_retranslation=allow_retranslation,  # <-- Pasar el flag de permitir re-traducción
            segmentation_config=effective_segmentation,
            timeout=self.timeout_config  # <-- Pasar el timeout configurado
        )

    def stop_translation(self):
        """Detiene el proceso de traducción"""
        self.translation_manager.stop_translation()
        self.stop_button.setEnabled(False)
        self.main_window.statusBar().showMessage(
            self._get_string("translate_panel.translation_stopping"))

    def update_progress(self, message):
        """Actualiza la barra de estado con el progreso"""
        self.main_window.statusBar().showMessage(message)

    def handle_translation_completed(self, filename, success):
        """Maneja la finalización de la traducción de un archivo"""
        if success:
            status_text = get_status_text(STATUS_TRANSLATED, self.main_window.lang_manager)
            self.update_file_status(filename, status_text)
        else:
            status_text = get_status_text(STATUS_ERROR, self.main_window.lang_manager)
            self.update_file_status(filename, status_text)

    def handle_all_completed(self):
        """Maneja la finalización de todas las traducciones"""
        self.translate_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.main_window.statusBar().showMessage(
            self._get_string("translate_panel.translation_completed"), 5000)

    def handle_error(self, error_message):
        """Maneja los errores durante la traducción"""
        self.main_window.statusBar().showMessage(
            self._get_string("error_dialog.title") + ": " + error_message)

    def update_file_status(self, filename, status):
        """Actualiza el estado de un archivo en la tabla"""
        for row in range(self.main_window.chapters_table.rowCount()):
            name_item = self.main_window.chapters_table.item(row, 0)
            if name_item and name_item.text() == filename:
                status_item = self.main_window.chapters_table.item(row, 1)
                if status_item:
                    status_item.setText(status)
                    # Aplicar color usando el método de la ventana principal
                    self.main_window._apply_status_color(status_item, status)
                break

    def set_working_directory(self, directory):
        """Establece el directorio de trabajo y recarga los términos guardados"""
        self.working_directory = directory
        # Recargar términos guardados cuando se cambia el directorio
        self.load_saved_terms()

    def copy_arrow_symbol(self):
        """Copia el símbolo → al portapapeles"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText("→")
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.copy_arrow_button.tooltip").replace("Copiar ", "").replace(" al portapapeles", ""), 2000)
        else:
            self.main_window.statusBar().showMessage(
                self._get_string("main_window.log_file_open_error").format(error=self._get_string("translate_panel.copy_arrow_button.clipboard_error")), 3000)

    def show_preset_terms(self):
        """Muestra el diálogo con términos predefinidos"""
        source_lang = self.source_lang_combo.currentData()
        target_lang = self.target_lang_combo.currentData()

        if not source_lang or not target_lang:
            QMessageBox.warning(self, self._get_string("warning_dialog.title"),
                              self._get_string("translate_panel.preset_terms.no_language_selected"))
            return

        dialog = PresetTermsDialog(source_lang, target_lang, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            selected_term = dialog.get_selected_term()
            if selected_term:
                current_text = self.terms_input.toPlainText()
                if current_text:
                    new_text = current_text + "\n" + selected_term
                else:
                    new_text = selected_term
                self.terms_input.setPlainText(new_text)

    def set_segmentation_config(self, config):
        """Set the segmentation configuration from main.py"""
        self.segmentation_config = config

    def set_terms_button_icons(self):
        """Configurar iconos para los botones de términos según el tema del sistema"""
        try:
            # Ruta del ícono de guardar
            save_icon_path = "src/gui/icons/save_2_line.svg"
            self.save_terms_btn.setIcon(self.main_window.create_themed_icon(save_icon_path))
        except Exception as e:
            print(f"Error cargando ícono del botón de guardar términos: {e}")

    def save_custom_terms(self):
        """Guarda los términos personalizados en la base de datos"""
        if not self.main_window.current_directory:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.error.no_directory"))
            return

        # Obtener términos personalizados del campo de texto
        custom_terms = self.terms_input.toPlainText()

        # Inicializar la base de datos y guardar términos
        db = TranslationDatabase(self.main_window.current_directory)
        if db.save_custom_terms(custom_terms):
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.save_terms_success", "Términos personalizados guardados"), 3000)
        else:
            self.main_window.statusBar().showMessage(
                self._get_string("translate_panel.save_terms_error", "Error al guardar términos personalizados"))
