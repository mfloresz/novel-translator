import re
from typing import Dict, List

from .xml_utils import escape_xml


class TextProcessingOptions:
    """Opciones para el procesamiento de texto"""

    def __init__(self, patterns=None):
        self.patterns = patterns or []


class EpubTextProcessor:
    """Procesador de texto para EPUB.

    Centraliza el procesamiento de markdown usando las reglas “Python” (más completas)
    y expone un único método ``process_chapter`` que aplica:
        1️⃣ Patrones personalizados
        2️⃣ Reglas de markdown (opcionalmente las de Python)
        3️⃣ Conversión a párrafos HTML
    Los métodos antiguos ``process_chapter_content`` y
    ``process_chapter_with_python_rules`` se conservan como wrappers
    para mantener compatibilidad.
    """

    def __init__(self):
        # En el futuro podrían cargarse reglas desde un archivo de configuración.
        self.markdown_rules = []

    def apply_markdown_formatting(self, text: str) -> str:
        """Reglas básicas de markdown (negrita **, cursiva *)."""
        text = re.sub(r"(?<!\*)\*\*([^*\n]+)\*\*(?!\*)", r"<b>\1</b>", text)
        text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
        return text

    def apply_custom_patterns(self, text: str, patterns: List[Dict]) -> str:
        """Aplica patrones personalizados de formateo"""
        processed = text

        for pattern_info in patterns:
            try:
                pattern = pattern_info.get("pattern", "")
                action = pattern_info.get("action", "center")

                # Usar flag multiline para patrones que podrían coincidir con líneas individuales
                regex = re.compile(pattern, re.MULTILINE)

                if action == "center":
                    processed = regex.sub(
                        r'<div style="text-align: center;">\g<0></div>', processed
                    )
                elif action == "separator":
                    processed = regex.sub(
                        r'<hr style="margin: 1em 0; border: none; border-top: 1px solid #ccc;">',
                        processed,
                    )
                elif action == "italic":
                    processed = regex.sub(r"<i>\g<0></i>", processed)

            except re.error as e:
                print(f"Advertencia: Patrón regex inválido '{pattern}': {e}")
                # Continuar procesando con otros patrones incluso si uno falla
                continue

        return processed

    def convert_paragraphs_to_html(self, text: str) -> str:
        """Convierte párrafos de texto plano a HTML, manteniendo mejor los saltos de línea"""
        # Verificar si el texto ya contiene etiquetas HTML y evitar doble procesamiento
        if "<p>" in text or "</p>" in text:
            # Si ya contiene etiquetas HTML, retornar sin procesar para evitar doble envoltura
            # Pero eliminar posibles etiquetas <p> innecesarias que estén como texto
            if text.startswith("<p>") and text.endswith("</p>"):
                return text  # Ya está formateado correctamente
            # Si contiene tags <p> como texto sin envolver todo, dejarlo tal cual
            return text

        # Separar por dobles saltos de línea (nuevos párrafos)
        return text.split("\n\n") if "\n\n" in text else [text]

    def _process_paragraphs(self, paragraphs: List[str]) -> str:
        """Procesa una lista de párrafos y los convierte a HTML"""
        html_paragraphs = []

        for paragraph in paragraphs:
            trimmed = paragraph.strip()
            if not trimmed:
                continue

            # Separar las líneas dentro del párrafo
            lines = [line.strip() for line in paragraph.split("\n") if line.strip()]

            # Juntar las líneas con <br/> para mantener los saltos de línea
            paragraph_text = "<br/>".join(lines)

            html_paragraphs.append(f"<p>{paragraph_text}</p>")

        return "\n".join(html_paragraphs)

    # ----------------------------------------------------------------------
    # API pública unificada
    # ----------------------------------------------------------------------
    def process_chapter(
        self,
        content: str,
        patterns: List[Dict] | None = None,
        use_python_rules: bool = False,
    ) -> str:
        """
        Procesa el contenido de un capítulo completo.

        Parámetros
        ----------
        content: str
            Texto bruto del capítulo.
        patterns: list[dict] | None
            Patrones personalizados (centrado, separador, itálica, etc.).
        use_python_rules: bool
            Si ``True`` se usan las reglas de markdown de Python
            (incluye subrayado ``_texto_``). Si ``False`` se usan las
            reglas básicas (solo ``**`` y ``*``).

        Retorna
        -------
        str
            HTML listo para insertarse en el XHTML del capítulo.
        """
        if patterns is None:
            patterns = []

        # 1️⃣ Patrones personalizados
        txt = self.apply_custom_patterns(content, patterns)

        # 2️⃣ Reglas de markdown
        txt = self._apply_markdown_rules(txt, use_python_rules)

        # 3️⃣ Conversión a párrafos HTML
        paragraphs = self.convert_paragraphs_to_html(txt)
        return self._process_paragraphs(paragraphs)

    def escape_xml(self, unsafe: str) -> str:
        """Escapa caracteres XML"""
        return escape_xml(unsafe)

    def clean_chapter_title(self, title: str) -> str:
        """Limpia el título del capítulo removiendo formato Markdown básico"""
        # Remover ** al inicio y fin si están presentes (negrita)
        return re.sub(r"^\*\*(.*)\*\*$", r"\1", title).strip()

    def apply_python_markdown_rules(self, text: str) -> str:
        """Reglas de markdown “Python” (negrita **, cursiva *, subrayado _)."""
        text = re.sub(r"(?<!\*)\*\*([^*\n]+)\*\*(?!\*)", r"<b>\1</b>", text)
        text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
        text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"<i>\1</i>", text)
        return text

    def _apply_markdown_rules(self, text: str, use_python_rules: bool) -> str:
        """Selecciona el conjunto de reglas de markdown a aplicar."""
        return (
            self.apply_python_markdown_rules(text)
            if use_python_rules
            else self.apply_markdown_formatting(text)
        )

    # ----------------------------------------------------------------------
    # Compatibilidad (wrappers)
    # ----------------------------------------------------------------------
    def process_chapter_content(self, content: str, patterns: List[Dict] = None) -> str:
        """Wrapper que mantiene el comportamiento anterior (reglas básicas)."""
        return self.process_chapter(content, patterns, use_python_rules=False)

    def process_chapter_with_python_rules(
        self, content: str, patterns: List[Dict] = None
    ) -> str:
        """Wrapper que mantiene el comportamiento anterior (reglas Python)."""
        return self.process_chapter(content, patterns, use_python_rules=True)
