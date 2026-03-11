import time
import json
import os
import re
import difflib
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from typing import Optional, Dict, List, Callable
from pathlib import Path
from src.logic import translator_req
from src.logic.session_logger import session_logger

class TranslatorLogic:
    def __init__(self, segment_size=None):
        """Inicializa el traductor con los idiomas soportados"""
        # Cargar mapeo de idiomas desde languages.json
        languages_path = Path(__file__).parent.parent / 'config' / 'languages.json'
        try:
            with open(languages_path, 'r', encoding='utf-8') as f:
                self.lang_codes = json.load(f)
        except Exception as e:
            print(f"Error cargando languages.json: {e}")
            # Fallback a valores hardcodeados si no se puede cargar el archivo
            self.lang_codes = {
                'auto': 'Detectar automáticamente',
                'Español (MX)': 'Spanish (México)',
                'Inglés': 'English'
            }

        # Cargar configuración de modelos
        models_path = Path(__file__).parent.parent / 'config' / 'translation_models.json'
        with open(models_path, 'r') as f:
            self.models_config = json.load(f)

        self.segment_size = segment_size  # Tamaño objetivo para cada segmento
        self.temp_prompts_path = None  # Ruta al directorio de prompts temporales

        # Cargar variables de entorno desde .env
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)

    def update_temp_prompts_path(self, path: Path):
        """Actualiza la ruta al directorio de prompts temporales"""
        self.temp_prompts_path = path
    def _handle_terminology_section(self, prompt_template: str, custom_terms: str) -> str:
        """
        Maneja la sección de terminología en los prompts.
        Si hay términos personalizados, los formatea y reemplaza {terminology_reference}.
        Si no hay términos, elimina toda la sección <terminology_reference>...</terminology_reference>.

        Args:
            prompt_template (str): Template del prompt
            custom_terms (str): Términos personalizados

        Returns:
            str: Prompt modificado
        """
        if custom_terms.strip():
            # Formatear los términos personalizados
            terms = custom_terms.strip().split('\n')
            terms = [
                line if line.strip().startswith('- ') else f'- {line.strip()}'
                for line in terms
                if line.strip()
            ]
            formatted_terms = '\n'.join(terms)
            # Reemplazar la etiqueta {terminology_reference} con los términos formateados
            return prompt_template.replace("{terminology_reference}", formatted_terms)
        else:
            # Si no hay términos personalizados, eliminar toda la sección <terminology_reference>
            return re.sub(r'<terminology_reference>.*?</terminology_reference>', '', prompt_template, flags=re.DOTALL)

    def _load_prompt(self, prompt_name: str, source_lang: str, target_lang: str) -> str:
        """
        Carga una plantilla de prompt desde un archivo, buscando en el siguiente orden:
        1. Directorio de prompts temporales de la sesión.
        2. Directorio específico del par de idiomas en la configuración.
        3. Directorio de prompts base en la configuración.

        Args:
            prompt_name (str): Nombre del archivo de prompt (ej: "translation.txt").
            source_lang (str): Código del idioma de origen.
            target_lang (str): Código del idioma de destino.

        Returns:
            str: Contenido del prompt.

        Raises:
            FileNotFoundError: Si no se encuentra el archivo de prompt en ninguna de las ubicaciones.
        """
        lang_pair_dir_name = f"{source_lang}_{target_lang}"

        # 1. Buscar en el directorio de prompts temporales
        if self.temp_prompts_path:
            temp_prompt_path = self.temp_prompts_path / lang_pair_dir_name / prompt_name
            if temp_prompt_path.exists():
                with open(temp_prompt_path, 'r', encoding='utf-8') as file:
                    return file.read()

        # 2. Si no se encuentra, buscar en el directorio específico del par de idiomas
        prompt_dir = Path(__file__).parent.parent / 'config' / 'prompts' / lang_pair_dir_name
        prompt_path = prompt_dir / prompt_name
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read()

        # 3. Si no existe, intentar en prompts-base
        base_prompt_dir = Path(__file__).parent.parent / 'config' / 'prompts' / 'prompts-base'
        base_prompt_path = base_prompt_dir / prompt_name
        if base_prompt_path.exists():
            with open(base_prompt_path, 'r', encoding='utf-8') as file:
                return file.read()

        # Si no se encuentra en ninguno de los dos lugares, lanzar error
        raise FileNotFoundError(f"No se pudo encontrar el prompt '{prompt_name}'")


    def _segment_text(self, text: str) -> List[str]:
        """
        Segmenta el texto en partes manejables basadas en un tamaño objetivo,
        respetando oraciones y párrafos usando búsqueda hacia atrás inteligente.

        Args:
            text (str): Texto completo a segmentar

        Returns:
            List[str]: Lista de segmentos de texto con cortes naturales
        """
        if self.segment_size is None:
            return [text]

        segments = []
        current_position = 0

        # Normalizar saltos de línea
        text = text.replace('\r\n', '\n')

        while current_position < len(text):
            # Calcular posición objetivo (guía, no corte fijo)
            target_position = min(current_position + self.segment_size, len(text))

            # Buscar punto de corte óptimo hacia atrás desde el objetivo
            cut_position = self._find_optimal_cut_point(text, target_position)

            # Validar que el corte sea razonable
            if cut_position <= current_position:
                # Fallback: cortar por palabras completas si no hay corte natural
                cut_position = self._find_word_boundary(text, target_position)

            segment_text = text[current_position:cut_position]
            if segment_text:
                segments.append(segment_text)

            current_position = cut_position

        return segments

    def _find_optimal_cut_point(self, text: str, target_position: int) -> int:
        """
        Busca hacia atrás desde la posición objetivo para encontrar
        el mejor punto de corte natural respetando oraciones completas.

        Args:
            text (str): Texto completo
            target_position (int): Posición objetivo desde donde buscar hacia atrás

        Returns:
            int: Posición del mejor punto de corte encontrado
        """
        # Si estamos cerca del final, devolver todo el texto restante
        if target_position >= len(text) - 100:
            return len(text)

        # Definir jerarquía de puntos de corte naturales (ordenados por prioridad)
        CUT_POINTS = [
            ("\n\n", 10.0),      # Párrafo doble - corte ideal
            (".\n", 9.5),        # Punto al final de línea
            ("?\n", 9.5),        # Interrogación al final de línea
            ("!\n", 9.5),        # Exclamación al final de línea
            (". ", 9.0),         # Punto con espacio
            ("? ", 9.0),         # Interrogación con espacio
            ("! ", 9.0),         # Exclamación con espacio
            ("\n", 7.0),         # Nueva línea simple
            (".", 6.0),          # Punto sin espacio (menos ideal)
            ("?", 6.0),          # Interrogación sin espacio
            ("!", 6.0),          # Exclamación sin espacio
            ("; ", 4.0),         # Punto y coma
            (": ", 3.0),         # Dos puntos
            (", ", 2.0),         # Coma
        ]

        best_position = target_position
        best_score = 0
        search_start = max(0, target_position - 500)  # Buscar hasta 500 chars atrás

        # Buscar hacia atrás desde la posición objetivo
        for pos in range(target_position, search_start, -1):
            for cut_pattern, base_priority in CUT_POINTS:
                if text[pos:pos + len(cut_pattern)] == cut_pattern:
                    # Calcular puntuación basada en cercanía al objetivo
                    distance = abs(target_position - pos)
                    # Más cerca = mejor puntuación
                    proximity_bonus = 1 - (distance / 500)
                    score = base_priority * proximity_bonus

                    if score > best_score:
                        best_score = score
                        best_position = pos + len(cut_pattern)

        return best_position

    def _find_word_boundary(self, text: str, target_position: int) -> int:
        """
        Busca el límite de palabra más cercano hacia atrás desde la posición objetivo.
        Método fallback cuando no se encuentran puntos de corte naturales.

        Args:
            text (str): Texto completo
            target_position (int): Posición objetivo

        Returns:
            int: Posición del límite de palabra encontrado
        """
        # Buscar hacia atrás hasta encontrar un espacio
        pos = target_position
        while pos > 0 and not text[pos].isspace():
            pos -= 1

        # Si encontramos un espacio, devolver esa posición
        if pos > 0:
            return pos

        # Si no encontramos espacio (texto muy largo sin espacios), cortar en objetivo
        return target_position

    def _validate_segment_integrity(self, segments: List[str], original_text: str) -> Dict:
        """
        Valida la integridad de los segmentos creados.

        Args:
            segments (List[str]): Lista de segmentos creados
            original_text (str): Texto original para comparación

        Returns:
            Dict: Reporte de validación con métricas y problemas encontrados
        """
        validation_report = {
            'total_segments': len(segments),
            'natural_cuts': 0,
            'word_boundary_cuts': 0,
            'forced_cuts': 0,
            'issues': [],
            'warnings': []
        }

        # Verificar cada segmento
        for i, segment in enumerate(segments):
            if not segment.strip():
                validation_report['issues'].append(f"Segmento {i+1}: vacío")
                continue

            # Verificar tipo de corte (si termina naturalmente)
            last_chars = segment[-10:] if len(segment) >= 10 else segment

            if last_chars.endswith(('. ', '? ', '! ', '.\n', '?\n', '!\n', '\n\n')):
                validation_report['natural_cuts'] += 1
            elif last_chars.rstrip().endswith(('.', '?', '!')):
                validation_report['word_boundary_cuts'] += 1
            else:
                validation_report['forced_cuts'] += 1
                validation_report['warnings'].append(
                    f"Segmento {i+1}: corte no natural en '{last_chars}'"
                )

        # Calcular estadísticas
        total_cuts = validation_report['natural_cuts'] + validation_report['word_boundary_cuts'] + validation_report['forced_cuts']
        if total_cuts > 0:
            validation_report['natural_cut_percentage'] = (validation_report['natural_cuts'] / total_cuts) * 100
        else:
            validation_report['natural_cut_percentage'] = 0

        return validation_report

    def _verify_segmentation_integrity(self, segments: List[str], original_text: str) -> bool:
        """
        Verifica que la segmentación no haya causado pérdida de contenido.

        Args:
            segments (List[str]): Lista de segmentos creados
            original_text (str): Texto original para comparación

        Returns:
            bool: True si la reconstrucción es idéntica al original, False si hay diferencias
        """
        # Reconstruir el texto uniendo los segmentos sin separadores
        reconstructed_text = ''.join(segments)

        # Comparar exactamente con el texto original
        if reconstructed_text == original_text:
            return True
        else:
            # Loggear detalles del error
            original_len = len(original_text)
            reconstructed_len = len(reconstructed_text)

            session_logger.log_error(
                f"Segmentación corrupta: longitud original {original_len}, reconstruida {reconstructed_len}"
            )

            # Mostrar primeras diferencias si son pequeñas
            if abs(original_len - reconstructed_len) <= 100:
                min_len = min(original_len, reconstructed_len)
                for i in range(min_len):
                    if original_text[i] != reconstructed_text[i]:
                        session_logger.log_error(
                            f"Primera diferencia en posición {i}: "
                            f"original='{original_text[i]}' vs reconstruido='{reconstructed_text[i]}'"
                        )
                        break
            else:
                session_logger.log_error("Diferencia demasiado grande para mostrar detalles")

            return False

    def _build_check_prompt(self, source_lang: str, target_lang: str,
                            original_text: str, translated_text: str,
                            custom_terms: str = "") -> Dict:
        """
        Construye el prompt para comprobar la calidad de la traducción.
        
        Args:
            source_lang (str): Idioma original
            target_lang (str): Idioma destino
            original_text (str): Texto original completo
            translated_text (str): Texto traducido completo
            custom_terms (str): Términos personalizados para la traducción

        Returns:
            Dict: Prompt estructurado con roles system y user
        """
        check_prompt_template = self._load_prompt("check.txt", source_lang, target_lang)
        prompt_content = self._handle_terminology_section(check_prompt_template, custom_terms)
        prompt_content = prompt_content.replace("{source_lang}", source_lang)
        prompt_content = prompt_content.replace("{target_lang}", target_lang)
        
        # Crear estructura con roles
        messages = [
            {"role": "system", "content": prompt_content},
            {"role": "user", "content": f"**Text 1 (Original - {source_lang}):**\n{original_text.strip()}\n\n**Text 2 (Translation - {target_lang}):**\n{translated_text.strip()}"}
        ]
        
        return {"messages": messages}

    def _build_refine_prompt(self, source_lang: str, target_lang: str,
                              source_text: str, translated_text: str,
                              custom_terms: str = "", prompt_name: str = "refine.txt") -> Dict:
        """
        Construye el prompt para refinar la traducción.

        Args:
            source_lang (str): Idioma original
            target_lang (str): Idioma destino
            source_text (str): Texto original
            translated_text (str): Texto traducido a refinar
            custom_terms (str): Términos personalizados para la traducción
            prompt_name (str): Nombre del archivo de prompt a usar

        Returns:
            Dict: Prompt estructurado con roles system y user
        """
        refine_prompt_template = self._load_prompt(prompt_name, source_lang, target_lang)
        prompt_content = self._handle_terminology_section(refine_prompt_template, custom_terms)
        prompt_content = prompt_content.replace("{source_lang}", source_lang)
        prompt_content = prompt_content.replace("{target_lang}", target_lang)

        # Preparar el contenido del texto traducido
        # Formato consistente para todos los prompts
        user_content = f"Original text ({source_lang}):\n{source_text.strip()}\n\nPreliminary translation ({target_lang}):\n{translated_text.strip()}"

        # Crear estructura con roles
        messages = [
            {"role": "system", "content": prompt_content},
            {"role": "user", "content": user_content}
        ]

        return {"messages": messages}

    def _apply_refinement_changes(self, translated_text: str, xml_response: str) -> str:
        """
        Aplica los cambios de refinamiento desde la respuesta XML al texto traducido.
        Busca y reemplaza cadenas exactas en lugar de trabajar con líneas numeradas.

        Args:
            translated_text (str): Texto traducido original
            xml_response (str): Respuesta XML con instrucciones de cambios

        Returns:
            str: Texto refinado con cambios aplicados
        """
        try:
            # Limpiar el XML de posibles errores comunes
            cleaned_xml = self._clean_xml_response(xml_response)

            # Parsear el XML
            root = ET.fromstring(cleaned_xml)

            # Lista de cambios a aplicar
            changes = []
            for change_elem in root.findall('.//change'):
                change_type = change_elem.get('type')

                if change_type == 'delete':
                    original = change_elem.find('original')
                    if original is not None and original.text:
                        original_text = original.text.strip()
                        changes.append(('delete', original_text, None, None))
                elif change_type == 'replace':
                    original = change_elem.find('original')
                    replacement = change_elem.find('replacement')
                    if original is not None and original.text and replacement is not None:
                        original_text = original.text.strip()
                        replacement_text = replacement.text.strip()
                        changes.append(('replace', original_text, replacement_text, None))
                elif change_type == 'add':
                    position = change_elem.find('position')
                    replacement = change_elem.find('replacement')
                    if position is not None and replacement is not None and replacement.text:
                        position_text = position.text.strip()
                        replacement_text = replacement.text.strip()
                        changes.append(('add', position_text, replacement_text, None))

            # Aplicar cambios en orden inverso para no afectar posiciones
            applied_changes = 0
            result_text = translated_text

            # Procesar cambios de eliminación y reemplazo primero
            for change_type, original, replacement, _ in reversed(changes):
                try:
                    if change_type == 'delete':
                        if original and original in result_text:
                            result_text = result_text.replace(original, '', 1)  # Reemplazar solo la primera ocurrencia
                            applied_changes += 1
                            session_logger.log_info(f"Eliminado: '{original}'")
                        else:
                            session_logger.log_warning(f"No se pudo eliminar: '{original}' no encontrado o vacío")
                    elif change_type == 'replace':
                        if original and replacement and original in result_text:
                            result_text = result_text.replace(original, replacement, 1)  # Reemplazar solo la primera ocurrencia
                            applied_changes += 1
                            session_logger.log_info(f"Reemplazado: '{original}' → '{replacement}'")
                        else:
                            session_logger.log_warning(f"No se pudo reemplazar: '{original}' o '{replacement}' no encontrado/vacío")
                except Exception as e:
                    session_logger.log_error(f"Error aplicando cambio {change_type}: {e}")

            # Procesar adiciones después
            for change_type, position, replacement, _ in changes:
                try:
                    if change_type == 'add':
                        if position and replacement and position in result_text:
                            # Insertar después de la posición de referencia
                            pos = result_text.find(position) + len(position)
                            result_text = result_text[:pos] + replacement + result_text[pos:]
                            applied_changes += 1
                            session_logger.log_info(f"Agregado después de: '{position}' → '{replacement}'")
                        else:
                            session_logger.log_warning(f"No se pudo agregar: posición '{position}' no encontrada o datos incompletos")
                except Exception as e:
                    session_logger.log_error(f"Error aplicando adición: {e}")

            session_logger.log_info(f"Cambios aplicados exitosamente: {applied_changes}")
            return result_text

        except ET.ParseError as e:
            session_logger.log_error(f"Error parseando respuesta XML: {e}")
            session_logger.log_error(f"XML recibido: {xml_response[:500]}...")
            return translated_text
        except Exception as e:
            session_logger.log_error(f"Error aplicando cambios de refinamiento: {e}")
            return translated_text

    def _clean_xml_response(self, xml_response: str) -> str:
        """
        Limpia la respuesta XML de errores comunes que pueden cometer los modelos.

        Args:
            xml_response (str): Respuesta XML cruda

        Returns:
            str: XML limpiado
        """
        # Eliminar cualquier texto antes de <refinement_instructions>
        start_tag = "<refinement_instructions>"
        if start_tag in xml_response:
            xml_response = xml_response[xml_response.find(start_tag):]

        # Eliminar cualquier texto después de </refinement_instructions>
        end_tag = "</refinement_instructions>"
        if end_tag in xml_response:
            xml_response = xml_response[:xml_response.find(end_tag) + len(end_tag)]

        # Corregir tags mal cerrados comunes
        # Ejemplo: <replacement>texto</original> -> <replacement>texto</replacement>
        import re
        # Buscar patrones donde un tag de cierre no coincide con el de apertura
        xml_response = re.sub(r'<(\w+)[^>]*>([^<]*)</(\w+)>', lambda m: f'<{m.group(1)}>{m.group(2)}</{m.group(1)}>' if m.group(1) != m.group(3) else m.group(0), xml_response)

        return xml_response

    def _find_best_match(self, text: str, search_string: str, threshold: float = 0.75) -> tuple:
        """
        Busca la mejor coincidencia de search_string dentro de text usando 3 niveles de tolerancia.
        Version optimizada para mitigar cuellos de botella de CPU.
        """
        if not search_string or not text:
            return None

        search_string = search_string.strip()
      
        # Nivel 1: Busqueda exacta (Mas rapida)
        exact_pos = text.find(search_string)
        if exact_pos != -1:
            return (exact_pos, exact_pos + len(search_string), 1.0)

        # Nivel 2: Busqueda normalizada por espacios/saltos de linea
        try:
            parts = search_string.split()
            if parts:
                escaped_parts = [re.escape(p) for p in parts]
                space_tolerant_pattern = r'\s+'.join(escaped_parts)
              
                match = re.search(space_tolerant_pattern, text)
                if match:
                    return (match.start(), match.end(), 0.95)
        except Exception:
            pass

        # Nivel 3: Busqueda difusa anclada (Altamente optimizada)
        # Identificar las palabras mas largas para usarlas como anclas de busqueda
        words = [w for w in search_string.split() if len(w) > 4]
        if not words:
            words = search_string.split()
          
        anchor_words = sorted(words, key=len, reverse=True)[:3]
        candidate_indices = set()
      
        # Encontrar indices donde aparecen las palabras ancla
        for word in anchor_words:
            idx = 0
            while True:
                idx = text.find(word, idx)
                if idx == -1:
                    break
                candidate_indices.add(idx)
                idx += 1
              
        search_len = len(search_string)
        best_ratio = 0.0
        best_start = 0
        best_end = 0
      
        # Si no hay anclas, iterar por bloques de texto (fallback seguro)
        if not candidate_indices:
            candidate_indices = set(range(0, len(text), search_len // 2))

        # Evaluar ventanas unicamente alrededor de los indices candidatos
        min_window = max(1, int(search_len * 0.8))
        max_window = min(len(text), int(search_len * 1.2))
      
        for base_idx in candidate_indices:
            # Ampliar el rango de busqueda alrededor del ancla
            start_range = max(0, base_idx - search_len)
            end_range = min(len(text), base_idx + search_len)
          
            for i in range(start_range, end_range, max(1, search_len // 10)):
                for window_size in (min_window, search_len, max_window):
                    if i + window_size > len(text):
                        continue
                      
                    candidate = text[i:i + window_size]
                    ratio = difflib.SequenceMatcher(None, search_string, candidate).ratio()
                  
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_start = i
                        best_end = i + window_size
                  
                    if best_ratio > 0.95:
                        return (best_start, best_end, best_ratio)

        if best_ratio >= threshold:
            return (best_start, best_end, best_ratio)
      
        return None


    def _apply_tool_refinement(self, translated_text: str, tool_response: str) -> str:
        """
        Aplica los cambios de refinamiento desde tool calls al texto traducido
        utilizando búsqueda difusa (fuzzy matching) para tolerar variaciones del LLM.
        """
        try:
            response_data = json.loads(tool_response)

            if "text_response" in response_data:
                session_logger.log_warning(
                    "El modelo respondió con texto en lugar de usar tools. "
                    "Retornando texto original sin cambios."
                )
                return translated_text

            tool_calls = response_data.get("tool_calls", [])

            if not tool_calls:
                session_logger.log_info("No se recibieron tool calls - sin cambios necesarios")
                return translated_text

            result_text = translated_text
            applied = 0
            failed = 0

            for call in tool_calls:
                name = call.get("name")
                args = call.get("arguments", {})

                try:
                    if name == "no_changes_needed":
                        confidence = args.get("confidence", "unknown")
                        session_logger.log_info(
                            f"Modelo indica que no se necesitan cambios (confianza: {confidence})"
                        )
                        return result_text

                    elif name == "replace_text":
                        original = args.get("original", "")
                        replacement = args.get("replacement", "")
                        reason = args.get("reason", "")

                        match = self._find_best_match(result_text, original)
                        
                        if match:
                            start, end, ratio = match
                            matched_text = result_text[start:end]
                            # Aplicar reemplazo mediante slicing
                            result_text = result_text[:start] + replacement + result_text[end:]
                            applied += 1
                            
                            match_type = "Exact" if ratio == 1.0 else f"Fuzzy ({ratio:.2f})"
                            session_logger.log_info(
                                f"[{match_type} replace] '{matched_text[:40]}...' → '{replacement[:40]}...' | Razón: {reason}"
                            )
                        else:
                            failed += 1
                            session_logger.log_warning(f"[replace] No encontrado en texto: '{original[:80]}...'")

                    elif name == "delete_text":
                        original = args.get("original", "")
                        reason = args.get("reason", "")

                        match = self._find_best_match(result_text, original)
                        
                        if match:
                            start, end, ratio = match
                            matched_text = result_text[start:end]
                            # Aplicar eliminación mediante slicing
                            result_text = result_text[:start] + result_text[end:]
                            applied += 1
                            
                            match_type = "Exact" if ratio == 1.0 else f"Fuzzy ({ratio:.2f})"
                            session_logger.log_info(
                                f"[{match_type} delete] Eliminado: '{matched_text[:40]}...' | Razón: {reason}"
                            )
                        else:
                            failed += 1
                            session_logger.log_warning(f"[delete] No encontrado en texto: '{original[:80]}...'")

                    elif name == "insert_text":
                        anchor = args.get("anchor", "")
                        content = args.get("content", "")
                        reason = args.get("reason", "")

                        match = self._find_best_match(result_text, anchor)
                        
                        if match and content:
                            start, end, ratio = match
                            # Insertar después del ancla
                            result_text = result_text[:end] + content + result_text[end:]
                            applied += 1
                            
                            match_type = "Exact" if ratio == 1.0 else f"Fuzzy ({ratio:.2f})"
                            session_logger.log_info(
                                f"[{match_type} insert] Después de '{anchor[:40]}...' → '{content[:40]}...' | Razón: {reason}"
                            )
                        else:
                            failed += 1
                            session_logger.log_warning(f"[insert] Anchor no encontrado: '{anchor[:80]}...'")

                    else:
                        session_logger.log_warning(f"Tool desconocido: {name}")

                except Exception as e:
                    failed += 1
                    session_logger.log_error(f"Error aplicando tool call '{name}': {e}")

            session_logger.log_info(
                f"Refinamiento por tools completado: {applied} aplicados, {failed} fallidos de {len(tool_calls)} total"
            )
            return result_text

        except json.JSONDecodeError as e:
            session_logger.log_error(f"Error parseando respuesta de tools: {e}")
            return translated_text
        except Exception as e:
            session_logger.log_error(f"Error general aplicando refinamiento por tools: {e}")
            return translated_text

    def _get_api_key_for_provider(self, provider: str) -> str:
        """
        Obtiene la API key para un proveedor específico, priorizando temporales y luego .env.

        Args:
            provider (str): Identificador del proveedor

        Returns:
            str: API key correspondiente
        """
        # Primero intentar obtener de variables temporales (no implementadas aquí, fallback a env)
        env_var_name = f"{provider.upper()}_API_KEY"
        return os.getenv(env_var_name, "")

    def _check_translation(self, original_text: str, translated_text: str,
                             source_lang: str, target_lang: str,
                             main_api_key: str, check_provider: str, check_model: str,
                             custom_terms: str = "", temp_api_keys: dict = None, retry_on_failure: bool = True, timeout: int = 120,
                             stop_callback: Optional[Callable[[], bool]] = None) -> bool:
        """
        Comprueba la calidad de la traducción usando la API.

        Retorna True si el modelo responde "Yes", False si "No" o error.

        Args:
            original_text (str): Texto original completo
            translated_text (str): Texto traducido completo
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            main_api_key (str): API key principal (no usado si check_provider diferente)
            check_provider (str): Proveedor para comprobación
            check_model (str): Modelo para comprobación
            temp_api_keys (dict): Diccionario de API keys temporales (opcional)
            retry_on_failure (bool): Si True, reintenta una vez en caso de fallo

        Returns:
            bool: Resultado de la comprobación
        """
        # Obtener API key específica para el proveedor de comprobación
        if temp_api_keys and check_provider in temp_api_keys:
            api_key = temp_api_keys[check_provider]
        else:
            api_key = self._get_api_key_for_provider(check_provider)

        if not api_key:
            session_logger.log_error(f"No se encontró API key para el proveedor de comprobación: {check_provider}")
            return False

        session_logger.log_info(f"Iniciando comprobación con Proveedor: {check_provider}, Modelo: {check_model}")
        prompt = self._build_check_prompt(source_lang, target_lang, original_text, translated_text, custom_terms)

        provider_config = self.models_config.get(check_provider)
        if not provider_config:
            print(f"Proveedor no soportado para comprobación: {check_provider}")
            return False
        model_config = provider_config['models'].get(check_model)
        if not model_config:
            print(f"Modelo no soportado para comprobación: {check_model}")
            return False

        def query_model():
            return translator_req.translate_segment(
                check_provider,
                "",  # texto ya incluido en prompt, pasar vacío para evitar doble agregado
                api_key,
                model_config,
                prompt,
                self.models_config,
                timeout
            )

        def _parse_check_response(response: str) -> (bool, Optional[str]):
            """
            Parses the check response in XML format.
            Extracts the result (Yes/No) and comments separately.
            """
            import re
            
            # Try to extract XML response
            xml_match = re.search(r'<response>.*?</response>', response, re.DOTALL)
            
            if xml_match:
                xml_content = xml_match.group(0)  # Use group(0) for the full match
                
                # Extract result
                result_match = re.search(r'<result>(.*?)</result>', xml_content, re.DOTALL)
                check_result = result_match.group(1).strip().lower() if result_match else None
                
                # Extract comments
                comments_match = re.search(r'<comments>(.*?)</comments>', xml_content, re.DOTALL)
                comments = comments_match.group(1).strip() if comments_match else ""
                
                if check_result == "yes":
                    # Log comments if present
                    if comments:
                        session_logger.log_info(f"Check comments: {comments}")
                    return True, None
                elif check_result == "no":
                    return False, comments if comments else "Respuesta No sin causa especificada"
                else:
                    return False, f"Respuesta inesperada: {response}"
            else:
                # Fallback to old format for backward compatibility
                response_lines = response.strip().split('\n')
                check_result = None
                cause = None

                for line in response_lines:
                    if line.lower().startswith("check response:"):
                        check_result = line.split(":", 1)[1].strip().lower()
                    elif line.lower().startswith("cause:"):
                        cause = line.split(":", 1)[1].strip()

                if check_result == "yes":
                    return True, None
                elif check_result == "no":
                    return False, cause
                else:
                    return False, f"Respuesta inesperada: {response}"

        try:
            # Verificar si se ha solicitado detener antes de hacer la llamada API
            if stop_callback and stop_callback():
                session_logger.log_info("Comprobación cancelada por solicitud del usuario")
                return False

            response = query_model()
            if response is None:
                session_logger.log_error("Error en la comprobación de la traducción (respuesta nula)")
                return False

            is_ok, cause = _parse_check_response(response)

            if is_ok:
                # Only log the response if it doesn't contain XML format (to avoid duplication)
                if not re.search(r'<response>.*?</response>', response, re.DOTALL):
                    session_logger.log_info(f"Comprobación exitosa - Respuesta: {response}")
                return True
            elif retry_on_failure:
                log_message = f"Comprobación falló - Respuesta: {response}"
                session_logger.log_warning(f"{log_message}. Reintentando...")
                
                # Log the cause if available
                if cause:
                    session_logger.log_warning(f"Causa del fallo: {cause}")

                # Reintentar una vez
                time.sleep(5)

                # Verificar nuevamente si se ha solicitado detener antes del reintento
                if stop_callback and stop_callback():
                    session_logger.log_info("Reintento de comprobación cancelado por solicitud del usuario")
                    return False

                response_retry = query_model()
                if response_retry is None:
                    session_logger.log_error("Error en la comprobación de la traducción (reintento respuesta nula)")
                    return False

                is_ok_retry, cause_retry = _parse_check_response(response_retry)

                if is_ok_retry:
                    session_logger.log_info(f"Comprobación exitosa en reintento - Respuesta: {response_retry}")
                    return True
                else:
                    log_message_retry = f"Comprobación falló en reintento - Respuesta: {response_retry}"
                    session_logger.log_error(log_message_retry)
                    return False
            else:
                # No reintentar, retornar el resultado directamente
                log_message = f"Comprobación falló - Respuesta: {response}"
                session_logger.log_error(log_message)
                return False
        except Exception as e:
            session_logger.log_error(f"Error al hacer la comprobación: {str(e)}")
            return False

    def _refine_translation(self, source_text: str, translated_text: str,
                              source_lang: str, target_lang: str,
                              main_api_key: str, refine_provider: str, refine_model: str,
                              custom_terms: str = "", temp_api_keys: dict = None, timeout: int = 120,
                              stop_callback: Optional[Callable[[], bool]] = None, 
                              prompt_name: str = "refine.txt",
                              use_tools: bool = False) -> Optional[str]:
        """
        Refina la traducción usando la API.
        Soporta tres modos:
          - refine.txt: regeneración completa del texto
          - refine_alt.txt: cambios XML parciales
          - use_tools=True: function calling para cambios quirúrgicos

        Args:
            source_text (str): Texto original
            translated_text (str): Texto traducido a refinar
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            main_api_key (str): API key principal (no usado si refine_provider diferente)
            refine_provider (str): Proveedor para refinamiento
            refine_model (str): Modelo para refinamiento
            custom_terms (str): Términos personalizados para la traducción
            temp_api_keys (dict): Diccionario de API keys temporales (opcional)
            prompt_name (str): Nombre del archivo de prompt a usar
            use_tools (bool): Si True, usa function calling en lugar de otros métodos

        Returns:
            Optional[str]: Texto refinado si tiene éxito, None si falla o error
        """
        # Obtener API key específica para el proveedor de refinamiento
        if temp_api_keys and refine_provider in temp_api_keys:
            api_key = temp_api_keys[refine_provider]
        else:
            api_key = self._get_api_key_for_provider(refine_provider)

        if not api_key:
            session_logger.log_error(f"No se encontró API key para el proveedor de refinamiento: {refine_provider}")
            return None

        session_logger.log_info(f"Iniciando refinamiento con Proveedor: {refine_provider}, Modelo: {refine_model}")
        prompt = self._build_refine_prompt(source_lang, target_lang, source_text, translated_text, custom_terms, prompt_name)

        provider_config = self.models_config.get(refine_provider)
        if not provider_config:
            print(f"Proveedor no soportado para refinamiento: {refine_provider}")
            return None

        model_config = provider_config['models'].get(refine_model)
        if not model_config:
            print(f"Modelo no soportado para refinamiento: {refine_model}")
            return None

        # Determinar si usar tools automáticamente según soporte del modelo
        # Solo usar tools si:
        # 1. use_tools=True explícitamente Y
        # 2. El modelo soporta tools
        # De lo contrario, fallback a refine_alt.txt
        tools_to_use = None
        actual_prompt_name = prompt_name
        
        if use_tools:
            if model_config.get('supports_tools', False):
                # El modelo soporta tools, importar y usar
                from src.logic.refine_tools import REFINE_TOOLS
                tools_to_use = REFINE_TOOLS
                actual_prompt_name = "refine_tools.txt"
                session_logger.log_info(
                    f"Usando function calling para refinamiento con {refine_model}"
                )
            else:
                # El modelo no soporta tools, hacer fallback a refine_alt.txt
                session_logger.log_warning(
                    f"{refine_model} no soporta tools, usando refine_alt.txt"
                )
                actual_prompt_name = "refine_alt.txt"
                use_tools = False

        try:
            # Verificar si se ha solicitado detener antes de hacer la llamada API
            if stop_callback and stop_callback():
                session_logger.log_info("Refinamiento cancelado por solicitud del usuario")
                return None

            # Construir el prompt
            prompt = self._build_refine_prompt(
                source_lang, target_lang, source_text, translated_text, 
                custom_terms, actual_prompt_name
            )

            response = translator_req.translate_segment(
                refine_provider,
                "",  # texto ya incluido en prompt
                api_key,
                model_config,
                prompt,
                self.models_config,
                timeout,
                tools=tools_to_use
            )

            if response is None:
                session_logger.log_error("Error en el refinamiento de la traducción (respuesta nula)")
                return None

            # Procesar según el modo
            if use_tools:
                return self._apply_tool_refinement(translated_text, response)
            elif actual_prompt_name == "refine_alt.txt":
                return self._apply_refinement_changes(translated_text, response)
            else:
                # Para el prompt normal, devolver la respuesta completa
                return response

        except Exception as e:
            session_logger.log_error(f"Error al hacer el refinamiento: {str(e)}")
            return None

    def _perform_translation(self, text: str, source_lang: str, target_lang: str,
                              api_key: str, provider: str, model: str,
                              custom_terms: str, enable_refine: bool,
                              refine_provider: str, refine_model: str,
                              temp_api_keys: dict, segmentation_config: Optional[Dict] = None,
                              timeout: int = 120, stop_callback: Optional[Callable[[], bool]] = None) -> Optional[str]:
        """
        Realiza la traducción completa del texto: segmentación, traducción y refinamiento opcional.
 
        Args:
            text (str): Texto a traducir
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            api_key (str): API key del servicio
            provider (str): Identificador del proveedor
            model (str): Identificador del modelo
            custom_terms (str): Términos personalizados para la traducción
            enable_refine (bool): Si True, realiza refinamiento de traducción
            refine_provider (str): Proveedor para refinamiento
            refine_model (str): Modelo para refinamiento
            temp_api_keys (dict): Diccionario de API keys temporales
            segmentation_config (Optional[Dict]): Configuración de segmentación automática
        Returns:
            Optional[str]: Texto traducido completo, None si hay error
        """
        try:
            provider_config = self.models_config.get(provider)
            if not provider_config:
                raise ValueError(f"Proveedor no soportado: {provider}")

            model_config = provider_config['models'].get(model)
            if not model_config:
                raise ValueError(f"Modelo no soportado: {model}")

            # Auto-segmentation logic
            local_segment_size = self.segment_size  # Preserve manual if set
            auto_activated = False
            if segmentation_config and segmentation_config.get("enabled", False):
                threshold = segmentation_config.get("threshold", 10000)
                if len(text) > threshold:
                    local_segment_size = segmentation_config.get("segment_size", 5000)
                    auto_activated = True
                    session_logger.log_info(f"Auto-segmentation activated: text length {len(text)} > {threshold}, using segment size {local_segment_size}")

            if not auto_activated:
                if self.segment_size is not None:
                    session_logger.log_info(f"Using manual segmentation with size {local_segment_size}")
                else:
                    session_logger.log_info("No segmentation applied - translating full text")
                    local_segment_size = None

            # Temporarily set segment_size for this translation
            original_segment_size = self.segment_size
            self.segment_size = local_segment_size
            segments = self._segment_text(text)
            self.segment_size = original_segment_size  # Restore original

            # Verificar integridad de segmentación solo cuando auto-segmentación esté activada
            if auto_activated and not self._verify_segmentation_integrity(segments, text):
                session_logger.log_error("Segmentación automática falló verificación de integridad - abortando traducción")
                return None

            if local_segment_size is not None:
                # Validar integridad de los segmentos creados
                validation_report = self._validate_segment_integrity(segments, text)

                # Log de métricas de segmentación
                session_logger.log_info(
                    f"Segmentación completada: {validation_report['total_segments']} segmentos, "
                    f"{validation_report['natural_cut_percentage']:.1f}% cortes naturales"
                )

                # Log de advertencias si hay cortes no naturales
                if validation_report['warnings']:
                    for warning in validation_report['warnings'][:3]:  # Solo primeras 3
                        session_logger.log_warning(f"Segmentación: {warning}")
            else:
                session_logger.log_info("Segmentación deshabilitada - traduciendo texto completo")

            translated_segments = []

            # Traducir cada segmento
            for i, segment in enumerate(segments, 1):
                # Verificar si se ha solicitado detener antes de procesar segmento
                if stop_callback and stop_callback():
                    session_logger.log_info(f"Traducción cancelada en segmento {i} por solicitud del usuario")
                    return None

                session_logger.log_info(f"Traduciendo segmento {i} de {len(segments)} con {provider}/{model}")

                # Construir prompt base con reemplazo de etiquetas
                prompt_template = self._load_prompt("translation.txt", source_lang, target_lang)
                prompt_content = self._handle_terminology_section(prompt_template, custom_terms)
                prompt_content = prompt_content.replace("{source_lang}", source_lang).replace("{target_lang}", target_lang)

                # Crear estructura con roles system/user
                prompt = {
                    "messages": [
                        {"role": "system", "content": prompt_content},
                        {"role": "user", "content": segment}
                    ]
                }

                # Verificar nuevamente antes de llamada API
                if stop_callback and stop_callback():
                    session_logger.log_info(f"Traducción cancelada antes de llamada API en segmento {i}")
                    return None

                # Delegar la petición al módulo translator_req
                translated_segment = translator_req.translate_segment(
                    provider,
                    segment,
                    api_key,
                    model_config,
                    prompt,
                    self.models_config,
                    timeout
                )

                if translated_segment is None:
                    session_logger.log_error(f"Error traduciendo segmento {i}")
                    raise ValueError(f"Error traduciendo segmento {i}")

                # Si enable_refine está habilitado, refinar la traducción del segmento
                if enable_refine:
                    # Verificar antes de refinamiento
                    if stop_callback and stop_callback():
                        session_logger.log_info(f"Refinamiento cancelado en segmento {i} por solicitud del usuario")
                        return None

                    session_logger.log_info(f"Refinando segmento {i} de {len(segments)}")
                    refined_segment = self._refine_translation(
                        source_text=segment,
                        translated_text=translated_segment,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        main_api_key=api_key,
                        refine_provider=refine_provider,
                        refine_model=refine_model,
                        custom_terms=custom_terms,
                        temp_api_keys=temp_api_keys,
                        timeout=timeout,
                        stop_callback=stop_callback
                    )

                    if refined_segment is not None:
                        # Usar la versión refinada
                        translated_segment = refined_segment
                        session_logger.log_info(f"Segmento {i} refinado exitosamente")
                    else:
                        # Continuar con la traducción original si el refinamiento falla
                        session_logger.log_warning(f"Falló el refinamiento del segmento {i}, usando traducción original")

                translated_segments.append(translated_segment)

                # Esperar entre segmentos para evitar límites de rate
                if i < len(segments):
                    time.sleep(5)

            # Unir todos los segmentos traducidos
            full_translation = '\n\n'.join(translated_segments)
            return full_translation

        except Exception as e:
            session_logger.log_error(f"Error en la traducción: {str(e)}")
            return None

    def translate_text(self, text: str, source_lang: str, target_lang: str,
                        api_key: str, provider: str, model: str,
                        custom_terms: str = "", enable_check: bool = True,
                        enable_refine: bool = False,
                        check_refine_settings: Optional[Dict] = None,
                        segmentation_config: Optional[Dict] = None,
                        temp_api_keys: dict = None, timeout: int = 120,
                        stop_callback: Optional[Callable[[], bool]] = None) -> Optional[str]:
        """
        Traduce el texto utilizando el proveedor y modelo especificados.

        Incluye refinamiento opcional y verificación con reintento de traducción completa si falla.

        Args:
            text (str): Texto a traducir
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            api_key (str): API key del servicio
            provider (str): Identificador del proveedor
            model (str): Identificador del modelo
            custom_terms (str): Términos personalizados para la traducción
            enable_check (bool): Si True, realiza comprobación de traducción; si False, omite comprobación.
            enable_refine (bool): Si True, realiza refinamiento de traducción; si False, omite refinamiento.
            check_refine_settings (Optional[Dict]): Configuración para check/refine
            temp_api_keys (dict): Diccionario de API keys temporales

        Returns:
            Optional[str]: Texto traducido si la comprobación pasa o no se realiza, None si falla definitivamente
        """
        # Determine provider and model for check/refine
        if check_refine_settings and check_refine_settings.get('use_separate_model'):
            check_provider = check_refine_settings.get('provider', provider)
            check_model = check_refine_settings.get('model', model)
            refine_provider = check_refine_settings.get('provider', provider)
            refine_model = check_refine_settings.get('model', model)
        else:
            check_provider = provider
            check_model = model
            refine_provider = provider
            refine_model = model

        # Preparar temp_api_keys para asegurar que el api_key principal se use cuando sea necesario
        temp_keys = temp_api_keys.copy() if temp_api_keys else {}
        if check_provider == provider and api_key:
            temp_keys[check_provider] = api_key
        if refine_provider == provider and api_key:
            temp_keys[refine_provider] = api_key

        # Primera traducción
        session_logger.log_info("Iniciando traducción inicial")
        full_translation = self._perform_translation(
            text, source_lang, target_lang, api_key, provider, model,
            custom_terms, enable_refine, refine_provider, refine_model, temp_keys,
            segmentation_config, timeout, stop_callback
        )

        if full_translation is None:
            return None

        # Si enable_check está habilitado, hacer comprobación
        if enable_check:
            check_passed = self._check_translation(
                original_text=text,
                translated_text=full_translation,
                source_lang=source_lang,
                target_lang=target_lang,
                main_api_key=api_key,
                check_provider=check_provider,
                check_model=check_model,
                custom_terms=custom_terms,
                temp_api_keys=temp_keys,
                retry_on_failure=False,  # No reintentar verificación internamente
                timeout=timeout,
                stop_callback=stop_callback
            )

            if not check_passed:
                session_logger.log_warning("La comprobación inicial falló. Reintentando traducción completa...")

                # Reintento de traducción completa
                session_logger.log_info("Iniciando reintento de traducción")
                retry_translation = self._perform_translation(
                    text, source_lang, target_lang, api_key, provider, model,
                    custom_terms, enable_refine, refine_provider, refine_model, temp_keys,
                    segmentation_config, timeout, stop_callback
                )

                if retry_translation is None:
                    session_logger.log_error("El reintento de traducción también falló")
                    return None

                # Verificar el reintento
                check_passed_retry = self._check_translation(
                    original_text=text,
                    translated_text=retry_translation,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    main_api_key=api_key,
                    check_provider=check_provider,
                    check_model=check_model,
                    custom_terms=custom_terms,
                    temp_api_keys=temp_keys,
                    retry_on_failure=False,  # No reintentar verificación internamente
                    timeout=timeout,
                    stop_callback=stop_callback
                )

                if not check_passed_retry:
                    session_logger.log_error("La comprobación del reintento también falló. Traducción marcada como fallida.")
                    return None

                # Verificar si se canceló durante el reintento
                if stop_callback and stop_callback():
                    session_logger.log_info("Reintento de traducción cancelado por solicitud del usuario")
                    return None

                # Si el reintento pasa la verificación, usar esa traducción
                full_translation = retry_translation
                session_logger.log_info("Reintento exitoso - traducción completada")

        # Si pasa la comprobación o no se realiza, devolver la traducción completa
        return full_translation

    def get_supported_languages(self) -> Dict[str, str]:
        """
        Obtiene la lista de idiomas soportados.
        Retorna un diccionario con los códigos como claves y los nombres para mostrar como valores.
        """
        return self.lang_codes

    
