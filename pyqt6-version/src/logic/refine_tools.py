"""
Definiciones de herramientas (tools) para el refinamiento de traducciones.

Este módulo contiene las definiciones de function calling que se usan
cuando el modelo soporta herramientas nativas para realizar cambios
quirúrgicos en el texto traducido.
"""

# Definición de tools para function calling en refinamiento
# Estas herramientas permiten al modelo realizar cambios precisos sin
# necesidad de regenerar todo el texto

REFINE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "replace_text",
            "description": "Replaces an exact substring in the translated document with a corrected version. Use this to fix translation errors, improve phrasing, or correct terminology.",
            "parameters": {
                "type": "object",
                "properties": {
                    "original": {
                        "type": "string",
                        "description": "The exact text fragment to find and replace (must match verbatim in the document)"
                    },
                    "replacement": {
                        "type": "string",
                        "description": "The corrected text that will replace the original"
                    }
                },
                "required": ["original", "replacement"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_text",
            "description": "Removes an exact substring from the translated document. Use this to remove redundant, hallucinated, or incorrectly added content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "original": {
                        "type": "string",
                        "description": "The exact text fragment to remove (must match verbatim)"
                    }
                },
                "required": ["original"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "insert_text",
            "description": "Inserts new text immediately after a reference anchor string in the document. Use this to add missing translations or content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "anchor": {
                        "type": "string",
                        "description": "The exact text after which the new content will be inserted (must match verbatim)"
                    },
                    "content": {
                        "type": "string",
                        "description": "The new text to insert after the anchor"
                    }
                },
                "required": ["anchor", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "no_changes_needed",
            "description": "Indicates that the translation is accurate and no modifications are required.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium"],
                        "description": "Confidence level that no changes are needed"
                    }
                },
                "required": ["confidence"]
            }
        }
    }
]


def get_refine_tools():
    """
    Retorna la lista de herramientas de refinamiento disponibles.
    
    Returns:
        list: Lista de definiciones de tools para function calling
    """
    return REFINE_TOOLS
