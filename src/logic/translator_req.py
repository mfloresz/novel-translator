import os
import json
from typing import Dict, Optional

import requests

from src.logic.session_logger import session_logger


def translate_segment(
    provider: str,
    text: str,
    api_key: str,
    model_config: Dict,
    prompt: str,
    models_config: Dict,
    timeout: int = 120,
) -> Optional[str]:
    """
    Envía el prompt al proveedor seleccionado y maneja la respuesta.

    Args:
        provider (str): Identificador del proveedor ('gemini', 'hyperbolic', 'chutes', 'mistral')
        text (str): Texto a traducir (ya incluido en el prompt)
        api_key (str): API key para autenticación
        model_config (Dict): Configuración del modelo seleccionado
        prompt (str): Prompt completo incluyendo instrucciones y texto a traducir
        models_config (Dict): Configuración de todos los modelos
        timeout (int): Tiempo de espera para la petición

    Returns:
        Optional[str]: Texto traducido recibido o None en caso de error
    """
    try:
        # Para verificación de traducción, el texto está en el prompt, no en text
        # Si text está vacío, usar la longitud del prompt para estimar el tamaño
        text_length = len(text) if text else len(prompt)
        
        # Si el prompt es un diccionario con messages, estimar longitud basada en el contenido
        if isinstance(prompt, dict) and "messages" in prompt:
            total_length = 0
            for message in prompt["messages"]:
                if "content" in message:
                    total_length += len(message["content"])
            text_length = total_length
        
        session_logger.log_api_request(
            provider,
            model_config.get("model_id", model_config.get("endpoint", "unknown")),
            text_length,
        )

        provider_config = models_config.get(provider)
        if not provider_config:
            raise ValueError(f"Proveedor no encontrado en configuración: {provider}")

        result = None
        if provider_config["type"] == "gemini":
            result = _translate_gemini(
                provider_config, api_key, model_config, prompt, timeout
            )
        elif provider_config["type"] == "openai":
            result = _translate_openai_like(
                provider_config, api_key, model_config, prompt, timeout
            )
        else:
            raise ValueError(
                f"Tipo de proveedor no soportado: {provider_config['type']}"
            )

        if result:
            session_logger.log_api_response(provider, True)
        else:
            session_logger.log_api_response(
                provider, False, error_message="No se obtuvo respuesta válida"
            )

        return result
    except Exception as e:
        error_msg = f"Error traduciendo segmento con proveedor {provider}: {str(e)}"
        session_logger.log_api_response(provider, False, error_message=error_msg)
        print(error_msg)
        return None


def _translate_gemini(
    provider_config: Dict,
    api_key: str,
    model_config: Dict,
    prompt: str,
    timeout: int = 120,
) -> Optional[str]:
    try:
        url = f"{provider_config['base_url']}/{model_config['endpoint']}?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        # Determinar el formato del prompt (string o dict con messages)
        contents = []
        if isinstance(prompt, dict) and "messages" in prompt:
            # Nuevo formato con roles system/user - convertir a formato Gemini
            for message in prompt["messages"]:
                role = message.get("role", "user")
                content = message.get("content", "")
                # Gemini usa "parts" en lugar de "content" y no tiene roles como OpenAI
                # Para Gemini, simplemente usamos el contenido sin distinguir roles
                contents.append({"parts": [{"text": content}]})
        else:
            # Formato antiguo: solo texto en prompt
            contents = [{"parts": [{"text": prompt}]}]
        
        data = {
            "contents": contents,
            "generationConfig": {"temperature": model_config.get("temperature", 0.6)},
        }
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        
        # Procesar respuesta según si es streaming o no
        if model_config.get("stream", False):
            return _process_streaming_response(
                provider_config["type"],
                response,
                model_config.get("thinking", False),
            )
        else:
            return _process_response(
                provider_config["type"],
                response.json(),
                model_config.get("thinking", False),
            )
    except requests.exceptions.RequestException as e:
        error_msg = f"Error HTTP Gemini: {str(e)}"
        response_text = None
        if hasattr(e, "response") and e.response:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response(
            "gemini", False, response_text=response_text, error_message=error_msg
        )
        print(error_msg)
        return None


