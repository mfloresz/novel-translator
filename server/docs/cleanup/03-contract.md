# 03 — Contrato del backend (v1, solo `original`)

El backend **nunca** confía en el LLM. Si algo no encaja con este documento, responde 422 y no aplica nada.

## alcance de v1

- Aplica **solo** sobre `chapter.originalContent`.
- Las variantes `translated` y `refined` son **v2** (otro prompt, otra ruta, mismo schema).
- Operación única: borrar líneas cuyo inicio coincide con un `text` dado.
- Sin razones, sin categorías, sin regex, sin rangos.

## endpoints

| método | ruta                                          | efecto                                  |
|--------|-----------------------------------------------|-----------------------------------------|
| POST   | `/api/db/chapters/{id}/cleanup:preview`       | ejecuta en memoria, devuelve before/after |
| POST   | `/api/db/chapters/{id}/cleanup:apply`         | igual + persiste en `originalContent`   |

request:
```json
{ "dryRun": false, "lines": [{"text":"..."}] }
```

response:
```json
{
  "before": "...",
  "after":  "...",
  "removed": 3,
  "warnings": ["text not found: \"...\""]
}
```

## validaciones obligatorias (en orden)

1. **Schema** — el de `02-schema.md`. Falla → 422 con el path.
2. **`len(lines) <= 5`** — por request, sin excepción.
3. **Dedupe** — si dos `text` son idénticos, el segundo se ignora silenciosamente.
4. **Cap de longitud** — `len(text) <= 200`. Más → 422.

No hay validación de `target`: el backend lo hardcodea a `original` y rechaza 501 cualquier intento del cliente de pasarlo.

## algoritmo de aplicación

```
input:  chapter.originalContent (string), lines (array de {text})
output: string limpio, count int, warnings []string

1. split por "\n" → lines_in
2. normalizar cada línea con trim de whitespace al inicio/fin
3. para cada {text} en lines:
     buscar TODAS las líneas que, tras trim, empiezan con text
     si no hay match → warnings.append("text not found: " + text)
     si hay match → marcarlas para borrar
4. reconstruir el texto sin las líneas marcadas
5. colapsar runs de líneas vacías a máximo 1 (evita gaps visuales)
6. devolver texto resultante + count + warnings
```

Punto importante: el matching es **prefix**, no equality. El modelo puede citar el inicio de la línea (lo más fácil) o la línea entera. Ambos funcionan.

## dry-run vs apply

| `dryRun` | efecto                                       |
|----------|----------------------------------------------|
| `true`   | calcula before/after, no escribe, no toca `updatedAt` |
| `false`  | escribe en `originalContent`, actualiza `updatedAt`     |

`status` del capítulo **no** cambia. Limpieza no es un nuevo estado, es un mutate.

## auditoría (mínima, una tabla)

```sql
CREATE TABLE cleanup_audit (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    input_json TEXT NOT NULL,    -- el body crudo que envió el cliente
    before_content TEXT NOT NULL,
    after_content TEXT NOT NULL,
    removed_count INTEGER NOT NULL,
    warnings_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
);
```

Sirve para: rollback manual (`chapter.originalContent = audit.before_content`), depurar falsos positivos, mejorar el prompt.

## rate limits

- 30 req/min por IP para `:preview`.
- 10 req/min por IP para `:apply`.

## lo que el backend **nunca** hace

- ❌ Aceptar `pattern` (regex) del LLM o del cliente.
- ❌ Aceptar `target` distinto de `original`. Si llega, 400.
- ❌ Aplicar un diff donde `len(after) < len(before) * 0.5`. Devuelve 409 — probable borrado masivo accidental.
- ❌ Llamar a otro LLM en cascada para "verificar". La única verificación es la diff que ve el humano en la UI.
- ❌ Cambiar `status` del capítulo.

## v2 (no implementar todavía)

- Variantes para `translatedContent` y `refinedContent`: otro `systemPrompt`, otra ruta o flag `target` server-side.
- Categorías cerradas (mapa de regex mantenido por humanos) para casos recurrentes.
- Operación "remove paragraph" para CTAs multilínea.
- Job bulk `operation: "cleanup"` con lista de capítulos.
