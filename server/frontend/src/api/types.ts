import type { Novel, Chapter, TranslationJob } from "@/domain";

export type PaginatedResult<T> = {
  items: T[];
  nextCursor?: string;
};

export type AuthUser = {
  id: string;
  email: string;
  name?: string;
  theme: "light" | "dark" | "system";
  createdAt?: string;
  updatedAt?: string;
};

export type AuthResponse = {
  token: string;
  user: AuthUser;
};

export type ImportEpubResult = {
  novel: Novel;
  epub: {
    id: string;
    novelId: string;
    fileKind: string;
    fileName: string;
    createdAt: string;
    updatedAt: string;
  };
  chaptersImported: number;
};

export type GeneralPromptKey = "translation" | "refine" | "check";

export type GeneralPromptRecord = {
  id: string;
  key: GeneralPromptKey;
  label?: string;
  description?: string;
  prompt: {
    systemPrompt?: string;
    userPrompt?: string;
  };
  active: boolean;
  updatedAt?: string;
};

export type NovelEpubRecord = {
  id: string;
  novelId: string;
  fileKind: "original" | "translated";
  sourceVariant?: "original" | "translated" | "refined";
  fileName?: string;
  url?: string;
  createdAt: string;
  updatedAt: string;
};

export type EpubPreviewChapter = {
  title: string;
  content: string;
};

export type EpubPreviewResult = {
  title: string;
  author: string;
  description: string;
  language: string;
  series: string;
  number: string;
  chapters: EpubPreviewChapter[];
};

export type ServerSettings = {
  theme: "light" | "dark" | "system";
  ai: {
    provider: string;
    baseUrl: string;
    model: string;
    timeoutMs: number;
  };
  translation: {
    autoSegment: boolean;
    thresholdChars: number;
    maxChars: number;
    minChars: number;
    maxRetries: number;
    enableCheck: boolean;
    includePreviousChapterTitles: boolean;
    concurrency: number;
  };
};

export type ProviderInfo = {
  id: string;
  name: string;
  baseUrl: string;
  models: string[];
  defaultModel: string;
  openaiCompat: boolean;
  apiKeyConfigured?: boolean;
  apiKeyUpdatedAt?: string;
  enabled?: boolean;
};

export type ProvidersResponse = {
  providers: ProviderInfo[];
};

export type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
  };
  message?: string;
};

export type ImportUrlResult = {
  novel: Novel;
  chaptersImported: number;
  totalChapters: number;
  downloadJob?: {
    id: string;
    totalChapters: number;
  };
};

export type PreviewUrlResult = {
  title: string;
  author?: string;
  description?: string;
  coverURL?: string;
  totalChapters: number;
  sourceURL: string;
};

export type UpdateUrlResult = {
  chaptersAdded: number;
  chapters: Chapter[];
  totalChapters: number;
  pendingChapters?: number;
  downloadJobId?: string;
  message?: string;
};

export type UpdateUrlPreviewResult = {
  title: string;
  author?: string;
  description?: string;
  coverURL?: string;
  sourceURL: string;
  currentChapters: number;
  totalChapters: number;
  newChapters: number;
  firstNewChapter: number;
  lastNewChapter: number;
};

export type ChapterSummary = {
  id: string;
  novelId: string;
  chapterOrder: number;
  title: string;
  translatedTitle?: string;
  status: Chapter["status"];
  errorMessage?: string;
  hasOriginalContent: boolean;
  hasTranslatedContent: boolean;
  hasRefinedContent: boolean;
  originalChars: number;
  translatedChars: number;
  refinedChars: number;
  createdAt: string;
  updatedAt: string;
};

export type ChapterSummaryPage = {
  items: ChapterSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type ChapterStats = {
  totalChapters: number;
  completedChapters: number;
  translatedChapters: number;
  originalCharacters: number;
  translatedCharacters: number;
  refinedCharacters: number;
  totalCharacters: number;
  maxChapterOrder: number;
};

export type CleanPreviewResponse = {
  chapterTitle: string;
  original: string;
  cleaned: string;
  changed: boolean;
  removedLines: number;
};

export type TranslationJobPatch = Partial<TranslationJob>;
export type ChapterList = Chapter[];

export type BatchCheckNovelResult = {
  novelId: string;
  sourceTitle: string;
  sourceAuthor?: string;
  coverUrl?: string;
  newChapters: number;
  firstNewChapter: number;
  lastNewChapter: number;
  startOrder: number;
  currentChapters: number;
  totalChapters: number;
  newChapterInfo: { url: string; title: string }[];
  error?: string;
};

export type BatchCheckResponse = {
  results: BatchCheckNovelResult[];
  checked: number;
  withUpdates: number;
  errors: number;
};

export type BatchUpdateSelection = {
  novelId: string;
  startOrder: number;
  startChapter?: number;
  endChapter?: number;
  newChapterInfo: { url: string; title: string }[];
};

export type BatchUpdateJobResult = {
  novelId: string;
  jobId: string;
  pendingChapters: number;
};

export type BatchUpdateResponse = {
  jobs: BatchUpdateJobResult[];
  totalPending: number;
};

export type BatchTranslateNovelResult = {
  novelId: string;
  sourceTitle: string;
  sourceAuthor?: string;
  coverUrl?: string;
  pendingChapters: number;
  totalChapters: number;
  translatedCount: number;
  completedCount: number;
  hasOriginalContent: boolean;
};

export type BatchTranslateResponse = {
  results: BatchTranslateNovelResult[];
  totalNovels: number;
  withPending: number;
};

export type BatchTranslateSelection = {
  novelId: string;
  chapterIds?: string[];
};

export type BatchTranslateJobResult = {
  novelId: string;
  jobId: string;
  pendingChapters: number;
};

export type ReadingProgress = {
  id: string;
  userId: string;
  novelId: string;
  chapterId: string;
  scrollPercent: number;
  createdAt: string;
  updatedAt: string;
};

export type BatchTranslateStartResponse = {
  jobs: BatchTranslateJobResult[];
  totalPending: number;
};
