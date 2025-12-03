import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QLabel, QScrollBar)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QTextCursor, QTextOption

from src.logic.session_logger import session_logger
from src.logic.language_manager import LanguageManager


class LogWindow(QDialog):
    def __init__(self, lang_manager: LanguageManager, parent=None):
        super().__init__(parent)
        self.lang_manager = lang_manager
        self.log_path = session_logger.get_log_path()
        self.user_scrolling = False  # Track if user is manually scrolling

        self.setWindowTitle(self.lang_manager.get_string("log_window.title", "Registro de Sesión"))
        self.setGeometry(200, 200, 900, 600)
        self.setModal(False)  # No modal para permitir interacción con la ventana principal

        # Layout principal
        layout = QVBoxLayout(self)

        # Etiqueta de título
        title_label = QLabel(self.lang_manager.get_string("log_window.title", "Registro de Sesión"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title_label.font()
        font.setBold(True)
        font.setPointSize(12)
        title_label.setFont(font)
        layout.addWidget(title_label)

        # Área de texto para el log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 10))  # Fuente monoespaciada para logs
        self.log_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)  # Habilitar ajuste de línea
        # Conectar señal para detectar cuando el usuario mueve el scrollbar
        self.log_text.verticalScrollBar().valueChanged.connect(self.on_scrollbar_changed)
        layout.addWidget(self.log_text)

        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.clear_button = QPushButton(self.lang_manager.get_string("log_window.clear_button", "Limpiar Log"))
        self.clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_button)

        self.close_button = QPushButton(self.lang_manager.get_string("log_window.close_button", "Cerrar"))
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        # Timer para actualizar el log en tiempo real
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_log_display)
        self.update_timer.start(1000)  # Actualizar cada segundo

        # Cargar log inicial
        self.update_log_display()

        # Auto-scroll al final inicialmente
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def on_scrollbar_changed(self, value):
        """Detecta cuando el usuario mueve el scrollbar manualmente"""
        scrollbar = self.log_text.verticalScrollBar()
        # Si no está al final, marcar que el usuario está leyendo manualmente
        if value < scrollbar.maximum():
            self.user_scrolling = True
        else:
            self.user_scrolling = False

    def update_log_display(self):
        """Actualiza la visualización del log leyendo el archivo"""
        if not self.log_path or not os.path.exists(self.log_path):
            self.log_text.setHtml(f"<div style=\"word-wrap: break-word; white-space: pre-wrap; font-family: 'Courier New', monospace;\">{self.lang_manager.get_string('log_window.no_log_file', 'Archivo de log no encontrado.')}</div>")
            return

        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Convertir a HTML con colores
            html_content = self.format_log_with_colors(content)
            self.log_text.setHtml(html_content)

            # Auto-scroll al final solo si el usuario no está leyendo manualmente
            if not self.user_scrolling:
                scrollbar = self.log_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            self.log_text.setHtml(f"<div style=\"word-wrap: break-word; white-space: pre-wrap; font-family: 'Courier New', monospace;\">Error leyendo log: {str(e)}</div>")

    def format_log_with_colors(self, content):
        """Formatea el contenido del log con colores HTML según el nivel"""
        lines = content.split('\n')
        formatted_lines = []

        for line in lines:
            if '[ERROR]' in line:
                # Rojo para errores
                formatted_lines.append(f'<span style="color: #ff4444;">{line}</span>')
            elif '[WARNING]' in line:
                # Naranja para warnings
                formatted_lines.append(f'<span style="color: #ff8800;">{line}</span>')
            elif '[API_ERROR]' in line:
                # Rojo oscuro para errores de API
                formatted_lines.append(f'<span style="color: #cc0000;">{line}</span>')
            elif '[INFO]' in line:
                # Azul para info
                formatted_lines.append(f'<span style="color: #4444ff;">{line}</span>')
            elif '[API_REQUEST]' in line or '[API_RESPONSE]' in line:
                # Verde para requests/responses de API
                formatted_lines.append(f'<span style="color: #44aa44;">{line}</span>')
            elif '[TRANSLATION_START]' in line or '[TRANSLATION_COMPLETE]' in line:
                # Púrpura para traducciones
                formatted_lines.append(f'<span style="color: #aa44aa;">{line}</span>')
            elif '[CHECK_RESULT]' in line:
                # Cyan para resultados de check
                formatted_lines.append(f'<span style="color: #44aaaa;">{line}</span>')
            else:
                # Color por defecto (negro o color del sistema)
                formatted_lines.append(line)

        # Unir con saltos de línea HTML y estilos para word-wrap
        html_content = '<div style="word-wrap: break-word; white-space: pre-wrap; font-family: \'Courier New\', monospace;">' + '<br>'.join(formatted_lines) + '</div>'
        return html_content

    def clear_log(self):
        """Limpia el contenido del log"""
        session_logger.clear_log()
        self.user_scrolling = False  # Reset user scrolling state
        self.update_log_display()
        # Mostrar mensaje de confirmación después de un breve delay para que se actualice primero
        QTimer.singleShot(100, lambda: self.show_clear_message())

    def show_clear_message(self):
        """Muestra mensaje de confirmación de limpieza"""
        current_html = self.log_text.toHtml()
        clear_message = self.lang_manager.get_string("log_window.log_cleared", "\n--- Log limpiado ---\n")
        # Agregar el mensaje al final
        if current_html.endswith('</pre>'):
            new_html = current_html[:-6] + f'<br><span style="color: #888888;">{clear_message}</span></pre>'
            self.log_text.setHtml(new_html)

    def closeEvent(self, event):
        """Detiene el timer al cerrar la ventana"""
        self.update_timer.stop()
        super().closeEvent(event)