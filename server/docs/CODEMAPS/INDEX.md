# Codebase Overview

**Last Updated:** 2026-06-30
**Entry Points:** `cmd/server/main.go`, `frontend/src/main.ts`
**Language:** Go 1.26.4 (backend), TypeScript/Vue 3 (frontend)
**Module Path:** `translator-server`

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     HTTP :5176                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │                  PocketBase                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │  │
│  │  │  Auth    │  │  Schema  │  │  File Storage  │  │  │
│  │  └──────────┘  └──────────┘  └────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│                           │                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │              internal/api                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │  │
│  │  │  Routes  │  │ Handlers │  │   Workers      │  │  │
│  │  │router.go │  │router_*.go│  │runtime_*.go    │  │  │
│  │  └──────────┘  └──────────┘  └────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│                           │                              │
│  ┌───────────┬───────────┬┴──────────┬──────────────┐   │
│  │           │           │           │              │   │
│  ▼           ▼           ▼           ▼              ▼   │
│ store/     ai/       secure/   epubimport/  noveldown.  │
│ (PB CRUD)  (prov.)   (AES-GCM) (EPUB parse) (scraper)  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │            Frontend Embed (frontend/dist)          │  │
│  │  Vue 3 + PrimeVue + vue-router → SPA fallback     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Key Modules

| Module | Purpose | Exports | Dependencies |
|--------|---------|---------|--------------|
| `cmd/server` | Entrypoint, wiring | `main()` | config, secure, store, api, pocketbase |
| `internal/api` | HTTP routes, handlers, job workers | `Server`, `Router()`, handlers | store, ai, config, noveldownloader |
| `internal/store` | PocketBase persistence, schema, migrations | `Store`, domain types | pocketbase, secure |
| `internal/ai` | AI provider interface + OpenAI | `Provider`, `Providers()` | goai |
| `internal/secure` | AES-GCM encryption | `Encryptor` | crypto stdlib |
| `internal/epubimport` | EPUB file parser | `Parse()` | goquery, html-to-markdown |
| `internal/noveldownloader` | Web novel scraper | `Downloader` | goquery, html-to-markdown |
| `internal/config` | CLI flags + env vars | `Config`, `Load()` | flag, os |
| `frontend/` | Vue 3 SPA | Pages, components, composables | vue, primevue, vue-router |

## Data Flow

```
User → HTTP → PocketBase Auth → api.Server → store.Store → SQLite
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                   downloadQueue         translateQueue
                   (goroutine)           (goroutine)
                          │                     │
                          ▼                     ▼
                   noveldownloader          ai.Provider
                   (NovelBin/Fire)          (Venice/OpenCode)
```

## External Dependencies

- `github.com/pocketbase/pocketbase v0.39.4` — Embedded Go framework with SQLite, auth, admin UI
- `github.com/zendev-sh/goai v0.7.2` — OpenAI-compatible client
- `github.com/PuerkitoBio/goquery` — HTML parsing (scrapers, EPUB)
- `github.com/JohannesKaufmann/html-to-markdown/v2` — HTML→Markdown conversion
- `primevue ^4.4.1` — Vue 3 component library
- `vue ^3.5.18` — Frontend framework
- `vite ^5.4.19` — Frontend bundler

## Related Codemaps

- [Backend](backend.md)
- [Frontend](frontend.md)
- [Database](database.md)
- [Integrations](integrations.md)
- [Workers](workers.md)
