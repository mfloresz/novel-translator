# Integrations Codemap

**Last Updated:** 2026-06-30
**Entry Points:** `src/logic/translator_req.py`, `src/config/translation_models.json`

## Architecture

The application integrates with multiple AI providers for translation, using a unified interface through `translator_req.py`. Each provider is configured in `translation_models.json` and invoked via provider-specific handlers.

```
translator_req.translate_segment()
    ├── Provider Type: "gemini"  → _translate_gemini()
    │                                └── _translate_gemini_with_tools() (if tools enabled)
    │
    ├── Provider Type: "openai"  → _translate_openai_like()
    │                                └── _process_streaming_response() (if stream enabled)
    │
    └── Both → _process_response()
               └── _clean_translation()
```

## AI Provider Configuration

### Provider: Google Gemini

| Config Key | `gemini` |
|------------|----------|
| API Type | `gemini` (proprietary) |
| Base URL | `https://generativelanguage.googleapis.com/v1beta/models` |
| Auth | `GOOGLE_GEMINI_API_KEY` from `.env` |

**Models:**

| Key | Name | Endpoint | Thinking |
|-----|------|----------|----------|
| `gemini-flash` | Gemini Flash | `gemini-flash-latest:generateContent` | No |
| `gemini-flash-lite` | Gemini Flash Lite | `gemini-flash-lite-latest:generateContent` | No |

### Provider: Chutes AI

| Config Key | `chutes` |
|------------|----------|
| API Type | `openai` (OpenAI-compatible) |
| Base URL | `https://llm.chutes.ai/v1/chat/completions` |
| Auth | `CHUTES_API_KEY` from `.env` |

**Models:** Mistral Small 3.1, Mistral Small 3.2, GPT OSS 120B, DeepSeek 3.2, DeepSeek 3.1, Xiaomi MiMo, Qwen3 80B A3B

### Provider: Mistral AI

| Config Key | `mistral` |
|------------|-----------|
| API Type | `openai` |
| Base URL | `https://api.mistral.ai/v1/chat/completions` |
| Auth | `MISTRAL_API_KEY` from `.env` |

**Models:** Ministral 8B, Mistral Small, Mistral Creative

### Provider: OpenRouter

| Config Key | `openrouter` |
|------------|--------------|
| API Type | `openai` |
| Base URL | `https://openrouter.ai/api/v1/chat/completions` |
| Auth | `OPENROUTER_API_KEY` from `.env` |

**Models:** Grok 4.1 Fast, GPT OSS 120B, Mistral Small 3.2, Gemini Flash Lite

### Provider: OpenAI

| Config Key | `openai` |
|------------|----------|
| API Type | `openai` |
| Base URL | `https://api.openai.com/v1/chat/completions` |
| Auth | `OPENAI_API_KEY` from `.env` |

**Models:** GPT 5 Mini

### Provider: OpenCode GO

| Config Key | `opencode` |
|------------|------------|
| API Type | `openai` |
| Base URL | `https://opencode.ai/zen/go/v1/chat/completions` |
| Auth | `OPENCODE_API_KEY` from `.env` |

**Models:** DeepSeek V4 Flash, MiMo 2.5, Qwen 3.5 Plus

### Provider: Deepinfra

| Config Key | `deepinfra` |
|------------|-------------|
| API Type | `openai` |
| Base URL | `https://api.deepinfra.com/v1/openai/chat/completions` |
| Auth | `DEEPINFRA_API_KEY` from `.env` |

**Models:** Mistral Small, DeepSeek 3.2

## API Request Flow

```
1. translate_segment() receives: provider, model, text, api_key, config
2. Route based on provider type:
   - "gemini" type → _translate_gemini()
       - Build request payload with model endpoint
       - POST to Google Gemini API
       - Parse response via _process_response()
       - Optionally use _translate_gemini_with_tools() for tool-based calls
   - "openai" type → _translate_openai_like()
       - Build OpenAI-format request payload
       - POST to provider's base_url + endpoint
       - Handle streaming if configured (mistral-small-3.2 via Chutes)
       - Handle tool calls if supported (gpt-oss-120b, deepseek models)
3. Post-process via _process_response()
4. Clean translation via _clean_translation()
```

## Streaming Support

- **Chutes AI**: Mistral Small 3.1 supports streaming (`"stream": false` currently)
- **OpenCode GO**: All models support streaming (`"stream": true`)
- Non-streaming providers receive full response on completion

## Tool/Function Calling Support

Models flagged with `"supports_tools": true` can use function calling for refinement:

- **Chutes**: GPT OSS 120B, DeepSeek 3.2, DeepSeek 3.1, Qwen3 80B A3B
- **Mistral**: Mistral Small
- **OpenRouter**: Mistral Small 3.2

Refinement tools defined in `refine_tools.py`:
- `replace_text` - Exact substring replacement
- `delete_text` - Remove exact substring
- `insert_text` - Insert content after anchor
- `no_changes_needed` - Signal no changes required

## Prompt System

| Location | Contents |
|----------|----------|
| `src/config/prompts/prompts-base/` | Default prompts: `translation.txt`, `check.txt`, `refine.txt`, `refine_alt.txt`, `refine_tools.txt` |
| `src/config/prompts/en-US_es-MX/` | Language-pair specific: `translation.txt`, `translation-alt.txt`, `translation-no-tr.txt`, `check.txt`, `refine.txt`, `refine_tools.txt` |
| `src/config/prompts/en-US_es-US/` | Language-pair specific prompts |

Prompts are Jinja-like templates with variables: `{source_lang}`, `{target_lang}`, `{terminology_reference}`, `{text_to_translate}`.

## Configuration File

`src/config/config.json` stores:

| Key | Purpose |
|-----|---------|
| `default_directory` | Default working directory |
| `provider` | Default AI provider |
| `model` | Default model |
| `source_language` | Default source language code |
| `target_language` | Default target language code |
| `ui_language` | UI locale (e.g., `en_US`, `es_MX`) |
| `check_refine_settings` | Separate provider/model for QA |
| `auto_segmentation` | Threshold and segment size |
| `timeout` | API request timeout in seconds |

## Session API Keys

The UI allows entering temporary API keys per session that override `.env` values, stored in `temp_api_keys` dict passed through the translation pipeline.
