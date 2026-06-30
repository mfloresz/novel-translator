import type { Ref } from "vue";
import { createHttpClient } from "@/api/http";
import type {
  AuthResponse,
  BatchCheckResponse,
  BatchUpdateResponse,
  BatchUpdateSelection,
  BatchTranslateResponse,
  BatchTranslateSelection,
  BatchTranslateStartResponse,
  CleanPreviewResponse,
  EpubPreviewResult,
  GeneralPromptKey,
  GeneralPromptRecord,
  ChapterSummary,
  ChapterSummaryPage,
  ImportEpubResult,
  ImportUrlResult,
  NovelEpubRecord,
  PaginatedResult,
  PreviewUrlResult,
  ReadingProgress,
  UpdateUrlPreviewResult,
  ProvidersResponse,
  ServerSettings,
  UpdateUrlResult,
} from "@/api/types";
import type {
  Chapter,
  ChapterUpsertInput,
  CreateNovelInput,
  Novel,
  TranslationJob,
  TranslationJobOptions,
  UpdateNovelInput,
} from "@/domain";
import {
  normalizePromptSettings,
  type ServerDefaults,
  type ServerTranslationDefaults,
} from "@/domain/project-settings";
import { getApiBaseUrl } from "@/utils/api-base-url";

function normalizeNovel(
  novel: Novel,
  translationDefaults?: ServerTranslationDefaults,
): Novel {
  return {
    ...novel,
    sourceTitle: typeof novel.sourceTitle === "string" ? novel.sourceTitle : "",
    sourceAuthor:
      typeof novel.sourceAuthor === "string" ? novel.sourceAuthor : "",
    sourceDescription:
      typeof novel.sourceDescription === "string"
        ? novel.sourceDescription
        : "",
    sourceSeries:
      typeof novel.sourceSeries === "string" ? novel.sourceSeries : "",
    sourceNumber:
      typeof novel.sourceNumber === "string" ? novel.sourceNumber : "",
    targetTitle: typeof novel.targetTitle === "string" ? novel.targetTitle : "",
    targetAuthor:
      typeof novel.targetAuthor === "string" ? novel.targetAuthor : "",
    targetDescription:
      typeof novel.targetDescription === "string"
        ? novel.targetDescription
        : "",
    targetSeries:
      typeof novel.targetSeries === "string" ? novel.targetSeries : "",
    targetNumber:
      typeof novel.targetNumber === "string" ? novel.targetNumber : "",
    glossary: Array.isArray(novel.glossary) ? novel.glossary : [],
    prompts: normalizePromptSettings(novel.prompts),
    notes: typeof novel.notes === "string" ? novel.notes : "",
    aiOptions: {
      provider: novel.aiOptions?.provider ?? "",
      model: novel.aiOptions?.model ?? "",
      timeoutMs: novel.aiOptions?.timeoutMs ?? undefined,
    },
    translationOptions: {
      ...(translationDefaults ?? {}),
      ...(novel.translationOptions ?? {}),
    },
    cleanupRules: Array.isArray(novel.cleanupRules) ? novel.cleanupRules : [],
    url: typeof novel.url === "string" ? novel.url : "",
    customCommands:
      typeof novel.customCommands === "string" ? novel.customCommands : "",
    status:
      novel.status === "completed" ||
      novel.status === "hiatus" ||
      novel.status === "cancelled"
        ? novel.status
        : "ongoing",
    tags: Array.isArray(novel.tags)
      ? novel.tags.filter((tag): tag is string => typeof tag === "string")
      : [],
    ownerId: typeof novel.ownerId === "string" ? novel.ownerId : "",
    isPublic: Boolean(novel.isPublic),
    chapterCount: Number.isFinite(novel.chapterCount) ? novel.chapterCount : 0,
    translatedCount: Number.isFinite(novel.translatedCount)
      ? novel.translatedCount
      : 0,
    completedCount: Number.isFinite(novel.completedCount)
      ? novel.completedCount
      : 0,
    originalCharCount: Number.isFinite(novel.originalCharCount)
      ? novel.originalCharCount
      : 0,
    translatedCharCount: Number.isFinite(novel.translatedCharCount)
      ? novel.translatedCharCount
      : 0,
    refinedCharCount: Number.isFinite(novel.refinedCharCount)
      ? novel.refinedCharCount
      : 0,
    totalCharCount: Number.isFinite(novel.totalCharCount)
      ? novel.totalCharCount
      : 0,
    maxChapterOrder: Number.isFinite(novel.maxChapterOrder)
      ? novel.maxChapterOrder
      : 0,
  };
}

