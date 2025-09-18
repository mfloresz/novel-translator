import json
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QRadioButton,
                            QComboBox, QFormLayout, QHBoxLayout, QPushButton,
                            QLabel, QPlainTextEdit, QSplitter, QScrollArea,
                            QWidget, QMessageBox)
from PyQt6.QtCore import Qt

class PromptRefineSettingsDialog(QDialog):
    def __init__(self, parent=None, current_settings=None, models_config=None,
                 source_lang=None, target_lang=None, temp_prompts_path=None):
        super().__init__(parent)
        self.main_window = parent.main_window if parent else None
        self.models_config = models_config or self._load_models_config()
        self.current_settings = current_settings or self._get_default_settings()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.temp_prompts_path = temp_prompts_path  # Ruta al directorio de prompts temporales

        self.init_ui()
        self.load_settings()
        self.load_prompts()

    def _get_string(self, key, default_text=""):
        if self.main_window and hasattr(self.main_window, 'lang_manager'):
            return self.main_window.lang_manager.get_string(key, default_text)
        return default_text or key

    def _load_models_config(self):
        try:
            models_path = Path(__file__).parent.parent / 'config' / 'translation_models.json'
            with open(models_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading models config: {e}")
            return {}

    def _get_default_settings(self):
        return {
            "use_separate_model": False,
            "provider": "chutes",
            "model": "mistral-3.2"
        }

    def _load_prompt(self, prompt_name: str) -> str:
        """Carga un prompt desde el archivo correspondiente al par de idiomas, con fallback a prompts-base"""
        if not self.source_lang or not self.target_lang:
            return f"Error: No se han especificado los idiomas de origen y destino."

        lang_pair_dir_name = f"{self.source_lang}_{self.target_lang}"

        # 1. Buscar en el directorio de prompts temporales
        if self.temp_prompts_path:
            temp_prompt_path = self.temp_prompts_path / lang_pair_dir_name / prompt_name
            if temp_prompt_path.exists():
                try:
                    with open(temp_prompt_path, 'r', encoding='utf-8') as file:
                        return file.read()
                except Exception as e:
                    return f"Error al cargar el prompt temporal: {str(e)}"

        # 2. Si no existe en el temporal, intentar en el directorio específico del par de idiomas
        prompt_dir = Path(__file__).parent.parent / 'config' / 'prompts' / lang_pair_dir_name
        prompt_path = prompt_dir / prompt_name

        if prompt_path.exists():
            try:
                with open(prompt_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except Exception as e:
                return f"Error al cargar el prompt: {str(e)}"

        # 3. Si no existe en el específico, intentar en prompts-base
        base_prompt_dir = Path(__file__).parent.parent / 'config' / 'prompts' / 'prompts-base'
        base_prompt_path = base_prompt_dir / prompt_name

        if base_prompt_path.exists():
            try:
                with open(base_prompt_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except Exception as e:
                return f"Error al cargar el prompt base: {str(e)}"

        return ""  # Retornar vacío si no se encuentra en ningún lado

    def init_ui(self):
        self.setWindowTitle(self._get_string("prompt_refine_settings_dialog.title", "Prompts and Check/Refine Settings"))
        self.setModal(True)
        self.resize(1200, 700)

        # Layout principal con splitter horizontal
        main_layout = QHBoxLayout()

        # Splitter para dividir en dos paneles
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel izquierdo: Comprobación y Refinamiento
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # Grupo para Comprobación y Refinamiento
        check_refine_group = QGroupBox(self._get_string("check_refine_settings_dialog.check_refine_group", "Comprobación y Refinamiento"))
        check_refine_layout = QVBoxLayout()

        # Options for model selection
        model_group = QGroupBox()
        model_layout = QVBoxLayout()

        self.use_same_model_radio = QRadioButton(self._get_string("check_refine_settings_dialog.use_same_model", "Usar el mismo modelo"))
        self.use_separate_model_radio = QRadioButton(self._get_string("check_refine_settings_dialog.use_separate_model", "Usar modelo diferente"))

        model_layout.addWidget(self.use_same_model_radio)
        model_layout.addWidget(self.use_separate_model_radio)
        model_group.setLayout(model_layout)
        check_refine_layout.addWidget(model_group)

        # Provider and Model selection (initially disabled)
        self.separate_model_group = QGroupBox()
        form_layout = QFormLayout()

        self.provider_combo = QComboBox()
        self.model_combo = QComboBox()

        form_layout.addRow(QLabel(self._get_string("check_refine_settings_dialog.provider_label", "Proveedor")), self.provider_combo)
        form_layout.addRow(QLabel(self._get_string("check_refine_settings_dialog.model_label", "Modelo")), self.model_combo)
        self.separate_model_group.setLayout(form_layout)
        check_refine_layout.addWidget(self.separate_model_group)

        check_refine_group.setLayout(check_refine_layout)
        left_layout.addWidget(check_refine_group)

        # Espaciador
        left_layout.addStretch()

        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        # Panel derecho: Prompts
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        # Grupo para Prompts
        prompts_group = QGroupBox(self._get_string("prompt_refine_settings_dialog.prompts_group", "Prompts"))
        prompts_layout = QVBoxLayout()

        # Advertencia sobre temporalidad
        warning_label = QLabel(self._get_string("prompt_refine_settings_dialog.warning",
                                               "⚠️ ADVERTENCIA: Las modificaciones a los prompts son TEMPORALES\n"
                                               "y solo estarán disponibles durante esta sesión de la aplicación.\n"
                                               "Los archivos originales NO serán modificados."))
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        warning_label.setWordWrap(True)
        prompts_layout.addWidget(warning_label)

        # Scroll area para los prompts
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QHBoxLayout()  # Cambiado a horizontal

        # Translation prompt
        translation_group = QGroupBox("Translation Prompt (translation.txt)")
        translation_layout = QVBoxLayout()
        self.translation_text = QPlainTextEdit()
        self.translation_text.setMinimumHeight(300)
        self.translation_text.setMinimumWidth(300)
        translation_layout.addWidget(self.translation_text)
        translation_group.setLayout(translation_layout)
        scroll_layout.addWidget(translation_group)

        # Refine prompt
        refine_group = QGroupBox("Refine Prompt (refine.txt)")
        refine_layout = QVBoxLayout()
        self.refine_text = QPlainTextEdit()
        self.refine_text.setMinimumHeight(300)
        self.refine_text.setMinimumWidth(300)
        refine_layout.addWidget(self.refine_text)
        refine_group.setLayout(refine_layout)
        scroll_layout.addWidget(refine_group)

        # Check prompt
        check_group = QGroupBox("Check Prompt (check.txt)")
        check_layout = QVBoxLayout()
        self.check_text = QPlainTextEdit()
        self.check_text.setMinimumHeight(300)
        self.check_text.setMinimumWidth(300)
        check_layout.addWidget(self.check_text)
        check_group.setLayout(check_layout)
        scroll_layout.addWidget(check_group)

        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        prompts_layout.addWidget(scroll_area)

        prompts_group.setLayout(prompts_layout)
        right_layout.addWidget(prompts_group)

        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        # Configurar splitter
        splitter.setSizes([400, 800])  # Tamaños iniciales de los paneles

        main_layout.addWidget(splitter)

        # Botones en la parte inferior
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(self._get_string("check_refine_settings_dialog.save_button", "Guardar"))
        self.cancel_button = QPushButton(self._get_string("check_refine_settings_dialog.cancel_button", "Cancelar"))

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.save_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        # Connect signals
        self.use_same_model_radio.toggled.connect(self.toggle_model_selection)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.provider_combo.currentTextChanged.connect(self.update_models)

        # Load providers
        self.load_providers()

    def load_providers(self):
        self.provider_combo.clear()
        for key, config in self.models_config.items():
            self.provider_combo.addItem(config['name'], userData=key)

    def update_models(self):
        provider_key = self.provider_combo.currentData()
        if provider_key:
            self.model_combo.clear()
            models = self.models_config.get(provider_key, {}).get('models', {})
            for key, model in models.items():
                self.model_combo.addItem(model['name'], userData=key)

    def toggle_model_selection(self, checked):
        self.separate_model_group.setEnabled(not checked)

    def load_settings(self):
        use_separate = self.current_settings.get("use_separate_model", False)
        if use_separate:
            self.use_separate_model_radio.setChecked(True)
        else:
            self.use_same_model_radio.setChecked(True)

        # Set provider
        provider_key = self.current_settings.get("provider")
        provider_index = self.provider_combo.findData(provider_key)
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
            self.update_models() # Important to update models before setting the model

            # Set model
            model_key = self.current_settings.get("model")
            model_index = self.model_combo.findData(model_key)
            if model_index >= 0:
                self.model_combo.setCurrentIndex(model_index)

        self.toggle_model_selection(self.use_same_model_radio.isChecked())

    def load_prompts(self):
        """Carga los prompts desde archivos, priorizando el directorio temporal."""
        if self.source_lang and self.target_lang:
            # Cargar cada prompt (translation, refine, check)
            self.translation_text.setPlainText(self._load_prompt("translation.txt"))
            self.refine_text.setPlainText(self._load_prompt("refine.txt"))
            self.check_text.setPlainText(self._load_prompt("check.txt"))

    def get_settings(self):
        """Retorna la configuración de check/refine y guarda los prompts modificados en archivos temporales."""
        settings = {
            "use_separate_model": self.use_separate_model_radio.isChecked(),
            "provider": self.provider_combo.currentData() or "",
            "model": self.model_combo.currentData() or ""
        }

        # Guardar prompts modificados en el directorio temporal
        if self.temp_prompts_path and self.source_lang and self.target_lang:
            lang_pair_dir = self.temp_prompts_path / f"{self.source_lang}_{self.target_lang}"
            lang_pair_dir.mkdir(parents=True, exist_ok=True)

            try:
                # Guardar translation.txt
                with open(lang_pair_dir / "translation.txt", 'w', encoding='utf-8') as f:
                    f.write(self.translation_text.toPlainText())
                
                # Guardar refine.txt
                with open(lang_pair_dir / "refine.txt", 'w', encoding='utf-8') as f:
                    f.write(self.refine_text.toPlainText())

                # Guardar check.txt
                with open(lang_pair_dir / "check.txt", 'w', encoding='utf-8') as f:
                    f.write(self.check_text.toPlainText())
                
                self.main_window.statusBar().showMessage(
                    self._get_string("translate_panel.prompts_saved_temporarily", "Prompts guardados temporalmente"), 3000)

            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudieron guardar los prompts temporales: {e}")

        return settings