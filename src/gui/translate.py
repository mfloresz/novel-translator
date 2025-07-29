import requests
import time
import json
import os
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QGroupBox, QComboBox,
                           QSpinBox, QFormLayout, QPlainTextEdit, QRadioButton,
                           QCheckBox, QDialog, QMessageBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
from dotenv import load_dotenv
from src.logic.translation_manager import TranslationManager
from src.logic.functions import show_confirmation_dialog

class PresetTermsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_term = None
        self.init_ui()
        self.load_preset_terms()

    def init_ui(self):
        self.setWindowTitle("Términos Predefinidos")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout()

        # Instrucciones
        instructions = QLabel("Seleccione un término para agregarlo al campo de términos personalizados:")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Lista de términos
        self.terms_list = QListWidget()
        self.terms_list.itemDoubleClicked.connect(self.on_term_double_clicked)
        layout.addWidget(self.terms_list)

        # Botones
        buttons_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancelar")
        self.add_button = QPushButton("Agregar Término")

        self.cancel_button.clicked.connect(self.reject)
        self.add_button.clicked.connect(self.add_selected_term)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.add_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def load_preset_terms(self):
        """Carga los términos predefinidos desde el archivo JSON"""
        try:
            json_path = Path(__file__).parent.parent / 'logic' / 'custom_terms.json'
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    terms = json.load(f)

                for term in terms:
                    item = QListWidgetItem(term)
                    self.terms_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar términos predefinidos: {str(e)}")

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
            QMessageBox.information(self, "Información", "Por favor seleccione un término de la lista.")

    def get_selected_term(self):
        """Retorna el término seleccionado"""
        return self.selected_term

