"""Utilidades para escapar caracteres XML/HTML"""


def escape_xml(text: str) -> str:
    """
    Escapa caracteres especiales XML/HTML.
    
    Convierte caracteres especiales a sus entidades XML equivalentes:
    - & → &amp;
    - < → &lt;
    - > → &gt;
    - " → &quot;
    - ' → &apos;
    
    Args:
        text: Texto a escapar
        
    Returns:
        Texto con caracteres especiales escapados
    """
    if not isinstance(text, str):
        text = str(text)
    
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))
