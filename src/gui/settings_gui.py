import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QComboBox, QPushButton, QGroupBox, QMessageBox,
                            QFormLayout, QLineEdit)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class SettingsDialog(QDialog):
    """
    Diálogo de configuración que permite ajustar proveedor, modelo e idiomas
    de traducción. La ventana es modal y bloquea la interfaz principal.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = Path(__file__).parent.parent / 'config' / 'config.json'
        self.models_file = Path(__file__).parent.parent / 'config' / 'models' / 'translation_models.json'
        self.languages_file = Path(__file__).parent.parent / 'config' / 'languages.json'
        
        # Cargar configuración actual
        self.current_config = self._load_config()
        self.models_config = self._load_models_config()
        self.languages_config = self._load_languages_config()
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Inicializa la interfaz de usuario del diálogo"""
        self.setWindowTitle("Configuración")
        self.setModal(True)  # Bloquea la interfaz principal
        self.resize(500, 400)
        
        # Layout principal
        main_layout = QVBoxLayout()
        
        # Grupo de configuración de traducción
        translation_group = QGroupBox("Configuración de Traducción")
        translation_layout = QFormLayout()
        
        # Proveedor
        self.provider_combo = QComboBox()
        self.provider_combo.setToolTip("Selecciona el proveedor de traducción")
        translation_layout.addRow("Proveedor:", self.provider_combo)
        
        # Modelo
        self.model_combo = QComboBox()
        self.model_combo.setToolTip("Selecciona el modelo de traducción")
        translation_layout.addRow("Modelo:", self.model_combo)
        
        # Idioma origen
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setToolTip("Selecciona el idioma de origen")
        translation_layout.addRow("Idioma Origen:", self.source_lang_combo)
        
        # Idioma destino
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setToolTip("Selecciona el idioma de destino")
        translation_layout.addRow("Idioma Destino:", self.target_lang_combo)
        
        translation_group.setLayout(translation_layout)
        main_layout.addWidget(translation_group)
        
        # Grupo de configuración de directorio
        directory_group = QGroupBox("Configuración de Directorio")
        directory_layout = QFormLayout()
        
        # Directorio inicial
        self.initial_dir_input = QLineEdit()
        self.initial_dir_input.setToolTip("Directorio inicial para el botón 'Abrir'")
        self.initial_dir_input.setPlaceholderText("Ruta del directorio inicial")
        self.browse_button = QPushButton("...")
        self.browse_button.setMaximumWidth(30)
        self.browse_button.setToolTip("Seleccionar directorio")
        self.browse_button.clicked.connect(self.browse_directory)
        
        directory_layout.addRow("Directorio Inicial:", self.initial_dir_input)
        directory_layout.addRow("", self.browse_button)
        
        directory_group.setLayout(directory_layout)
        main_layout.addWidget(directory_group)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Guardar")
        self.save_button.setToolTip("Guardar configuración")
        self.save_button.clicked.connect(self.save_settings)
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setToolTip("Cancelar sin guardar")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)
        
        # Conectar señal de cambio de proveedor
        self.provider_combo.currentTextChanged.connect(self.update_models)
        
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo JSON"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración: {e}")
        
        # Valores por defecto si no existe el archivo
        return {
            "provider": "gemini",
            "model": "gemini-2.5-flash-lite",
            "source_language": "auto",
            "target_language": "Español (MX)",
            "initial_directory": os.path.expanduser('~')
        }
    
    def _load_models_config(self) -> Dict[str, Any]:
        """Carga la configuración de modelos desde el archivo JSON"""
        try:
            if self.models_file.exists():
                with open(self.models_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración de modelos: {e}")
        
        return {}
    
    def _load_languages_config(self) -> Dict[str, str]:
        """Carga la configuración de idiomas desde el archivo JSON"""
        try:
            if self.languages_file.exists():
                with open(self.languages_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración de idiomas: {e}")
        
        return {}
    
    def load_settings(self):
        """Carga los valores actuales en los controles de la interfaz"""
        # Cargar proveedores
        self.provider_combo.clear()
        if self.models_config:
            for provider_key, provider_data in self.models_config.items():
                self.provider_combo.addItem(provider_data['name'], provider_key)
        
        # Cargar idiomas
        self.source_lang_combo.clear()
        self.target_lang_combo.clear()
        if self.languages_config:
            # Ordenar: primero "auto", luego el resto alfabéticamente
            sorted_languages = sorted(self.languages_config.items(), 
                                    key=lambda x: (x[0] != 'auto', x[0]))
            for lang_key, lang_name in sorted_languages:
                self.source_lang_combo.addItem(lang_name, lang_key)
                self.target_lang_combo.addItem(lang_name, lang_key)
        
        # Seleccionar valores actuales
        provider_index = self.provider_combo.findData(self.current_config.get('provider', ''))
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        
        # Actualizar modelos según el proveedor seleccionado
        self.update_models()
        
        # Seleccionar modelos e idiomas
        model_index = self.model_combo.findData(self.current_config.get('model', ''))
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        
        source_lang_index = self.source_lang_combo.findData(
            self.current_config.get('source_language', 'auto'))
        if source_lang_index >= 0:
            self.source_lang_combo.setCurrentIndex(source_lang_index)
        
        target_lang_index = self.target_lang_combo.findData(
            self.current_config.get('target_language', 'Español (MX)'))
        if target_lang_index >= 0:
            self.target_lang_combo.setCurrentIndex(target_lang_index)
        
        # Cargar directorio inicial
        initial_dir = self.current_config.get('initial_directory', '')
        if initial_dir:
            self.initial_dir_input.setText(initial_dir)
    
    def update_models(self):
        """Actualiza la lista de modelos según el proveedor seleccionado"""
        self.model_combo.clear()
        
        provider_key = self.provider_combo.currentData()
        if provider_key and self.models_config and provider_key in self.models_config:
            provider_data = self.models_config[provider_key]
            if 'models' in provider_data:
                for model_key, model_data in provider_data['models'].items():
                    self.model_combo.addItem(model_data['name'], model_key)
    
    def save_settings(self):
        """Guarda la configuración actual en el archivo JSON"""
        # Validación básica
        if not self.provider_combo.currentData():
            QMessageBox.warning(self, "Advertencia", "Debe seleccionar un proveedor válido")
            return
        
        if not self.model_combo.currentData():
            QMessageBox.warning(self, "Advertencia", "Debe seleccionar un modelo válido")
            return
        
        source_lang = self.source_lang_combo.currentData()
        target_lang = self.target_lang_combo.currentData()
        
        if source_lang == target_lang:
            QMessageBox.warning(self, "Advertencia", "El idioma de origen y destino no pueden ser el mismo")
            return
        
        # Guardar configuración
        new_config = {
            "provider": self.provider_combo.currentData(),
            "model": self.model_combo.currentData(),
            "source_language": source_lang,
            "target_language": target_lang,
            "initial_directory": self.initial_dir_input.text().strip()
        }
        
        try:
            # Crear directorio si no existe
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Guardar archivo
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            
            # Actualizar configuración actual
            self.current_config = new_config
            
            QMessageBox.information(self, "Éxito", "Configuración guardada correctamente")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {str(e)}")
    
    def get_config(self) -> Dict[str, Any]:
        """Obtiene la configuración actual"""
        return self.current_config.copy()
    
    def get_new_config(self) -> Dict[str, Any]:
        """Obtiene la nueva configuración (después de guardar)"""
        return {
            "provider": self.provider_combo.currentData(),
            "model": self.model_combo.currentData(),
            "source_language": self.source_lang_combo.currentData(),
            "target_language": self.target_lang_combo.currentData(),
            "initial_directory": self.initial_dir_input.text().strip()
        }
    
    def browse_directory(self):
        """Abre un diálogo para seleccionar un directorio"""
        from PyQt6.QtWidgets import QFileDialog
        
        current_dir = self.initial_dir_input.text().strip()
        if not current_dir:
            current_dir = os.path.expanduser('~')
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar directorio inicial",
            current_dir
        )
        
        if directory:
            self.initial_dir_input.setText(directory)