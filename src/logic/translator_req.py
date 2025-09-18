import requests
import os
from typing import Optional, Dict
from src.logic.session_logger import session_logger

def translate_segment(provider: str,
                      text: str,
                      api_key: str,
                      model_config: Dict,
                      prompt: str) -> Optional[str]:
    """
    Envía el prompt al proveedor seleccionado y maneja la respuesta.

    Args:
        provider (str): Identificador del proveedor ('gemini', 'together', 'deepinfra', 'openai')
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

        result = None
        if provider == 'gemini':
            result = _translate_gemini(api_key, model_config, prompt)
        elif provider == 'together':
            result = _translate_together(api_key, model_config, prompt)
        elif provider == 'deepinfra':
            result = _translate_deepinfra(api_key, model_config, prompt)
        elif provider == 'openai':
            result = _translate_openai(api_key, model_config, prompt)
        elif provider == 'openrouter':
            result = _translate_openrouter(api_key, model_config, prompt)
        elif provider == 'hyperbolic':
            result = _translate_hyperbolic(api_key, model_config, prompt)
        elif provider == 'chutes':
            result = _translate_chutes(api_key, model_config, prompt)
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

def _translate_gemini(api_key: str, model_config: Dict, prompt: str) -> Optional[str]:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_config['endpoint']}?key={api_key}"
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
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return _process_gemini_response(response.json())
    except requests.exceptions.RequestException as e:
        error_msg = f"Error HTTP Gemini: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response('gemini', False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None

def _translate_together(api_key: str, model_config: Dict, prompt: str) -> Optional[str]:
    try:
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": model_config['model_id'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": model_config.get('temperature', 0.6),
            "top_p": 0.95,
            "top_k": 55,
            "repetition_penalty": 1.2,
            "stop": ["</s>", "[/INST]"],
            "max_tokens": model_config.get('max_tokens', 4096),
            "stream": False
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return _process_together_response(response.json())
    except Exception as e:
        error_msg = f"Error Together AI: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response:
            response_text = e.response.text
        session_logger.log_api_response('together', False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None

def _translate_deepinfra(api_key: str, model_config: Dict, prompt: str) -> Optional[str]:
    try:
        url = "https://api.deepinfra.com/v1/openai/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": model_config['model_id'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": model_config.get('temperature', 0.6),
            "top_p": 0.95,
            "max_tokens": 100000,
            "stream": False
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return _process_deepinfra_response(response.json())
    except Exception as e:
        error_msg = f"Error DeepInfra: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response('deepinfra', False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None

def _translate_openai(api_key: str, model_config: Dict, prompt: str) -> Optional[str]:
    import requests
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_config['model_id'],  # Asegúrate que sea modelo válido
            "messages": [
                {"role": "system", "content": "Eres un traductor literario profesional."},  # Opcional, mejora contexto
                {"role": "user", "content": prompt}
            ],
            "temperature": model_config.get('temperature', 0.6),
            "max_tokens": model_config.get('max_tokens', 4096),
            "top_p": 0.95,
            "n": 1
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        json_response = response.json()
        content = json_response['choices'][0]['message']['content']
        return _clean_translation(content)
    except requests.exceptions.RequestException as e:
        error_msg = f"Error HTTP OpenAI: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response is not None:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response('openai', False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None
    except Exception as e:
        error_msg = f"Error procesando respuesta OpenAI: {str(e)}"
        session_logger.log_api_response('openai', False, error_message=error_msg)
        print(error_msg)
        return None

def _process_gemini_response(response: Dict) -> Optional[str]:
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
        return _clean_translation(translated_text)
    except Exception as e:
        error_msg = f"Error procesando respuesta de Gemini: {str(e)}"
        print(error_msg)
        return None

def _process_together_response(response: Dict) -> Optional[str]:
    try:
        if 'choices' not in response or not response['choices']:
            return None
        message = response['choices'][0]['message']
        if 'content' not in message:
            return None
        return _clean_translation(message['content'])
    except Exception as e:
        error_msg = f"Error procesando respuesta de Together: {str(e)}"
        print(error_msg)
        return None

def _process_deepinfra_response(response: Dict) -> Optional[str]:
    try:
        if 'choices' not in response or not response['choices']:
            return None
        message = response['choices'][0]['message']
        if 'content' not in message:
            return None
        return _clean_translation(message['content'])
    except Exception as e:
        error_msg = f"Error procesando respuesta de DeepInfra: {str(e)}"
        print(error_msg)
        return None

def _translate_openrouter(api_key: str, model_config: Dict, prompt: str) -> Optional[str]:
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Headers opcionales para OpenRouter
        referer = os.getenv("OPENROUTER_REFERER")
        if referer:
            headers["HTTP-Referer"] = referer
        title = os.getenv("OPENROUTER_TITLE")
        if title:
            headers["X-Title"] = title

        data = {
            "model": model_config['endpoint'],  # Usa el endpoint como model_id, ej: "openrouter/sonoma-dusk-alpha"
            "messages": [{"role": "user", "content": prompt}],
            "temperature": model_config.get('temperature', 0.6),
            "max_tokens": model_config.get('max_tokens', 4096),
            "top_p": 0.95,
            "stream": False
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        json_response = response.json()
        content = json_response['choices'][0]['message']['content']
        return _clean_translation(content)
    except requests.exceptions.RequestException as e:
        error_msg = f"Error HTTP OpenRouter: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response is not None:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response('openrouter', False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None
    except Exception as e:
        error_msg = f"Error procesando respuesta OpenRouter: {str(e)}"
        session_logger.log_api_response('openrouter', False, error_message=error_msg)
        print(error_msg)
        return None

def _translate_hyperbolic(api_key: str, model_config: Dict, prompt: str) -> Optional[str]:
    try:
        url = "https://api.hyperbolic.xyz/v1/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": model_config['model_id'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": model_config.get('temperature', 0.6),
            "top_p": 0.95,
            "max_tokens": model_config.get('max_tokens', 4096),
            "stream": False
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return _process_hyperbolic_response(response.json())
    except Exception as e:
        error_msg = f"Error Hyperbolic: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response('hyperbolic', False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None

def _process_hyperbolic_response(response: Dict) -> Optional[str]:
    try:
        if 'choices' not in response or not response['choices']:
            return None
        message = response['choices'][0]['message']
        if 'content' not in message:
            return None
        return _clean_translation(message['content'])
    except Exception as e:
        error_msg = f"Error procesando respuesta de Hyperbolic: {str(e)}"
        print(error_msg)
        return None

def _translate_chutes(api_key: str, model_config: Dict, prompt: str) -> Optional[str]:
    try:
        url = "https://llm.chutes.ai/v1/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": model_config['endpoint'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": model_config.get('temperature', 0.6),
            "max_tokens": model_config.get('max_tokens', 4096),
            "stream": False
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return _process_chutes_response(response.json())
    except Exception as e:
        error_msg = f"Error Chutes AI: {str(e)}"
        response_text = None
        if hasattr(e, 'response') and e.response:
            response_text = e.response.text
            error_msg += f"\nRespuesta detallada: {response_text}"
        session_logger.log_api_response('chutes', False, response_text=response_text, error_message=error_msg)
        print(error_msg)
        return None

def _process_chutes_response(response: Dict) -> Optional[str]:
    try:
        if 'choices' not in response or not response['choices']:
            return None
        message = response['choices'][0]['message']
        if 'content' not in message:
            return None
        return _clean_translation(message['content'])
    except Exception as e:
        error_msg = f"Error procesando respuesta de Chutes AI: {str(e)}"
        print(error_msg)
        return None

def _clean_translation(text: str) -> str:
    """
    Limpia el texto recibido del proveedor para eliminar encabezados o texto adicional no deseado.

    Args:
        text (str): Texto sin procesar

    Returns:
        str: Texto limpio y listo para usar
    """
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
