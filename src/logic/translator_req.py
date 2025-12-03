import requests
import os
from typing import Optional, Dict
from src.logic.session_logger import session_logger

def translate_segment(provider: str,
                      text: str,
                      api_key: str,
                      model_config: Dict,
                      prompt: str,
                      models_config: Dict,
                      timeout: int = 120) -> Optional[str]:
    """
    Envía el prompt al proveedor seleccionado y maneja la respuesta.

    Args:
        provider (str): Identificador del proveedor ('gemini', 'hyperbolic', 'chutes', 'mistral')
        text (str): Texto a traducir (ya incluido en el prompt)
        api_key (str): API key para autenticación
        model_config (Dict): Configuración del modelo seleccionado
        prompt (str): Prompt completo incluyendo instrucciones y texto a traducir

    Returns:
        Optional[str]: Texto traducido recibido o None en caso de error
    """
    try:
        # Para verificación de traducción, el texto está en el prompt, no en text
        text_length = len(text) if text else len(prompt)
        session_logger.log_api_request(provider, model_config.get('model_id', model_config.get('endpoint', 'unknown')), text_length)

        provider_config = models_config.get(provider)
        if not provider_config:
            raise ValueError(f"Proveedor no encontrado en configuración: {provider}")

        result = None
        if provider == 'gemini':
            result = _translate_gemini(provider_config, api_key, model_config, prompt, timeout)
        elif provider in ['hyperbolic', 'chutes', 'mistral']:
            result = _translate_openai_like(provider_config, api_key, model_config, prompt, timeout)
        else:
            raise ValueError(f"Proveedor no implementado: {provider}")

        if result:
            session_logger.log_api_response(provider, True)
        else:
            session_logger.log_api_response(provider, False, error_message="No se obtuvo respuesta válida")

        return result
    except Exception as e:
        error_msg = f"Error traduciendo segmento con proveedor {provider}: {str(e)}"
        session_logger.log_api_response(provider, False, error_message=error_msg)
        print(error_msg)
        return None

def _translate_gemini(provider_config: Dict, api_key: str, model_config: Dict, prompt: str, timeout: int = 120) -> Optional[str]:
    try:
        url = f"{provider_config['base_url']}/{model_config['endpoint']}?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": model_config.get('temperature', 0.6)
            }
        }
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        return _process_response(provider_config['type'], response.json(), model_config.get('thinking', False))
    except requests.exceptions.RequestException as e:
        error_msg = f"Error HTTP Gemini: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response('gemini', False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None




def _translate_openai_like(provider_config: Dict, api_key: str, model_config: Dict, prompt: str, timeout: int = 120) -> Optional[str]:
    try:
        url = provider_config['base_url']
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        if provider_config.get('name') == 'Mistral':
            headers['Accept'] = 'application/json'
        data = {
            "model": model_config['endpoint'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": model_config.get('temperature', 0.6),
            "top_p": model_config.get('top_p', 0.95),
            "max_tokens": model_config.get('max_tokens', 4096),
            "stream": False
        }
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        return _process_response(provider_config['type'], response.json(), model_config.get('thinking', False))
    except Exception as e:
        error_msg = f"Error {provider_config['name']}: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response(provider_config.get('name', 'openai').lower(), False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None



def _process_response(provider_type: str, response: Dict, thinking: bool = False) -> Optional[str]:
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
        if provider_type == 'openai':
            if 'choices' not in response or not response['choices']:
                return None
            message = response['choices'][0]['message']
            if 'content' not in message:
                return None
            content = message['content']
            if thinking and isinstance(content, list):
                # Extraer solo los textos de type "text"
                texts = [item['text'] for item in content if item.get('type') == 'text']
                raw_text = '\n'.join(texts)
            else:
                raw_text = content if isinstance(content, str) else ""
            return _clean_translation(raw_text)
        elif provider_type == 'gemini':
            if 'candidates' not in response or not response['candidates']:
                return None
            candidate = response['candidates'][0]
            if 'content' not in candidate or 'parts' not in candidate['content']:
                return None
            parts = candidate['content']['parts']
            if not parts or 'text' not in parts[0]:
                return None
            translated_text = parts[0]['text']
            return _clean_translation(translated_text)
        else:
            raise ValueError(f"Tipo de proveedor no soportado: {provider_type}")
    except Exception as e:
        error_msg = f"Error procesando respuesta del tipo {provider_type}: {str(e)}"
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
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Si solo hay </think> al final, remover todo antes de él
    text = re.sub(r'.*?</think>', '', text, flags=re.DOTALL)

    lines = text.split('\n')
    actual_translation = []
    translation_started = False

    for line in lines:
        if translation_started or (
            not line.startswith('-') and
            'Requirements:' not in line and
            'Translation:' not in line
        ):
            translation_started = True
            actual_translation.append(line)

    return '\n'.join(actual_translation).strip()
