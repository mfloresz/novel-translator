# AGENTS.md

> Part of [Novel Translator](../README.md). Web server edition.

## What this is

`translator-server` — single Go binary that embeds PocketBase, ships a Vue frontend inside the binary, and exposes a JSON API for translating literary novels with configurable AI providers. Module path is `translator-server` (Go 1.26.4).

Layout:

- `cmd/server/main.go` — entrypoint. Wires config → encryptor → PocketBase → `store.Store` → `api.Server` → `http.ListenAndServe`.
- `internal/api/` — HTTP layer. `router.go` mounts everything; per-domain files (`router_auth.go`, `router_novels.go`, `router_chapters.go`, `router_jobs.go`, `router_epubs.go`, `router_import.go`, `router_settings.go`, `router_providers.go`, `router_prompts.go`, `router_responses.go`, `router_helpers.go`). `runtime_*.go` contains the in-process job worker and per-job translate/refine/config logic.
- `internal/store/` — PocketBase-backed persistence. `store.go` defines collection name constants; per-domain files (`store_novels.go`, `store_chapters.go`, `store_jobs.go`, `store_epubs.go`, `store_providers.go`, `store_settings.go`, `store_auth.go`, `store_helpers.go`, `store_mapping.go`, `store_schema.go`, `store_db_migrations.go`). All collections are created/seeded by `Store.EnsureSchema()`.
- `internal/ai/` — `Provider` interface plus a single `OpenAIProvider` implementation backed by `github.com/zendev-sh/goai`. The provider catalog lives in `registry.go` (currently: `venice`, `opencode-go`).
- `internal/secure/encryption.go` — AES-GCM encryptor for provider API keys. Key comes from `APP_ENCRYPTION_KEY` (base64 or hex, must decode to 32 bytes) or is auto-generated to `<data-dir>/app.key`.
- `internal/epubimport/`, `internal/noveldownloader/` — pure parsers/scrappers with no HTTP or store dependencies.
- `frontend/` — Vue 3 + Vite + PrimeVue SPA. Vite dev port is fixed at 5175 and proxies `/api` and `/ai` to the Go backend on `127.0.0.1:5176`.
- `frontend_embed.go` — `package translatorserver`, `//go:embed all:frontend/dist`. The Go import alias `translatorserver "translator-server"` (note: matches the module name, NOT the kebab-case path) is what makes the embed reachable from `internal/api`.
- `docs/` — historical planning notes (`pocketbase-multiuser-plan.md`, `go-backend-refactor-plan.md`). Treat as context, not current truth.
- `test/` — gitignored fixtures (EPUBs, chapter text) used by some manual tests. Not used by `go test`.
- `data/` — runtime PocketBase SQLite + uploaded files. Gitignored.

## Build & run

All commands are run from the repo root unless noted.

- `make build` — builds the frontend (`npm install && npm run build`) then compiles `bin/translator-server` with `CGO_ENABLED=0` and `-trimpath -ldflags="-s -w"`. The build is CGO-disabled on purpose so it can be cross-compiled.
- `make android` — same, with `GOOS=android GOARCH=arm64`, output `bin/translator-server-android-arm64`. For Termux; pair with `--data-dir $HOME/data` and a high port (e.g. 5176).
- `make compress` — wraps the built binary with UPX (must be installed).
- `make dev` — prints the two-terminal instructions; does not start anything.
- Run the server: `./bin/translator-server` (defaults: `:5176`, `./data` next to binary) or `go run ./cmd/server --addr :5176 --data-dir ./data`.
- Dev loop — terminal 1 `cd frontend && npm run dev` (port 5175, proxies `/api` and `/ai` to `127.0.0.1:5176`); terminal 2 `go run ./cmd/server --addr :5176 --data-dir ./data`.
- If you change the frontend, re-run `make build` (or `npm run build` in `frontend/`) so `frontend/dist/` reflects your changes. `frontend_embed.go` embeds that directory; stale builds silently serve the old SPA.

## Tests & verification

- Backend: `go test ./...`. Integration tests live next to handlers (`internal/api/router_integration_test.go`, `import_url_test.go`, `runtime_config_test.go`, `refine_test.go`, `segmentation_test.go`, `cleaner_test.go`) and `internal/store/store_test.go`. They boot a real PocketBase against `t.TempDir()` via the shared `newAPITestEnv` helper — there is no in-memory mock.
- Frontend: `npm run build` (which runs `vue-tsc -b && vite build`) is the typecheck. There is no separate `npm test`.
- The `realtest_test.go` files in `internal/noveldownloader/` hit live URLs. They are gated by `if testing.Short() { t.Skip(...) }`, so use `go test -short ./...` in CI / local loops and full `go test ./...` only when you specifically want to exercise the scrapers.
- No linter is configured in the repo. `go vet ./...` is the minimum sanity check used by the planning docs.
- The planning docs (`docs/pocketbase-multiuser-plan.md`, `docs/go-backend-refactor-plan.md`) mention `rtk err go build ./cmd/server` / `rtk test go test ./...` as their validation steps — `rtk` is a third-party CLI wrapper for ripgrep-style output. Plain `go build ./cmd/server` and `go test ./...` work too.

## Operational gotchas

