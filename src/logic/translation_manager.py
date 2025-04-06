from typing import List, Dict, Optional, Tuple, Callable
from PyQt6.QtCore import QObject, pyqtSignal
import os
import time
from .database import TranslationDatabase
from .translator import TranslatorLogic

class TranslationManager(QObject):
    # Señales para comunicar con la UI
    progress_updated = pyqtSignal(str)  # Mensaje de progreso
    translation_completed = pyqtSignal(str, bool)  # (filename, success)
    all_translations_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)  # Mensaje de error

    def __init__(self):
        super().__init__()
        self.translator = TranslatorLogic()
        self.db: Optional[TranslationDatabase] = None
        self.working_directory: Optional[str] = None
        self._stop_requested = False
        self.current_provider = None
        self.current_model = None

    def initialize(self, directory: str, provider: str = None, model: str = None) -> None:
        """
        Inicializa el gestor con un directorio de trabajo y configuración del traductor.

        Args:
            directory (str): Directorio de trabajo
            provider (str): Proveedor de traducción seleccionado
            model (str): Modelo de traducción seleccionado
        """
        self.working_directory = directory
        self.db = TranslationDatabase(directory)
        self.current_provider = provider
        self.current_model = model

    def get_translation_status(self, filename: str) -> str:
        """
        Obtiene el estado de traducción de un archivo.

        Args:
            filename (str): Nombre del archivo

        Returns:
            str: Estado de la traducción ('Traducido' o 'Pendiente')
        """
        if not self.db:
            return 'Pendiente'
        return 'Traducido' if self.db.is_file_translated(filename) else 'Pendiente'

    def translate_files(self,
                       files_to_translate: List[Dict[str, str]],
                       source_lang: str,
                       target_lang: str,
                       api_key: str,
                       status_callback: Optional[Callable[[str, str], None]] = None,
                       custom_terms: str = "") -> None:
        """
        Traduce una lista de archivos.

        Args:
            files_to_translate (List[Dict[str, str]]): Lista de archivos a traducir
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            api_key (str): API key para el servicio de traducción
            status_callback (Callable): Función para actualizar el estado en la UI
            custom_terms (str): Términos personalizados para la traducción
        """
        if not self.working_directory or not self.db:
            self.error_occurred.emit("No se ha inicializado el directorio de trabajo")
            return

        # Guardar términos personalizados en la base de datos
        if custom_terms.strip():
            self.db.save_custom_terms(custom_terms)

        total_files = len(files_to_translate)
        successful_translations = 0
        self._stop_requested = False

        for i, file_info in enumerate(files_to_translate, 1):
            if self._stop_requested:
                break

            filename = file_info['name']
            self.progress_updated.emit(f"Traduciendo capítulo {i} de {total_files}: {filename}")

            # Verificar si ya está traducido
            if self.db.is_file_translated(filename):
                continue

            # Traducir el archivo
            success = self._translate_single_file(
                filename,
                source_lang,
                target_lang,
                api_key,
                custom_terms
            )

            if success:
                successful_translations += 1
                # Actualizar base de datos
                self.db.add_translation_record(filename, source_lang, target_lang)
                # Emitir señal de completado para este archivo
                self.translation_completed.emit(filename, True)
                # Actualizar estado en la UI
                if status_callback:
                    status_callback(filename, "Traducido")
            else:
                self.translation_completed.emit(filename, False)

            # Esperar antes de la siguiente traducción
            if i < total_files and not self._stop_requested:
                time.sleep(15)  # Espera entre traducciones

        # Emitir señal de finalización
        if not self._stop_requested:
            final_message = (f"Traducción completada. {successful_translations} "
                           f"de {total_files} archivos traducidos exitosamente.")
            self.progress_updated.emit(final_message)
            self.all_translations_completed.emit()

    def _translate_single_file(self,
                             filename: str,
                             source_lang: str,
                             target_lang: str,
                             api_key: str,
                             custom_terms: str) -> bool:
        """
        Traduce un único archivo.

        Args:
            filename (str): Nombre del archivo a traducir
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            api_key (str): API key para el servicio de traducción
            custom_terms (str): Términos personalizados para la traducción

        Returns:
            bool: True si la traducción fue exitosa, False en caso contrario
        """
        try:
            input_path = os.path.join(self.working_directory, filename)
            temp_output_path = os.path.join(self.working_directory, f".temp_{filename}")

            # Leer archivo original
            with open(input_path, 'r', encoding='utf-8') as file:
                text = file.read()

            # Intentar traducir
            translated_text = self.translator.translate_text(
                text,
                source_lang,
                target_lang,
                api_key,
                self.current_provider,
                self.current_model,
                custom_terms
            )

            if not translated_text:
                self.error_occurred.emit(f"Error al traducir {filename}: No se obtuvo traducción")
                return False

            # Guardar primero en archivo temporal
            with open(temp_output_path, 'w', encoding='utf-8') as file:
                file.write(translated_text)

            # Si todo salió bien, reemplazar el archivo original
            os.replace(temp_output_path, input_path)
            return True

        except Exception as e:
            self.error_occurred.emit(f"Error al traducir {filename}: {str(e)}")
            # Limpiar archivo temporal si existe
            if os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except:
                    pass
            return False

    def stop_translation(self) -> None:
        """Detiene el proceso de traducción actual"""
        self._stop_requested = True
        self.progress_updated.emit("Deteniendo traducción...")

    def get_supported_languages(self) -> Dict[str, str]:
        """
        Obtiene la lista de idiomas soportados.

        Returns:
            Dict[str, str]: Diccionario de idiomas soportados
        """
        return self.translator.lang_codes

    def get_custom_terms(self) -> str:
        """
        Recupera los términos personalizados guardados para el directorio actual.

        Returns:
            str: Términos personalizados o cadena vacía si no hay
        """
        if self.db:
            return self.db.get_custom_terms()
        return ""
