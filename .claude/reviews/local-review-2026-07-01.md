# Local Review — 2026-07-01

## Summary

Uncommitted changes across 4 files enhance EPUB export with richer markdown rendering, deterministic book IDs, improved CSS styling, frontend lazy-loading and code-splitting. All validation passes.

## Validation Results

| Check | Result |
|-------|--------|
| `gofmt -l` | No issues |
| `go vet ./...` | No issues |
| `go build ./cmd/server` | Success |
| `go test -short ./...` | 99 passed (11 packages) |
| `vue-tsc -b && vite build` | Success (353 modules, 8.70s) |

## Findings

### MEDIUM — `hashFunc` overflow edge case

**File:** `internal/epubexport/generator.go:32-43`

`hashFunc` computes `h = -h` when `h < 0`, but if `h == math.MinInt64`, `-h` overflows back to `math.MinInt64` (still negative). The `deterministicBookID` output would contain a negative number, which is valid but inconsistent with the intent.

**Impact:** Extremely unlikely — requires the concatenated metadata to hash exactly to `math.MinInt64`. Not a blocking issue.

**Suggestion:** No change required for correctness. If you want defensive consistency, add:
```go
if h == math.MinInt64 {
    h = 1
}
```

### LOW — `reBlockquote` matches escaped HTML

**File:** `internal/epubexport/text_processor.go:23`

```go
reBlockquote = regexp.MustCompile(`(?m)^&gt; ?(.*)$`)
```

This is correct (escapeXML runs first), but it means a literal `&gt;` in the source text also matches as a blockquote. Acceptable trade-off — the probability of source text containing literal `&gt;` is negligible.

### LOW — `descriptionToEscapedHTML` double-escapes HTML tags

**File:** `internal/epubexport/generator.go:142-165`

The function builds `<p>` tags, then calls `escapeXML` on the result, turning `<p>` into `&lt;p&gt;`. This is intentional — `dc:description` is XML text content, not HTML. Calibre and EPUB readers expect escaped markup here. Correct behavior.

### INFO — Frontend lazy routes

**File:** `frontend/src/router/index.ts:4-11`

All 8 page components are now lazy-loaded via dynamic `import()`. This enables route-level code splitting. The `const LoginPage = () => import(...)` pattern is correct for Vue 3 + Vite.

### INFO — `content-visibility: auto` on tab panels

**File:** `frontend/src/pages/NovelDetailPage.vue:1513-1516`

```css
.tab-panel {
  content-visibility: auto;
  contain-intrinsic-size: auto 400px;
}
```

Good performance optimization — inactive tab panels skip rendering until scrolled into view. The 400px intrinsic size is a reasonable estimate for the panels in this layout.

### INFO — Debounced resize handler

**File:** `frontend/src/pages/NovelDetailPage.vue:712-716`

The resize listener is debounced at 150ms and properly cleaned up in `onUnmounted`. This prevents layout thrashing during window resize.

## Notable Correctness Fixes

1. **Deterministic book IDs** — `deterministicBookID` replaces `time.Now().UnixNano()`, making EPUB exports reproducible for the same metadata. This is a correctness improvement for export stability.

2. **Word-boundary underline detection** — `convertUnderlineItalics` correctly avoids mangling `snake_case` identifiers (common in game-system web novels). The `isWordRune` check includes `_` to handle this.

3. **List heuristic** — `convertListRuns` requires 2+ consecutive marker lines to trigger `<ul>` wrapping, avoiding false positives where `- ` is used as a dialogue dash.

## Files Reviewed

| File | Lines Changed |
|------|--------------|
| `internal/epubexport/text_processor.go` | +176, -18 |
| `internal/epubexport/generator.go` | +66, -9 |
| `internal/epubexport/generator_test.go` | +41 (new) |
| `frontend/src/router/index.ts` | +9, -8 |
| `frontend/src/pages/NovelDetailPage.vue` | +27, -10 |
| `frontend/package.json` | +1 |
