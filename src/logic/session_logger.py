import os
import tempfile
import time
from datetime import datetime
from typing import Optional

class SessionLogger:
    """
    Logger para registrar las salidas del trabajo durante la sesión.
    El archivo se crea en el directorio temporal del sistema y se borra al cerrar la aplicación.
    """

    def __init__(self):
        self.log_file_path: Optional[str] = None
        self._create_log_file()

    def _create_log_file(self) -> None:
        """Crea el archivo de log en el directorio temporal del sistema"""
        try:
            # Crear nombre único para el archivo de log
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"novel_translator_session_{timestamp}.log"

            # Obtener directorio temporal del sistema
            temp_dir = tempfile.gettempdir()
            self.log_file_path = os.path.join(temp_dir, log_filename)

            # Crear archivo con encabezado
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                f.write(f"=== Novel Translator Session Log ===\n")
                f.write(f"Sesión iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Archivo de log: {self.log_file_path}\n")
                f.write("=" * 50 + "\n\n")

        except Exception as e:
            print(f"Error creando archivo de log: {e}")
            self.log_file_path = None

    def log_info(self, message: str) -> None:
        """Registra un mensaje informativo"""
        self._write_log("INFO", message)

    def log_error(self, message: str) -> None:
        """Registra un mensaje de error"""
        self._write_log("ERROR", message)

    def log_warning(self, message: str) -> None:
        """Registra un mensaje de advertencia"""
        self._write_log("WARNING", message)

    def log_api_request(self, provider: str, model: str, text_length: int) -> None:
        """Registra una petición a la API"""
        message = f"Petición API - Proveedor: {provider}, Modelo: {model}, Longitud texto: {text_length}"
        self._write_log("API_REQUEST", message)

    def log_api_response(self, provider: str, success: bool, response_text: str = None, error_message: str = None) -> None:
        """Registra la respuesta de la API"""
        if success:
            message = f"Respuesta API exitosa - Proveedor: {provider}"
            self._write_log("API_RESPONSE", message)
        else:
            message = f"Error en API - Proveedor: {provider}"
            if error_message:
                message += f"\nError: {error_message}"
            elif response_text:
                message += f"\nRespuesta de error: {response_text[:500]}{'...' if len(response_text) > 500 else ''}"
            self._write_log("API_ERROR", message)

    def log_translation_start(self, filename: str, source_lang: str, target_lang: str) -> None:
        """Registra el inicio de una traducción"""
        message = f"Iniciando traducción - Archivo: {filename}, {source_lang} -> {target_lang}"
        self._write_log("TRANSLATION_START", message)

    def log_translation_complete(self, filename: str, success: bool, segments: int = 0) -> None:
        """Registra la finalización de una traducción"""
        status = "exitosa" if success else "fallida"
        message = f"Traducción {status} - Archivo: {filename}"
        if segments > 0:
            message += f", Segmentos: {segments}"
        self._write_log("TRANSLATION_COMPLETE", message)

    def log_check_result(self, filename: str, passed: bool, attempt: int = 1) -> None:
        """Registra el resultado de la comprobación de traducción"""
        result = "PASÓ" if passed else "FALLÓ"
        message = f"Comprobación {result} - Archivo: {filename}, Intento: {attempt}"
        self._write_log("CHECK_RESULT", message)

    def _write_log(self, level: str, message: str) -> None:
        """Escribe un mensaje al archivo de log"""
        if not self.log_file_path:
            return

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {message}\n"

            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                f.flush()  # Asegurar que se escriba inmediatamente

        except Exception as e:
            print(f"Error escribiendo al log: {e}")

    def get_log_path(self) -> Optional[str]:
        """Retorna la ruta del archivo de log"""
        return self.log_file_path

    def cleanup(self) -> None:
        """Limpia el archivo de log al cerrar la aplicación"""
        if self.log_file_path and os.path.exists(self.log_file_path):
            try:
                os.remove(self.log_file_path)
                print(f"Archivo de log eliminado: {self.log_file_path}")
            except Exception as e:
                print(f"Error eliminando archivo de log: {e}")

# Instancia global del logger
session_logger = SessionLogger()
