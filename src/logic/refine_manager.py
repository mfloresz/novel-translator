from typing import List, Dict, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import os
import time
from .database import TranslationDatabase
from .translator import TranslatorLogic
from .session_logger import session_logger
from .folder_structure import NovelFolderStructure
from src.logic.status_manager import STATUS_REFINED, STATUS_ERROR, STATUS_PROCESSING, get_status_text

class RefineWorker(QObject):
    progress_updated = pyqtSignal(str)
    refine_completed = pyqtSignal(str, bool)
    all_refines_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, files_to_refine: List[Dict[str, str]],
                 working_directory: str,
                 translator: TranslatorLogic, source_lang: str,
                 target_lang: str, api_key: str, provider: str,
                 model: str, custom_terms: str = "",
                 status_callback: Optional[Callable[[str, str], None]] = None,
                 lang_manager=None, temp_api_keys: dict = None,
                 timeout: int = 120):
        super().__init__()
        self.files_to_refine = files_to_refine
        self.working_directory = working_directory
        self.translator = translator
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.custom_terms = custom_terms
        self.status_callback = status_callback
        self.lang_manager = lang_manager
        self.temp_api_keys = temp_api_keys or {}
        self.timeout = timeout
        self._stop_requested = False

    def _get_status_string(self, key, default_text=""):
        """Get a localized status string from the language manager."""
        if self.lang_manager:
            return self.lang_manager.get_string(key, default_text)
        return default_text if default_text else key

    def stop(self):
        self._stop_requested = True

    def is_stop_requested(self) -> bool:
        """Retorna True si se ha solicitado detener el refinamiento"""
        return self._stop_requested

    def run(self):
        try:
            total_files = len(self.files_to_refine)
            successful_refines = 0

            for i, file_info in enumerate(self.files_to_refine, 1):
                if self._stop_requested:
                    break

                filename = file_info['name']
                self.progress_updated.emit(self._get_status_string("refine_manager.progress.refining_chapter", "Refinando capítulo {index} de {total}: {filename}").format(
                    index=i, total=total_files, filename=filename))

                # Actualizar estado a "Procesando"
                if self.status_callback:
                    status_text = get_status_text(STATUS_PROCESSING, self.lang_manager)
                    self.status_callback(filename, status_text)

                # Registrar inicio de refinamiento
                session_logger.log_refine_start(filename, self.source_lang, self.target_lang)

                # Refinar el archivo
                success = self._refine_single_file(filename)

                if success:
                    successful_refines += 1
                    session_logger.log_refine_complete(filename, True)
                    self.refine_completed.emit(filename, True)
                else:
                    session_logger.log_refine_complete(filename, False)
                    self.refine_completed.emit(filename, False)

                # Esperar antes del siguiente refinamiento si no es el último archivo
                if i < total_files and not self._stop_requested:
                    time.sleep(5)

            if not self._stop_requested:
                final_message = self._get_status_string("refine_manager.progress.completed", "Refinamiento completado. {successful} de {total} archivos refinados exitosamente.").format(
                    successful=successful_refines, total=total_files)
                self.progress_updated.emit(final_message)
                self.all_refines_completed.emit()

        except Exception as e:
            self.error_occurred.emit(self._get_status_string("refine_manager.error.general", "Error en el proceso de refinamiento: {error}").format(error=str(e)))
        finally:
            self.all_refines_completed.emit()

    def _refine_single_file(self, filename: str) -> bool:
        try:
            # Asegurar que la estructura de carpetas exista
            NovelFolderStructure.ensure_structure(self.working_directory)

            # Rutas usando la nueva estructura
            originals_path = NovelFolderStructure.get_originals_path(self.working_directory)
            translated_path = NovelFolderStructure.get_translated_path(self.working_directory)

            source_path = originals_path / filename
            translated_path_file = translated_path / filename
            temp_output_path = translated_path / f".temp_refined_{filename}"

            # Verificar que el archivo original existe
            if not source_path.exists():
                error_msg = f"Archivo original no encontrado: {source_path}"
                session_logger.log_error(error_msg)
                self.error_occurred.emit(error_msg)
                return False

            # Verificar que el archivo traducido existe
            if not translated_path_file.exists():
                error_msg = f"Archivo traducido no encontrado: {translated_path_file}"
                session_logger.log_error(error_msg)
                self.error_occurred.emit(error_msg)
                return False

            # Leer archivo original
            with open(source_path, 'r', encoding='utf-8') as file:
                source_text = file.read()

            # Leer archivo traducido
            with open(translated_path_file, 'r', encoding='utf-8') as file:
                translated_text = file.read()

            # Refinar la traducción
            refined_text = self.translator._refine_translation(
                source_text=source_text,
                translated_text=translated_text,
                source_lang=self.source_lang,
                target_lang=self.target_lang,
                main_api_key=self.api_key,
                refine_provider=self.provider,
                refine_model=self.model,
                custom_terms=self.custom_terms,
                temp_api_keys=self.temp_api_keys,
                timeout=self.timeout,
                stop_callback=self.is_stop_requested
            )

            if not refined_text:
                error_msg = f"Error al refinar {filename}: No se obtuvo refinamiento"
                session_logger.log_error(error_msg)
                self.error_occurred.emit(error_msg)
                return False

            # Verificar si se ha solicitado detener antes de guardar archivos
            if self.is_stop_requested():
                session_logger.log_info(f"Guardado cancelado para {filename} por solicitud del usuario")
                return False

            # Guardar primero en archivo temporal
            with open(temp_output_path, 'w', encoding='utf-8') as file:
                file.write(refined_text)

            # Verificar nuevamente antes de mover el archivo final
            if self.is_stop_requested():
                session_logger.log_info(f"Guardado final cancelado para {filename} por solicitud del usuario")
                # Limpiar archivo temporal
                try:
                    temp_output_path.unlink()
                except:
                    pass
                return False

            # Si todo salió bien, mover el archivo temporal al destino final
            temp_output_path.replace(translated_path_file)

            return True

        except Exception as e:
            error_msg = f"Error al refinar {filename}: {str(e)}"
            session_logger.log_error(error_msg)
            self.error_occurred.emit(error_msg)
            # Limpiar archivo temporal si existe
            if temp_output_path.exists():
                try:
                    temp_output_path.unlink()
                except:
                    pass
            return False

