import json
import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QComboBox, QPushButton, QGroupBox, QMessageBox,
                            QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem,
                            QHeaderView, QRadioButton)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from typing import Dict, Any, Optional
from src.logic.language_manager import LanguageManager

class AddLanguageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(parent._get_string("add_language_dialog.title") if hasattr(parent, '_get_string') else "Add Language")
        self.setModal(True)
        layout = QFormLayout()
        self.name_input = QLineEdit()
        self.code_input = QLineEdit()
        layout.addRow(parent._get_string("add_language_dialog.name") if hasattr(parent, '_get_string') else "Name:", self.name_input)
        layout.addRow(parent._get_string("add_language_dialog.code") if hasattr(parent, '_get_string') else "Code:", self.code_input)
        
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(parent._get_string("add_language_dialog.save_button") if hasattr(parent, '_get_string') else "Save")
        self.cancel_button = QPushButton(parent._get_string("add_language_dialog.cancel_button") if hasattr(parent, '_get_string') else "Cancel")
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def get_data(self):
        return self.name_input.text().strip(), self.code_input.text().strip()

class NewPromptDialog(QDialog):
    def __init__(self, languages, parent=None):
        super().__init__(parent)
        self.setWindowTitle(parent._get_string("new_prompt_dialog.title") if hasattr(parent, '_get_string') else "New Prompt")
        self.setModal(True)
        layout = QFormLayout()
        self.source_lang_combo = QComboBox()
        self.target_lang_combo = QComboBox()
        
        for code, name in languages.items():
            self.source_lang_combo.addItem(name, code)
            self.target_lang_combo.addItem(name, code)
            
        layout.addRow(parent._get_string("new_prompt_dialog.source_language") if hasattr(parent, '_get_string') else "Source Language:", self.source_lang_combo)
        layout.addRow(parent._get_string("new_prompt_dialog.target_language") if hasattr(parent, '_get_string') else "Target Language:", self.target_lang_combo)
        
        buttons_layout = QHBoxLayout()
        self.create_button = QPushButton(parent._get_string("new_prompt_dialog.create_button") if hasattr(parent, '_get_string') else "Create")
        self.cancel_button = QPushButton(parent._get_string("new_prompt_dialog.cancel_button") if hasattr(parent, '_get_string') else "Cancel")
        buttons_layout.addWidget(self.create_button)
        buttons_layout.addWidget(self.cancel_button)
        
        self.create_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def get_data(self):
        return self.source_lang_combo.currentData(), self.target_lang_combo.currentData()