export function createApiClient(defaultsRef: Ref<ServerDefaults | null>) {
  const http = createHttpClient({ baseUrl: getApiBaseUrl() });
  const withDefaults = (novel: Novel) =>
    normalizeNovel(novel, defaultsRef.value?.translation);

  return {
    auth: {
      register(input: { email: string; password: string; name?: string }) {
        return http.post<AuthResponse>("/api/auth/register", input);
      },
      login(input: { email: string; password: string }) {
        return http.post<AuthResponse>("/api/auth/login", input);
      },
      refresh() {
        return http.post<AuthResponse>("/api/auth/refresh");
      },
      logout() {
        return http.post<void>("/api/auth/logout");
      },
    },
    defaults: {
      async get(): Promise<ServerDefaults> {
        return http.get<ServerDefaults>("/api/defaults");
      },
    },
    settings: {
      async get(): Promise<ServerSettings> {
        return http.get<ServerSettings>("/api/user/settings");
      },
      async update(payload: ServerSettings): Promise<ServerSettings> {
        return http.put<ServerSettings>("/api/user/settings", payload);
      },
    },
    providers: {
      async list(): Promise<ProvidersResponse> {
        const result = await http.get<{
          providers: Array<{
            provider: string;
            label: string;
            baseUrl: string;
            model: string;
            models?: string[];
            kind: string;
            apiKeyConfigured?: boolean;
            apiKeyUpdatedAt?: string;
            enabled?: boolean;
          }>;
        }>("/api/user/providers");
        return {
          providers: result.providers.map((provider) => ({
            id: provider.provider,
            name: provider.label,
            baseUrl: provider.baseUrl,
            models: provider.models ?? [],
            defaultModel: provider.model,
            openaiCompat: provider.kind === "openai-compatible",
            apiKeyConfigured: provider.apiKeyConfigured,
            apiKeyUpdatedAt: provider.apiKeyUpdatedAt,
            enabled: provider.enabled,
          })),
        };
      },
      async update(
        providerKey: string,
        payload: { model: string; baseUrl: string; timeoutMs?: number },
      ) {
        return http.put(`/api/user/providers/${providerKey}`, payload);
      },
      async replaceKey(providerKey: string, apiKey: string) {
        return http.put(`/api/user/providers/${providerKey}/key`, { apiKey });
      },
      async deleteKey(providerKey: string) {
        return http.delete(`/api/user/providers/${providerKey}/key`);
      },
    },
    novels: {
      async previewFromUrl(url: string): Promise<PreviewUrlResult> {
        return http.post<PreviewUrlResult>("/api/db/novels/preview-from-url", {
          url,
        });
      },
      async importFromUrl(input: {
        url: string;
        sourceLanguage?: string;
        targetLanguage?: string;
        startChapter?: number;
        endChapter?: number;
      }): Promise<ImportUrlResult> {
        const result = await http.post<ImportUrlResult>(
          "/api/db/novels/import-from-url",
          input,
        );
        return { ...result, novel: withDefaults(result.novel) };
      },
      async updateFromUrl(
        novelId: string,
        input: { startChapter?: number; endChapter?: number },
      ): Promise<UpdateUrlResult> {
        return http.post<UpdateUrlResult>(
          `/api/db/novels/${novelId}/update-from-url`,
          input,
        );
      },
      async updatePreviewFromUrl(
        novelId: string,
      ): Promise<UpdateUrlPreviewResult> {
        return http.get<UpdateUrlPreviewResult>(
          `/api/db/novels/${novelId}/update-preview`,
        );
      },
      async importFromEpub(input: {
        file: Blob;
        fileName: string;
        sourceLanguage?: string;
        targetLanguage: string;
      }) {
        const form = new FormData();
        form.set(
          "file",
          new File([input.file], input.fileName, {
            type: "application/epub+zip",
          }),
        );
        if (input.sourceLanguage)
          form.set("sourceLanguage", input.sourceLanguage);
        form.set("targetLanguage", input.targetLanguage);
        const result = await http.post<ImportEpubResult>(
          "/api/db/novels/import-epub",
          form,
        );
        return { ...result, novel: withDefaults(result.novel) };
      },
      async list(
        params: { cursor?: string; limit?: number; select?: string[] } = {},
      ): Promise<PaginatedResult<Novel>> {
        const search = new URLSearchParams();
        if (params.cursor) search.set("cursor", params.cursor);
        if (params.limit) search.set("limit", String(params.limit));
        if (params.select && params.select.length > 0)
          search.set("select", params.select.join(","));
        const suffix = search.size > 0 ? `?${search.toString()}` : "";
        const result = await http.get<PaginatedResult<Novel>>(
          `/api/db/novels${suffix}`,
        );
        return { ...result, items: result.items.map(withDefaults) };
      },
      async get(novelId: string): Promise<Novel | null> {
        const novel = await http.get<Novel | null>(`/api/db/novels/${novelId}`);
        return novel ? withDefaults(novel) : null;
      },
      async listTagSuggestions(query = "", limit = 100): Promise<string[]> {
        const search = new URLSearchParams();
        if (query.trim()) search.set("q", query.trim());
        if (limit > 0) search.set("limit", String(limit));
        const suffix = search.size > 0 ? `?${search.toString()}` : "";
        const result = await http.get<{ items?: string[] }>(
          `/api/db/novels/tags/suggestions${suffix}`,
        );
        return Array.isArray(result.items)
          ? result.items.filter(
              (item): item is string => typeof item === "string",
            )
          : [];
      },
      async listSeriesSuggestions(query = "", limit = 100): Promise<string[]> {
        const search = new URLSearchParams();
        if (query.trim()) search.set("q", query.trim());
        if (limit > 0) search.set("limit", String(limit));
        const suffix = search.size > 0 ? `?${search.toString()}` : "";
        const result = await http.get<{ items?: string[] }>(
          `/api/db/novels/series/suggestions${suffix}`,
        );
        return Array.isArray(result.items)
          ? result.items.filter(
              (item): item is string => typeof item === "string",
            )
          : [];
      },
      async create(data: CreateNovelInput): Promise<Novel> {
        const novel = await http.post<Novel>("/api/db/novels", data);
        return withDefaults(novel);
      },
      async update(novelId: string, patch: UpdateNovelInput): Promise<Novel> {
        const novel = await http.patch<Novel>(
          `/api/db/novels/${novelId}`,
          patch,
        );
        return withDefaults(novel);
      },
      async remove(novelId: string): Promise<void> {
        await http.delete<{ ok: boolean }>(`/api/db/novels/${novelId}`);
      },
      async uploadCover(novelId: string, file: File): Promise<Novel> {
        const form = new FormData();
        form.set("cover", file);
        const novel = await http.post<Novel>(
          `/api/db/novels/${novelId}/cover`,
          form,
        );
        return withDefaults(novel);
      },
      async copy(novelId: string): Promise<Novel> {
        const novel = await http.post<Novel>(`/api/db/novels/${novelId}/copy`);
        return withDefaults(novel);
      },
      async updateVisibility(
        novelId: string,
        isPublic: boolean,
      ): Promise<Novel> {
        const novel = await http.patch<Novel>(
          `/api/db/novels/${novelId}/visibility`,
          { isPublic },
        );
        return withDefaults(novel);
      },
      async checkBatchUpdates(): Promise<BatchCheckResponse> {
        return http.get<BatchCheckResponse>("/api/db/novels/check-batch-updates");
      },
      async batchUpdateFromUrl(
        selections: BatchUpdateSelection[],
      ): Promise<BatchUpdateResponse> {
        return http.post<BatchUpdateResponse>(
          "/api/db/novels/batch-update-from-url",
          { selections },
        );
      },
      async batchTranslatePreview(): Promise<BatchTranslateResponse> {
        return http.get<BatchTranslateResponse>("/api/db/novels/batch-translate-preview");
      },
      async batchTranslate(
        selections: BatchTranslateSelection[],
      ): Promise<BatchTranslateStartResponse> {
        return http.post<BatchTranslateStartResponse>(
          "/api/db/novels/batch-translate",
          { selections },
        );
      },
    },
    chapters: {
      list(novelId: string) {
        return http.get<ChapterSummary[]>(`/api/db/novels/${novelId}/chapters`);
      },
      listFull(novelId: string) {
        return http.get<Chapter[]>(`/api/db/novels/${novelId}/chapters/full`);
      },
      listSummaries(
        novelId: string,
        params: { limit?: number; offset?: number } = {},
      ) {
        const search = new URLSearchParams();
        if (params.limit) search.set("limit", String(params.limit));
        if (params.offset) search.set("offset", String(params.offset));
        const suffix = search.size > 0 ? `?${search.toString()}` : "";
        return http.get<ChapterSummaryPage>(
          `/api/db/novels/${novelId}/chapter-summaries${suffix}`,
        );
      },

      get(novelId: string, chapterId: string) {
        return http.get<Chapter | null>(
          `/api/db/novels/${novelId}/chapters/${chapterId}`,
        );
      },
      upsert(novelId: string, chapter: ChapterUpsertInput) {
        return http.post<Chapter>(
          `/api/db/novels/${novelId}/chapters`,
          chapter,
        );
      },
      async remove(novelId: string, chapterId: string) {
        await http.delete<{ ok: boolean }>(
          `/api/db/novels/${novelId}/chapters/${chapterId}`,
        );
      },
      async bulkRemove(novelId: string, ids: string[]) {
        return http.post<{ deleted: number; requested: number }>(
          `/api/db/novels/${novelId}/chapters/bulk-delete`,
          { ids },
        );
      },
      clean(
        novelId: string,
        input: {
          chapterIds: string[];
          mode: string;
          searchText: string;
          replaceText?: string;
          caseSensitive: boolean;
          useRegex: boolean;
          applyTo: string;
        },
      ) {
        return http.post<{
          modified: number;
          total: number;
          skipped: number;
          notFound: number;
          failed: number;
        }>(`/api/db/novels/${novelId}/chapters/clean`, input);
      },
      cleanPreview(
        novelId: string,
        input: {
          chapterId: string;
          mode: string;
          searchText: string;
          replaceText?: string;
          caseSensitive: boolean;
          useRegex: boolean;
          applyTo: string;
        },
      ) {
        return http.post<CleanPreviewResponse>(
          `/api/db/novels/${novelId}/chapters/clean-preview`,
          input,
        );
      },
      async updateStatus(
        novelId: string,
        chapterId: string,
        status: Chapter["status"],
        errorMessage?: string,
      ) {
        await http.patch<Chapter>(
          `/api/db/novels/${novelId}/chapters/${chapterId}/status`,
          { status, errorMessage },
        );
      },
    },
    jobs: {
      create(
        novelId: string,
        chapterIds: string[],
        options: TranslationJobOptions = {},
      ) {
        return http.post<TranslationJob>(
          `/api/db/novels/${novelId}/translation-jobs`,
          {
            chapterIds,
            operation: options.operation,
            options: {
              provider: options.provider,
              model: options.model,
            },
          },
        );
      },
      list(novelId: string, options: { failedOnly?: boolean } = {}) {
        const search = new URLSearchParams();
        if (options.failedOnly) search.set("failedOnly", "1");
        const suffix = search.size > 0 ? `?${search.toString()}` : "";
        return http.get<TranslationJob[]>(
          `/api/db/novels/${novelId}/translation-jobs${suffix}`,
        );
      },
      status() {
        return http.get<{ hasActive: boolean }>(
          `/api/db/translation-jobs/active/status`,
        );
      },
      listActive() {
        return http.get<TranslationJob[]>(`/api/db/translation-jobs/active`);
      },
      update(jobId: string, patch: Partial<TranslationJob>) {
        return http.patch<TranslationJob>(
          `/api/db/translation-jobs/${jobId}`,
          patch,
        );
      },
    },
    prompts: {
      async list() {
        const records =
          await http.get<Array<Record<string, unknown>>>("/api/user/prompts");
        return records as GeneralPromptRecord[];
      },
      upsert(input: {
        key: GeneralPromptKey;
        label?: string;
        description?: string;
        prompt: { systemPrompt?: string; userPrompt?: string };
        active?: boolean;
      }) {
        return http.put<GeneralPromptRecord>(
          `/api/user/prompts/${input.key}`,
          input,
        );
      },
    },
    readingProgress: {
      async get(novelId: string): Promise<ReadingProgress | null> {
        try {
          return await http.get<ReadingProgress>(
            `/api/user/novels/${novelId}/reading-progress`,
          );
        } catch {
          return null;
        }
      },
      async update(
        novelId: string,
        data: { chapterId: string; scrollPercent: number },
      ): Promise<ReadingProgress> {
        return http.put<ReadingProgress>(
          `/api/user/novels/${novelId}/reading-progress`,
          data,
        );
      },
    },
    epubs: {
      listByNovel(novelId: string) {
        return http.get<NovelEpubRecord[]>(
          `/api/epubs?novelId=${encodeURIComponent(novelId)}`,
        );
      },
      save(input: {
        novelId: string;
        fileKind: "original" | "translated";
        sourceVariant?: "original" | "translated" | "refined";
        fileName: string;
        blob: Blob;
      }) {
        const form = new FormData();
        form.set("novelId", input.novelId);
        form.set("fileKind", input.fileKind);
        if (input.sourceVariant) form.set("sourceVariant", input.sourceVariant);
        form.set(
          "file",
          new File([input.blob], input.fileName, {
            type: input.blob.type || "application/epub+zip",
          }),
        );
        return http.post<NovelEpubRecord>("/api/epubs", form);
      },
      preview(file: Blob, fileName: string) {
        const form = new FormData();
        form.set(
          "file",
          new File([file], fileName, { type: "application/epub+zip" }),
        );
        return http.post<EpubPreviewResult>("/api/epubs/preview", form);
      },
      buildDownloadUrl(id: string) {
        return `${getApiBaseUrl()}/api/epubs/${id}/download`;
      },
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
