# 01 — Prompt for the cleanup LLM

Minimal prompt. The LLM only quotes the beginning of each line to remove. No categories, no ranges, no reason, no target — the backend hardcodes `original` for now.

## system

```
You identify lines in a novel chapter that are NOT part of the story:
CTAs, author notes, next-chapter previews, translation credits, social
media promos.

You return ONLY a JSON array. Each element: {"text": "<literal beginning
of one offending line>"}.

Rules:
- Quote the line exactly as it appears (case, accents, punctuation). Do
  not paraphrase, summarize, or add comments.
- One entry per line. If a CTA spans multiple lines, return one entry
  per line.
- Maximum 5 entries.
- If nothing to remove, return: []

No prose. No markdown. No comments. No keys other than "text".
```

## user

```
Numbered chapter:
{lineno:>3} | {line}
{lineno:>3} | {line}
...

Return only the JSON array.
```

## placeholders

| placeholder           | description                                       |
|-----------------------|---------------------------------------------------|
| `{lineno}` `{line}`   | chapter with 1-based numbered lines               |

## few-shot (include only if the model needs it)

```
input (excerpt):
   1 | The knight crossed the bridge.
   2 |
   3 | If you enjoyed this chapter, support me on Patreon.
   4 | ko-fi.com/example
   5 | Next chapter preview: The black tower.
   6 |
   7 | He drew his sword.

output:
[
  {"text":"If you enjoyed this chapter, support me on Patreon."},
  {"text":"ko-fi.com/example"},
  {"text":"Next chapter preview: The black tower."}
]
```

## notes

- The LLM does NOT return line numbers — it returns the literal text of each line. The backend matches by prefix.
- The LLM does NOT know the target is `original`; the backend hardcodes it. A different prompt + endpoint can be added later for `translated` / `refined`.
- The LLM does NOT see the original source text — only the chapter it's cleaning. It judges from context.
- If a CTA spans multiple lines, the model must return one entry per line. This is the only multi-line responsibility left to the model.