class SettingsDialog(QDialog):
    """
    Diálogo de configuración que permite ajustar proveedor, modelo e idiomas
    de traducción. La ventana es modal y bloquea la interfaz principal.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.config_file = Path(__file__).parent.parent / 'config' / 'config.json'
        self.models_file = Path(__file__).parent.parent / 'config' / 'models' / 'translation_models.json'
        self.languages_file = Path(__file__).parent.parent / 'config' / 'languages.json'
        
        self.current_config = self._load_config()
        self.models_config = self._load_models_config()
        self.languages_config = self._load_languages_config()
        
        self.init_ui()
        self.load_settings()
        self.connect_settings_signals()
        
    def _get_string(self, key, default_text=""):
        """Get a localized string from the language manager."""
        if hasattr(self.main_window, 'lang_manager'):
            return self.main_window.lang_manager.get_string(key, default_text)
        return default_text or key
        
    def init_ui(self):
        self.setWindowTitle(self._get_string("settings_dialog.title"))
        self.setModal(True)
        self.resize(600, 700)
        
        main_layout = QVBoxLayout()
        
        # Add UI Language selection
        ui_language_group = QGroupBox(self._get_string("settings_dialog.ui_language_group"))
        ui_language_layout = QFormLayout()
        self.ui_language_combo = QComboBox()
        ui_language_layout.addRow(self._get_string("settings_dialog.ui_language_label"), self.ui_language_combo)
        ui_language_group.setLayout(ui_language_layout)
        main_layout.addWidget(ui_language_group)
        
        translation_group = QGroupBox(self._get_string("settings_dialog.translation_group"))
        main_translation_layout = QHBoxLayout()

        # Columna izquierda
        left_layout = QFormLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.setToolTip(self._get_string("settings_dialog.provider_tooltip"))
        left_layout.addRow(self._get_string("settings_dialog.provider_label"), self.provider_combo)
        
        self.model_combo = QComboBox()
        self.model_combo.setToolTip(self._get_string("settings_dialog.model_tooltip"))
        left_layout.addRow(self._get_string("settings_dialog.model_label"), self.model_combo)

        # Columna derecha
        right_layout = QFormLayout()
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setToolTip(self._get_string("settings_dialog.source_language_tooltip"))
        right_layout.addRow(self._get_string("settings_dialog.source_language_label"), self.source_lang_combo)
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setToolTip(self._get_string("settings_dialog.target_language_tooltip"))
        right_layout.addRow(self._get_string("settings_dialog.target_language_label"), self.target_lang_combo)

        main_translation_layout.addLayout(left_layout)
        main_translation_layout.addLayout(right_layout)

        translation_group.setLayout(main_translation_layout)
        main_layout.addWidget(translation_group)

        # Check and Refine Settings Group
        check_refine_group = QGroupBox(self._get_string("settings_dialog.check_refine_group"))
        check_refine_layout = QHBoxLayout()

        radio_button_layout = QVBoxLayout()
        self.check_refine_use_same_model_radio = QRadioButton(self._get_string("check_refine_settings_dialog.use_same_model"))
        self.check_refine_use_separate_model_radio = QRadioButton(self._get_string("check_refine_settings_dialog.use_separate_model"))
        radio_button_layout.addWidget(self.check_refine_use_same_model_radio)
        radio_button_layout.addWidget(self.check_refine_use_separate_model_radio)
        radio_button_layout.addStretch()

        self.check_refine_model_group = QGroupBox()
        check_refine_model_layout = QFormLayout()
        self.check_refine_provider_combo = QComboBox()
        self.check_refine_model_combo = QComboBox()
        check_refine_model_layout.addRow(self._get_string("check_refine_settings_dialog.provider_label"), self.check_refine_provider_combo)
        check_refine_model_layout.addRow(self._get_string("check_refine_settings_dialog.model_label"), self.check_refine_model_combo)
        self.check_refine_model_group.setLayout(check_refine_model_layout)

        check_refine_layout.addLayout(radio_button_layout)
        check_refine_layout.addWidget(self.check_refine_model_group)
        check_refine_group.setLayout(check_refine_layout)
        main_layout.addWidget(check_refine_group)

        languages_group = QGroupBox(self._get_string("settings_dialog.languages_group"))
        languages_layout = QVBoxLayout()
        self.languages_table = QTableWidget()
        self.languages_table.setColumnCount(2)
        self.languages_table.setHorizontalHeaderLabels([
            self._get_string("settings_dialog.languages_table.name"),
            self._get_string("settings_dialog.languages_table.code")
        ])
        self.languages_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        languages_layout.addWidget(self.languages_table)

        lang_buttons_layout = QHBoxLayout()
        self.add_lang_button = QPushButton(self._get_string("settings_dialog.add_language_button"))
        self.remove_lang_button = QPushButton(self._get_string("settings_dialog.remove_language_button"))
        lang_buttons_layout.addWidget(self.add_lang_button)
        lang_buttons_layout.addWidget(self.remove_lang_button)
        languages_layout.addLayout(lang_buttons_layout)
        languages_group.setLayout(languages_layout)
        main_layout.addWidget(languages_group)

        prompts_group = QGroupBox(self._get_string("settings_dialog.prompts_group"))
        prompts_layout = QVBoxLayout()
        self.prompts_table = QTableWidget()
        self.prompts_table.setColumnCount(2)
        self.prompts_table.setHorizontalHeaderLabels([
            self._get_string("settings_dialog.prompts_table.name"),
            self._get_string("settings_dialog.prompts_table.terms")
        ])
        self.prompts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        prompts_layout.addWidget(self.prompts_table)

        prompt_buttons_layout = QHBoxLayout()
        self.new_prompt_button = QPushButton(self._get_string("settings_dialog.new_prompt_button"))
        self.remove_prompt_button = QPushButton(self._get_string("settings_dialog.remove_prompt_button"))
        prompt_buttons_layout.addWidget(self.new_prompt_button)
        prompt_buttons_layout.addWidget(self.remove_prompt_button)
        prompts_layout.addLayout(prompt_buttons_layout)
        prompts_group.setLayout(prompts_layout)
        main_layout.addWidget(prompts_group)
        
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(self._get_string("settings_dialog.save_button"))
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button = QPushButton(self._get_string("settings_dialog.cancel_button"))
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.save_button)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)
        
        self.provider_combo.currentTextChanged.connect(self.update_models)
        self.check_refine_provider_combo.currentTextChanged.connect(self.update_check_refine_models)
        self.check_refine_use_same_model_radio.toggled.connect(self.toggle_check_refine_model_selection)
        
    def _load_config(self) -> Dict[str, Any]:
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración: {e}")
        return {
            "provider": "gemini",
            "model": "gemini-2.5-flash-lite",
            "source_language": "auto",
            "target_language": "es-MX",
        }
    
    def _load_models_config(self) -> Dict[str, Any]:
        try:
            if self.models_file.exists():
                with open(self.models_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración de modelos: {e}")
        return {}
    
    def _load_languages_config(self) -> Dict[str, str]:
        try:
            if self.languages_file.exists():
                with open(self.languages_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración de idiomas: {e}")
        return {}
    
    def load_settings(self):
        # Load UI languages
        self.load_ui_languages()
        
        self.provider_combo.clear()
        if self.models_config:
            for provider_key, provider_data in self.models_config.items():
                self.provider_combo.addItem(provider_data['name'], provider_key)
        
        self.load_languages_combos()
        
        provider_index = self.provider_combo.findData(self.current_config.get('provider', ''))
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        
        self.update_models()
        
        model_index = self.model_combo.findData(self.current_config.get('model', ''))
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)

        # Handle source language with fallback
        source_lang_code = self.current_config.get('source_language', 'auto')
        source_lang_index = self.source_lang_combo.findData(source_lang_code)
        if source_lang_index == -1:
            source_lang_index = self.source_lang_combo.findText(source_lang_code)
        if source_lang_index >= 0:
            self.source_lang_combo.setCurrentIndex(source_lang_index)

        # Handle target language with fallback
        target_lang_code = self.current_config.get('target_language', 'es-MX')
        target_lang_index = self.target_lang_combo.findData(target_lang_code)
        if target_lang_index == -1:
            target_lang_index = self.target_lang_combo.findText(target_lang_code)
        if target_lang_index >= 0:
            self.target_lang_combo.setCurrentIndex(target_lang_index)

        self.load_languages_table()
        self.load_prompts_table()

        # Load check and refine settings
        check_refine_settings = self.current_config.get("check_refine_settings", {})
        use_separate = check_refine_settings.get("use_separate_model", False)
        if use_separate:
            self.check_refine_use_separate_model_radio.setChecked(True)
        else:
            self.check_refine_use_same_model_radio.setChecked(True)

        # Load providers for check/refine
        self.check_refine_provider_combo.clear()
        if self.models_config:
            for provider_key, provider_data in self.models_config.items():
                self.check_refine_provider_combo.addItem(provider_data['name'], provider_key)

        provider_index = self.check_refine_provider_combo.findData(check_refine_settings.get('provider', ''))
        if provider_index >= 0:
            self.check_refine_provider_combo.setCurrentIndex(provider_index)

        self.update_check_refine_models()

        model_index = self.check_refine_model_combo.findData(check_refine_settings.get('model', ''))
        if model_index >= 0:
            self.check_refine_model_combo.setCurrentIndex(model_index)

        self.toggle_check_refine_model_selection(self.check_refine_use_same_model_radio.isChecked())

    def load_languages_combos(self):
        self.source_lang_combo.clear()
        self.target_lang_combo.clear()
        if self.languages_config:
            sorted_languages = sorted(self.languages_config.items(), key=lambda x: (x[0] != 'auto', x[0]))
            for lang_key, lang_name in sorted_languages:
                self.source_lang_combo.addItem(lang_name, lang_key)
                self.target_lang_combo.addItem(lang_name, lang_key)

    def load_ui_languages(self):
        """Load available UI languages into the combo box."""
        self.ui_language_combo.clear()
        available_languages = LanguageManager.get_available_languages()
        current_ui_language = self.current_config.get('ui_language', 'es_MX')
        
        for lang_code, lang_name in available_languages.items():
            self.ui_language_combo.addItem(lang_name, lang_code)
            
        # Set current selection
        current_index = self.ui_language_combo.findData(current_ui_language)
        if current_index >= 0:
            self.ui_language_combo.setCurrentIndex(current_index)

    def load_languages_table(self):
        self.languages_table.setRowCount(0)
        for code, name in self.languages_config.items():
            row_position = self.languages_table.rowCount()
            self.languages_table.insertRow(row_position)
            self.languages_table.setItem(row_position, 0, QTableWidgetItem(name))
            self.languages_table.setItem(row_position, 1, QTableWidgetItem(code))

    def load_prompts_table(self):
        self.prompts_table.setRowCount(0)
        prompts_dir = Path(__file__).parent.parent / 'config' / 'prompts'
        if not prompts_dir.exists():
            return

        for item in prompts_dir.iterdir():
            if item.is_dir() and item.name != 'prompts-base':
                row_position = self.prompts_table.rowCount()
                self.prompts_table.insertRow(row_position)
                self.prompts_table.setItem(row_position, 0, QTableWidgetItem(item.name))
                
                edit_button = QPushButton(self._get_string("settings_dialog.edit_button"))
                edit_button.clicked.connect(lambda _, p=item: self.edit_preset_terms(p))
                self.prompts_table.setCellWidget(row_position, 1, edit_button)

    def connect_settings_signals(self):
        self.add_lang_button.clicked.connect(self.add_language)
        self.remove_lang_button.clicked.connect(self.remove_language)
        self.new_prompt_button.clicked.connect(self.create_new_prompt)
        self.remove_prompt_button.clicked.connect(self.remove_prompt)

    def add_language(self):
        dialog = AddLanguageDialog(self)
        if dialog.exec():
            name, code = dialog.get_data()
            if name and code:
                if name in self.languages_config.values() or code in self.languages_config:
                    QMessageBox.warning(self, self._get_string("warning_dialog.title"), self._get_string("language_already_exists"))
                    return
                self.languages_config[code] = name
                self._save_languages_config()
                self.load_languages_table()
                self.load_languages_combos()

    def remove_language(self):
        selected_row = self.languages_table.currentRow()
        if selected_row >= 0:
            code = self.languages_table.item(selected_row, 1).text()
            if code == 'auto':
                QMessageBox.warning(self, self._get_string("warning_dialog.title"), self._get_string("cannot_remove_auto_language"))
                return
            reply = QMessageBox.question(self, self._get_string("confirmation_dialog.title"),
                                       self._get_string("remove_language_confirmation").format(code=code),
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                del self.languages_config[code]
                self._save_languages_config()
                self.load_languages_table()
                self.load_languages_combos()

    def create_new_prompt(self):
        dialog = NewPromptDialog(self.languages_config, self)
        if dialog.exec():
            source_code, target_code = dialog.get_data()
            if source_code and target_code:
                if source_code == target_code:
                    QMessageBox.warning(self, self._get_string("warning_dialog.title"), self._get_string("same_languages_error"))
                    return
                
                prompt_dir_name = f"{source_code}_{target_code}"
                prompt_path = Path(__file__).parent.parent / 'config' / 'prompts' / prompt_dir_name
                if prompt_path.exists():
                    QMessageBox.warning(self, self._get_string("warning_dialog.title"), self._get_string("prompt_already_exists").format(name=prompt_dir_name))
                    return

                try:
                    base_path = Path(__file__).parent.parent / 'config' / 'prompts' / 'prompts-base'
                    shutil.copytree(base_path, prompt_path)
                    self.load_prompts_table()
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(prompt_path)))
                except Exception as e:
                    QMessageBox.critical(self, self._get_string("error_dialog.title"), self._get_string("create_prompt_error").format(error=str(e)))

    def remove_prompt(self):
        selected_row = self.prompts_table.currentRow()
        if selected_row >= 0:
            prompt_dir_name = self.prompts_table.item(selected_row, 0).text()
            
            reply = QMessageBox.question(self, self._get_string("confirmation_dialog.title"),
                                       self._get_string("remove_prompt_confirmation").format(name=prompt_dir_name),
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    prompt_path = Path(__file__).parent.parent / 'config' / 'prompts' / prompt_dir_name
                    if prompt_path.exists() and prompt_path.is_dir():
                        shutil.rmtree(prompt_path)
                        self.load_prompts_table()
                        QMessageBox.information(self, self._get_string("success_dialog.title"), self._get_string("remove_prompt_success").format(name=prompt_dir_name))
                    else:
                        QMessageBox.warning(self, self._get_string("error_dialog.title"), self._get_string("prompt_folder_not_found").format(name=prompt_dir_name))
                except Exception as e:
                    QMessageBox.critical(self, self._get_string("error_dialog.title"), self._get_string("remove_prompt_error").format(error=str(e)))

    def edit_preset_terms(self, prompt_dir: Path):
        preset_terms_file = prompt_dir / 'preset_terms.json'
        if preset_terms_file.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(preset_terms_file)))
        else:
            QMessageBox.warning(self, self._get_string("warning_dialog.title"), self._get_string("prompt_file_not_found").format(path=prompt_dir))

    def _save_languages_config(self):
        try:
            with open(self.languages_file, 'w', encoding='utf-8') as f:
                json.dump(self.languages_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, self._get_string("error_dialog.title"), self._get_string("settings_dialog.languages.save_error").format(error=str(e)))

    def update_models(self):
        self.model_combo.clear()
        provider_key = self.provider_combo.currentData()
        if provider_key and self.models_config and provider_key in self.models_config:
            provider_data = self.models_config[provider_key]
            if 'models' in provider_data:
                for model_key, model_data in provider_data['models'].items():
                    self.model_combo.addItem(model_data['name'], model_key)

    def update_check_refine_models(self):
        self.check_refine_model_combo.clear()
        provider_key = self.check_refine_provider_combo.currentData()
        if provider_key and self.models_config and provider_key in self.models_config:
            provider_data = self.models_config[provider_key]
            if 'models' in provider_data:
                for model_key, model_data in provider_data['models'].items():
                    self.check_refine_model_combo.addItem(model_data['name'], model_key)

    def toggle_check_refine_model_selection(self, checked):
        self.check_refine_model_group.setEnabled(not checked)
    
    def save_settings(self):
        if not self.provider_combo.currentData():
            QMessageBox.warning(self, self._get_string("warning_dialog.title"), self._get_string("no_provider_selected"))
            return
        
        if not self.model_combo.currentData():
            QMessageBox.warning(self, self._get_string("warning_dialog.title"), self._get_string("no_model_selected"))
            return
        
        source_lang = self.source_lang_combo.currentData()
        target_lang = self.target_lang_combo.currentData()
        
        if source_lang == target_lang:
            QMessageBox.warning(self, self._get_string("warning_dialog.title"), self._get_string("settings_dialog.save_error.same_languages"))
            return
        
        # Get UI language
        ui_language = self.ui_language_combo.currentData()

        # Get check and refine settings
        check_refine_settings = {
            "use_separate_model": self.check_refine_use_separate_model_radio.isChecked(),
            "provider": self.check_refine_provider_combo.currentData(),
            "model": self.check_refine_model_combo.currentData()
        }
        
        new_config = {
            "provider": self.provider_combo.currentData(),
            "model": self.model_combo.currentData(),
            "source_language": source_lang,
            "target_language": target_lang,
            "ui_language": ui_language,
            "check_refine_settings": check_refine_settings
        }
        
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            self.current_config = new_config
            
            # Show restart message if UI language changed
            if ui_language != self.current_config.get('ui_language'):
                QMessageBox.information(
                    self,
                    self._get_string("success_dialog.title"),
                    self._get_string("settings_restart_required")
                )
            else:
                QMessageBox.information(self, self._get_string("success_dialog.title"), self._get_string("settings_saved_success"))
                
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self._get_string("error_dialog.title"), self._get_string("settings_dialog.save_error").format(error=str(e)))