class RefineManager(QObject):
    # Señales para comunicar con la UI
    progress_updated = pyqtSignal(str)
    refine_completed = pyqtSignal(str, bool)
    all_refines_completed = pyqtSignal()
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
        Inicializa el administrador de refinamiento con un directorio de trabajo.

        Args:
            directory: Ruta al directorio de trabajo
            provider: Proveedor de refinamiento
            model: Modelo de refinamiento
        """
        self.working_directory = directory
        self.db = TranslationDatabase(directory)
        self.current_provider = provider
        self.current_model = model

    def refine_files(self, files_to_refine: List[Dict[str, str]],
                     source_lang: str, target_lang: str, api_key: str,
                     status_callback: Optional[Callable[[str, str], None]] = None,
                     custom_terms: str = "", temp_api_keys: dict = None,
                     timeout: int = 120) -> None:
        """
        Inicia el refinamiento de archivos.

        Args:
            files_to_refine: Lista de diccionarios con información de archivos
            source_lang: Idioma de origen
            target_lang: Idioma de destino
            api_key: API key del servicio
            status_callback: Función para actualizar el estado en la UI
            custom_terms: Términos personalizados para el refinamiento
            temp_api_keys: Diccionario de API keys temporales
            timeout: Timeout para las llamadas API
        """
        if not self.working_directory:
            self.error_occurred.emit(self.lang_manager.get_string("refine_manager.error.no_working_directory", "No se ha inicializado el directorio de trabajo"))
            return

        # Crear y configurar el worker
        self.thread = QThread()
        self.worker = RefineWorker(
            files_to_refine,
            self.working_directory,
            self.translator,
            source_lang,
            target_lang,
            api_key,
            self.current_provider,
            self.current_model,
            custom_terms,
            status_callback,
            self.lang_manager,
            temp_api_keys,
            timeout
        )

        # Mover el worker al thread
        self.worker.moveToThread(self.thread)

        # Conectar señales
        self.thread.started.connect(self.worker.run)
        self.worker.progress_updated.connect(self.progress_updated)
        self.worker.refine_completed.connect(self.refine_completed)
        self.worker.all_refines_completed.connect(self.all_refines_completed)
        self.worker.error_occurred.connect(self.error_occurred)

        # Conectar el callback de estado si existe
        if status_callback:
            self.worker.refine_completed.connect(
                lambda filename, success: status_callback(
                    filename,
                    get_status_text(STATUS_REFINED if success else STATUS_ERROR, self.lang_manager)
                )
            )

        # Limpieza cuando termine
        self.worker.all_refines_completed.connect(self.thread.quit)
        self.worker.all_refines_completed.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Iniciar el thread
        self.thread.start()

    def stop_refine(self) -> None:
        """Detiene el proceso de refinamiento en curso"""
        if self.worker:
            self.worker.stop()
            self.progress_updated.emit(self._get_status_string("refine_manager.progress.stopping", "Deteniendo refinamiento..."))

    def get_supported_languages(self) -> Dict[str, str]:
        """Obtiene la lista de idiomas soportados"""
        return self.translator.get_supported_languages()

    def get_custom_terms(self) -> str:
        """Obtiene los términos personalizados guardados"""
        if self.db:
            return self.db.get_custom_terms()
        return ""