import requests
from typing import Optional, Dict

def translate_segment(provider: str,
                      text: str,
                      api_key: str,
                      model_config: Dict,
                      prompt: str) -> Optional[str]:
    """
    Envía el prompt al proveedor seleccionado y maneja la respuesta.

    Args:
        provider (str): Identificador del proveedor ('gemini', 'together', 'deepinfra')
        text (str): Texto a traducir (ya incluido en el prompt)
        api_key (str): API key para autenticación
        model_config (Dict): Configuración del modelo seleccionado
        prompt (str): Prompt completo incluyendo instrucciones y texto a traducir

    Returns:
        Optional[str]: Texto traducido recibido o None en caso de error
    """
    try:
        if provider == 'gemini':
            return _translate_gemini(api_key, model_config, prompt)
        elif provider == 'together':
            return _translate_together(api_key, model_config, prompt)
        elif provider == 'deepinfra':
            return _translate_deepinfra(api_key, model_config, prompt)
        else:
            raise ValueError(f"Proveedor no implementado: {provider}")
    except Exception as e:
        print(f"Error traduciendo segmento con proveedor {provider}: {str(e)}")
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
            }]
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return _process_gemini_response(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error HTTP Gemini: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print("Respuesta detallada:", e.response.text)
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
        return _process_together_response(response.json())
    except Exception as e:
        print(f"Error Together AI: {str(e)}")
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
            "temperature": 0.6,
            "top_p": 0.95,
            "max_tokens": 100000,
            "stream": False
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return _process_deepinfra_response(response.json())
    except Exception as e:
        print(f"Error DeepInfra: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print("Respuesta detallada:", e.response.text)
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
        print(f"Error procesando respuesta de Gemini: {str(e)}")
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
        print(f"Error procesando respuesta de Together: {str(e)}")
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
        print(f"Error procesando respuesta de DeepInfra: {str(e)}")
        return None

def _clean_translation(text: str) -> str:
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
