import json
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QRadioButton,
                           QComboBox, QFormLayout, QHBoxLayout, QPushButton,
                           QLabel)

class CheckRefineSettingsDialog(QDialog):
    def __init__(self, parent=None, current_settings=None, models_config=None):
        super().__init__(parent)
        self.main_window = parent.main_window if parent else None
        self.models_config = models_config or self._load_models_config()
        self.current_settings = current_settings or self._get_default_settings()

        self.init_ui()
        self.load_settings()

    def _get_string(self, key, default_text=""):
        if self.main_window and hasattr(self.main_window, 'lang_manager'):
            return self.main_window.lang_manager.get_string(key, default_text)
        return default_text or key

    def _load_models_config(self):
        try:
            models_path = Path(__file__).parent.parent / 'config' / 'models' / 'translation_models.json'
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

    def init_ui(self):
        self.setWindowTitle(self._get_string("check_refine_settings_dialog.title", "Check/Refine Settings"))
        self.setModal(True)
        self.resize(450, 250)

        layout = QVBoxLayout()

        # Options for model selection
        model_group = QGroupBox()
        model_layout = QVBoxLayout()

        self.use_same_model_radio = QRadioButton(self._get_string("check_refine_settings_dialog.use_same_model"))
        self.use_separate_model_radio = QRadioButton(self._get_string("check_refine_settings_dialog.use_separate_model"))

        model_layout.addWidget(self.use_same_model_radio)
        model_layout.addWidget(self.use_separate_model_radio)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # Provider and Model selection (initially disabled)
        self.separate_model_group = QGroupBox()
        form_layout = QFormLayout()

        self.provider_combo = QComboBox()
        self.model_combo = QComboBox()

        form_layout.addRow(QLabel(self._get_string("check_refine_settings_dialog.provider_label")), self.provider_combo)
        form_layout.addRow(QLabel(self._get_string("check_refine_settings_dialog.model_label")), self.model_combo)
        self.separate_model_group.setLayout(form_layout)
        layout.addWidget(self.separate_model_group)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(self._get_string("check_refine_settings_dialog.save_button"))
        self.cancel_button = QPushButton(self._get_string("check_refine_settings_dialog.cancel_button"))

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.save_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

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

    def get_settings(self):
        return {
            "use_separate_model": self.use_separate_model_radio.isChecked(),
            "provider": self.provider_combo.currentData() or "",
            "model": self.model_combo.currentData() or ""
        }
