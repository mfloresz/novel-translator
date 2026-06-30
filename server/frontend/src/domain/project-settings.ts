export type ServerTranslationDefaults = {
  autoSegment: boolean;
  thresholdChars: number;
  maxChars: number;
  minChars: number;
  maxRetries: number;
  enableCheck: boolean;
  includePreviousChapterTitles: boolean;
  concurrency: number;
};

export type ServerDefaults = {
  translation: ServerTranslationDefaults;
};

export type GlossaryEntry = {
  id: string;
  source: string;
  target: string;
  context?: string;
};

export type PromptRoleTemplate = {
  systemPrompt?: string;
};

export type PromptSettings = {
  translation?: PromptRoleTemplate;
  refine?: PromptRoleTemplate;
  check?: PromptRoleTemplate;
};

export type LegacyPromptSettings = {
  translationPrompt?: string;
  refinePrompt?: string;
  checkPrompt?: string;
};

export type NovelAIOptions = {
  provider: string;
  model: string;
  timeoutMs?: number;
};

export type NovelTranslationOptions = {
  autoSegment: boolean;
  thresholdChars: number;
  maxChars: number;
  minChars: number;
  maxRetries: number;
  enableCheck: boolean;
  includePreviousChapterTitles: boolean;
};

export const DEFAULT_TRANSLATION_OPTIONS: NovelTranslationOptions = {
  autoSegment: true,
  thresholdChars: 10000,
  maxChars: 5000,
  minChars: 500,
  maxRetries: 2,
  enableCheck: false,
  includePreviousChapterTitles: false,
};

export function normalizeTranslationOptions(
  input?:
    | Partial<NovelTranslationOptions>
    | Partial<ServerTranslationDefaults>
    | null,
): NovelTranslationOptions {
  return {
    autoSegment: input?.autoSegment ?? DEFAULT_TRANSLATION_OPTIONS.autoSegment,
    thresholdChars:
      input?.thresholdChars ?? DEFAULT_TRANSLATION_OPTIONS.thresholdChars,
    maxChars: input?.maxChars ?? DEFAULT_TRANSLATION_OPTIONS.maxChars,
    minChars: input?.minChars ?? DEFAULT_TRANSLATION_OPTIONS.minChars,
    maxRetries: input?.maxRetries ?? DEFAULT_TRANSLATION_OPTIONS.maxRetries,
    enableCheck: input?.enableCheck ?? DEFAULT_TRANSLATION_OPTIONS.enableCheck,
    includePreviousChapterTitles:
      input?.includePreviousChapterTitles ??
      DEFAULT_TRANSLATION_OPTIONS.includePreviousChapterTitles,
  };
}

export type CleanupRule = {
  id: string;
  name: string;
  mode:
    | "remove_after"
    | "remove_line"
    | "remove_multiple_blanks"
    | "remove_duplicates"
    | "search_replace";
  searchText: string;
  replaceText?: string;
  applyTo: "original" | "translated" | "refined" | "all";
  enabled: boolean;
};

export type ProjectSettings = {
  notes: string;
  glossary: GlossaryEntry[];
  prompts: PromptSettings;
  ai: NovelAIOptions;
  translation: NovelTranslationOptions;
  cleanupRules: CleanupRule[];
};

export function normalizePromptSettings(
  input?: PromptSettings | LegacyPromptSettings | null,
): PromptSettings {
  if (!input || typeof input !== "object") return {};

  const next: PromptSettings = {};
  const maybe = input as PromptSettings & LegacyPromptSettings;

  if (maybe.translation && typeof maybe.translation === "object") {
    next.translation = { systemPrompt: maybe.translation.systemPrompt };
  } else if (maybe.translationPrompt) {
    next.translation = { systemPrompt: maybe.translationPrompt };
  }

  if (maybe.refine && typeof maybe.refine === "object") {
    next.refine = { systemPrompt: maybe.refine.systemPrompt };
  } else if (maybe.refinePrompt) {
    next.refine = { systemPrompt: maybe.refinePrompt };
  }

  if (maybe.check && typeof maybe.check === "object") {
    next.check = { systemPrompt: maybe.check.systemPrompt };
  } else if (maybe.checkPrompt) {
    next.check = { systemPrompt: maybe.checkPrompt };
  }

  return next;
}
