# translator-server

> Parte del proyecto [Novel Translator](../README.md). Versión servidor web multiusuario en Go + PocketBase + Vue 3.

Backend autónomo en Go para traducción literaria con PocketBase embebido, auth multiusuario, frontend embebido y workers en proceso.

## Arquitectura

```
cmd/server/main.go          ← entrypoint
  ├── internal/config/      ← Flags + env vars
  ├── internal/secure/      ← AES-GCM cifrado de API keys
  ├── internal/store/       ← PocketBase: esquemas, migraciones, CRUD
  │   ├── store.go          ← 10 colecciones, EnsureSchema()
  │   ├── store_schema.go   ← Definiciones de colecciones
  │   ├── settings.go       ← Tipos de dominio (Novel, Chapter, Job…)
  │   ├── store_*.go        ← CRUD por recurso
  │   └── prompt_defaults.go / prompt_overrides.go
  ├── internal/api/         ← HTTP handlers + workers
  │   ├── router.go         ← Montaje de rutas, gestión de workers
  │   ├── router_*.go       ← Handlers por recurso (auth, novels, chapters, jobs…)
  │   ├── runtime_worker.go ← 2 colas: download + translate
  │   ├── runtime_translate.go / runtime_refine.go / runtime_config.go
  │   ├── segmentation.go / cleaner.go
  │   └── *test.go          ← Tests de integración
  ├── internal/ai/          ← Proveedores de IA
  │   ├── provider.go       ← Interfaz (Translate, Refine, Check)
  │   ├── openai.go         ← OpenAI-compatible (goai)
  │   └── registry.go       ← Proveedores conocidos (venice, opencode-go)
  ├── internal/epubimport/  ← Parser EPUB → capítulos
  ├── internal/noveldownloader/ ← Descarga desde NovelBin / NovelFire
  └── frontend_embed.go     ← Embed del frontend compilado

frontend/                   ← Vue 3 + PrimeVue + TypeScript
  ├── src/pages/            ← 8 páginas (Dashboard, NovelDetail, Reader…)
  ├── src/components/       ← 6 componentes reutilizables
  ├── src/composables/      ← 8 composables (useNovels, useChapters…)
  ├── src/api/              ← Cliente HTTP + tipos
  ├── src/router/           ← vue-router (8 rutas)
  └── src/theme/            ← Preset PrimeVue personalizado
```

## Colecciones PocketBase

| Colección | Propósito |
|-----------|-----------|
| `users` | Auth multiusuario |
| `providers` | Catálogo de proveedores AI |
| `user_provider_settings` | Config por usuario (API key cifrada, modelo) |
| `user_prompt_settings` | Prompts personalizados (translation, refine, check) |
| `user_translation_settings` | Valores por defecto de traducción |
| `novels` | Novelas con metadatos, opciones, glosario |
| `chapters` | Capítulos con contenido original/traducido/refinado |
| `translation_jobs` | Jobs de traducción/descarga con progreso |
| `epubs` | EPUBs generados (original/traducido/refinado) |
| `reading_progress` | Progreso de lectura por usuario/novela |

## API endpoints

Todas las rutas protegidas requieren `Authorization: Bearer <token>`.

### Auth (públicas)
- `POST /api/auth/register` — Registro email/password
- `POST /api/auth/login` — Login, devuelve token
- `GET /healthz` — Health check

### Settings
- `GET /api/user/settings` — Config global del usuario
- `PUT /api/user/settings` — Actualizar configuración
- `GET /api/user/defaults` — Valores por defecto

### Providers
- `GET /api/user/providers` — Lista providers con `apiKeyConfigured`
- `PUT /api/user/providers/{key}/key` — Guardar API key (write-only)

### Prompts
- `GET /api/user/prompts` — Listar prompts (translation/refine/check)
- `PUT /api/user/prompts` — Actualizar prompt

### Novels
- `GET /api/db/novels` — Listar novelas del usuario
- `POST /api/db/novels` — Crear novela
- `GET /api/db/novels/{id}` — Detalle de novela
- `PUT /api/db/novels/{id}` — Actualizar novela
- `DELETE /api/db/novels/{id}` — Eliminar novela
- `PUT /api/db/novels/{id}/cover` — Subir portada

### Chapters
- `GET /api/db/novels/{novelId}/chapters` — Listar capítulos
- `GET /api/db/novels/{novelId}/chapters/{id}` — Detalle capítulo
- `PUT /api/db/novels/{novelId}/chapters/{id}` — Actualizar contenido
- `POST /api/db/novels/{novelId}/chapters` — Crear capítulo
- `PUT /api/db/chapters/{id}/title` — Traducir título
- `DELETE /api/db/chapters/{id}` — Eliminar capítulo
- `PUT /api/db/chapters/reorder` — Reordenar capítulos

### Jobs
- `GET /api/db/novels/{novelId}/jobs` — Jobs de una novela
- `POST /api/db/novels/{novelId}/jobs` — Crear job (translate/refine/download)
- `GET /api/db/jobs/{id}` — Estado del job
- `POST /api/db/jobs/{id}/cancel` — Cancelar job
- `GET /api/db/jobs/active` — Jobs activos del usuario

