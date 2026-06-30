# Database Codemap

**Last Updated:** 2026-06-30
**Engine:** SQLite (via embedded PocketBase)
**Schema Management:** Code-defined in `internal/store/store_schema.go` with idempotent `ensureField` migrations

## Collections

### `users` — Auth multiusuario

| Field | Type | Notes |
|-------|------|-------|
| `id` | text | PK, auto |
| `email` | text | Unique, login |
| `password` | text | Hashed by PB |
| `name` | text | Display name |
| `theme` | text | `light`, `dark`, `system` |
| `created` | autodate | Auto |
| `updated` | autodate | Auto |

### `providers` — Catálogo de proveedores AI (seed data)

| Field | Type | Notes |
|-------|------|-------|
| `id` | text | PK |
| `provider` | text | ID único (`venice`, `opencode-go`) |
| `label` | text | Nombre visible |
| `baseUrl` | text | URL base de la API |
| `models` | json | Array de modelos disponibles |
| `defaultModel` | text | Modelo por defecto |
| `kind` | text | `openai` |
| `enabled` | bool | Activo |
| `timeoutMs` | number | Timeout por defecto |
| `concurrency` | number | Concurrencia por defecto |

### `user_provider_settings` — Config por usuario

| Field | Type | Notes |
|-------|------|-------|
| `owner` | relation → users | Propietario |
| `provider` | relation → providers | Proveedor |
| `label` | text | Sobrescribe el del catálogo |
| `api_key` | text | Cifrado AES-GCM |
| `base_url` | text | Sobrescribe |
| `models` | json | Sobrescribe |
| `timeoutMs` | number | Sobrescribe |
| `concurrency` | number | Sobrescribe |
| `enabled` | bool | Por usuario |

### `user_prompt_settings` — Prompts personalizados

| Field | Type | Notes |
|-------|------|-------|
| `owner` | relation → users | Propietario |
| `key` | text | `translation`, `refine`, `check` |
| `label` | text | Nombre |
| `description` | text | Descripción |
| `system_prompt` | text | System prompt |
| `user_prompt` | text | User prompt |
| `active` | bool | Habilitado |

### `user_translation_settings` — Valores por defecto

| Field | Type | Notes |
|-------|------|-------|
| `owner` | relation → users | Propietario |
| `autoSegment` | bool | Segmentación automática |
| `thresholdChars` | number | Umbral para segmentar |
| `maxChars` | number | Máximo por segmento |
| `minChars` | number | Mínimo por segmento |
| `maxRetries` | number | Reintentos máximos |
| `enableCheck` | bool | Verificación post-traducción |
| `includePreviousChapterTitles` | bool | Contexto entre capítulos |
| `concurrency` | number | Concurrencia (reservado) |

### `novels` — Novelas

| Field | Type | Notes |
|-------|------|-------|
| `owner` | relation → users | Propietario |
| `sourceLanguage` | text | Idioma origen |
| `targetLanguage` | text | Idioma destino |
| `sourceTitle` | text | Título original |
| `sourceAuthor` | text | Autor original |
| `sourceDescription` | text | Descripción original |
| `sourceSeries` | text | Serie |
| `sourceNumber` | text | Número en serie |
| `targetTitle` | text | Título traducido |
| `targetAuthor` | text | Autor (traducción) |
| `targetDescription` | text | Descripción traducida |
| `targetSeries` | text | Serie (traducción) |
| `targetNumber` | text | Número (traducción) |
| `glossary` | json | Lista de entradas glosario |
| `notes` | text | Notas del traductor |
| `url` | text | URL de origen (NovelBin/Fire) |
| `status` | text | `ongoing`, `completed`, `hiatus`, `cancelled` |
| `tags` | text | Tags |
| `isPublic` | bool | Visible por otros usuarios |
| `cover` | file | Portada |
| `ai_options` | json | Provider, modelo, timeout |
| `translation_options` | json | Auto-segment, threshold, etc. |
| `cleanup_rules` | json | Reglas de limpieza |
| `translation_system_prompt` | text | Prompt específico (legacy) |
| `translation_user_prompt` | text | Prompt específico (legacy) |
| `refine_system_prompt` | text | Prompt refine (legacy) |
| `refine_user_prompt` | text | Prompt refine (legacy) |
| `check_system_prompt` | text | Prompt check (legacy) |
| `check_user_prompt` | text | Prompt check (legacy) |
| `custom_commands` | text | Comandos personalizados |
| `chapterCount` | number | Cache: total capítulos |
| `translatedCount` | number | Cache: traducidos |
| `completedCount` | number | Cache: refinados |
| `originalCharCount` | number | Cache: chars original |
| `translatedCharCount` | number | Cache: chars traducido |
| `refinedCharCount` | number | Cache: chars refinado |
| `totalCharCount` | number | Cache: chars total |
| `maxChapterOrder` | number | Cache: último orden |

### `chapters` — Capítulos

| Field | Type | Notes |
|-------|------|-------|
| `novel` | relation → novels (cascade delete) | Novela padre |
| `chapterOrder` | number | Orden numérico |
| `title` | text | Título original |
| `translated_title` | text | Título traducido |
| `original_content` | text | Contenido original (markdown) |
| `translated_content` | text | Contenido traducido |
| `refined_content` | text | Contenido refinado |
| `status` | text | `pending`, `translated`, `completed`, `failed` |
| `error_message` | text | Mensaje de error |

### `translation_jobs` — Jobs de procesamiento

| Field | Type | Notes |
|-------|------|-------|
| `owner` | relation → users | Propietario |
| `novel` | relation → novels (cascade delete) | Novela |
| `status` | text | `pending`, `running`, `done`, `failed`, `cancelled` |
| `operation` | text | `translate`, `refine`, `download` |
| `provider` | text | Proveedor usado |
| `model` | text | Modelo usado |
| `chapter_ids` | json | IDs de capítulos |
| `options_json` | json | Opciones serializadas |
| `error_message` | text | Error global |
| `total_chapters` | number | Total a procesar |
| `completed_chapters` | number | Completados |
| `failed_chapters` | number | Fallidos |
| `auto_segment_*` | various | Estado de segmentación |

### `epubs` — EPUBs generados

| Field | Type | Notes |
|-------|------|-------|
| `novel` | relation → novels (cascade delete) | Novela |
| `file_kind` | text | `original`, `translated` |
| `source_variant` | text | `original`, `translated`, `refined` |
| `label` | text | Etiqueta |
| `file` | file | Archivo EPUB |
| `url` | text | URL pública |

### `reading_progress` — Progreso de lectura

| Field | Type | Notes |
|-------|------|-------|
| `user` | relation → users | Lector |
| `novel` | relation → novels | Novela |
| `chapter` | relation → chapters | Capítulo actual |
| `scrollPercent` | number | Porcentaje de scroll |

## Schema Migrations

- All collections created in `EnsureSchema()` (`internal/store/store.go:37`)
- `ensureField()` helper for idempotent field additions
- `migrateChapterCascadeDelete()`, `migrateJobCascadeDelete()`, `migrateEpubCascadeDelete()` enable cascade deletes
- Backfill runs: `BackfillChapterCharCounts()`, `BackfillNovelStats()`

## Related Codemaps

- [Backend](backend.md) — Store layer consuming these collections
- [Integrations](integrations.md) — Provider data seeded from registry
