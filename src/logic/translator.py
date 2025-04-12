import requests
import time
import json
from typing import Optional, Dict, List
from pathlib import Path

class TranslatorLogic:
    def __init__(self, segment_size=None):
        """Inicializa el traductor con los idiomas soportados"""
        self.lang_codes = {
            'Español (MX)': 'Spanish (es_MX)',
            'Español (ES)': 'Spanish (es_ES)',
            'Inglés': 'English',
            'Francés': 'French',
            'Alemán': 'German',
            'Italiano': 'Italian'
        }

        # Cargar configuración de modelos
        models_path = Path(__file__).parent / 'translation_models.json'
        with open(models_path, 'r') as f:
            self.models_config = json.load(f)

        self.prompt_template = self._load_prompt_template()
        self.segment_size = segment_size  # Tamaño objetivo para cada segmento

    def _load_prompt_template(self) -> str:
        """
        Carga el prompt base desde el archivo prompt_base.txt

        Returns:
            str: Contenido del prompt base
        """
        try:
            prompt_path = Path(__file__).parent / 'prompt_base.txt'
            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error cargando el prompt base: {str(e)}")
            return ""

    def _segment_text(self, text: str) -> List[str]:
        """
        Segmenta el texto en partes manejables basadas en un tamaño objetivo,
        respetando oraciones y párrafos.

        Args:
            text (str): Texto completo a segmentar

        Returns:
            List[str]: Lista de segmentos de texto
        """
        if self.segment_size is None:
            return [text]

        segments = []
        current_position = 0

        # Normalizar saltos de línea
        text = text.replace('\r\n', '\n')

        # Definir marcadores de fin de oración
        sentence_endings = [
            '. ', '? ', '! ',           # Puntuación básica
            '] ', '] \n', ']\n',        # Diálogos con corchetes
            '..." ', '..." \n',         # Diálogos con puntos suspensivos
            '…" ', '…" \n',             # Puntos suspensivos (Unicode)
            '" ', '" \n',               # Diálogos con comillas
            '."', '?"', '!"',           # Puntuación dentro de comillas
            '." ', '?" ', '!" '         # Puntuación dentro de comillas con espacio
        ]

        while current_position < len(text):
            # 1. Avanzar hasta el tamaño de segmento objetivo
            target_position = min(current_position + self.segment_size, len(text))

            # 2. Desde esa posición, buscar el próximo final de oración válido
            best_end_pos = -1
            search_position = target_position

            # Buscar hacia adelante para encontrar un final de oración válido
            while search_position < len(text):
                # Encontrar el próximo final de oración
                next_end = -1
                for ending in sentence_endings:
                    pos = text.find(ending, search_position)
                    if pos != -1 and (next_end == -1 or pos < next_end):
                        next_end = pos + len(ending)

                if next_end == -1:
                    # No se encontraron más finales, tomar el resto del texto
                    break

                # Verificar si después del final hay una línea en blanco
                end_pos = next_end
                while end_pos < len(text) and text[end_pos].isspace():
                    if end_pos + 1 < len(text) and text[end_pos:end_pos+2] == '\n\n':
                        best_end_pos = end_pos + 2  # Incluir la línea en blanco
                        break
                    end_pos += 1

                if best_end_pos != -1:
                    break  # Encontramos un buen punto de corte

                # Si no encontramos línea en blanco, seguir buscando
                search_position = next_end

                # Verificar si hemos buscado demasiado lejos (1.5 veces el tamaño objetivo)
                if search_position > current_position + (self.segment_size * 1.5):
                    # Forzar el corte en el último final de oración encontrado
                    best_end_pos = next_end
                    break

            # Si no encontramos un buen punto de corte, usar el final del texto
            if best_end_pos == -1:
                best_end_pos = len(text)

            # Extraer y añadir el segmento
            segment_text = text[current_position:best_end_pos].strip()
            if segment_text:
                segments.append(segment_text)

            # Avanzar al siguiente segmento (después de la línea en blanco)
            current_position = best_end_pos

        return segments

    def translate_text(self, text: str, source_lang: str, target_lang: str,
                      api_key: str, provider: str, model: str,
                      custom_terms: str = "") -> Optional[str]:
        """
        Traduce el texto utilizando el proveedor y modelo especificados.

        Args:
            text (str): Texto a traducir
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            api_key (str): API key del servicio
            provider (str): Identificador del proveedor
            model (str): Identificador del modelo
            custom_terms (str): Términos personalizados para la traducción

        Returns:
            Optional[str]: Texto traducido o None si hay error
        """
        try:
            provider_config = self.models_config.get(provider)
            if not provider_config:
                raise ValueError(f"Proveedor no soportado: {provider}")

            model_config = provider_config['models'].get(model)
            if not model_config:
                raise ValueError(f"Modelo no soportado: {model}")

            # Segmentar el texto
            segments = self._segment_text(text)
            translated_segments = []

            # Traducir cada segmento
            for i, segment in enumerate(segments, 1):
                print(f"Traduciendo segmento {i} de {len(segments)}")

                translated_segment = self._translate_segment(
                    segment, source_lang, target_lang, api_key,
                    provider, model_config, custom_terms
                )

                if translated_segment is None:
                    raise ValueError(f"Error traduciendo segmento {i}")

                translated_segments.append(translated_segment)

                # Esperar entre segmentos para evitar límites de rate
                if i < len(segments):
                    time.sleep(2)

            # Unir todos los segmentos traducidos
            return '\n\n'.join(translated_segments)

        except Exception as e:
            print(f"Error en la traducción: {str(e)}")
            return None

    def _translate_segment(self, text: str, source_lang: str, target_lang: str,
                         api_key: str, provider: str, model_config: Dict,
                         custom_terms: str = "") -> Optional[str]:
        """
        Traduce un segmento individual de texto.
        """
        try:
            if provider == 'gemini':
                return self._translate_gemini(
                    text, source_lang, target_lang, api_key, model_config,
                    custom_terms
                )
            elif provider == 'together':
                return self._translate_together(
                    text, source_lang, target_lang, api_key, model_config,
                    custom_terms
                )
            elif provider == 'deepinfra':
                return self._translate_deepinfra(
                    text, source_lang, target_lang, api_key, model_config,
                    custom_terms
                )
            else:
                raise ValueError(f"Proveedor no implementado: {provider}")
        except Exception as e:
            print(f"Error traduciendo segmento: {str(e)}")
            return None

    def _translate_gemini(self, text: str, source_lang: str, target_lang: str,
                         api_key: str, model_config: Dict, custom_terms: str = "") -> Optional[str]:
        """Traduce usando la API de Google Gemini"""
        try:
            url = f"{self.models_config['gemini']['base_url']}/{model_config['endpoint']}?key={api_key}"

            # Construir el prompt base
            prompt = self.prompt_template.replace(
                "{source_lang}", self.lang_codes[source_lang]
            ).replace(
                "{target_lang}", self.lang_codes[target_lang]
            )

            # Añadir términos personalizados si existen
            if custom_terms:
                ref_section = "Use the following predefined translations for domain-specific or recurring terms. These must be used consistently throughout the translation:"
                final_instructions = "\n5. Final Output Constraint:"

                pre_terms = prompt[:prompt.find(ref_section) + len(ref_section)]
                post_terms = prompt[prompt.find(final_instructions):]

                terms = custom_terms.strip().split('\n')
                terms = [
                    line if line.strip().startswith('- ') else f'- {line.strip()}'
                    for line in terms
                    if line.strip()
                ]
                formatted_terms = '\n'.join(terms)

                prompt = f"{pre_terms}\n{formatted_terms}{post_terms}"

            # Añadir el texto a traducir
            prompt += f"\n\n{text}"

            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }

            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            return self._process_gemini_response(response.json())

        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud HTTP: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print("Respuesta detallada:", e.response.text)
            return None
        except Exception as e:
            print(f"Error en la traducción con Gemini: {str(e)}")
            return None

    def _translate_together(self, text: str, source_lang: str, target_lang: str,
                          api_key: str, model_config: Dict, custom_terms: str = "") -> Optional[str]:
        """Traduce usando la API de Together AI"""
        try:
            url = self.models_config['together']['base_url']
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # Construir el prompt con el template base
            prompt = self.prompt_template.replace(
                "{source_lang}", self.lang_codes[source_lang]
            ).replace(
                "{target_lang}", self.lang_codes[target_lang]
            )

            # Si hay términos personalizados, insertarlos en el lugar correcto
            if custom_terms:
                ref_section = "Use the following predefined translations for domain-specific or recurring terms. These must be used consistently throughout the translation:"
                final_instructions = "\n5. Final Output Constraint:"

                pre_terms = prompt[:prompt.find(ref_section) + len(ref_section)]
                post_terms = prompt[prompt.find(final_instructions):]

                terms = custom_terms.strip().split('\n')
                terms = [
                    line if line.strip().startswith('- ') else f'- {line.strip()}'
                    for line in terms
                    if line.strip()
                ]
                formatted_terms = '\n'.join(terms)

                prompt = f"{pre_terms}\n{formatted_terms}{post_terms}"

            # Agregar el texto a traducir al final del prompt
            prompt += f"\n\n{text}"

            data = {
                "model": model_config['model_id'],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 55,
                "repetition_penalty": 1.2,
                "stop": ["</s>", "[/INST]"],
                "max_tokens": model_config.get('max_tokens', 4096),
                "stream": False
            }

            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            return self._process_together_response(response.json())

        except Exception as e:
            print(f"Error en Together AI: {str(e)}")
            return None

    def _translate_deepinfra(self, text: str, source_lang: str, target_lang: str,
                           api_key: str, model_config: Dict, custom_terms: str = "") -> Optional[str]:
        """Traduce usando la API de DeepInfra (formato OpenAI compatible)"""
        try:
            url = self.models_config['deepinfra']['base_url']
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # Construir el prompt con el template base
            prompt = self.prompt_template.replace(
                "{source_lang}", self.lang_codes[source_lang]
            ).replace(
                "{target_lang}", self.lang_codes[target_lang]
            )

            # Si hay términos personalizados, insertarlos en el lugar correcto
            if custom_terms:
                ref_section = "Use the following predefined translations for domain-specific or recurring terms. These must be used consistently throughout the translation:"
                final_instructions = "\n5. Final Output Constraint:"

                pre_terms = prompt[:prompt.find(ref_section) + len(ref_section)]
                post_terms = prompt[prompt.find(final_instructions):]

                terms = custom_terms.strip().split('\n')
                terms = [
                    line if line.strip().startswith('- ') else f'- {line.strip()}'
                    for line in terms
                    if line.strip()
                ]
                formatted_terms = '\n'.join(terms)

                prompt = f"{pre_terms}\n{formatted_terms}{post_terms}"

            # Agregar el texto a traducir al final del prompt
            prompt += f"\n\n{text}"

            data = {
                "model": model_config['model_id'],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "top_p": 0.95,
                "max_tokens": 100000,
                "stream": False  # Podemos dejarlo como False para traducciones
            }

            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            return self._process_deepinfra_response(response.json())

        except Exception as e:
            print(f"Error en DeepInfra: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print("Respuesta detallada:", e.response.text)
            return None

    def _process_gemini_response(self, response: Dict) -> Optional[str]:
        """
        Procesa la respuesta de la API de Gemini y extrae el texto traducido.
        """
        try:
            if 'candidates' not in response or not response['candidates']:
                return None

            candidate = response['candidates'][0]
            if 'content' not in candidate or 'parts' not in candidate['content']:
                return None

            parts = candidate['content']['parts']
            if not parts or 'text' not in parts[0]:
                return None

            translated_text = parts[0]['text']
            return self._clean_translation(translated_text)

        except Exception as e:
            print(f"Error procesando respuesta de Gemini: {str(e)}")
            return None

    def _process_together_response(self, response: Dict) -> Optional[str]:
        """
        Procesa la respuesta de la API de Together y extrae el texto traducido.
        """
        try:
            if 'choices' not in response or not response['choices']:
                return None

            message = response['choices'][0]['message']
            if 'content' not in message:
                return None

            return self._clean_translation(message['content'])

        except Exception as e:
            print(f"Error procesando respuesta de Together: {str(e)}")
            return None

    def _process_deepinfra_response(self, response: Dict) -> Optional[str]:
        """
        Procesa la respuesta de la API de DeepInfra y extrae el texto traducido.
        """
        try:
            if 'choices' not in response or not response['choices']:
                return None

            message = response['choices'][0]['message']
            if 'content' not in message:
                return None

            return self._clean_translation(message['content'])

        except Exception as e:
            print(f"Error procesando respuesta de DeepInfra: {str(e)}")
            return None

    def _clean_translation(self, text: str) -> str:
        """
        Limpia y formatea el texto traducido.
        """
        lines = text.split('\n')
        actual_translation = []
        translation_started = False

        for line in lines:
            if translation_started or (
                not line.startswith('-') and
                not 'Requirements:' in line and
                not 'Translation:' in line
            ):
                translation_started = True
                actual_translation.append(line)

        return '\n'.join(actual_translation).strip()

    def get_supported_languages(self) -> Dict[str, str]:
        """
        Obtiene la lista de idiomas soportados.
        """
        return self.lang_codes.copy()
