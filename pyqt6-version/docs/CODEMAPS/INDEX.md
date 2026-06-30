# Codemap Index

**Last Updated:** 2026-06-30

## Project Overview

**Novel Translator** is a comprehensive desktop application for managing, processing, and translating novels and text documents. Built with Python, PyQt6, and a modular architecture separating UI (GUI), business logic, and configuration layers.

| Area | Codemap | Entry Points | Description |
|------|---------|--------------|-------------|
| Frontend (GUI) | [frontend.md](frontend.md) | `main.py` | PyQt6 UI panels and dialogs |
| Backend (Logic) | [backend.md](backend.md) | `src/logic/` | Translation engine, file management, EPUB processing |
| Database | [database.md](database.md) | `src/logic/database.py` | Hybrid SQLite + JSON persistence |
| Integrations | [integrations.md](integrations.md) | `src/logic/translator_req.py` | AI providers (Gemini, Chutes, Mistral, etc.) |
| Workers | [workers.md](workers.md) | `src/logic/translation_manager.py`, `refine_manager.py` | Background QThread workers |

## High-Level Architecture

```
main.py  (Application Entry Point)
   │
   ├── src/gui/          (Qt UI Panels)
   │   ├── translate.py      →  TranslationManager
   │   ├── clean.py          →  CleanerLogic
   │   ├── create.py         →  EpubConverterLogic
   │   ├── refine.py         →  RefineManager
   │   ├── settings_gui.py   →  config.json, LanguageManager
   │   ├── epub_preview.py   →  EpubConverter
   │   ├── log_window.py     →  SessionLogger
   │   ├── notes_dialog.py   →  TranslationDatabase
   │   └── prompt_refine_settings.py
   │
   └── src/logic/        (Business Logic)
       ├── translator.py        →  translator_req.py
       ├── translator_req.py    →  AI Provider APIs
       ├── translation_manager.py  (QThread Worker)
       ├── refine_manager.py       (QThread Worker)
       ├── database.py
       ├── cleaner.py
       ├── folder_structure.py
       ├── epub_converter.py
       ├── epub_generator.py
       ├── epub_importer.py
       ├── epub_text_processor.py
       ├── creator.py
       ├── session_logger.py
       ├── status_manager.py
       ├── language_manager.py
       ├── loader.py
       └── functions.py

   src/config/        (Configuration)
   ├── config.json
   ├── translation_models.json
   ├── languages.json
   ├── markdown_rules.json
   ├── i18n/          (UI translations)
   └── prompts/       (AI prompts per language pair)
```

## Key Dataflows

```
1. Translation Flow:
   GUI (Translate Panel) → TranslationManager → TranslationWorker (QThread)
       → TranslatorLogic._segment_text() → translator_req.translate_segment()
       → AI Provider API → Verify → Save to originals/translated

2. EPUB Import Flow:
   GUI (Import EPUB) → EpubImporter → EpubConverter
       → Extract chapters → Convert HTML→Markdown → Save to originals/

3. EPUB Creation Flow:
   GUI (Create Panel) → EpubConverterLogic → EpubGenerator
       → Read translated/ files → Generate EPUB (XHTML + CSS + OPF)

4. Text Cleaning Flow:
   GUI (Clean Panel) → CleanerLogic
       → Apply cleaning modes to originals/ and translated/ files

5. Refinement Flow:
   GUI (Refine Panel) → RefineManager → RefineWorker (QThread)
       → TranslatorLogic._refine_translation()
       → Tool-based or prompt-based refinement → Save
```

## Project Structure

```
novel-translator/
├── main.py                        # Application entry point (NovelManagerApp)
├── pyproject.toml                 # Package configuration
├── clean.sh                       # Cache cleanup
├── install.sh / install_test.sh   # Linux installer
├── run_nt.sh / run_nt.bat / run_nt.exe  # Launch scripts
├── create_shortcut.ps1            # Windows shortcut creator
│
├── src/
│   ├── __init__.py
│   ├── gui/          # UI layer
│   ├── logic/        # Business logic layer
│   └── config/       # JSON configs, prompts, i18n
│
├── docs/
│   ├── CODEMAPS/     # Architecture documentation
│   └── plan_refinamiento_selectivo.md
│
├── assets/           # Screenshots for README
├── plans/            # (empty - planning folder)
└── .kilocode/        # Tool configuration
```

## Related Documentation

- [Frontend Codemap](frontend.md) - All GUI components and panels
- [Backend Codemap](backend.md) - Business logic modules
- [Database Codemap](database.md) - SQLite schema and JSON backup
- [Integrations Codemap](integrations.md) - AI providers and API configuration
- [Workers Codemap](workers.md) - Background QThread workers
