# Frontend Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `frontend/src/main.ts`, `frontend/src/app/App.vue`
**Framework:** Vue 3 + TypeScript + Vite + PrimeVue
**Dev Port:** 5175 (proxies `/api` and `/ai` to `127.0.0.1:5176`)

## Architecture

```
frontend/
├── index.html
├── vite.config.ts            ← proxy /api, /ai → :5176
├── tsconfig.json
├── package.json
└── src/
    ├── main.ts               ← createApp, PrimeVue, router mount
    ├── vite-env.d.ts
    ├── app/
    ├── api/
    ├── components/
    ├── composables/
    ├── config/
    ├── domain/
    ├── features/
    ├── pages/
    ├── router/
    ├── theme/
    └── utils/
```

## Key Modules

### App Shell — `src/app/`

| File | Purpose |
|------|---------|
| `App.vue` | Root component |
| `auth.ts` | Auth state (token, user, theme), login/logout/restore |
| `services.ts` | `AppServices` provide/inject pattern (api, auth, providers, defaults) |
| `styles.css` | Global styles |

### API Layer — `src/api/`

| File | Purpose |
|------|---------|
| `http.ts` | `HttpTransport` — fetch wrapper with auth header injection |
| `client.ts` | `ApiClient` — all endpoint methods grouped by domain |
| `types.ts` | TypeScript types for API responses (291 lines) |

### Pages — `src/pages/` (8)

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | `DashboardPage.vue` | Novel list, quick actions |
| `/settings` | `SettingsPage.vue` | Global settings, providers, prompts |
| `/operations` | `OperationsPage.vue` | Batch operations, job monitoring |
| `/novels/:novelId` | `NovelDetailPage.vue` | Novel metadata, chapter list, actions |
| `/novels/:novelId/chapters/:chapterId` | `ChapterPage.vue` | Chapter editor (original + translated) |
| `/novels/:novelId/read` | `ReaderPage.vue` | Reading view with scroll progress |
| `/login` | `LoginPage.vue` | Login form |
| `/register` | `RegisterPage.vue` | Registration form |

### Components — `src/components/` (6)

| Component | Purpose |
|-----------|---------|
| `AppLayout.vue` | Sidebar + topbar layout shell |
| `ChapterList.vue` | Chapter list with status indicators |
| `FieldNumber.vue` | Number input field with validation |
| `JobsDrawer.vue` | Slide-out drawer showing active jobs |
| `MetadataEditor.vue` | Novel metadata form |
| `PromptRoleEditor.vue` | Editor for system/user prompts |

### Composables — `src/composables/` (8)

| Composable | Purpose |
|------------|---------|
| `useNovels.ts` | Novel CRUD operations |
| `useChapters.ts` | Chapter CRUD + reorder + clean |
| `useTranslationJobs.ts` | Job creation, status polling |
| `useActiveJobs.ts` | Active job list with live updates |
| `useActiveJobStatus.ts` | Single job status polling |
| `useProjectSettings.ts` | Project-level settings (glossary, prompts, AI) |
| `useProviders.ts` | Provider listing + API key management |
| `useReadingProgress.ts` | Reading progress tracking |

### Router — `src/router/index.ts`

8 routes with auth guards (`requiresAuth`, `guestOnly` meta fields) and redirect logic.

### Theme — `src/theme/pixeo-preset.ts`

Custom PrimeVue design preset (pixeo theme).

### Utils — `src/utils/`

| File | Purpose |
|------|---------|
| `api-base-url.ts` | Base URL resolution |
| `cleaner.ts` | Text cleaning rules |
| `epub-generator.ts` | Client-side EPUB generation |
| `epub-importer.ts` | EPUB file import utility |
| `job-events.ts` | Job event helpers |
| `markdown.ts` | Markdown rendering |
| `project-settings.ts` | Settings normalization |

### Config — `src/config/languages.ts`

Source/target language options.

### Domain — `src/domain/`

| File | Purpose |
|------|---------|
| `index.ts` | Core type exports |
| `project-settings.ts` | `ProjectSettings`, `NovelTranslationOptions`, `CleanupRule`, `GlossaryEntry` |

## Data Flow

```
Page → Composable → ApiClient → HttpTransport → HTTP → Backend
                                                    ↓
AppServices (provide/inject) ← authState ← localStorage (token)
```

## Build

```bash
cd frontend && npm install && npm run build
# vue-tsc -b && vite build → frontend/dist/
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| vue | ^3.5.18 | Framework |
| vue-router | ^4.5.1 | Routing |
| primevue | ^4.4.1 | UI components |
| primeicons | ^7.0.0 | Icons |
| @primeuix/themes | ^1.2.3 | Theme engine |
| jszip | ^3.10.1 | EPUB generation |
| vite | ^5.4.19 | Bundler |
| vue-tsc | ^2.2.12 | Type checker |
| typescript | ^5.8.3 | Language |

## Related Codemaps

- [Backend](backend.md) — API endpoints this frontend consumes
- [Database](database.md) — Data model reflected in frontend types
