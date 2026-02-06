#!/usr/bin/env python3
"""
Script de prueba para el nuevo sistema de refinamiento con formato diff.
Prueba el prompt refine_alt.txt que genera instrucciones XML de cambios.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from logic.translator import TranslatorLogic

def main():
    # Cargar variables de entorno
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        print("Error: Archivo .env no encontrado")
        return 1

    # Leer API key
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print("Error: CHUTES_API_KEY no encontrada en .env")
        return 1

    print("✓ API key cargada")

    # Leer archivos de prueba
    try:
        with open('original.txt', 'r', encoding='utf-8') as f:
            original_text = f.read()
        with open('translated.txt', 'r', encoding='utf-8') as f:
            translated_text = f.read()
    except FileNotFoundError as e:
        print(f"Error: Archivo no encontrado: {e}")
        return 1

    print("✓ Archivos de prueba leídos")

    # Crear instancia del traductor
    translator = TranslatorLogic()

    # Configurar parámetros
    source_lang = "English"
    target_lang = "Spanish (MX)"
    provider = "mistral"
    model = "mistral-creative"  # Correspondiente a Qwen/Qwen3-Next-80B-A3B-Instruct

    print(f"✓ Configuración: {provider}/{model}")
    print(f"✓ Idiomas: {source_lang} → {target_lang}")

    # Realizar refinamiento con el nuevo prompt
    print("🔄 Iniciando refinamiento con prompt alternativo...")

    try:
        # Para capturar la respuesta del modelo, necesitamos simular el proceso
        # Primero, construir el prompt
        prompt = translator._build_refine_prompt(
            source_lang, target_lang, original_text, translated_text, "", "refine_alt.txt"
        )

        # Obtener configuración del modelo
        models_config = translator.models_config
        provider_config = models_config.get(provider)
        if not provider_config:
            print(f"❌ Error: Proveedor no encontrado: {provider}")
            return 1

        model_config = provider_config['models'].get(model)
        if not model_config:
            print(f"❌ Error: Modelo no encontrado: {model}")
            return 1

        # Importar el módulo de requests del traductor
        from logic.translator_req import translate_segment

        print("🔄 Llamando al modelo...")

        # Hacer la llamada al modelo directamente para capturar la respuesta
        model_response = translate_segment(
            provider,
            "",  # texto ya incluido en prompt
            api_key,
            model_config,
            prompt,
            models_config,
            300  # timeout
        )

        if model_response is None:
            print("❌ Error: Respuesta nula del modelo")
            return 1

        # Guardar la respuesta cruda del modelo
        with open('model_response.txt', 'w', encoding='utf-8') as f:
            f.write(model_response)

        print("✓ Respuesta del modelo guardada en model_response.txt")

        # Aplicar los cambios usando la función del traductor
        refined_text = translator._apply_refinement_changes(translated_text, model_response)

        # Guardar el resultado aplicado
        with open('translated_test.txt', 'w', encoding='utf-8') as f:
            f.write(refined_text)

        print("✓ Resultado refinado guardado en translated_test.txt")
        print("✓ Prueba completada exitosamente")
        print(f"✓ Longitud del texto original: {len(translated_text)} caracteres")
        print(f"✓ Longitud del texto refinado: {len(refined_text)} caracteres")

        return 0

    except Exception as e:
        print(f"❌ Error durante el refinamiento: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())