### EPUBs
- `GET /api/db/novels/{novelId}/epubs` — EPUBs generados
- `POST /api/db/novels/{novelId}/epubs` — Generar EPUB
- `GET /api/db/epubs/{id}/download` — Descargar EPUB

### Importación
- `POST /api/db/novels/import-from-zip` — Importar ZIP con metadata.json + capítulos
- `POST /api/db/novels/import-from-epub` — Importar EPUB
- `POST /api/db/novels/import-from-url` — Importar desde URL (NovelBin/NovelFire)
- `GET /api/db/novels/{id}/update-preview` — Vista previa de capítulos nuevos
- `POST /api/db/novels/{id}/update-from-url` — Descargar capítulos nuevos
- `POST /api/db/novels/batch/check-urls` — Batch check de URLs
- `POST /api/db/novels/batch/update-from-urls` — Batch update desde URLs
- `POST /api/db/novels/batch/translate` — Batch translate de novelas

### Batch / Utilidades
- `POST /api/db/novels/batch/check-translate` — Batch check de novelas traducibles
- `POST /api/chapters/segment` — Segmentar capítulo
- `POST /api/chapters/clean` — Limpiar contenido con reglas

### Reading Progress
- `GET /api/db/novels/{novelId}/progress` — Progreso de lectura
- `PUT /api/db/novels/{novelId}/progress` — Actualizar progreso

## Workers en proceso

Dos goroutines con colas bufferizadas (cap 128 c/u):
- **downloadQueue** — Descarga capítulos desde NovelBin/NovelFire
- **translateQueue** — Traducción, refinamiento y verificación vía AI

Los jobs se recuperan al arrancar si quedaron en estado `running` o `pending`.

## Proveedores AI

Registrados en `internal/ai/registry.go`:
- **venice** — `api.venice.ai/api/v1` (default, deepseek-v4-flash)
- **opencode-go** — `opencode.ai/zen/go/v1`

Implementación vía `github.com/zendev-sh/goai` con `useResponsesAPI: false` y `strictJsonSchema: true`.

## Build

```bash
make build
```

Compila frontend (`npm install && npm run build`) y luego genera `bin/translator-server` con `CGO_ENABLED=0`.

```bash
make android    # GOOS=android GOARCH=arm64 → bin/translator-server-android-arm64
make compress   # UPX --best --lzma
```

## Run

```bash
./bin/translator-server
./bin/translator-server --addr 127.0.0.1:9000
./bin/translator-server --port 9000
./bin/translator-server --data-dir ./data
```

## Dev

Terminal 1:
```bash
cd frontend && npm run dev    # http://localhost:5175
```

Terminal 2:
```bash
go run ./cmd/server --addr :5176 --data-dir ./data
```

El frontend de Vite corre en `:5175` y proxya `/api` y `/ai` al backend en `:5176`.

## Android / Termux

```bash
make android
```

Copia el binario al teléfono y ejecuta:
```bash
chmod +x translator-server-android-arm64
./translator-server-android-arm64 --addr 127.0.0.1:5176 --data-dir ./data
```

Requiere Android 7.0+ (API 24). No necesita root para puertos altos.

## Persistencia

- `data/` junto al binario contiene SQLite de PocketBase, archivos subidos y `app.key`.
- `APP_ENCRYPTION_KEY` (base64/hex, 32 bytes) para cifrar API keys. Si no existe, se genera `app.key`.

## Auth y multiusuario

- Registro y login por email/password (`/api/auth/*`).
- Aislamiento total: cada usuario ve solo sus novelas, capítulos, jobs, EPUBs.
- Novelas públicas: leyables por otros usuarios pero no editables.
- API keys write-only: el backend expone solo `apiKeyConfigured`.

## Env

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ADDR` | `:5176` | Dirección de escucha |
| `PORT` | — | Puerto (si no se usa `ADDR`) |
| `DATA_DIR` | `./data` junto al binario | Directorio de datos |
| `STATIC_DIR` | — | Directorio local de assets (dev) |
| `APP_ENCRYPTION_KEY` | — | Clave AES-GCM (base64/hex, 32 bytes) |
| `DOWNLOAD_MIN_DELAY_MS` | — | Espera mínima entre descargas (ms) |
| `DOWNLOAD_MAX_DELAY_MS` | — | Espera máxima entre descargas (ms) |

## Tests

```bash
go test ./...              # Todos los tests
go test -short ./...       # Sin tests de red (scrapers)
```

Tests de integración en `internal/api/router_integration_test.go` bootean PocketBase real en `t.TempDir()`.

## Importación desde ZIP

Ver `template/import/README.md` para el formato esperado:
- `metadata.json` obligatorio (title, sourceLanguage, targetLanguage)
- `originals/` capítulos en .txt o .md
- `translated/` traducciones opcionales (mismo nombre que en originals/)
- `cover.jpg` opcional
