import type {
  CleanupRule,
  GlossaryEntry,
  NovelAIOptions,
  NovelTranslationOptions,
  PromptRoleTemplate,
  PromptSettings,
} from "@/domain/project-settings";

export type {
  CleanupRule,
  GlossaryEntry,
  NovelAIOptions,
  NovelTranslationOptions,
  PromptRoleTemplate,
  PromptSettings,
} from "@/domain/project-settings";

export type NovelStatus = "ongoing" | "completed" | "hiatus" | "cancelled";

export type Novel = {
  id: string;
  ownerId: string;
  sourceLanguage: string;
  targetLanguage: string;
  sourceTitle: string;
  sourceAuthor: string;
  sourceDescription: string;
  sourceSeries: string;
  sourceNumber: string;
  targetTitle: string;
  targetAuthor: string;
  targetDescription: string;
  targetSeries: string;
  targetNumber: string;
  glossary: GlossaryEntry[];
  prompts: PromptSettings;
  notes: string;
  aiOptions: NovelAIOptions;
  translationOptions: NovelTranslationOptions;
  cleanupRules: CleanupRule[];
  url: string;
  customCommands: string;
  status: NovelStatus;
  tags: string[];
  coverPath?: string;
  isPublic: boolean;
  chapterCount: number;
  translatedCount: number;
  completedCount: number;
  originalCharCount: number;
  translatedCharCount: number;
  refinedCharCount: number;
  totalCharCount: number;
  maxChapterOrder: number;
  createdAt: string;
  updatedAt: string;
};

export type ChapterStatus =
  | "pending"
  | "processing"
  | "translated"
  | "refined"
  | "done"
  | "failed";

export type Chapter = {
  id: string;
  novelId: string;
  chapterOrder: number;
  title: string;
  translatedTitle?: string;
  originalContent?: string;
  translatedContent?: string;
  refinedContent?: string;
  status: ChapterStatus;
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
};

export type TranslationJobStatus =
  | "pending"
  | "running"
  | "done"
  | "cancelled"
  | "failed";

export type TranslationJob = {
  id: string;
  novelId: string;
  status: TranslationJobStatus;
  operation?: "translate" | "refine" | "download";
  provider?: string;
  model?: string;
  totalChapters: number;
  completedChapters: number;
  failedChapters: number;
  errorMessage?: string;
  chapterIds?: string[];
  autoSegmentEnabled?: boolean;
  autoSegmentActive?: boolean;
  autoSegmentCount?: number;
  autoSegmentCurrentIndex?: number;
  autoSegmentCompletedCount?: number;
  autoSegmentChapterId?: string;
  autoSegmentChapterTitle?: string;
  createdAt: string;
  updatedAt: string;
  novelTitle?: string;
};

export type CreateNovelInput = {
  sourceTitle: string;
  sourceAuthor?: string;
  sourceDescription?: string;
  sourceLanguage: string;
  targetLanguage: string;
  sourceSeries?: string;
  sourceNumber?: string;
  targetTitle?: string;
  targetAuthor?: string;
  targetDescription?: string;
  targetSeries?: string;
  targetNumber?: string;
  glossary?: GlossaryEntry[];
  prompts?: PromptSettings;
  notes?: string;
  aiOptions?: Partial<NovelAIOptions>;
  translationOptions?: Partial<NovelTranslationOptions>;
  cleanupRules?: CleanupRule[];
  url?: string;
  customCommands?: string;
  status?: NovelStatus;
  tags?: string[];
};

export type UpdateNovelInput = Partial<CreateNovelInput>;

export type ChapterUpsertInput = {
  id?: string;
  chapterOrder: number;
  title?: string;
  translatedTitle?: string;
  originalContent?: string;
  translatedContent?: string;
  refinedContent?: string;
  status?: ChapterStatus;
  errorMessage?: string;
};

export type TranslationJobOptions = {
  operation?: "translate" | "refine" | "download";
  provider?: string;
  model?: string;
};

export function getNovelDisplayTitle(
  novel: Pick<Novel, "targetTitle" | "sourceTitle">,
): string {
  return novel.targetTitle || novel.sourceTitle;
}

export function getNovelDisplayAuthor(
  novel: Pick<Novel, "targetAuthor" | "sourceAuthor">,
): string {
  return novel.targetAuthor || novel.sourceAuthor;
}

export function getNovelDisplayDescription(
  novel: Pick<Novel, "targetDescription" | "sourceDescription">,
): string {
  return novel.targetDescription || novel.sourceDescription;
}

export function getNovelDisplaySeries(
  novel: Pick<Novel, "targetSeries" | "sourceSeries">,
): string {
  return (novel.targetSeries || novel.sourceSeries || "").trim();
}

export function getNovelDisplayNumber(
  novel: Pick<Novel, "targetNumber" | "sourceNumber">,
): string {
  return (novel.targetNumber || novel.sourceNumber || "").trim();
}
