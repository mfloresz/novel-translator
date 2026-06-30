# Database Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `src/logic/database.py`

## Architecture

Hybrid database system using **SQLite** as primary storage with **JSON files** as automatic backup/fallback.

### File Location

```
{novel_directory}/
├── .translation_records.db   # SQLite database
└── .translation_backup.json  # Automatic JSON backup
```

## Database Schema

### SQLite Tables

#### `translated_files`
Tracks which files have been translated.

```sql
CREATE TABLE translated_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    source_language TEXT NOT NULL,
    target_language TEXT NOT NULL,
    translated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `custom_terms`
Project-specific terminology for consistent translations.

```sql
CREATE TABLE custom_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    terms TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `book_metadata`
Comprehensive book information.

```sql
CREATE TABLE book_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    author TEXT,
    description TEXT,
    language TEXT DEFAULT 'es',
    collection TEXT,
    collection_type TEXT,
    collection_position TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `custom_prompts`
User-defined translation/check/refine prompts per language pair.

```sql
CREATE TABLE custom_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_lang TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    prompt TEXT NOT NULL,
    prompt_type TEXT DEFAULT 'translation',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_lang, target_lang, prompt_type)
);
```

#### `refined_files` (from code reference)
Tracks refinement status.

```sql
CREATE TABLE refined_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    refined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Class: `TranslationDatabase`

| Method | Purpose | SQLite | JSON Fallback |
|--------|---------|--------|---------------|
| `initialize_database()` | Creates tables on first run | Yes | - |
| `is_file_translated(filename)` | Check if file was already translated | Yes | Yes |
| `add_translation_record()` | Mark file as translated | Yes | Yes |
| `get_all_translated_files()` | List all translated files | Yes | Yes |
| `save_custom_terms(terms)` | Store custom terminology | Yes | Yes |
| `get_custom_terms()` | Retrieve custom terms | Yes | Yes |
| `save_book_metadata(...)` | Store book metadata | Yes | Yes |
| `get_book_metadata()` | Retrieve book metadata | Yes | Yes |
| `save_custom_prompt(...)` | Store custom prompt per language pair | Yes | - |
| `get_custom_prompt(...)` | Retrieve custom prompt | Yes | - |
| `is_file_refined(filename)` | Check refinement status | Yes | - |
| `add_refine_record(filename)` | Mark file as refined | Yes | - |

## JSON Backup Structure

### `_translation_backup.json`
```json
{
  "translated_files": [
    {
      "filename": "chapter_001.txt",
      "source_language": "en-US",
      "target_language": "es-MX",
      "translated_at": "2024-01-15T10:30:00"
    }
  ],
  "custom_terms": {
    "terms": "...",
    "updated_at": "2024-01-15T10:30:00"
  },
  "book_metadata": {
    "title": "...",
    "author": "...",
    "description": "...",
    "language": "es",
    "collection": "Saga Name",
    "collection_type": "series",
    "collection_position": "1"
  }
}
```

## Data Flow

```
Operation → Try SQLite ──success──→ Done
                      └──failure──→ Try JSON Backup ──success──→ Done
                                     └──failure──→ Log error, return safe default
```

## Related Modules

| Module | Interaction |
|--------|-------------|
| `translation_manager.py` | Reads/writes translation status, custom terms |
| `refine_manager.py` | Reads/writes refinement status |
| `loader.py` | Reads translation status for file listing |
| `creator.py` | Reads book metadata for EPUB |
| `epub_importer.py` | Writes book metadata on import |
| `main.py` | Reads/writes book metadata, custom prompts |
| `notes_dialog.py` | Reads/writes project notes |
