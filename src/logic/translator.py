import time
import json
from typing import Optional, Dict, List
from pathlib import Path
from src.logic import translator_req

class TranslatorLogic:
    def __init__(self, segment_size=None):
        """Inicializa el traductor con los idiomas soportados"""
        self.lang_codes = {
            'Español (Neutro)': 'Spanish (Neutral, non-regional)',
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
        self.check_prompt_template = self._load_check_prompt_template()
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

    def _load_check_prompt_template(self) -> str:
        """
        Carga el prompt base de comprobación desde prompt_check.txt

        Returns:
            str: Contenido del prompt de comprobación
        """
        try:
            check_path = Path(__file__).parent / 'prompt_check.txt'
            with open(check_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error cargando el prompt de comprobación: {str(e)}")
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
            '. ', '? ', '! ',
            '] ', '] \n', ']\n',
            '..." ', '..." \n',
            '…" ', '…" \n',
            '" ', '" \n',
            '."', '?"', '!"',
            '." ', '?" ', '!" '
        ]

        while current_position < len(text):
            target_position = min(current_position + self.segment_size, len(text))
            best_end_pos = -1
            search_position = target_position

            while search_position < len(text):
                next_end = -1
                for ending in sentence_endings:
                    pos = text.find(ending, search_position)
                    if pos != -1 and (next_end == -1 or pos < next_end):
                        next_end = pos + len(ending)

                if next_end == -1:
                    break

                end_pos = next_end
                while end_pos < len(text) and text[end_pos].isspace():
                    if end_pos + 1 < len(text) and text[end_pos:end_pos+2] == '\n\n':
                        best_end_pos = end_pos + 2
                        break
                    end_pos += 1

                if best_end_pos != -1:
                    break

                search_position = next_end

                if search_position > current_position + (self.segment_size * 1.5):
                    best_end_pos = next_end
                    break

            if best_end_pos == -1:
                best_end_pos = len(text)

            segment_text = text[current_position:best_end_pos].strip()
            if segment_text:
                segments.append(segment_text)

            current_position = best_end_pos

        return segments

    def _build_check_prompt(self, source_lang: str, target_lang: str,
                            original_text: str, translated_text: str) -> str:
        """
        Construye el prompt para comprobar la calidad de la traducción.

        Args:
            source_lang (str): Idioma original
            target_lang (str): Idioma destino
            original_text (str): Texto original completo
            translated_text (str): Texto traducido completo

        Returns:
            str: Prompt completo para la comprobación
        """
        prompt = self.check_prompt_template
        prompt = prompt.replace("{source_lang}", self.lang_codes.get(source_lang, source_lang))
        prompt = prompt.replace("{target_lang}", self.lang_codes.get(target_lang, target_lang))

        # Insertar texto original y traducido en el lugar correcto
        # La suposición es que prompt_check.txt tiene líneas "Text 1:" y "Text 2:" para insertar
        # Vamos a hacer esto para asegurar:
        # Insertamos original tras "Text 1:", traducido tras "Text 2:"

        idx_text1 = prompt.find("Text 1:")
        idx_text2 = prompt.find("Text 2:")

        if idx_text1 == -1 or idx_text2 == -1:
            # Formato inesperado, simplemente añadir al final
            return prompt + "\n\nText 1:\n" + original_text + "\n\nText 2:\n" + translated_text

        # Construir nuevo prompt con textos insertados, manteniendo orden
        before_text1 = prompt[:idx_text1 + len("Text 1:")]
        between = prompt[idx_text1 + len("Text 1:"):idx_text2 + len("Text 2:")]
        after_text2 = prompt[idx_text2 + len("Text 2:"):]

        # Insertar los textos, dejando un salto de línea después de la marca
        final_prompt = (
            before_text1 + "\n" +
            original_text.strip() + "\n" +
            between + "\n" +
            translated_text.strip() + "\n" +
            after_text2
        )
        return final_prompt

    def _check_translation(self, original_text: str, translated_text: str,
                           source_lang: str, target_lang: str,
                           api_key: str, provider: str, model: str) -> bool:
        """
        Comprueba la calidad de la traducción usando la API.

        Retorna True si el modelo responde "Yes", False si "No" o error.

        Se hace un reintento una vez en caso de "No".

        Args:
            original_text (str): Texto original completo
            translated_text (str): Texto traducido completo
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            api_key (str): API key
            provider (str): Proveedor
            model (str): Modelo

        Returns:
            bool: Resultado de la comprobación
        """
        prompt = self._build_check_prompt(source_lang, target_lang, original_text, translated_text)

        provider_config = self.models_config.get(provider)
        if not provider_config:
            print(f"Proveedor no soportado para comprobación: {provider}")
            return False
        model_config = provider_config['models'].get(model)
        if not model_config:
            print(f"Modelo no soportado para comprobación: {model}")
            return False

        def query_model():
            return translator_req.translate_segment(
                provider,
                "",  # texto ya incluido en prompt, pasar vacío para evitar doble agregado
                api_key,
                model_config,
                prompt
            )

        try:
            response = query_model()
            if response is None:
                print("Error en la comprobación de la traducción (respuesta nula)")
                return False

            cleaned_response = response.strip().lower()
            if cleaned_response == "yes":
                return True
            elif cleaned_response == "no":
                # Reintentar una vez
                time.sleep(2)
                response_retry = query_model()
                if response_retry is None:
                    print("Error en la comprobación de la traducción (reintento respuesta nula)")
                    return False
                if response_retry.strip().lower() == "yes":
                    return True
                else:
                    return False
            else:
                # Respuesta inesperada, consideramos error
                print(f"Respuesta inesperada en comprobación: '{response}'")
                return False
        except Exception as e:
            print(f"Error al hacer la comprobación: {str(e)}")
            return False

    def translate_text(self, text: str, source_lang: str, target_lang: str,
                      api_key: str, provider: str, model: str,
                      custom_terms: str = "") -> Optional[str]:
        """
        Traduce el texto utilizando el proveedor y modelo especificados.

        Agrega comprobación de la traducción tras completarla.

        Args:
            text (str): Texto a traducir
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            api_key (str): API key del servicio
            provider (str): Identificador del proveedor
            model (str): Identificador del modelo
            custom_terms (str): Términos personalizados para la traducción

        Returns:
            Optional[str]: Texto traducido si la comprobación pasa, None si falla o error
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

                # Construir prompt base
                prompt = self.prompt_template.replace(
                    "{source_lang}", self.lang_codes[source_lang]
                ).replace(
                    "{target_lang}", self.lang_codes[target_lang]
                )

                # Agregar términos personalizados si existen
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
                prompt += f"\n\n{segment}"

                # Delegar la petición al módulo translator_req
                translated_segment = translator_req.translate_segment(
                    provider,
                    segment,
                    api_key,
                    model_config,
                    prompt
                )

                if translated_segment is None:
                    raise ValueError(f"Error traduciendo segmento {i}")

                translated_segments.append(translated_segment)

                # Esperar entre segmentos para evitar límites de rate
                if i < len(segments):
                    time.sleep(2)

            # Unir todos los segmentos traducidos
            full_translation = '\n\n'.join(translated_segments)

            # Ahora hacemos la comprobación de la traducción contra el texto original completo
            check_passed = self._check_translation(
                original_text=text,
                translated_text=full_translation,
                source_lang=source_lang,
                target_lang=target_lang,
                api_key=api_key,
                provider=provider,
                model=model
            )

            if not check_passed:
                print("La comprobación de la traducción NO pasó.")
                return None

            # Si pasa la comprobación, devolver la traducción completa
            return full_translation

        except Exception as e:
            print(f"Error en la traducción: {str(e)}")
            return None

    def get_supported_languages(self) -> Dict[str, str]:
        """
        Obtiene la lista de idiomas soportados.
        """
        return self.lang_codes.copy()
