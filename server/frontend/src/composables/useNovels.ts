import { computed, ref } from "vue";
import type { CreateNovelInput, Novel, UpdateNovelInput } from "@/domain";
import type {
  ImportEpubResult,
  ImportUrlResult,
  PreviewUrlResult,
} from "@/api/types";
import { useAppServices } from "@/app/services";

const novels = ref<Novel[]>([]);
const loadedListSignatures = new Set<string>();
const fullNovelIds = new Set<string>();

export function useNovels() {
  const { api } = useAppServices();
  const loading = ref(false);

  function listSignature(select?: string[]) {
    if (!select || select.length === 0) return "__full__";
    return [...select].sort().join(",");
  }

  function markNovelsFull(items: Novel[]) {
    items.forEach((item) => fullNovelIds.add(item.id));
  }

  function mergeListedNovel(
    existing: Novel | undefined,
    incoming: Novel,
    select?: string[],
  ) {
    if (!existing || !select || select.length === 0) return incoming;
    const next = { ...existing } as Record<string, unknown>;
    const source = incoming as Record<string, unknown>;
    for (const field of select) {
      next[field] = source[field];
    }
    next.id = incoming.id;
    return next as Novel;
  }

  function mergeNovelList(items: Novel[], select?: string[]) {
    const existingById = new Map(novels.value.map((item) => [item.id, item]));
    return items.map((item) =>
      mergeListedNovel(existingById.get(item.id), item, select),
    );
  }

  async function listNovels(force = false, select?: string[]) {
    const signature = listSignature(select);
    if (loadedListSignatures.has(signature) && !force) return novels.value;
    loading.value = true;
    try {
      const result = await api.novels.list({ select });
      novels.value = mergeNovelList(result.items, select);
      loadedListSignatures.add(signature);
      if (!select || select.length === 0) {
        markNovelsFull(result.items);
      }
      return novels.value;
    } finally {
      loading.value = false;
    }
  }

  async function importNovelFromEpub(input: {
    file: Blob;
    fileName: string;
    sourceLanguage?: string;
    targetLanguage: string;
  }): Promise<ImportEpubResult> {
    const result = await api.novels.importFromEpub(input);
    novels.value = [
      result.novel,
      ...novels.value.filter((item) => item.id !== result.novel.id),
    ];
    fullNovelIds.add(result.novel.id);
    return result;
  }

  async function importNovelFromUrl(input: {
    url: string;
    sourceLanguage?: string;
    targetLanguage?: string;
    startChapter?: number;
    endChapter?: number;
  }): Promise<ImportUrlResult> {
    const result = await api.novels.importFromUrl(input);
    novels.value = [
      result.novel,
      ...novels.value.filter((item) => item.id !== result.novel.id),
    ];
    fullNovelIds.add(result.novel.id);
    return result;
  }

  async function previewNovelFromUrl(url: string): Promise<PreviewUrlResult> {
    return api.novels.previewFromUrl(url);
  }

  async function getNovel(novelId: string, force = true) {
    const cached = novels.value.find((item) => item.id === novelId);
    if (cached && !force && fullNovelIds.has(novelId)) return cached;
    const novel = await api.novels.get(novelId);
    if (novel) {
      replaceNovelInList(novel);
    }
    return novel;
  }

  async function createNovel(data: CreateNovelInput) {
    const novel = await api.novels.create(data);
    novels.value = [
      novel,
      ...novels.value.filter((item) => item.id !== novel.id),
    ];
    fullNovelIds.add(novel.id);
    return novel;
  }

  async function updateNovel(novelId: string, patch: UpdateNovelInput) {
    const updated = await api.novels.update(novelId, patch);
    novels.value = novels.value.map((item) =>
      item.id === novelId ? updated : item,
    );
    fullNovelIds.add(updated.id);
    return updated;
  }

  async function deleteNovel(novelId: string) {
    await api.novels.remove(novelId);
    novels.value = novels.value.filter((item) => item.id !== novelId);
    fullNovelIds.delete(novelId);
  }

  function replaceNovelInList(updated: Novel) {
    const index = novels.value.findIndex((item) => item.id === updated.id);
    if (index >= 0) {
      novels.value[index] = updated;
      novels.value = [...novels.value];
    } else {
      novels.value = [updated, ...novels.value];
    }
    fullNovelIds.add(updated.id);
  }

  const items = computed(() => novels.value);

  return {
    novels: items,
    loading,
    listNovels,
    importNovelFromEpub,
    importNovelFromUrl,
    previewNovelFromUrl,
    getNovel,
    createNovel,
    updateNovel,
    deleteNovel,
    replaceNovelInList,
  };
}
