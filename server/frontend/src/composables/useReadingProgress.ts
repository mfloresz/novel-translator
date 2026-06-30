import { ref, onScopeDispose, type Ref } from "vue";
import { useAppServices } from "@/app/services";

export function useReadingProgress(
  novelId: Ref<string>,
  activeChapterId: Ref<string | null>,
  scrollPercent: Ref<number>,
) {
  const { api } = useAppServices();

  const savedChapterId = ref<string | null>(null);
  const savedScrollPercent = ref(0);
  const isLoaded = ref(false);
  let saveTimer: ReturnType<typeof setInterval> | null = null;

  async function load() {
    if (!novelId.value) {
      isLoaded.value = true;
      return;
    }
    try {
      const result = await api.readingProgress.get(novelId.value);
      if (result && result.chapterId) {
        savedChapterId.value = result.chapterId;
        savedScrollPercent.value = result.scrollPercent ?? 0;
      } else {
        savedChapterId.value = null;
        savedScrollPercent.value = 0;
      }
    } catch {
      savedChapterId.value = null;
      savedScrollPercent.value = 0;
    }
    isLoaded.value = true;
  }

  async function flush() {
    if (!novelId.value || !activeChapterId.value) return;
    try {
      await api.readingProgress.update(novelId.value, {
        chapterId: activeChapterId.value,
        scrollPercent: scrollPercent.value,
      });
    } catch {
      // fallo silencioso
    }
  }

  function startAutoSave() {
    stopAutoSave();
    saveTimer = setInterval(() => {
      void flush();
    }, 30_000);
  }

  function stopAutoSave() {
    if (saveTimer !== null) {
      clearInterval(saveTimer);
      saveTimer = null;
    }
  }

  onScopeDispose(() => {
    stopAutoSave();
    void flush();
  });

  return {
    savedChapterId,
    savedScrollPercent,
    isLoaded,
    load,
    flush,
    startAutoSave,
    stopAutoSave,
  };
}
