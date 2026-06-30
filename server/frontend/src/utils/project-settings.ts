import type { GeneralPromptRecord } from "@/api/types";
import type { Novel } from "@/domain";
import {
  normalizePromptSettings,
  normalizeTranslationOptions,
  type ProjectSettings,
  type PromptSettings,
  type ServerTranslationDefaults,
} from "@/domain/project-settings";

function promptRecordsToSettings(
  records: GeneralPromptRecord[],
): PromptSettings {
  const next: PromptSettings = {};

  for (const record of records) {
    if (!record.active) continue;
    next[record.key] = { systemPrompt: record.prompt.systemPrompt };
  }

  return normalizePromptSettings(next);
}

export function buildProjectSettings(
  novel?: Novel | null,
  globalPrompts?: GeneralPromptRecord[],
  translationDefaults?: ServerTranslationDefaults,
): ProjectSettings {
  const promptFallbacks = globalPrompts
    ? promptRecordsToSettings(globalPrompts)
    : undefined;

  return {
    notes: novel?.notes ?? "",
    glossary: Array.isArray(novel?.glossary) ? novel.glossary : [],
    prompts: normalizePromptSettings({
      ...(promptFallbacks ?? {}),
      ...(novel?.prompts ?? {}),
    }),
    ai: {
      provider: novel?.aiOptions?.provider ?? "",
      model: novel?.aiOptions?.model ?? "",
      timeoutMs: novel?.aiOptions?.timeoutMs ?? undefined,
    },
    translation: normalizeTranslationOptions({
      ...normalizeTranslationOptions(translationDefaults),
      ...(novel?.translationOptions ?? {}),
    }),
    cleanupRules: Array.isArray(novel?.cleanupRules) ? novel.cleanupRules : [],
  };
}
