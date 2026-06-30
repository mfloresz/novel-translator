# Workers Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `internal/api/runtime_worker.go`
**Architecture:** Two in-process goroutines with buffered channels

## Architecture

```
enqueueJob(jobID)
  │
  ├─ operation == "download"  → downloadQueue (chan string, cap 128)
  └─ operation == "translate"
     └─ operation == "refine" → translateQueue (chan string, cap 128)
                                     │
                                     ▼
                              workerLoop(queue)
                                │
                                ▼
                             processJob(jobID)
                                │
                   ┌────────────┴────────────┐
                   │                         │
            download:                  translate/refine:
            processDownloadJob()       buildJobContext()
                   │                         │
                   ▼                         ▼
            noveldownloader             ai.Provider
            (por capítulo)              (por capítulo)
```

## Startup — `startJobWorker()`

Called from `api.New()` in `router.go:48`. On boot:
1. Creates two buffered channels (cap 128 each)
2. Starts `downloadWorkerLoop()` and `translateWorkerLoop()` goroutines
3. Calls `ListRunnableJobs()` to re-enqueue any jobs left in `pending` or `running` state

## Queuing — `enqueueJob(jobID)`

- Deduplication via `queuedJobs` map (mutex-protected)
- Routes job to correct queue based on `job.Operation`
- If queue is full: marks job as `failed` with "Server is busy" message
- Removes from dedup map after pickup

## Job Lifecycle

```
pending → running → done
                → failed
                → cancelled (external)
```

States checked in `processJob()`: `cancelled`, `done`, `failed` → short-circuit skip.

## Translate/Refine Pipeline — `processJob()` (translate branch)

### 1. Build Context — `buildJobContext()`

```
job → LoadJobChapters() → []Chapter + Novel
   → resolveJobConfig() → AI options, translation options, prompts
   → newAIProvider()    → ai.Provider instance
   → formatGlossary()   → glossary text
```

### 2. Chapter Loop

For each chapter (respecting `runCtx` cancellation):

```
switch job.Operation:
  "refine" → runRefineChapter()
  default  → runTranslateChapterDetailed()
                → previewChapterSegmentation() (if autoSegment)
                → segment → translate segment loop
```

### 3. Progress Tracking

Each chapter result recorded via `recordChapterResult()`, progress flushed via `flushProgress()`.

After all chapters: `RecalculateNovelStats()`.

### 4. Final Status

| Condition | Status |
|-----------|--------|
| Context cancelled | `cancelled` |
| No errors | `done` |
| Some chapters failed | `failed` (with `lastError`) |

## Download Pipeline — `processDownloadJob()`

### 1. Parse Options

```json
{
  "url": "https://novelfire.net/novel/...",
  "chapters": [{"url": "...", "title": "..."}],
  "startOrder": 1,
  "sourceLanguage": "en",
  "targetLanguage": "es"
}
```

### 2. Chapter Loop

For each chapter URL:
1. `SleepBetweenChapters()` (rate limiting)
2. `DownloadChapters()` → HTML → Markdown
3. `UpsertChapterWithoutStats()` → store
4. Update `completedChapters` / `failedChapters`

### 3. Final Status

| Condition | Status |
|-----------|--------|
| All succeeded | `done` |
| Any failed | `failed` |

## Job Cancellation

- `registerJobCancel(jobID, cancel)` stores context cancel func
- `cancelJob(jobID)` calls it (from HTTP handler)
- Workers check `runCtx.Err()` between chapters
- On cancel: resets current chapter status to `pending`

## Auto-segmentation

For long chapters (`thresholdChars` default 20000):
- `previewChapterSegmentation()` splits content into segments
- Progress tracked in job record (`autoSegmentActive`, `autoSegmentCount`, etc.)
- Each segment translated independently, then reassembled

## Concurrency Notes

- `Concurrency` setting in `AISettings` is persisted but **not wired** — all jobs run sequentially per queue
- Each queue has a single goroutine; new jobs wait until previous finishes
- Two independent queues allow simultaneous download + translate

## Related Codemaps

- [Backend](backend.md) — Runtime files (`runtime_translate.go`, `runtime_refine.go`, `runtime_config.go`)
- [Integrations](integrations.md) — Providers and downloaders used by workers
- [Database](database.md) — `translation_jobs` collection schema
