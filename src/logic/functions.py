from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
import os

# Funciones existentes
def show_confirmation_dialog(message, title="Confirmación"):
    """
    Muestra un diálogo de confirmación y retorna True si el usuario acepta.
    """
    dialog = QMessageBox()
    dialog.setIcon(QMessageBox.Icon.Warning)
    dialog.setText(message)
    dialog.setWindowTitle(title)
    dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    dialog.setDefaultButton(QMessageBox.StandardButton.No)
    return dialog.exec() == QMessageBox.StandardButton.Yes

def get_file_range(table, start, end):
    """
    Obtiene la lista de archivos en el rango especificado de la tabla.
    """
    files = []
    for row in range(start - 1, end):
        if row < table.rowCount():
            name_item = table.item(row, 0)
            if name_item:
                files.append(name_item.text())
    return files

def validate_range(start, end, max_value):
    """
    Valida que el rango especificado sea válido.
    """
    if start < 1:
        return False, "El capítulo inicial debe ser mayor o igual a 1"
    if end > max_value:
        return False, f"El capítulo final no puede ser mayor que {max_value}"
    if start > end:
        return False, "El capítulo inicial no puede ser mayor que el final"
    return True, ""

def show_error_dialog(message, title="Error"):
    """
    Muestra un diálogo de error.
    """
    dialog = QMessageBox()
    dialog.setIcon(QMessageBox.Icon.Critical)
    dialog.setText(message)
    dialog.setWindowTitle(title)
    dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
    dialog.exec()

def update_status_bar(window, message, timeout=0):
    """
    Actualiza la barra de estado de la ventana principal.
    """
    window.statusBar().showMessage(message, timeout)

def get_selected_mode(radio_buttons):
    """
    Obtiene el modo seleccionado de un grupo de radio buttons.
    """
    for mode, button in radio_buttons.items():
        if button.isChecked():
            return mode
    return None

# Nuevas funciones para el manejo de EPUB

def get_cover_image(initial_dir=None):
    """
    Abre un diálogo para seleccionar una imagen de portada.

    Args:
        initial_dir (str, optional): Directorio inicial para el diálogo

    Returns:
        tuple: (path, pixmap) si se selecciona una imagen válida, (None, None) en caso contrario
    """
    file_dialog = QFileDialog()
    if initial_dir is None:
        initial_dir = os.path.expanduser('~')
    
    file_path, _ = file_dialog.getOpenFileName(
        caption="Seleccionar imagen de portada",
        directory=initial_dir,
        filter="Imágenes (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;JPEG (*.jpg *.jpeg);;PNG (*.png);;Todos los archivos (*.*)"
    )

    if file_path:
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                return file_path, pixmap
        except Exception as e:
            show_error_dialog(f"Error al cargar la imagen: {str(e)}")

    return None, None

def preview_image(pixmap, label, max_size=150):
    """
    Muestra una vista previa de la imagen en un QLabel.

    Args:
        pixmap (QPixmap): La imagen a mostrar
        label (QLabel): El widget donde se mostrará la imagen
        max_size (int): Tamaño máximo para la vista previa
    """
    if pixmap and not pixmap.isNull():
        # Mantener la proporción de aspecto
        scaled_pixmap = pixmap.scaled(
            max_size, max_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    else:
        label.clear()
        label.setText("Sin imagen")

def validate_epub_input(title, author, directory):
    """
    Valida los datos de entrada para la creación del EPUB.

    Returns:
        tuple: (bool, str) - (es_válido, mensaje_de_error)
    """
    if not title:
        return False, "El título es obligatorio"
    if not author:
        return False, "El autor es obligatorio"
    if not directory:
        return False, "Seleccione un directorio de trabajo"
    if not os.path.isdir(directory):
        return False, "El directorio seleccionado no es válido"
    return True, ""

def get_epub_files(table, start_index=None, end_index=None):
    """
    Obtiene la lista de archivos para el EPUB desde la tabla.

    Args:
        table: QTableWidget que contiene la lista de archivos
        start_index (int, optional): Índice inicial (1-based)
        end_index (int, optional): Índice final (1-based)

    Returns:
        list: Lista de diccionarios con información de los archivos
    """
    files = []

    if start_index is None or end_index is None:
        # Si no se especifica rango, usar todos los archivos
        start_index = 1
        end_index = table.rowCount()

    for row in range(start_index - 1, end_index):
        if row < table.rowCount():
            name_item = table.item(row, 0)
            if name_item and name_item.text().endswith('.txt'):
                files.append({
                    'name': name_item.text(),
                    'chapter': row + 1
                })

    return files

def create_epub_filename(title, author):
    """
    Crea un nombre de archivo válido para el EPUB usando título y autor.

    Args:
        title (str): Título del libro
        author (str): Autor del libro

    Returns:
        str: Nombre de archivo válido
    """
    # Eliminar caracteres no válidos
    valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    filename = ''.join(c for c in title if c in valid_chars)
    # Limitar longitud y añadir extensión
    return f"{filename[:50]}.epub".strip()
