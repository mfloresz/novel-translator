import json
import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QComboBox, QPushButton, QGroupBox, QMessageBox,
                            QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem,
                            QHeaderView, QRadioButton, QSpinBox, QWidget)
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
        self.models_file = Path(__file__).parent.parent / 'config' / 'translation_models.json'
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
        self.resize(800, 600)
        
        main_layout = QVBoxLayout()
        
        # Create two columns layout
        columns_layout = QHBoxLayout()
        
        # Left column
        left_column = QVBoxLayout()
        
        # Add UI Language selection
        ui_language_group = QGroupBox(self._get_string("settings_dialog.ui_language_group"))
        ui_language_layout = QFormLayout()
        self.ui_language_combo = QComboBox()
        ui_language_layout.addRow(self._get_string("settings_dialog.ui_language_label"), self.ui_language_combo)
        ui_language_group.setLayout(ui_language_layout)
        left_column.addWidget(ui_language_group)
        
        # Library settings group
        library_group = QGroupBox(self._get_string("settings_dialog.library_group", "Biblioteca"))
        library_layout = QFormLayout()
        self.library_path_label = QLabel()
        self.library_path_label.setWordWrap(True)
        self.library_path_label.setMinimumWidth(400)
        self.library_path_label.setToolTip(self._get_string("settings_dialog.library_path_tooltip", "Ruta actual de la biblioteca"))
        self.select_library_button = QPushButton(self._get_string("settings_dialog.select_library_button", "Seleccionar Biblioteca"))
        self.select_library_button.clicked.connect(self.select_library_directory)
        library_layout.addRow(self._get_string("settings_dialog.library_path_label", "Ubicación:"), self.library_path_label)
        library_layout.addRow("", self.select_library_button)
        library_group.setLayout(library_layout)
        left_column.addWidget(library_group)
        
        # Create two columns for Translation and Check/Refine settings
        translation_columns_layout = QHBoxLayout()

        # Left sub-column: Translation settings
        translation_left_column = QVBoxLayout()
        translation_group = QGroupBox(self._get_string("settings_dialog.translation_group"))
        translation_layout = QFormLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.setToolTip(self._get_string("settings_dialog.provider_tooltip"))
        translation_layout.addRow(self._get_string("settings_dialog.provider_label"), self.provider_combo)
        
        self.model_combo = QComboBox()
        self.model_combo.setToolTip(self._get_string("settings_dialog.model_tooltip"))
        translation_layout.addRow(self._get_string("settings_dialog.model_label"), self.model_combo)

        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setToolTip(self._get_string("settings_dialog.source_language_tooltip"))
        translation_layout.addRow(self._get_string("settings_dialog.source_language_label"), self.source_lang_combo)
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setToolTip(self._get_string("settings_dialog.target_language_tooltip"))
        translation_layout.addRow(self._get_string("settings_dialog.target_language_label"), self.target_lang_combo)
        
        translation_group.setLayout(translation_layout)
        translation_left_column.addWidget(translation_group)
        translation_left_column.addStretch()

        # Right sub-column: Check and Refine Settings
        translation_right_column = QVBoxLayout()
        check_refine_group = QGroupBox(self._get_string("settings_dialog.check_refine_group"))
        check_refine_layout = QVBoxLayout()

        self.check_refine_use_same_model_radio = QRadioButton(self._get_string("check_refine_settings_dialog.use_same_model"))
        self.check_refine_use_separate_model_radio = QRadioButton(self._get_string("check_refine_settings_dialog.use_separate_model"))

        self.check_refine_model_group = QGroupBox()
        check_refine_model_layout = QFormLayout()
        self.check_refine_provider_combo = QComboBox()
        self.check_refine_model_combo = QComboBox()
        check_refine_model_layout.addRow(self._get_string("check_refine_settings_dialog.provider_label"), self.check_refine_provider_combo)
        check_refine_model_layout.addRow(self._get_string("check_refine_settings_dialog.model_label"), self.check_refine_model_combo)
        self.check_refine_model_group.setLayout(check_refine_model_layout)

        check_refine_layout.addWidget(self.check_refine_use_same_model_radio)
        check_refine_layout.addWidget(self.check_refine_use_separate_model_radio)
        check_refine_layout.addWidget(self.check_refine_model_group)
        check_refine_layout.addStretch()
        check_refine_group.setLayout(check_refine_layout)
        translation_right_column.addWidget(check_refine_group)
        translation_right_column.addStretch()

        # Add sub-columns to the translation columns layout
        translation_columns_layout.addLayout(translation_left_column)
        translation_columns_layout.addLayout(translation_right_column)

        # Add the translation columns to left_column
        left_column.addLayout(translation_columns_layout)
        
        # Default Segmentation Settings Group (below the two columns)
        segmentation_group = QGroupBox(self._get_string("settings_dialog.segmentation_group"))
        segmentation_layout = QVBoxLayout()

        # Radio buttons for auto-segmentation
        radio_layout = QVBoxLayout()
        self.no_auto_segmentation_radio = QRadioButton(self._get_string("settings_dialog.no_auto_segmentation"))
        self.auto_segmentation_radio = QRadioButton(self._get_string("settings_dialog.auto_segmentation_label"))
        radio_layout.addWidget(self.no_auto_segmentation_radio)
        radio_layout.addWidget(self.auto_segmentation_radio)
        segmentation_layout.addLayout(radio_layout)

        # Threshold and segment size inputs (initially hidden)
        inputs_layout = QFormLayout()
        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setMinimum(1)
        self.threshold_spinbox.setMaximum(100000)
        self.threshold_spinbox.setValue(10000)
        self.threshold_spinbox.setSuffix(" caracteres")
        inputs_layout.addRow(self._get_string("settings_dialog.auto_segmentation_enabled"), self.threshold_spinbox)

        self.segment_size_spinbox = QSpinBox()
        self.segment_size_spinbox.setMinimum(100)
        self.segment_size_spinbox.setMaximum(10000)
        self.segment_size_spinbox.setValue(5000)
        self.segment_size_spinbox.setSuffix(" caracteres")
        inputs_layout.addRow(self._get_string("settings_dialog.segment_size_label"), self.segment_size_spinbox)

        self.inputs_widget = QWidget()
        self.inputs_widget.setLayout(inputs_layout)
        segmentation_layout.addWidget(self.inputs_widget)
        segmentation_layout.addStretch()

        segmentation_group.setLayout(segmentation_layout)
        left_column.addWidget(segmentation_group)

        # Connect radio buttons to toggle inputs
        self.auto_segmentation_radio.toggled.connect(lambda checked: self.inputs_widget.setEnabled(checked))
        self.no_auto_segmentation_radio.toggled.connect(lambda checked: self.inputs_widget.setEnabled(not checked))

        # Right column
        right_column = QVBoxLayout()
        
        # Languages management group
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
        right_column.addWidget(languages_group)

        # Prompts management group
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
        right_column.addWidget(prompts_group)
        
        # Add columns to main layout
        columns_layout.addLayout(left_column)
        columns_layout.addLayout(right_column)
        main_layout.addLayout(columns_layout)
        
        # Add buttons at the bottom
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
        
        # Load library path
        library_path = self.current_config.get('default_directory', os.path.expanduser("~"))
        self.library_path_label.setText(library_path)
        
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

        # Set initial state for segmentation inputs (default to no auto-segmentation)
        self.no_auto_segmentation_radio.setChecked(True)
        self.inputs_widget.setEnabled(False)

        # Load default segmentation settings
        segmentation_config = self.current_config.get("auto_segmentation", {"enabled": False, "threshold": 10000, "segment_size": 5000})
        if segmentation_config["enabled"]:
            self.auto_segmentation_radio.setChecked(True)
            self.threshold_spinbox.setValue(segmentation_config["threshold"])
            self.segment_size_spinbox.setValue(segmentation_config["segment_size"])
            self.inputs_widget.setEnabled(True)
        else:
            self.no_auto_segmentation_radio.setChecked(True)
            self.inputs_widget.setEnabled(False)

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
        self.provider_combo.currentTextChanged.connect(self.update_models)
        self.check_refine_provider_combo.currentTextChanged.connect(self.update_check_refine_models)
        self.check_refine_use_same_model_radio.toggled.connect(self.toggle_check_refine_model_selection)
        
    def select_library_directory(self):
        """Selecciona un nuevo directorio de biblioteca"""
        from PyQt6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self,
            self._get_string("settings_dialog.select_library_title", "Seleccionar Directorio de Biblioteca"),
            self.current_config.get('default_directory', os.path.expanduser("~"))
        )
        if directory:
            self.current_config["default_directory"] = directory
            self.library_path_label.setText(directory)
            self._save_config()
            QMessageBox.information(
                self,
                self._get_string("success_dialog.title"),
                self._get_string("settings_dialog.library_updated", "Directorio de biblioteca actualizado")
            )

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

        # Save default segmentation settings
        auto_segmentation = {
            "enabled": self.auto_segmentation_radio.isChecked(),
            "threshold": self.threshold_spinbox.value(),
            "segment_size": self.segment_size_spinbox.value()
        }
        
        new_config = {
            "default_directory": self.current_config.get("default_directory", os.path.expanduser("~")),
            "last_used_directories": self.current_config.get("last_used_directories", []),
            "provider": self.provider_combo.currentData(),
            "model": self.model_combo.currentData(),
            "source_language": source_lang,
            "target_language": target_lang,
            "ui_language": ui_language,
            "check_refine_settings": check_refine_settings,
            "auto_segmentation": auto_segmentation
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

    def _save_config(self):
        """Guarda solo la configuración actual sin validar otros campos"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando configuración: {e}")