- PocketBase is in-process. There is no external PB process, no separate admin port, and no `_/` admin UI exposed by this binary. The HTTP server only serves `/healthz`, `/api/...` (and PocketBase's own `/api/collections/...` routes that the embedded app registers), plus the SPA fallback.
- The embedded `frontend/dist` is only used when `STATIC_DIR` env / `--static-dir` is empty. Set `STATIC_DIR` in dev only if you want the Go binary to serve files from disk instead of the embed; the normal Vite dev workflow does not need it.
- API keys for AI providers are stored encrypted with AES-GCM. The encryptor prefers `APP_ENCRYPTION_KEY` (base64 or hex, exactly 32 bytes decoded). If unset, it generates a random key at `<data-dir>/app.key` on first start. To rotate, set the env var; existing data encrypted with a previous key will be unreadable.
- API keys are write-only: the UI sends them to `PUT /api/user/providers/{key}/key`; `GET /api/user/providers` returns an `apiKeyConfigured` flag and never the secret. Tests assert on that flag, not the value.
- The server refuses to start if it detects a legacy novel schema. If you see `legacy novel schema/data detected; run ./translator-server --migrate-db before starting the server`, run the binary once with `--migrate-db`, then restart normally. `RunDatabaseMigrations` also runs backfills (`BackfillChapterCharCounts`, `BackfillNovelStats`) on every boot via `EnsureSchema`.
- `--data-dir` is resolved to an absolute path at startup. Pass an absolute path (or one relative to the binary's CWD) — the binary does not chdir.
- The job worker (`internal/api/runtime_worker.go`) is in-process with two buffered queues (`downloadQueue` cap 128, `translateQueue` cap 128) and one goroutine each. The `Concurrency` setting on `AISettings` is **persisted but not yet wired into execution** (deliberately per `docs/go-backend-refactor-plan.md`); translation and refine jobs run sequentially per job. Don't add new code that relies on concurrency being honored.
- The downloader supports throttling via `DOWNLOAD_MIN_DELAY_MS` / `DOWNLOAD_MAX_DELAY_MS` env vars (random delay between chapter fetches). They only apply to the import-from-URL flow; they are not exposed as flags.

## Code conventions worth knowing

- HTTP handlers live in `internal/api` and follow one-file-per-resource. Add a new resource by creating `router_<thing>.go` with a `register<Thing>Routes(api, s)` function, then wire it from `registerProtectedRoutes` in `router.go`. Public (unauthenticated) routes go via `registerAuthRoutes` or directly on `router` in `registerRoutes`.
- Store layer returns `store.ErrNotFound` / `store.ErrForbidden` for permission/missing cases. Map them in handlers with `notFoundOrForbidden(e, err)` (in `router_helpers.go`) — don't inline the switch.
- Response shaping is bespoke: handlers return `map[string]any` or call small `*Record(...)` helpers (e.g. `novelRecord`, `jobRecord`, `epubRecord`, `parseJSONFields`) instead of serializing structs directly. The frontend expects this exact shape. Tests in `router_integration_test.go` assert on field names, so changing them is a breaking change.
- All PocketBase collections are defined in code (see `store_schema.go`) and seeded in `EnsureSchema`. There are no JSON migration files. If you add a field, add it to the relevant `ensure*Collection` and use `ensureField` for idempotent migration.
- The `translatorserver` import alias in `internal/api/router.go` and `static.go` is the **module-name alias** for the `translator-server` module — its only job is to expose the `FrontendFS` embed declared in `frontend_embed.go`. The package name on that file is `translatorserver` (single word), which is why the alias matches.
- Frontend uses `vue-router` and the `appServicesKey` provide/inject pattern (`frontend/src/app/services.ts`) for cross-page state. New composables live in `frontend/src/composables/`; new pages in `frontend/src/pages/`. The dev proxy in `frontend/vite.config.ts` proxies `/api` and `/ai` to the Go backend — both are required because some routes are mounted at the root level by PocketBase.
- Don't add `//nolint`, doc-comments explaining obvious code, or new top-level `cmd/...` binaries without checking with the user — the project ships a single binary and the planning docs flag god-object growth as the main risk.

## Frontend is a pure consumer

All logic lives in the Go backend. The frontend (`frontend/`) is a thin Vue SPA that only renders state and fires HTTP requests — it does not run jobs, parse EPUBs, call AI providers, or own any business rules. Anything that feels like "real work" (translation, refinement, cleaning, scoring, scheduling, downloading) belongs in `internal/api` / `internal/store` / `internal/ai` / `internal/noveldownloader` / `internal/epubimport`. When extending a feature, push the logic into a new backend handler/store method and have the frontend call it; do not duplicate the logic in TypeScript.

## Where to look first when changing X

- New HTTP route → `internal/api/router.go` (wire-in) + a `router_*.go` file (handler).
- New persistence field → `internal/store/store_schema.go` (collection def) + relevant `store_*.go` (record mapping in `store_mapping.go` and persistence) + `internal/store/settings.go` (struct type if it's a domain object).
- New AI provider → `internal/ai/registry.go` (catalog entry; sets `GoAIOptions` like `useResponsesAPI` and `strictJsonSchema`) and verify `internal/ai/openai.go` honors those options.
- New job operation → extend the switch in `internal/api/runtime_worker.go` (`enqueueJob`) and add a `runtime_*.go` workflow file. Status transitions live in `store_jobs.go`; the worker respects `cancelled` / `done` / `failed` short-circuits.
- Schema/migration change → prefer `ensureField` over touching raw collection JSON; for data backfills add to `EnsureSchema` after the new fields are in place.
- Anything that touches the persisted collection names in `internal/store/store.go` (e.g. `NovelsCollection`) is a breaking change for existing `data/` directories.