class ApiKeyConfigDialog(QDialog):
    def __init__(self, provider_name, current_api_key="", parent=None):
        super().__init__(parent)
        self.provider_name = provider_name
        self.api_key = current_api_key
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Configurar API Key - {self.provider_name}")
        self.setModal(True)
        self.resize(400, 200)

        layout = QVBoxLayout()

        # Información
        info_label = QLabel(
            f"Configurar API Key para {self.provider_name}\n\n"
            "Esta configuración es TEMPORAL y se perderá al cerrar la aplicación.\n"
            "Para cambios permanentes, modifique el archivo .env en la raíz del proyecto."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #666; margin-bottom: 10px; }")
        layout.addWidget(info_label)

        # Campo API Key
        form_layout = QFormLayout()
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Ingrese su API key")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_input.setText(self.api_key)
        form_layout.addRow("API Key:", self.api_input)
        layout.addLayout(form_layout)

        # Botones
        buttons_layout = QHBoxLayout()

        self.ok_button = QPushButton("Aceptar")
        self.cancel_button = QPushButton("Cancelar")

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.ok_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def get_api_key(self):
        return self.api_input.text().strip()

class TranslatePanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.translation_manager = TranslationManager()
        self.working_directory = None

        # Variable para almacenar API keys temporales
        self.temp_api_keys = {}

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

        # Provider and Model selection
        provider_layout = QHBoxLayout()
        self.provider_combo = QComboBox()
        self.config_button = QPushButton("⚙️")
        self.config_button.setToolTip("Cambiar API Key")
        self.config_button.setMaximumWidth(30)
        self.config_button.clicked.connect(self.configure_api_key)
        self.model_combo = QComboBox()

        provider_layout.addWidget(QLabel("Proveedor:"))
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addWidget(self.config_button)
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

        # New checkbox for enabling translation check
        self.check_translation_checkbox = QCheckBox("Habilitar comprobación de traducción")
        self.check_translation_checkbox.setChecked(True)  # Por defecto está habilitado

        form_layout.addRow(self.check_translation_checkbox)

        # Custom Terms section
        terms_group = QGroupBox("Términos Personalizados")
        terms_layout = QVBoxLayout()

        # Instrucciones para los términos con botones
        terms_header_layout = QHBoxLayout()

        terms_instructions = QLabel(
            "Ingrese los términos y sus traducciones (uno por línea)"
        )
        terms_instructions.setWordWrap(True)
        terms_header_layout.addWidget(terms_instructions)

        # Botón para copiar símbolo →
        self.copy_arrow_btn = QPushButton("→")
        self.copy_arrow_btn.setMaximumWidth(30)
        self.copy_arrow_btn.setToolTip("Copiar símbolo → al portapapeles")
        self.copy_arrow_btn.clicked.connect(self.copy_arrow_symbol)
        terms_header_layout.addWidget(self.copy_arrow_btn)

        # Botón para mostrar términos predefinidos
        self.preset_terms_btn = QPushButton("⚙")
        self.preset_terms_btn.setMaximumWidth(30)
        self.preset_terms_btn.setToolTip("Cargar términos predefinidos")
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

        # Comentar estas líneas para permitir escritura libre
        # self.start_chapter_spin.textChanged.connect(self.adjust_chapter_range)
        # self.end_chapter_spin.textChanged.connect(self.adjust_chapter_range)

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



            # Cargar modelos iniciales
            self.update_models()



        except Exception as e:
            print(f"Error cargando modelos: {e}")

    def configure_api_key(self):
        """Abre el diálogo de configuración de API Key"""
        provider_name = self.provider_combo.currentText()
        if not provider_name:
            return

        # Obtener API key actual (temporal o del .env)
        current_api_key = self.get_current_api_key()

        dialog = ApiKeyConfigDialog(provider_name, current_api_key, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_api_key = dialog.get_api_key()
            if new_api_key:
                # Guardar API key temporal para el proveedor actual
                provider_key = next(
                    (k for k, v in self.models_config.items()
                     if v['name'] == provider_name),
                    None
                )
                if provider_key:
                    self.temp_api_keys[provider_key] = new_api_key
                    self.main_window.statusBar().showMessage(f"API Key configurada temporalmente para {provider_name}", 3000)

    def get_current_api_key(self):
        """Obtiene la API key actual (temporal o del .env)"""
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
        if self.working_directory:
            self.translation_manager.initialize(self.working_directory)
            saved_terms = self.translation_manager.get_custom_terms()
            if saved_terms:
                self.terms_input.setPlainText(saved_terms)

    def start_translation(self):
        """Inicia el proceso de traducción"""
        if not self.main_window.current_directory:
            self.main_window.statusBar().showMessage("Error: Seleccione un directorio primero")
            return

        # Validar API key
        api_key = self.get_current_api_key()
        if not api_key:
            self.main_window.statusBar().showMessage("Error: API key no configurada. Use el botón de configuración.")
            return

        # Obtener proveedor y modelo seleccionados
        provider = next(
            (k for k, v in self.models_config.items()
             if v['name'] == self.provider_combo.currentText()),
            None
        )

        if not provider:
            self.main_window.statusBar().showMessage("Error: Debe seleccionar un proveedor válido")
            return

        model = next(
            (k for k, v in self.models_config[provider]['models'].items()
             if v['name'] == self.model_combo.currentText()),
            None
        )

        if not model:
            self.main_window.statusBar().showMessage("Error: Debe seleccionar un modelo válido")
            return

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

        # Obtener estado de la comprobación
        enable_check = self.check_translation_checkbox.isChecked()

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
            segment_size,
            enable_check   # <-- Pasar nuevo parámetro para habilitar comprobación
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
            self.main_window.statusBar().showMessage("Símbolo → copiado al portapapeles", 2000)
        else:
            self.main_window.statusBar().showMessage("Error: No se pudo acceder al portapapeles", 3000)

    def show_preset_terms(self):
        """Muestra el diálogo con términos predefinidos"""
        dialog = PresetTermsDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            selected_term = dialog.get_selected_term()
            if selected_term:
                current_text = self.terms_input.toPlainText()
                if current_text:
                    new_text = current_text + "\n" + selected_term
                else:
                    new_text = selected_term
                self.terms_input.setPlainText(new_text)
