"""Gestor de códigos de estado para capítulos."""

from PyQt6.QtGui import QColor

# Constantes de estado
STATUS_UNPROCESSED = 0
STATUS_TRANSLATED = 1
STATUS_PROCESSING = 2
STATUS_ERROR = 3
STATUS_REFINED = 4

# Mapeo de código a claves de traducción
STATUS_CODE_TO_KEY = {
    STATUS_UNPROCESSED: "main_window.chapters_table.status.unprocessed",
    STATUS_TRANSLATED: "main_window.chapters_table.status.translated",
    STATUS_PROCESSING: "main_window.chapters_table.status.processing",
    STATUS_ERROR: "main_window.chapters_table.status.error",
    STATUS_REFINED: "main_window.chapters_table.status.refined"
}

def get_status_text(status_code, lang_manager):
    """Convierte código numérico a texto localizado."""
    key = STATUS_CODE_TO_KEY.get(status_code, "main_window.chapters_table.status.unprocessed")
    return lang_manager.get_string(key)

def get_status_color(status_code):
    """Obtiene el código de color para un estado específico."""
    # Colores como tuplas RGB
    status_colors = {
        STATUS_UNPROCESSED: None,  # Color por defecto del sistema
        STATUS_TRANSLATED: (34, 139, 34),  # Verde oscuro
        STATUS_PROCESSING: (255, 165, 0),  # Naranja
        STATUS_ERROR: (165, 42, 42),  # Rojo oscuro
        STATUS_REFINED: (0, 100, 0)  # Verde más oscuro para refinado
    }
    return status_colors.get(status_code, None)

def get_status_code_from_text(status_text):
    """Convierte texto de estado a código numérico."""
    # Este método se usa solo para compatibilidad con valores existentes
    # No se debe usar para nuevos idiomas
    STATUS_TEXT_TO_CODE = {
        # Español
        "Sin procesar": STATUS_UNPROCESSED,
        "Traducido": STATUS_TRANSLATED,
        "Procesando": STATUS_PROCESSING,
        "Error": STATUS_ERROR,
        "Refinado": STATUS_REFINED,
        # Inglés
        "Unprocessed": STATUS_UNPROCESSED,
        "Translated": STATUS_TRANSLATED,
        "Processing": STATUS_PROCESSING,
        "Error": STATUS_ERROR,
        "Refined": STATUS_REFINED
    }
    return STATUS_TEXT_TO_CODE.get(status_text, STATUS_UNPROCESSED)