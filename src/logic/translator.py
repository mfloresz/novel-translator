import time
import json
import os
from dotenv import load_dotenv
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

    def _write_prompt_to_file(self, prompt: str, filename: str = "test_prompt.txt"):
        """
        Escribe el prompt en un archivo para fines de testing.

        Args:
            prompt (str): El prompt a escribir
            filename (str): Nombre del archivo (por defecto test_prompt.txt)
        """
        try:
            path = Path(__file__).parent.parent.parent / filename
            with open(path, 'w', encoding='utf-8') as f:
                f.write(prompt)
        except Exception as e:
            session_logger.log_error(f"Error escribiendo prompt a archivo: {e}")

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
        check_prompt_template = self._load_prompt("check.txt", source_lang, target_lang)
        prompt = check_prompt_template
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
        refine_prompt_template = self._load_prompt("refine.txt", source_lang, target_lang)
        prompt = refine_prompt_template
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
                            temp_api_keys: dict = None, retry_on_failure: bool = True) -> bool:
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
        prompt = self._build_check_prompt(source_lang, target_lang, original_text, translated_text)

        # Escribir prompt a archivo para testing
        self._write_prompt_to_file(prompt, "test_check_prompt.txt")

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
                prompt
            )

        def _parse_check_response(response: str) -> (bool, Optional[str]):
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
            response = query_model()
            if response is None:
                session_logger.log_error("Error en la comprobación de la traducción (respuesta nula)")
                return False

            is_ok, cause = _parse_check_response(response)

            if is_ok:
                session_logger.log_info(f"Comprobación exitosa - Respuesta: {response}")
                return True
            elif retry_on_failure:
                log_message = f"Comprobación falló - Respuesta: {response}"
                if cause:
                    log_message += f" - Causa: {cause}"
                session_logger.log_warning(f"{log_message}. Reintentando...")

                # Reintentar una vez
                time.sleep(5)
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
                    if cause_retry:
                        log_message_retry += f" - Causa: {cause_retry}"
                    session_logger.log_error(log_message_retry)
                    return False
            else:
                # No reintentar, retornar el resultado directamente
                log_message = f"Comprobación falló - Respuesta: {response}"
                if cause:
                    log_message += f" - Causa: {cause}"
                session_logger.log_error(log_message)
                return False
        except Exception as e:
            session_logger.log_error(f"Error al hacer la comprobación: {str(e)}")
            return False

    def _refine_translation(self, source_text: str, translated_text: str,
                           source_lang: str, target_lang: str,
                           main_api_key: str, refine_provider: str, refine_model: str,
                           custom_terms: str = "", temp_api_keys: dict = None) -> Optional[str]:
        """
        Refina la traducción usando la API.

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
        prompt = self._build_refine_prompt(source_lang, target_lang, source_text, translated_text, custom_terms)

        # Escribir prompt a archivo para testing
        self._write_prompt_to_file(prompt, "test_refine_prompt.txt")

        provider_config = self.models_config.get(refine_provider)
        if not provider_config:
            print(f"Proveedor no soportado para refinamiento: {refine_provider}")
            return None

        model_config = provider_config['models'].get(refine_model)
        if not model_config:
            print(f"Modelo no soportado para refinamiento: {refine_model}")
            return None

        try:
            response = translator_req.translate_segment(
                refine_provider,
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

    def _perform_translation(self, text: str, source_lang: str, target_lang: str,
                            api_key: str, provider: str, model: str,
                            custom_terms: str, enable_refine: bool,
                            refine_provider: str, refine_model: str,
                            temp_api_keys: dict) -> Optional[str]:
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

            # Segmentar el texto
            segments = self._segment_text(text)
            translated_segments = []

            # Traducir cada segmento
            for i, segment in enumerate(segments, 1):
                session_logger.log_info(f"Traduciendo segmento {i} de {len(segments)} con {provider}/{model}")

                # Construir prompt base con reemplazo de etiquetas
                prompt_template = self._load_prompt("translation.txt", source_lang, target_lang)
                prompt = prompt_template.replace(
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

                # Escribir prompt a archivo para testing
                self._write_prompt_to_file(prompt)

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
                        main_api_key=api_key,
                        refine_provider=refine_provider,
                        refine_model=refine_model,
                        custom_terms=custom_terms,
                        temp_api_keys=temp_api_keys
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
                       temp_api_keys: dict = None) -> Optional[str]:
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
            custom_terms, enable_refine, refine_provider, refine_model, temp_keys
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
                temp_api_keys=temp_keys,
                retry_on_failure=False  # No reintentar verificación internamente
            )

            if not check_passed:
                session_logger.log_warning("La comprobación inicial falló. Reintentando traducción completa...")

                # Reintento de traducción completa
                session_logger.log_info("Iniciando reintento de traducción")
                retry_translation = self._perform_translation(
                    text, source_lang, target_lang, api_key, provider, model,
                    custom_terms, enable_refine, refine_provider, refine_model, temp_keys
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
                    temp_api_keys=temp_keys,
                    retry_on_failure=False  # No reintentar verificación internamente
                )

                if not check_passed_retry:
                    session_logger.log_error("La comprobación del reintento también falló. Traducción marcada como fallida.")
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

    
