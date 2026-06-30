# Frontend Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `main.py`, `src/gui/*.py`
**Framework:** PyQt6

## Architecture

```
main.py: NovelManagerApp (QMainWindow)
   │
   ├── Tab 0: [Translate Panel]  ─── src/gui/translate.py
   │       TranslationTab(QWidget): Provider/model selection,
   │       custom terms, range controls, translate/stop buttons
   │
   ├── Tab 1: [Refine Panel]     ─── src/gui/refine.py
   │       RefineTab(QWidget): Refinement of translated chapters
   │       with separate provider/model, tool-based refinement
   │
   ├── Tab 2: [Clean Panel]      ─── src/gui/clean.py
   │       CleanPanel(QWidget): 5 cleaning modes,
   │       range selection, preview & backup
   │
   ├── Tab 3: [EPUB Creation]    ─── src/gui/create.py
   │       CreateEpubPanel(QWidget): Metadata editor,
   │       cover selection, collection info, pattern rules
   │
   ├── Dialogs:
   │   ├── SettingsDialog        ─── src/gui/settings_gui.py
   │   ├── EpubPreviewWindow     ─── src/gui/epub_preview.py
   │   ├── LogWindow             ─── src/gui/log_window.py
   │   ├── NotesDialog           ─── src/gui/notes_dialog.py
   │   ├── PromptRefineSettings  ─── src/gui/prompt_refine_settings.py
   │   ├── ApiKeyDialog          ─── (inline in translate.py/refine.py)
   │   └── PresetTermsDialog     ─── (inline in translate.py/refine.py)
   │
   └── Icons (SVG/PNG/ICO)      ─── src/gui/icons/
```

## Key GUI Modules

| Module | Class | Purpose | Dependencies |
|--------|-------|---------|--------------|
| `main.py` | `NovelManagerApp` | Main window, tab management, file table, recent folders, theme detection | All panels, `FileLoader`, `TranslationDatabase` |
| `translate.py` | `TranslationTab` | Translation UI: providers, models, languages, terms, range, check/refine toggles | `TranslationManager`, `TranslationDatabase`, `PresetTermsDialog` |
| `refine.py` | `RefineTab` | Refinement UI: separate provider/model, terms, range controls | `RefineManager`, `TranslationDatabase` |
| `clean.py` | `CleanPanel` | Text cleaning: 5 radio-button modes, search/replace, range | `CleanerLogic` |
| `create.py` | `CreateEpubPanel` | EPUB creation: title, author, cover, description, patterns, collection | `EpubConverterLogic`, `TranslationDatabase` |
| `settings_gui.py` | `SettingsDialog` | Settings: UI language, provider/model, source/target langs, library path, segmentation, prompts management | `LanguageManager`, `config.json` |
| `epub_preview.py` | `EpubPreviewWindow` | EPUB import preview: side-by-side chapter view, formatting options | `EpubConverter` |
| `log_window.py` | `LogWindow` | Session log viewer with clear/close | `SessionLogger` |
| `notes_dialog.py` | `NotesDialog` | Per-project notes editor with persistence | `TranslationDatabase` |
| `prompt_refine_settings.py` | `PromptRefineSettingsDialog` | Advanced: segmentation config, custom prompts per language pair | - |

## Data Flow — UI to Logic

```
User Action → GUI Widget → Signal/Slot → Logic Layer → Async Worker → Result → Update UI
```

| User Action | GUI Path | Logic Called | Async? |
|-------------|----------|-------------|--------|
| Click Translate | `translate.py` → button signal | `TranslationManager.translate_files()` | Yes (QThread) |
| Click Refine | `refine.py` → button signal | `RefineManager.refine_files()` | Yes (QThread) |
| Click Clean | `clean.py` → button signal | `CleanerLogic.clean_files()` | No |
| Create EPUB | `create.py` → button signal | `EpubConverterLogic.create_epub()` | No |
| Import EPUB | `main.py` → menu action | `EpubImporter.start_import()` | Yes (QRunnable) |
| Open File | `main.py` → table double-click | `open_chapter_file()` | No |
| Save Settings | `settings_gui.py` → save button | Writes to `config.json` | No |
| Switch Library | `main.py` → combobox | Reloads files + metadata | No |

## Theming & Icons

- **Theme Detection**: `_is_dark_theme()` checks `QPalette.Window` luminance
- **Icons**: SVG icons in `src/gui/icons/` with automatic light/dark adaptation via `create_themed_icon()`
- **Status Colors**: Color-coded chapter status via `status_manager.get_status_color()` (green=translated, orange=processing, red=error)

## Exports

| Module | Public API |
|--------|-----------|
| `main.py` | `ElidedLabel`, `ImportChaptersThread`, `NovelManagerApp` |
| `translate.py` | `PresetTermsDialog`, `ApiKeyDialog`, `TranslationTab` |
| `refine.py` | `PresetTermsDialog`, `ApiKeyDialog`, `RefineTab` |
| `clean.py` | `CleanPanel` |
| `create.py` | `EpubPattern`, `CreateEpubPanel` |
| `settings_gui.py` | `SettingsDialog`, `AddLanguageDialog`, `NewPromptDialog` |
| `epub_preview.py` | `EpubPreviewWindow` |
| `log_window.py` | `LogWindow` |
| `notes_dialog.py` | `NotesDialog` |
| `prompt_refine_settings.py` | `PromptRefineSettingsDialog` |
