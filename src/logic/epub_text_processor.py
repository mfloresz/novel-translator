import re
from typing import List, Dict
from .xml_utils import escape_xml

class TextProcessingOptions:
    """Opciones para el procesamiento de texto"""
    def __init__(self, patterns=None):
        self.patterns = patterns or []

class EpubTextProcessor:
    """Procesador de texto para EPUB replicando la funcionalidad del proyecto Vue"""
    
    def __init__(self):
        # Reglas de markdown básicas (ahora se cargan desde config/markdown_rules.json)
        self.markdown_rules = []

    def apply_markdown_formatting(self, text: str) -> str:
        """Aplica formateo markdown básico al texto"""
        formatted = text

        # Reglas de markdown básicas mejoradas para evitar conflictos
        # Negrita: **texto** (no procesar si hay más de 2 asteriscos seguidos)
        formatted = re.sub(r'(?<!\*)\*\*([^*\n]+)\*\*(?!\*)', r'<b>\1</b>', formatted)
        
        # Cursiva: *texto* (no procesar si hay más de 1 asterisco seguido o si está en una línea de ***)
        formatted = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', formatted)

        return formatted

    def apply_custom_patterns(self, text: str, patterns: List[Dict]) -> str:
        """Aplica patrones personalizados de formateo"""
        processed = text
        
        for pattern_info in patterns:
            try:
                pattern = pattern_info.get('pattern', '')
                action = pattern_info.get('action', 'center')
                
                # Usar flag multiline para patrones que podrían coincidir con líneas individuales
                regex = re.compile(pattern, re.MULTILINE)
                
                if action == 'center':
                    processed = regex.sub(r'<div style="text-align: center;">\g<0></div>', processed)
                elif action == 'separator':
                    processed = regex.sub(r'<hr style="margin: 1em 0; border: none; border-top: 1px solid #ccc;">', processed)
                elif action == 'italic':
                    processed = regex.sub(r'<i>\g<0></i>', processed)
                    
            except re.error as e:
                print(f"Advertencia: Patrón regex inválido '{pattern}': {e}")
                # Continuar procesando con otros patrones incluso si uno falla
                continue
        
        return processed

    def convert_paragraphs_to_html(self, text: str) -> str:
        """Convierte párrafos de texto plano a HTML, manteniendo mejor los saltos de línea"""
        # Verificar si el texto ya contiene etiquetas HTML y evitar doble procesamiento
        if '<p>' in text or '</p>' in text:
            # Si ya contiene etiquetas HTML, retornar sin procesar para evitar doble envoltura
            # Pero eliminar posibles etiquetas <p> innecesarias que estén como texto
            if text.startswith('<p>') and text.endswith('</p>'):
                return text  # Ya está formateado correctamente
            # Si contiene tags <p> como texto sin envolver todo, dejarlo tal cual
            return text
        
        # Separar por dobles saltos de línea (nuevos párrafos)
        return text.split('\n\n') if '\n\n' in text else [text]

    def _process_paragraphs(self, paragraphs: List[str]) -> str:
        """Procesa una lista de párrafos y los convierte a HTML"""
        html_paragraphs = []
        
        for paragraph in paragraphs:
            trimmed = paragraph.strip()
            if not trimmed:
                continue
            
            # Separar las líneas dentro del párrafo
            lines = [line.strip() for line in paragraph.split('\n') if line.strip()]
            
            # Juntar las líneas con <br/> para mantener los saltos de línea
            paragraph_text = '<br/>'.join(lines)
            
            html_paragraphs.append(f'<p>{paragraph_text}</p>')
        
        return '\n'.join(html_paragraphs)

    def process_chapter_content(self, content: str, patterns: List[Dict] = None) -> str:
        """Procesa el contenido de un capítulo completo"""
        if patterns is None:
            patterns = []
        
        # Aplicar patrones personalizados primero (para que líneas como *** se manejen antes)
        processed_content = content
        processed_content = self.apply_custom_patterns(processed_content, patterns)
        
        # Luego aplicar formateo markdown básico
        processed_content = self.apply_markdown_formatting(processed_content)
        
        # Convertir a HTML con párrafos
        paragraphs_data = self.convert_paragraphs_to_html(processed_content)
        
        if isinstance(paragraphs_data, list):
            html_content = self._process_paragraphs(paragraphs_data)
        else:
            # Si no hay dobles saltos de línea, procesar como un solo párrafo
            html_content = self._process_paragraphs([paragraphs_data])
        
        return html_content

    def escape_xml(self, unsafe: str) -> str:
        """Escapa caracteres XML"""
        return escape_xml(unsafe)

    def clean_chapter_title(self, title: str) -> str:
        """Limpia el título del capítulo removiendo formato Markdown básico"""
        # Remover ** al inicio y fin si están presentes (negrita)
        return re.sub(r'^\*\*(.*)\*\*$', r'\1', title).strip()

    def apply_python_markdown_rules(self, text: str) -> str:
        """
        Aplica las reglas de markdown existentes en Python (del config/markdown_rules.json)
        NO replica las reglas defectuosas de Vue, usa las existentes de Python
        """
        # Reglas de markdown básicas mejoradas para evitar conflictos
        # Negrita: **texto** (no procesar si hay más de 2 asteriscos seguidos)
        text = re.sub(r'(?<!\*)\*\*([^*\n]+)\*\*(?!\*)', r'<b>\1</b>', text)
        
        # Cursiva: *texto* (no procesar si hay más de 1 asterisco seguido o si está en una línea de ***)
        text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', text)

        return text

    def process_chapter_with_python_rules(self, content: str, patterns: List[Dict] = None) -> str:
        """
        Procesa el contenido usando las reglas de markdown de Python (no las de Vue)
        para evitar los problemas mencionados por el usuario
        """
        if patterns is None:
            patterns = []
        
        # Primero aplicar patrones personalizados
        processed_content = self.apply_custom_patterns(content, patterns)
        
        # Luego aplicar las reglas de markdown de Python (no las de Vue)
        processed_content = self.apply_python_markdown_rules(processed_content)
        
        # Convertir a HTML con párrafos
        paragraphs_data = self.convert_paragraphs_to_html(processed_content)
        
        if isinstance(paragraphs_data, list):
            html_content = self._process_paragraphs(paragraphs_data)
        else:
            html_content = self._process_paragraphs([paragraphs_data])
        
        return html_content