import { onScopeDispose, ref, watch, type Ref } from "vue";
import type { Chapter, ChapterUpsertInput } from "@/domain";
import { useAppServices } from "@/app/services";

const PARALLEL_BATCH = 4;

export function useChapters(
  novelId: Ref<string>,
  options: { autoLoad?: boolean } = {},
) {
  const { api } = useAppServices();
  const chapters = ref<Chapter[]>([]);
  const loading = ref(false);
  const refreshing = ref(false);

  async function listChapters() {
    if (!novelId.value) {
      chapters.value = [];
      return chapters.value;
    }
    const isInitialLoad = chapters.value.length === 0;
    if (isInitialLoad) {
      loading.value = true;
    } else {
      refreshing.value = true;
    }
    try {
      const fresh = await api.chapters.listFull(novelId.value);
      mergeChapters(fresh);
      return chapters.value;
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  }

  function mergeChapters(fresh: Chapter[]) {
    const current = chapters.value;

    if (current.length === 0) {
      chapters.value = fresh;
      return;
    }

    const currentById = new Map(current.map((item) => [item.id, item]));
    const seen = new Set<string>();
    let mutated = false;

    for (const item of fresh) {
      seen.add(item.id);
      const existing = currentById.get(item.id);
      if (existing) {
        if (!shallowChapterEquals(existing, item)) {
          Object.assign(existing, item);
          mutated = true;
        }
      } else {
        mutated = true;
      }
    }

    const removedIds: string[] = [];
    for (const item of current) {
      if (!seen.has(item.id)) removedIds.push(item.id);
    }

    if (removedIds.length > 0) {
      const removed = new Set(removedIds);
      chapters.value = current.filter((item) => !removed.has(item.id));
    } else if (mutated) {
      chapters.value = [...current];
    }
  }

  function shallowChapterEquals(a: Chapter, b: Chapter): boolean {
    return (
      a.id === b.id &&
      a.novelId === b.novelId &&
      a.chapterOrder === b.chapterOrder &&
      a.title === b.title &&
      a.status === b.status &&
      a.originalContent === b.originalContent &&
      a.translatedContent === b.translatedContent &&
      a.refinedContent === b.refinedContent &&
      a.errorMessage === b.errorMessage &&
      a.createdAt === b.createdAt &&
      a.updatedAt === b.updatedAt
    );
  }

  async function createChapter(chapter: ChapterUpsertInput) {
    const created = await api.chapters.upsert(novelId.value, chapter);
    chapters.value = [...chapters.value, created].sort(
      (a, b) => a.chapterOrder - b.chapterOrder,
    );
    return created;
  }

  async function updateChapter(chapter: ChapterUpsertInput) {
    if (!chapter.id) throw new Error("Chapter id required");
    const updated = await api.chapters.upsert(novelId.value, chapter);
    chapters.value = chapters.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
    return updated;
  }

  async function updateChapterStatus(
    chapterId: string,
    status: Chapter["status"],
    errorMessage?: string,
  ) {
    await api.chapters.updateStatus(
      novelId.value,
      chapterId,
      status,
      errorMessage,
    );
    chapters.value = chapters.value.map((item) =>
      item.id === chapterId ? { ...item, status, errorMessage } : item,
    );
  }

  async function bulkCreateChapters(inputs: ChapterUpsertInput[]) {
    const created: Chapter[] = [];
    for (let i = 0; i < inputs.length; i += PARALLEL_BATCH) {
      const slice = inputs.slice(i, i + PARALLEL_BATCH);
      const results = await Promise.all(
        slice.map((input) => api.chapters.upsert(novelId.value, input)),
      );
      created.push(...results);
    }
    const map = new Map(chapters.value.map((item) => [item.id, item]));
    created.forEach((item) => map.set(item.id, item));
    chapters.value = Array.from(map.values()).sort(
      (a, b) => a.chapterOrder - b.chapterOrder,
    );
    return created;
  }

  async function deleteChapter(chapterId: string) {
    await api.chapters.remove(novelId.value, chapterId);
    chapters.value = chapters.value.filter((item) => item.id !== chapterId);
  }

  async function bulkDeleteChapters(chapterIds: string[]) {
    if (chapterIds.length === 0) {
      return { deleted: 0, requested: 0, missing: [] as string[] };
    }
    const result = await api.chapters.bulkRemove(novelId.value, chapterIds);
    const removed = new Set(chapterIds);
    chapters.value = chapters.value.filter((item) => !removed.has(item.id));
    return {
      deleted: result.deleted,
      requested: result.requested,
      missing: [] as string[],
    };
  }

  watch(
    novelId,
    () => {
      if (options.autoLoad === false) return;
      void listChapters();
    },
    { immediate: true },
  );

  onScopeDispose(() => {
    chapters.value = [];
  });

  return {
    chapters,
    loading,
    refreshing,
    listChapters,
    createChapter,
    updateChapter,
    updateChapterStatus,
    bulkCreateChapters,
    deleteChapter,
    bulkDeleteChapters,
  };
}
