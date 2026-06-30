# Integrations Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `internal/ai/registry.go`, `internal/noveldownloader/`

## AI Providers

Provider catalog in `internal/ai/registry.go` with `ProviderInfo` struct. All providers use OpenAI-compatible API via `github.com/zendev-sh/goai`.

### Registered Providers

| ID | Name | Base URL | Models | Default |
|----|------|----------|--------|---------|
| `venice` | Venice | `https://api.venice.ai/api/v1` | deepseek-v4-flash, mistral-small-3-2-24b-instruct, google-gemma-4-31b-it | deepseek-v4-flash |
| `opencode-go` | OpenCode Go | `https://opencode.ai/zen/go/v1` | mimo-v2.5, deepseek-v4-flash | mimo-v2.5 |

### Provider Interface — `internal/ai/provider.go`

```go
type Provider interface {
    TranslateTitle(ctx, input) (string, error)
    TranslateText(ctx, input) (string, error)
    Refine(ctx, input) (RefineOutput, error)
    Check(ctx, input) (CheckOutput, error)
}
```

### Implementation — `internal/ai/openai.go`

- Single `OpenAIProvider` struct implementing `Provider`
- Uses `goai.Client` for API calls
- JSON mode: `useResponsesAPI: false`, `strictJsonSchema: true`
- Timeout configurable per request

### Module Files

| File | Purpose |
|------|---------|
| `registry.go` | `knownProviders` slice, `Providers()`, `ProviderByID()`, `DefaultProvider()` |
| `provider.go` | `Provider` interface + input/output types |
| `openai.go` | `OpenAIProvider` full implementation |
| `translation_schema.go` | JSON schemas for structured output |

## Web Novel Scrapers

Module: `internal/noveldownloader/` (17 files)

### Supported Sites

| Site | Parser Files | Features |
|------|-------------|----------|
| NovelBin | `novelbin.go`, `novelbin_metadata.go`, `novelbin_chapters.go`, `novelbin_content.go` | Metadata, chapter list, content extraction |
| NovelFire | `novelfire.go`, `novelfire_metadata.go`, `novelfire_chapters.go`, `novelfire_content.go` | Metadata, chapter list, content extraction |

### Downloader — `internal/noveldownloader/downloader.go`

| Feature | Detail |
|---------|--------|
| Rate limiting | Random delay between `MinChapterDelay` (default 1s) and `MaxChapterDelay` (default 3s) |
| Env config | `DOWNLOAD_MIN_DELAY_MS`, `DOWNLOAD_MAX_DELAY_MS` |
| HTML→Markdown | Via `html-to-markdown/v2` |
| Parser selection | URL-based pattern matching in `FindParser()` |

### Key Files

| File | Purpose |
|------|---------|
| `downloader.go` | `Downloader` struct, `DownloadChapters()`, `SleepBetweenChapters()` |
| `client.go` | HTTP client setup |
| `parser.go` | `Parser` interface |
| `models.go` | `ChapterURL`, `Chapter` types |
| `url_helpers.go` | URL parsing and normalization |
| `html_helpers.go` | HTML cleaning utilities |
| `pagination_test.go` | Tests for pagination detection |
| `delay_test.go` | Tests for rate limiting |

## EPUB Import

Module: `internal/epubimport/` (10 files)

| File | Purpose |
|------|---------|
| `parser.go` | EPUB zip parsing → `Result` structure |
| `container.go` | `META-INF/container.xml` parsing |
| `manifest.go` | OPF manifest parsing |
| `metadata.go` | OPF metadata parsing |
| `ncx.go` | NCX navigation parsing |
| `types.go` | `Result`, `Metadata` types |
| `chapter_extract.go` | Chapter content extraction from XHTML |
| `normalize.go` | Content normalization |
| `zip.go` | ZIP file helpers |
| `parser_test.go` | Tests |

## Data Flow

```
Provider UI → PUT /api/user/providers/{key}/key → store (encrypted)
                                                    ↓
Job → resolveJobConfig() → aiOptions.provider + aiOptions.model
  → registry.ProviderByID() → baseURL, goai options
  → openai.NewProvider(baseURL, apiKey, model, timeout)
  → goai.Client → HTTP → external API
                                                    ↑
Download Job → noveldownloader.Downloader
  → FindParser(url) → Parser matching domain
  → HTTP GET → HTML → goquery → html-to-markdown → Markdown
  → store (chapters)
```

## Related Codemaps

- [Database](database.md) — Encrypted API keys in `user_provider_settings`
- [Workers](workers.md) — How providers/downloaders are invoked from jobs
- [Backend](backend.md) — Provider config resolution in `runtime_config.go`
