# Backend / Logic Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `src/logic/*.py`

## Architecture

```
src/logic/
│
├── translator.py          ─── Core translation engine (segmentation, verification, refinement orchestration)
├── translator_req.py      ─── HTTP API requests to AI providers
├── translation_manager.py ─── QThread worker for batch translation
├── refine_manager.py      ─── QThread worker for batch refinement
├── refine_tools.py        ─── Function calling tool definitions for refinement
│
├── database.py            ─── Hybrid SQLite + JSON persistence
├── folder_structure.py    ─── File system organization (originals/, translated/)
│
├── cleaner.py             ─── Text cleaning operations
├── creator.py             ─── EPUB creation orchestration
├── epub_converter.py      ─── EPUB → Markdown conversion
├── epub_generator.py      ─── EPUB generation (OPF, NCX, XHTML, CSS)
├── epub_importer.py       ─── EPUB import with chapter preview
├── epub_text_processor.py ─── Markdown → HTML text processing
│
├── session_logger.py      ─── Temp-file session logging
├── status_manager.py      ─── Chapter status constants and helpers
├── language_manager.py    ─── UI i18n string loading
├── loader.py              ─── File discovery and status detection
├── functions.py           ─── Shared UI utilities (dialogs, sorting, validation)
├── get_path.py            ─── Cross-platform native directory picker
└── xml_utils.py           ─── XML/HTML escaping utilities
```

## Key Modules

### Translator Engine (`translator.py`)

| Method | Purpose |
|--------|---------|
| `translate_text()` | Main entry point: segment text, translate segments, check quality, refine if needed |
| `_segment_text()` | Splits text into segments respecting narrative boundaries |
| `_find_optimal_cut_point()` | Backward search for paragraph/sentence breaks |
| `_validate_segment_integrity()` | Ensures no content lost during segmentation |
| `_perform_translation()` | Calls AI API for each segment, assembles result |
| `_check_translation()` | Verifies translation quality via AI |
| `_refine_translation()` | Improves translation using tools or prompt-based refinement |
| `_apply_refinement_changes()` | Applies tool-based surgical changes to text |
| `_build_check_prompt()` / `_build_refine_prompt()` | Dynamic prompt construction |

### API Requests (`translator_req.py`)

| Function | Purpose |
|----------|---------|
| `translate_segment()` | Routes translation to appropriate provider handler |
| `_translate_gemini()` | Google Gemini API calls |
| `_translate_openai_like()` | OpenAI-compatible API calls (Chutes, Mistral, OpenRouter, etc.) |
| `_translate_gemini_with_tools()` | Gemini with function calling support |
| `_process_response()` | Normalizes API responses |
| `_process_streaming_response()` | Handles streaming responses |
| `_clean_translation()` | Post-processing text cleanup |
| `_convert_tools_to_gemini_format()` | Tool format adaptation for Gemini |

### Folder Structure (`folder_structure.py`)

```
novel/
├── originals/          # Source text files (.txt, .md)
├── translated/         # Translated output files
├── cover.*             # Cover image
└── .translation_records.db  # SQLite database
```

`NovelFolderStructure` provides static methods for path management, ensuring consistent directory layout across all operations.

### EPUB Processing

| Module | Class | Purpose |
|--------|-------|---------|
| `epub_converter.py` | `EpubConverter` | Read EPUB → extract chapters, metadata, cover; convert HTML → markdown |
| `epub_generator.py` | `EpubGenerator` | Create EPUB from scratch: OPF, NCX, TOC XHTML, chapter XHTML, CSS |
| `epub_importer.py` | `EpubImporter` | Full EPUB import workflow with QRunnable threading |
| `epub_text_processor.py` | `EpubTextProcessor` | Markdown formatting (bold, italic, underline), custom patterns (center, separator) |
| `creator.py` | `EpubConverterLogic` | Orchestrates EPUB creation from translated chapters |

### Text Cleaning (`cleaner.py`)

| Mode | Method | Description |
|------|--------|-------------|
| Remove After Text | `_remove_after_text()` | Delete all content after a pattern |
| Remove Duplicates | `_remove_duplicates()` | Keep only last occurrence of pattern |
| Remove Specific Lines | `_remove_line()` | Delete lines matching pattern |
| Normalize Spacing | `_remove_multiple_blanks()` | Collapse multiple blank lines to one |
| Find & Replace | `_search_replace()` | Text replace across all lines |

### File Loader (`loader.py`)

`FileLoader.load_files()` discovers `.txt`/`.md` files from `originals/` and `translated/` directories, checks translation status via database, and emits structured file lists with status metadata.

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | >=6.0.0 | Desktop GUI framework |
| beautifulsoup4 | >=4.12.0 | HTML/XML parsing (EPUB processing) |
| pypub3 | >=2.0.8 | EPUB creation support |
| requests | >=2.28.0 | HTTP client for AI API calls |
| python-dotenv | >=1.0.0 | `.env` API key loading |
| ebooklib | >=0.18 | EPUB reading/writing |
| mistune | >=3.0.0 | Markdown parsing |