def _translate_openai_like(
    provider_config: Dict,
    api_key: str,
    model_config: Dict,
    prompt: str,
    timeout: int = 120,
) -> Optional[str]:
    try:
        url = provider_config["base_url"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider_config.get("name") == "Mistral":
            headers["Accept"] = "application/json"
        # Determinar el formato del prompt (string o dict con messages)
        messages = []
        if isinstance(prompt, dict) and "messages" in prompt:
            # Nuevo formato con roles system/user
            messages = prompt["messages"]
        else:
            # Formato antiguo: solo texto en prompt
            messages = [{"role": "user", "content": prompt}]
        
        data = {
            "model": model_config["endpoint"],
            "messages": messages,
            **(
                {"temperature": model_config["temperature"]}
                if model_config.get("temperature") is not None
                else {}
            ),
            **(
                {"top_p": model_config["top_p"]}
                if model_config.get("top_p") is not None
                else {}
            ),
            **(
                {"max_tokens": model_config["max_tokens"]}
                if model_config.get("max_tokens") is not None
                else {}
            ),
            "stream": model_config.get("stream", False),
        }

        # Incluir parámetro 'reasoning' si está configurado en el modelo
        if model_config.get("include_reasoning", False):
            data["reasoning"] = {"enabled": model_config.get("reasoning", False)}

        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        
        # Procesar respuesta según si es streaming o no
        if model_config.get("stream", False):
            return _process_streaming_response(
                provider_config["type"],
                response,
                model_config.get("thinking", False),
            )
        else:
            return _process_response(
                provider_config["type"],
                response.json(),
                model_config.get("thinking", False),
            )
    except Exception as e:
        error_msg = f"Error {provider_config['name']}: {str(e)}"
        response_text = None
        if hasattr(e, "response") and e.response:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response(
            provider_config.get("name", "openai").lower(),
            False,
            response_text=response_text,
            error_message=error_msg,
        )
        print(error_msg)
        return None


def _process_response(
    provider_type: str, response: Dict, thinking: bool = False
) -> Optional[str]:
    """
    Procesa la respuesta del proveedor basado en su tipo y configuración de thinking.

    Args:
        provider_type (str): Tipo de proveedor ('openai' o 'gemini')
        response (Dict): Respuesta JSON del proveedor
        thinking (bool): Si True, maneja respuestas con thinking tokens

    Returns:
        Optional[str]: Texto traducido limpio o None si hay error
    """
    try:
        if provider_type == "openai":
            if "choices" not in response or not response["choices"]:
                return None
            message = response["choices"][0]["message"]
            if "content" not in message:
                return None
            content = message["content"]
            if thinking and isinstance(content, list):
                # Extraer solo los textos de type "text"
                texts = [item["text"] for item in content if item.get("type") == "text"]
                raw_text = "\n".join(texts)
            else:
                raw_text = content if isinstance(content, str) else ""
            return _clean_translation(raw_text)
        elif provider_type == "gemini":
            if "candidates" not in response or not response["candidates"]:
                return None
            candidate = response["candidates"][0]
            if "content" not in candidate or "parts" not in candidate["content"]:
                return None
            parts = candidate["content"]["parts"]
            if not parts or "text" not in parts[0]:
                return None
            translated_text = parts[0]["text"]
            return _clean_translation(translated_text)
        else:
            raise ValueError(f"Tipo de proveedor no soportado: {provider_type}")
    except Exception as e:
        error_msg = f"Error procesando respuesta del tipo {provider_type}: {str(e)}"
        print(error_msg)
        return None


def _process_streaming_response(
    provider_type: str, response, thinking: bool = False
) -> Optional[str]:
    """
    Procesa la respuesta en streaming del proveedor basado en su tipo y configuración de thinking.

    Args:
        provider_type (str): Tipo de proveedor ('openai' o 'gemini')
        response: Respuesta HTTP con streaming
        thinking (bool): Si True, maneja respuestas con thinking tokens

    Returns:
        Optional[str]: Texto traducido limpio o None si hay error
    """
    try:
        if provider_type == "openai":
            full_content = ""
            # Usar iter_lines() para manejar correctamente el buffering de líneas SSE
            for line in response.iter_lines():
                if line:
                    # Decodificar bytes a string si es necesario
                    line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                    line_str = line_str.strip()
                    
                    if line_str.startswith('data:'):
                        # Extraer el JSON de los datos
                        json_str = line_str[5:].strip()  # Remover 'data: ' y espacios
                        if json_str == '[DONE]':
                            break
                        try:
                            data = json.loads(json_str)
                            if data.get('choices'):
                                choice = data['choices'][0]
                                if 'delta' in choice:
                                    delta = choice['delta']
                                    if 'content' in delta and delta['content']:
                                        full_content += delta['content']
                        except json.JSONDecodeError:
                            # Ignorar líneas que no son JSON válido
                            pass
            
            if not full_content:
                return None
            
            return _clean_translation(full_content)
        else:
            raise ValueError(f"Streaming no soportado para tipo de proveedor: {provider_type}")
    except Exception as e:
        error_msg = f"Error procesando respuesta en streaming del tipo {provider_type}: {str(e)}"
        print(error_msg)
        return None


def _clean_translation(text: str) -> str:
    """
    Limpia el texto recibido del proveedor para eliminar encabezados o texto adicional no deseado.
    Para modelos thinking, elimina el bloque de pensamiento entre <think> y </think>.

    Args:
        text (str): Texto sin procesar

    Returns:
        str: Texto limpio y listo para usar
    """
    # Remover bloque de pensamiento si existe (para modelos thinking)
    import re

    # Remover desde <think> hasta </think> si existe el bloque completo
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Si solo hay </think> al final, remover todo antes de él
    text = re.sub(r".*?</think>", "", text, flags=re.DOTALL)

    lines = text.split("\n")
    actual_translation = []
    translation_started = False

    for line in lines:
        if translation_started or (
            not line.startswith("-")
            and "Requirements:" not in line
            and "Translation:" not in line
        ):
            translation_started = True
            actual_translation.append(line)

    return "\n".join(actual_translation).strip()
