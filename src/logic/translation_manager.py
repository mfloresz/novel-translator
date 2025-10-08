from typing import List, Dict, Optional, Tuple, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import os
import time
from .database import TranslationDatabase
from .translator import TranslatorLogic
from .session_logger import session_logger
from .folder_structure import NovelFolderStructure
from src.logic.status_manager import STATUS_PROCESSING, STATUS_TRANSLATED, STATUS_ERROR, get_status_text

class TranslationWorker(QObject):
    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(str, bool)
    all_translations_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, files_to_translate: List[Dict[str, str]],
                 working_directory: str, db: TranslationDatabase,
                 translator: TranslatorLogic, source_lang: str,
                 target_lang: str, api_key: str, provider: str,
                 model: str, custom_terms: str = "",
                 segment_size: Optional[int] = None,
                 enable_check: bool = True,
                 enable_refine: bool = False,
                 check_refine_settings: Optional[Dict] = None,
                 status_callback: Optional[Callable[[str, str], None]] = None,
                 lang_manager = None, temp_api_keys: dict = None,
                 allow_retranslation: bool = False,
                 segmentation_config: Optional[Dict] = None):
        super().__init__()
        self.files_to_translate = files_to_translate
        self.working_directory = working_directory
        self.db = db
        self.translator = translator
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.custom_terms = custom_terms
        self.segment_size = segment_size
        self.enable_check = enable_check
        self.enable_refine = enable_refine
        self.check_refine_settings = check_refine_settings
        self.status_callback = status_callback
        self.lang_manager = lang_manager
        self.temp_api_keys = temp_api_keys or {}
        self.allow_retranslation = allow_retranslation
        self.segmentation_config = segmentation_config
        self._stop_requested = False
        self.translator.segment_size = segment_size

    def _get_status_string(self, key, default_text=""):
        """Get a localized status string from the language manager."""
        if self.lang_manager:
            return self.lang_manager.get_string(key, default_text)
        return default_text if default_text else key

    def stop(self):
        self._stop_requested = True

    def run(self):
        try:
            total_files = len(self.files_to_translate)
            successful_translations = 0

            # Configurar tamaño de segmento si se especificó
            if self.segment_size is not None:
                self.translator.segment_size = self.segment_size

            for i, file_info in enumerate(self.files_to_translate, 1):
                if self._stop_requested:
                    break

                filename = file_info['name']
                self.progress_updated.emit(self._get_status_string("translation_manager.progress.translating_chapter", "Traduciendo capítulo {index} de {total}: {filename}").format(
                    index=i, total=total_files, filename=filename))

                # Actualizar estado a "Procesando"
                if self.status_callback:
                    status_text = get_status_text(STATUS_PROCESSING, self.lang_manager)
                    self.status_callback(filename, status_text)

                # Verificar si ya está traducido
                if self.db.is_file_translated(filename) and not self.allow_retranslation:
                    session_logger.log_info(f"Archivo ya traducido, omitiendo: {filename}")
                    continue

                # Registrar inicio de traducción
                session_logger.log_translation_start(filename, self.source_lang, self.target_lang)

                # Traducir el archivo
                success = self._translate_single_file(filename)

                if success:
                    successful_translations += 1
                    self.db.add_translation_record(filename, self.source_lang, self.target_lang)
                    session_logger.log_translation_complete(filename, True)
                    self.translation_completed.emit(filename, True)
                else:
                    session_logger.log_translation_complete(filename, False)
                    self.translation_completed.emit(filename, False)

                # Esperar antes de la siguiente traducción si no es el último archivo
                if i < total_files and not self._stop_requested:
                    time.sleep(5)

            if not self._stop_requested:
                final_message = self._get_status_string("translation_manager.progress.completed", "Traducción completada. {successful} de {total} archivos traducidos exitosamente.").format(
                    successful=successful_translations, total=total_files)
                self.progress_updated.emit(final_message)
                self.all_translations_completed.emit()

        except Exception as e:
            self.error_occurred.emit(self._get_status_string("translation_manager.error.general", "Error en el proceso de traducción: {error}").format(error=str(e)))
        finally:
            self.all_translations_completed.emit()

    def _translate_single_file(self, filename: str) -> bool:
        try:
            # Asegurar que la estructura de carpetas exista
            NovelFolderStructure.ensure_structure(self.working_directory)

            # Rutas usando la nueva estructura
            originals_path = NovelFolderStructure.get_originals_path(self.working_directory)
            translated_path = NovelFolderStructure.get_translated_path(self.working_directory)

            input_path = originals_path / filename
            output_path = translated_path / filename
            temp_output_path = translated_path / f".temp_{filename}"

            # Verificar que el archivo original existe
            if not input_path.exists():
                error_msg = f"Archivo original no encontrado: {input_path}"
                session_logger.log_error(error_msg)
                self.error_occurred.emit(error_msg)
                return False

            # Leer archivo original
            with open(input_path, 'r', encoding='utf-8') as file:
                text = file.read()

            # Intentar traducir usando parámetros enable_check y enable_refine
            translated_text = self.translator.translate_text(
                text,
                self.source_lang,
                self.target_lang,
                self.api_key,
                self.provider,
                self.model,
                self.custom_terms,
                enable_check=self.enable_check,
                enable_refine=self.enable_refine,
                check_refine_settings=self.check_refine_settings,
                temp_api_keys=self.temp_api_keys,
                segmentation_config=self.segmentation_config
            )

            if not translated_text:
                error_msg = f"Error al traducir {filename}: No se obtuvo traducción"
                session_logger.log_error(error_msg)
                self.error_occurred.emit(error_msg)
                return False

            # Guardar primero en archivo temporal
            with open(temp_output_path, 'w', encoding='utf-8') as file:
                file.write(translated_text)

            # Si todo salió bien, mover el archivo temporal al destino final
            temp_output_path.replace(output_path)
            return True

        except Exception as e:
            error_msg = f"Error al traducir {filename}: {str(e)}"
            session_logger.log_error(error_msg)
            self.error_occurred.emit(error_msg)
            # Limpiar archivo temporal si existe
            if temp_output_path.exists():
                try:
                    temp_output_path.unlink()
                except:
                    pass
            return False

