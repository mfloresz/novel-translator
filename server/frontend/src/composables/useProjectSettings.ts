import { computed, ref, watch, type Ref } from "vue";
import type { GeneralPromptRecord } from "@/api/types";
import type { Novel } from "@/domain";
import { useAppServices } from "@/app/services";
import { normalizeTranslationOptions } from "@/domain/project-settings";
import { buildProjectSettings } from "@/utils/project-settings";

export function useProjectSettings(novel: Ref<Novel | null | undefined>) {
  const { api, defaults } = useAppServices();
  const globalPrompts = ref<GeneralPromptRecord[]>([]);
  const loading = ref(false);

  async function refresh() {
    loading.value = true;
    try {
      globalPrompts.value = await api.prompts.list();
    } finally {
      loading.value = false;
    }
  }

  watch(
    () => novel.value?.id,
    () => {
      void refresh();
    },
    { immediate: true },
  );

  const settings = computed(() => {
    if (!novel.value) {
      return {
        notes: "",
        glossary: [],
        prompts: {},
        ai: { provider: "", model: "" },
        translation: normalizeTranslationOptions(defaults.value?.translation),
        cleanupRules: [],
      };
    }

    return buildProjectSettings(novel.value, globalPrompts.value, defaults.value?.translation);
  });

  return {
    settings,
    globalPrompts,
    loading,
    refresh,
  };
}
