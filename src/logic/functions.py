from PyQt6.QtWidgets import QMessageBox, QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox
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

def validate_epub_file(file_path):
    """
    Valida que un archivo sea un EPUB válido antes de importarlo.

    Args:
        file_path (str): Ruta al archivo EPUB

    Returns:
        tuple: (bool, str) - (es_válido, mensaje_de_error)
    """
    import zipfile

    if not file_path:
        return False, "No se seleccionó ningún archivo"

    if not os.path.exists(file_path):
        return False, "El archivo no existe"

    if not file_path.lower().endswith('.epub'):
        return False, "El archivo debe tener extensión .epub"

    try:
        with zipfile.ZipFile(file_path, 'r') as epub_zip:
            # Verificar estructura básica de EPUB
            files = epub_zip.namelist()

            if 'META-INF/container.xml' not in files:
                return False, "Archivo EPUB inválido: falta container.xml"

            # Verificar que tenga al menos un archivo OPF
            has_opf = any(f.endswith('.opf') for f in files)
            if not has_opf:
                return False, "Archivo EPUB inválido: falta archivo OPF"

            return True, ""

    except zipfile.BadZipFile:
        return False, "El archivo está corrupto o no es un ZIP válido"
    except Exception as e:
        return False, f"Error al validar EPUB: {str(e)}"

class EpubImportDialog(QDialog):
    """
    Diálogo personalizado para confirmar la importación de EPUB con opciones adicionales.
    """
    def __init__(self, epub_name, output_dir, parent=None):
        super().__init__(parent)
        self.epub_name = epub_name
        self.output_dir = output_dir
        self.add_numbering = True
        self.add_chapter_titles = True
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Importar EPUB")
        self.setModal(True)
        self.resize(500, 200)

        layout = QVBoxLayout()

        # Información principal
        info_label = QLabel(
            f"Se importará el EPUB: {self.epub_name}\n\n"
            f"Se creará una nueva carpeta en: {self.output_dir}\n"
            "Los capítulos se convertirán a archivos TXT."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Opciones
        options_label = QLabel("Opciones de importación:")
        options_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(options_label)

        # Opción 1: Numeración automática en contenido
        self.numbering_checkbox = QCheckBox(
            "Añadir numeración automática al principio del contenido (Capítulo 001, Capítulo 002, etc.)"
        )
        self.numbering_checkbox.setChecked(False)
        self.numbering_checkbox.setToolTip(
            "Si está marcado, se añadirá 'Capítulo 001', 'Capítulo 002', etc. al principio del contenido del archivo TXT.\n"
            "Si no está marcado, no se añadirá numeración automática al contenido."
        )
        layout.addWidget(self.numbering_checkbox)

        # Opción 2: Insertar títulos de capítulos en contenido
        self.titles_checkbox = QCheckBox(
            "Insertar título del capítulo al principio del contenido"
        )
        self.titles_checkbox.setChecked(True)
        self.titles_checkbox.setToolTip(
            "Si está marcado, el título del capítulo (del marcador) se añadirá al principio del contenido del archivo TXT.\n"
            "Si no está marcado, solo se incluirá el contenido original sin añadir títulos."
        )
        layout.addWidget(self.titles_checkbox)

        # Botones
        buttons_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancelar")
        self.ok_button = QPushButton("Importar")

        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.accept)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.ok_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def get_options(self):
        """
        Retorna las opciones seleccionadas por el usuario.

        Returns:
            dict: Diccionario con las opciones seleccionadas
        """
        return {
            'add_numbering_to_content': self.numbering_checkbox.isChecked(),
            'add_chapter_titles_to_content': self.titles_checkbox.isChecked()
        }

def show_import_confirmation_dialog(epub_name, output_dir, parent=None):
    """
    Muestra un diálogo específico para confirmar la importación de EPUB con opciones.

    Args:
        epub_name (str): Nombre del archivo EPUB
        output_dir (str): Directorio donde se creará la carpeta
        parent: Widget padre para el diálogo

    Returns:
        tuple: (bool, dict) - (aceptado, opciones_seleccionadas)
    """
    dialog = EpubImportDialog(epub_name, output_dir, parent)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return True, dialog.get_options()
    else:
        return False, {}

def sanitize_directory_name(name):
    """
    Sanitiza un nombre para usar como nombre de directorio.

    Args:
        name (str): Nombre original

    Returns:
        str: Nombre sanitizado válido para directorio
    """
    # Caracteres no válidos en nombres de archivo/directorio
    invalid_chars = '<>:"/\\|?*'

    # Reemplazar caracteres inválidos
    for char in invalid_chars:
        name = name.replace(char, '_')

    # Remover espacios extra y caracteres especiales adicionales
    name = ''.join(c for c in name if c.isalnum() or c in ' -_.')

    # Limitar longitud
    name = name[:100].strip()

    # Asegurar que no esté vacío
    if not name:
        name = "Libro_Importado"

    return name
