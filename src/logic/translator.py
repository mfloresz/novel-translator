import time
import json
from typing import Optional, Dict, List
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
        models_path = Path(__file__).parent.parent / 'config' / 'models' / 'translation_models.json'
        with open(models_path, 'r') as f:
            self.models_config = json.load(f)

        self.prompt_template = self._load_prompt_template()
        self.check_prompt_template = self._load_check_prompt_template()
        self.refine_prompt_template = self._load_refine_prompt_template()
        self.segment_size = segment_size  # Tamaño objetivo para cada segmento

    def _load_prompt_template(self) -> str:
        """
        Carga el prompt base desde el archivo translation.txt

        Returns:
            str: Contenido del prompt base
        """
        try:
            prompt_path = Path(__file__).parent.parent / 'config' / 'prompts' / 'translation.txt'
            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error cargando el prompt base: {str(e)}")
            return ""

    def _load_check_prompt_template(self) -> str:
        """
        Carga el prompt base de comprobación desde check.txt

        Returns:
            str: Contenido del prompt de comprobación
        """
        try:
            check_path = Path(__file__).parent.parent / 'config' / 'prompts' / 'check.txt'
            with open(check_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error cargando el prompt de comprobación: {str(e)}")
            return ""

    def _load_refine_prompt_template(self) -> str:
        """
        Carga el prompt base de refinamiento desde refine.txt

        Returns:
            str: Contenido del prompt de refinamiento
        """
        try:
            refine_path = Path(__file__).parent.parent / 'config' / 'prompts' / 'refine.txt'
            with open(refine_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error cargando el prompt de refinamiento: {str(e)}")
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
            '…” ', '…” \n',
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
        prompt = prompt.replace("{source_lang}", source_lang)
        prompt = prompt.replace("{target_lang}", target_lang)
        prompt = prompt.replace("{TEXT_1}", original_text.strip())
        prompt = prompt.replace("{TEXT_2}", translated_text.strip())
        return prompt

    def _build_refine_prompt(self, source_lang: str, target_lang: str,
                            source_text: str, translated_text: str,
                            custom_terms: str = "") -> str:
        """
        Construye el prompt para refinar la traducción.

        Args:
            source_lang (str): Idioma original
            target_lang (str): Idioma destino
            source_text (str): Texto original
            translated_text (str): Texto traducido a refinar
            custom_terms (str): Términos personalizados para la traducción

        Returns:
            str: Prompt completo para el refinamiento
        """
        prompt = self.refine_prompt_template
        prompt = prompt.replace("{source_lang}", source_lang)
        prompt = prompt.replace("{target_lang}", target_lang)
        prompt = prompt.replace("{source_text}", source_text.strip())
        prompt = prompt.replace("{translated_text}", translated_text.strip())

        # Reemplazar etiqueta de terminología si existen términos personalizados
        if custom_terms:
            # Formatear los términos personalizados
            terms = custom_terms.strip().split('\n')
            terms = [
                line if line.strip().startswith('- ') else f'- {line.strip()}'
                for line in terms
                if line.strip()
            ]
            formatted_terms = '\n'.join(terms)

            # Reemplazar la etiqueta {terminology_reference} con los términos formateados
            prompt = prompt.replace("{terminology_reference}", formatted_terms)
        else:
            # Si no hay términos personalizados, eliminar la etiqueta
            prompt = prompt.replace("{terminology_reference}", "")

        return prompt

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
                session_logger.log_info(f"Comprobación exitosa - Respuesta: {response}")
                return True
            elif cleaned_response == "no":
                session_logger.log_warning(f"Comprobación falló - Respuesta: {response}. Reintentando...")
                # Reintentar una vez
                time.sleep(5)
                response_retry = query_model()
                if response_retry is None:
                    session_logger.log_error("Error en la comprobación de la traducción (reintento respuesta nula)")
                    return False
                if response_retry.strip().lower() == "yes":
                    session_logger.log_info(f"Comprobación exitosa en reintento - Respuesta: {response_retry}")
                    return True
                else:
                    session_logger.log_error(f"Comprobación falló en reintento - Respuesta: {response_retry}")
                    return False
            else:
                session_logger.log_error(f"Respuesta inesperada en comprobación: '{response}'")
                return False
        except Exception as e:
            session_logger.log_error(f"Error al hacer la comprobación: {str(e)}")
            return False

    def _refine_translation(self, source_text: str, translated_text: str,
                           source_lang: str, target_lang: str,
                           api_key: str, provider: str, model: str,
                           custom_terms: str = "") -> Optional[str]:
        """
        Refina la traducción usando la API.

        Args:
            source_text (str): Texto original
            translated_text (str): Texto traducido a refinar
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino
            api_key (str): API key
            provider (str): Proveedor
            model (str): Modelo
            custom_terms (str): Términos personalizados para la traducción

        Returns:
            Optional[str]: Texto refinado si tiene éxito, None si falla o error
        """
        prompt = self._build_refine_prompt(source_lang, target_lang, source_text, translated_text, custom_terms)

        provider_config = self.models_config.get(provider)
        if not provider_config:
            print(f"Proveedor no soportado para refinamiento: {provider}")
            return None

        model_config = provider_config['models'].get(model)
        if not model_config:
            print(f"Modelo no soportado para refinamiento: {model}")
            return None

        try:
            response = translator_req.translate_segment(
                provider,
                "",  # texto ya incluido en prompt, pasar vacío para evitar doble agregado
                api_key,
                model_config,
                prompt
            )

            if response is None:
                session_logger.log_error("Error en el refinamiento de la traducción (respuesta nula)")
                return None

            return response

        except Exception as e:
            session_logger.log_error(f"Error al hacer el refinamiento: {str(e)}")
            return None

    def translate_text(self, text: str, source_lang: str, target_lang: str,
                      api_key: str, provider: str, model: str,
                      custom_terms: str = "", enable_check: bool = True,
                      enable_refine: bool = False) -> Optional[str]:
        """
        Traduce el texto utilizando el proveedor y modelo especificados.

        Agrega refinamiento de la traducción si enable_refine=True y
        comprobación de la traducción tras completarla si enable_check=True.

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

        Returns:
            Optional[str]: Texto traducido si la comprobación pasa o no se realiza, None si falla o error
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
                session_logger.log_info(f"Traduciendo segmento {i} de {len(segments)}")

                # Construir prompt base con reemplazo de etiquetas
                prompt = self.prompt_template.replace(
                    "{source_lang}", source_lang
                ).replace(
                    "{target_lang}", target_lang
                )

                # Reemplazar etiqueta de terminología si existen términos personalizados
                if custom_terms:
                    # Formatear los términos personalizados
                    terms = custom_terms.strip().split('\n')
                    terms = [
                        line if line.strip().startswith('- ') else f'- {line.strip()}'
                        for line in terms
                        if line.strip()
                    ]
                    formatted_terms = '\n'.join(terms)

                    # Reemplazar la etiqueta {terminology_reference} con los términos formateados
                    prompt = prompt.replace("{terminology_reference}", formatted_terms)
                else:
                    # Si no hay términos personalizados, eliminar la etiqueta
                    prompt = prompt.replace("{terminology_reference}", "")

                # Reemplazar la etiqueta {text_to_translate} con el segmento actual
                prompt = prompt.replace("{text_to_translate}", segment)

                # Delegar la petición al módulo translator_req
                translated_segment = translator_req.translate_segment(
                    provider,
                    segment,
                    api_key,
                    model_config,
                    prompt
                )

                if translated_segment is None:
                    session_logger.log_error(f"Error traduciendo segmento {i}")
                    raise ValueError(f"Error traduciendo segmento {i}")

                # Si enable_refine está habilitado, refinar la traducción del segmento
                if enable_refine:
                    session_logger.log_info(f"Refinando segmento {i} de {len(segments)}")
                    refined_segment = self._refine_translation(
                        source_text=segment,
                        translated_text=translated_segment,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        api_key=api_key,
                        provider=provider,
                        model=model,
                        custom_terms=custom_terms
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

            # Si enable_check está habilitado, hacer comprobación
            if enable_check:
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
                    session_logger.log_error("La comprobación de la traducción NO pasó.")
                    return None

            # Si pasa la comprobación o no se realiza, devolver la traducción completa
            return full_translation

        except Exception as e:
            session_logger.log_error(f"Error en la traducción: {str(e)}")
            return None

    def get_supported_languages(self) -> Dict[str, str]:
        """
        Obtiene la lista de idiomas soportados.
        Retorna un diccionario con las claves como nombres para mostrar en la GUI
        y las claves mismas como valores para identificar el idioma.
        """
        # Retornar las claves como display names y como valores para la GUI
        return {k: k for k in self.lang_codes.keys()}

    def get_language_code_for_translation(self, display_name: str) -> str:
        """
        Obtiene el código de idioma real para usar en la traducción.

        Args:
            display_name: Nombre mostrado en la GUI (ej: "Español (MX)")

        Returns:
            Código de idioma para la traducción (ej: "Spanish (México)")
        """
        return self.lang_codes.get(display_name, display_name)