class TranslationManager(QObject):
    # Señales para comunicar con la UI
    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(str, bool)
    all_translations_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, lang_manager=None):
        super().__init__()
        self.translator = TranslatorLogic()
        self.db: Optional[TranslationDatabase] = None
        self.working_directory: Optional[str] = None
        self.current_provider = None
        self.current_model = None
        self.worker = None
        self.thread = None
        self.lang_manager = lang_manager

    def set_language_manager(self, lang_manager):
        """Set the language manager for status translations."""
        self.lang_manager = lang_manager

    def update_temp_prompts_path(self, path):
        """Actualiza la ruta de prompts temporales en el translator"""
        self.translator.update_temp_prompts_path(path)

    def _get_status_string(self, key, default_text=""):
        """Get a localized status string from the language manager."""
        if self.lang_manager:
            return self.lang_manager.get_string(key, default_text)
        return default_text if default_text else key

    def initialize(self, directory: str, provider: str = None, model: str = None) -> None:
        """
        Inicializa el administrador de traducción con un directorio de trabajo.

        Args:
            directory: Ruta al directorio de trabajo
            provider: Proveedor de traducción
            model: Modelo de traducción
        """
        self.working_directory = directory
        self.db = TranslationDatabase(directory)
        self.current_provider = provider
        self.current_model = model

    def translate_files(self, files_to_translate: List[Dict[str, str]],
                       source_lang: str, target_lang: str, api_key: str,
                       status_callback: Optional[Callable[[str, str], None]] = None,
                       custom_terms: str = "", segment_size: Optional[int] = None,
                       enable_check: bool = True, enable_refine: bool = False,
                       check_refine_settings: Optional[Dict] = None,
                       temp_api_keys: dict = None, allow_retranslation: bool = False,
                       segmentation_config: Optional[Dict] = None) -> None:
        """
        Inicia la traducción de archivos.

        Args:
            files_to_translate: Lista de diccionarios con información de archivos
            source_lang: Idioma de origen
            target_lang: Idioma de destino
            api_key: API key del servicio
            status_callback: Función para actualizar el estado en la UI
            custom_terms: Términos personalizados para la traducción
            segment_size: Tamaño de segmentación opcional (caracteres por segmento)
            enable_check: Bool para habilitar o no la comprobación de la traducción
            enable_refine: Bool para habilitar o no el refinamiento de la traducción
            temp_api_keys: Diccionario de API keys temporales
            allow_retranslation: Bool para permitir re-traducción de archivos ya traducidos
        """
        if not self.working_directory or not self.db:
                self.error_occurred.emit(self.lang_manager.get_string("translation_manager.error.no_working_directory", "No se ha inicializado el directorio de trabajo"))
                return

        # Guardar términos personalizados
        if custom_terms.strip():
            self.db.save_custom_terms(custom_terms)

        # Crear y configurar el worker
        self.thread = QThread()
        self.worker = TranslationWorker(
            files_to_translate,
            self.working_directory,
            self.db,
            self.translator,
            source_lang,
            target_lang,
            api_key,
            self.current_provider,
            self.current_model,
            custom_terms,
            segment_size,
            enable_check,  # Opción para habilitar/deshabilitar la comprobación
            enable_refine,  # Opción para habilitar/deshabilitar el refinamiento
            check_refine_settings, # Pasar la configuración de comprobación/refinado
            status_callback,  # Pasar el callback de estado
            self.lang_manager,  # Pasar el administrador de idioma
            temp_api_keys,  # Pasar las API keys temporales
            allow_retranslation,  # Pasar el flag de permitir re-traducción
            segmentation_config  # Pasar config de segmentación
        )

        # Mover el worker al thread
        self.worker.moveToThread(self.thread)

        # Conectar señales
        self.thread.started.connect(self.worker.run)
        self.worker.progress_updated.connect(self.progress_updated)
        self.worker.translation_completed.connect(self.translation_completed)
        self.worker.all_translations_completed.connect(self.all_translations_completed)
        self.worker.error_occurred.connect(self.error_occurred)

        # Conectar el callback de estado si existe
        if status_callback:
            self.worker.translation_completed.connect(
                lambda filename, success: status_callback(
                    filename, 
                    get_status_text(STATUS_TRANSLATED if success else STATUS_ERROR, self.lang_manager)
                )
            )

        # Limpieza cuando termine
        self.worker.all_translations_completed.connect(self.thread.quit)
        self.worker.all_translations_completed.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Iniciar el thread
        self.thread.start()

    def stop_translation(self) -> None:
        """Detiene el proceso de traducción en curso"""
        if self.worker:
                self.worker.stop()
                self.progress_updated.emit(self._get_status_string("translation_manager.progress.stopping", "Deteniendo traducción..."))

    def get_supported_languages(self) -> Dict[str, str]:
        """Obtiene la lista de idiomas soportados"""
        return self.translator.get_supported_languages()

    def get_custom_terms(self) -> str:
        """Obtiene los términos personalizados guardados"""
        if self.db:
            return self.db.get_custom_terms()
        return ""

    
