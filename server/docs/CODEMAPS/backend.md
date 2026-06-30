# Backend Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `cmd/server/main.go`, `internal/api/router.go`
**Package:** `translator-server`

## Architecture

```
cmd/server/main.go
  └── config.Load()           ← flags + env
  └── secure.NewEncryptor()   ← AES-GCM key
  └── pocketbase.New()        ← embedded PB
  └── store.New()             ← persistence layer
  └── store.EnsureSchema()    ← 10 collections
  └── api.New()               ← Server + workers
  └── api.Router()            ← HTTP mux
  └── http.ListenAndServe()
```

## Key Modules

### Entrypoint — `cmd/server/main.go`

| Dependency | Purpose |
|------------|---------|
| `pocketbase` | Framework bootstrap |
| `internal/config` | Config from flags/env |
| `internal/secure` | Encryption for API keys |
| `internal/store` | Persistence, schema |
| `internal/api` | HTTP server, routes, workers |

### HTTP Layer — `internal/api/` (29 files)

| File | Purpose |
|------|---------|
| `router.go` | `Server` struct, `Router()`, `registerRoutes()`, job cancel registry |
| `router_auth.go` | Registro, login endpoints |
| `router_novels.go` | CRUD novelas, batch operations |
| `router_chapters.go` | CRUD capítulos, reorder, segment, clean |
| `router_jobs.go` | Crear jobs, listar, cancelar |
| `router_epubs.go` | Generar y descargar EPUBs |
| `router_import.go` | Import ZIP/EPUB/URL, update from URL, batch check/update |
| `router_settings.go` | Config global del usuario |
| `router_providers.go` | Listar providers, guardar API key |
| `router_prompts.go` | CRUD prompts personalizados |
| `router_responses.go` | Endpoint para respuestas raw de AI translate |
| `router_reading_progress.go` | Progreso de lectura |
| `router_helpers.go` | `notFoundOrForbidden()`, record helpers |
| `static.go` | Sirve frontend embebido o static dir |
| `runtime_worker.go` | 2 goroutines (downloadQueue, translateQueue), enqueue/logic |
| `runtime_translate.go` | `jobContext`, `runTranslateChapterDetailed()`, progress |
| `runtime_refine.go` | `runRefineChapter()` |
| `runtime_config.go` | `resolveJobConfig()`, effective model, defaults |
| `runtime_prompts.go` | Resolución de prompts para el job |
| `runtime_types.go` | Tipos compartidos del runtime |
| `runtime.go` | `dynamicSystemPrompt()`, helper de formato |
| `segmentation.go` | Segmentación de capítulos largos |
| `cleaner.go` | Reglas de limpieza post-traducción |

### Store Layer — `internal/store/` (18 files)

| File | Purpose |
|------|---------|
| `store.go` | Collection constants, `Store` struct, `EnsureSchema()`, prompt CRUD |
| `store_schema.go` | Definiciones de 10 colecciones + field migrations |
| `store_auth.go` | Auth helpers |
| `store_novels.go` | Novel CRUD, stats, batch operations |
| `store_chapters.go` | Chapter CRUD, status updates, reorder |
| `store_jobs.go` | Job CRUD, status transitions, progress |
| `store_epubs.go` | EPUB CRUD |
| `store_providers.go` | Provider settings + API key CRUD |
| `store_settings.go` | Settings CRUD, defaults |
| `store_reading_progress.go` | Reading progress CRUD |
| `store_helpers.go` | Utility functions |
| `store_mapping.go` | Record → struct mapping |
| `store_db_migrations.go` | Legacy data migration |

### AI Layer — `internal/ai/` (8 files)

| File | Purpose |
|------|---------|
| `provider.go` | `Provider` interface (Translate, Refine, Check) |
| `openai.go` | `OpenAIProvider` implementation |
| `registry.go` | `knownProviders` (venice, opencode-go) |
| `translation_schema.go` | JSON schemas para AI responses |
| `translation_prompt_test.go` | Tests de prompts |
| `openai_translate_request_test.go` | Tests de request building |
| `dynamic_system_prompt_test.go` | Tests de system prompt dinámico |
| `registry_test.go` | Tests del registro |

### Config — `internal/config/config.go`

| Field | Source | Default |
|-------|--------|---------|
| `Addr` | `--addr` / `ADDR` | `:5176` |
| `Port` | `--port` / `PORT` | — |
| `DataDir` | `--data-dir` / `DATA_DIR` | `./data` junto al binario |
| `StaticDir` | `--static-dir` / `STATIC_DIR` | — |
| `AppEncryptionKey` | `APP_ENCRYPTION_KEY` | — |
| `DownloadMinDelayMs` | `DOWNLOAD_MIN_DELAY_MS` | 0 (default del downloader) |
| `DownloadMaxDelayMs` | `DOWNLOAD_MAX_DELAY_MS` | 0 (default del downloader) |
| `MigrateDB` | `--migrate-db` | false |

## API Route Tree

```
/healthz                                    [público]
/auth/register                              [público]
/auth/login                                 [público]
/api/user/settings                          [auth]
/api/user/defaults                          [auth]
/api/user/providers                         [auth]
/api/user/providers/{key}/key               [auth]
/api/user/prompts                           [auth]
/api/db/novels                              [auth]
/api/db/novels/{id}                         [auth]
/api/db/novels/{id}/cover                   [auth]
/api/db/novels/{id}/chapters                [auth]
/api/db/novels/{id}/chapters/{chId}         [auth]
/api/db/chapters/{id}/title                 [auth]
/api/db/chapters/reorder                    [auth]
/api/db/chapters/{id}                       [auth]
/api/db/novels/{id}/jobs                    [auth]
/api/db/jobs/{id}                           [auth]
/api/db/jobs/{id}/cancel                    [auth]
/api/db/jobs/active                         [auth]
/api/db/novels/{id}/epubs                   [auth]
/api/db/epubs/{id}/download                 [auth]
/api/db/novels/import-from-zip              [auth]
/api/db/novels/import-from-epub             [auth]
/api/db/novels/import-from-url              [auth]
/api/db/novels/{id}/update-preview          [auth]
/api/db/novels/{id}/update-from-url         [auth]
/api/db/novels/batch/check-urls             [auth]
/api/db/novels/batch/update-from-urls       [auth]
/api/db/novels/batch/translate              [auth]
/api/db/novels/batch/check-translate        [auth]
/api/chapters/segment                       [auth]
/api/chapters/clean                         [auth]
/api/db/novels/{id}/progress                [auth]
/{path...}                                  [SPA fallback]
```

## Data Flow

```
Request → PocketBase middleware (auth) → handler
  → store.Store method → PocketBase DAO → SQLite
  ↓ (si es job)
  → enqueueJob() → channel → worker goroutine
      → download: noveldownloader → store
      → translate: ai.Provider → store
```

## Tests

| File | Type |
|------|------|
| `router_integration_test.go` | Integration (boots real PB) |
| `import_url_test.go` | Integration |
| `runtime_config_test.go` | Unit |
| `refine_test.go` | Unit |
| `segmentation_test.go` | Unit |
| `cleaner_test.go` | Unit |

## Related Codemaps

- [Database](database.md) — All collections and schema
- [Workers](workers.md) — Job processing details
- [Integrations](integrations.md) — External services
