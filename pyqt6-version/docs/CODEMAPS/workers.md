# Background Workers Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `src/logic/translation_manager.py`, `src/logic/refine_manager.py`, `src/logic/epub_importer.py`

## Architecture

Background tasks use PyQt6's threading primitives (`QThread` + `QObject` worker pattern and `QRunnable` + `QThreadPool`) to keep the UI responsive during long operations.

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Thread                            │
│  NovelManagerApp / TranslationTab / RefineTab / CreatePanel │
└──────────┬────────────────────────────┬─────────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────┐   ┌──────────────────────────┐
│   TranslationWorker  │   │   RefineWorker           │
│   (QObject + QThread)│   │   (QObject + QThread)    │
├──────────────────────┤   ├──────────────────────────┤
│ - translate_file()   │   │ - _refine_single_file()  │
│ - stop()             │   │ - stop()                 │
│ - is_stop_requested()│   │ - is_stop_requested()    │
└──────────────────────┘   └──────────────────────────┘

┌─────────────────────────────┐
│   EpubImportWorker          │
│   (QRunnable + QThreadPool) │
├─────────────────────────────┤
│ - run() → import_epub...()  │
└─────────────────────────────┘
```

## Worker: TranslationWorker

**File:** `src/logic/translation_manager.py`

| Aspect | Detail |
|--------|--------|
| **Pattern** | `QObject` moved to `QThread` |
| **Parent** | `TranslationManager` (creates thread + worker per batch) |
| **Lifecycle** | Created per batch → `moveToThread()` → `thread.started.connect(worker.run)` → auto-delete on finish |

### Signals

| Signal | Signature | Purpose |
|--------|-----------|---------|
| `progress_updated` | `str` | Chapter-level progress messages |
| `translation_completed` | `str, bool` | (filename, success) per file |
| `all_translations_completed` | `()` | Batch complete |
| `error_occurred` | `str` | Error description |

### Execution Flow

```
1. Main loop over files_to_translate
2. For each file:
   a. Check stop_requested flag
   b. Emit progress_updated
   c. Update status_callback → "Processing"
   d. Skip if already translated (unless allow_retranslation)
   e. Read source file from originals/
   f. Call translator.translate_text() with all config
   g. Save to temp file → atomic move to translated/
   h. Add translation record to database
   i. Emit translation_completed
   j. Sleep 5s between files (rate limiting)
3. Emit all_translations_completed
```

### Stop Mechanism

```
translate_panel → TranslationManager.stop_translation()
    → TranslationWorker.stop()  (sets _stop_requested = True)
    → Worker checks flag between files and during processing
    → Also passed as stop_callback to TranslatorLogic.translate_text()
```

## Worker: RefineWorker

**File:** `src/logic/refine_manager.py`

| Aspect | Detail |
|--------|--------|
| **Pattern** | `QObject` moved to `QThread` (translation_manager pattern) |
| **Parent** | `RefineManager` |

### Signals

| Signal | Signature | Purpose |
|--------|-----------|---------|
| `progress_updated` | `str` | Chapter-level progress |
| `refine_completed` | `str, bool` | (filename, success) per file |
| `all_refines_completed` | `()` | Batch complete |
| `error_occurred` | `str` | Error description |

### Execution Flow

```
1. Validate model supports tools at start (checked via _check_model_supports_tools())
2. For each file:
   a. Read source (originals/) and translation (translated/)
   b. Call translator._refine_translation() with use_tools detection
   c. Auto-detect if model supports function calling
   d. Save with atomic temp file → replace
   e. Sleep 5s between files
3. Emit completion
```

## Worker: EpubImportWorker

**File:** `src/logic/epub_importer.py`

| Aspect | Detail |
|--------|--------|
| **Pattern** | `QRunnable` via `QThreadPool` |
| **Parent** | `EpubImporter` |

### Signals

| Signal | Signature | Purpose |
|--------|-----------|---------|
| `progress_updated` | `str` | Import progress messages |
| `import_finished` | `bool, str, str` | (success, message, directory_path) |

### Execution Flow

```
1. EpubConverter opens EPUB, extracts chapters + metadata + cover
2. Creates output directory: {epub_dir}/{book_title}
3. Creates originals/ and translated/ subdirectories
4. Saves cover image
5. For each chapter:
   a. Get HTML content
   b. Extract chapter title
   c. Convert HTML → Markdown
   d. Save as .txt to originals/
6. Save book metadata to database
7. Emit import_finished
```

## Concurrency Summary

| Worker | Threading Model | Max Concurrency | Cancellable |
|--------|----------------|-----------------|-------------|
| TranslationWorker | QThread (sequential per batch) | 1 | Yes |
| RefineWorker | QThread (sequential per batch) | 1 | Yes |
| EpubImportWorker | QRunnable / ThreadPool | Per pool config | No (runs to completion) |

All workers emit progress signals to update the UI status bar and chapter table in real time.
