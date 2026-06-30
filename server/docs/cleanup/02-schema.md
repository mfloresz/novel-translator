# 02 — Schema de structured output

El LLM devuelve un array plano. Una sola propiedad por elemento. El backend valida antes de aplicar nada.

## schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "translator-server://cleanup.schema.json",
  "title": "Cleanup",
  "type": "array",
  "minItems": 0,
  "maxItems": 5,
  "items": {
    "type": "object",
    "required": ["text"],
    "additionalProperties": false,
    "properties": {
      "text": { "type": "string", "minLength": 1, "maxLength": 200 }
    }
  }
}
```

## ejemplo válido

```json
[
  {"text":"If you enjoyed this chapter, support me on Patreon."},
  {"text":"ko-fi.com/example"},
  {"text":"Next chapter preview: The black tower."}
]
```

## ejemplo vacío

```json
[]
```

## errores (backend responde 422)

| caso                              | mensaje                              |
|-----------------------------------|--------------------------------------|
| elemento sin `text`               | `missing "text"`                     |
| `text` vacío                      | `"text" is empty`                    |
| `text` > 200 chars                | `"text" too long (max 200)`          |
| más de 5 elementos                | `too many entries (max 5)`           |
| campo extra (`reason`, `target`…) | `unknown field "reason"`             |

## uso en los providers

**OpenAI**:
```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "cleanup",
      "schema": { /* el de arriba */ }
    }
  }
}
```



## request del usuario al backend

```json
POST /api/db/chapters/{id}/cleanup
{
  "dryRun": false,
  "lines": [
    {"text":"If you enjoyed this chapter..."}
  ]
}
```

`lines` es el mismo array que produce el LLM. El backend no transforma nombres.

## response del backend

```json
{
  "before": "...",
  "after": "...",
  "removed": 3,
  "warnings": ["text not found: \"Buy me a coffee\""]
}
```

Sin `diff` estructurado en v1: `before` y `after` bastan para que la UI muestre el cambio.
