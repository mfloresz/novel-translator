import { ref, watch, type Ref } from "vue";
import type { TranslationJob } from "@/domain";
import { useAppServices } from "@/app/services";
import { emitJobChanged } from "@/utils/job-events";

export function useTranslationJobs(
  novelId: Ref<string>,
  options: { failedOnly?: boolean; autoLoad?: boolean } = {},
) {
  const { api } = useAppServices();
  const jobs = ref<TranslationJob[]>([]);
  const loading = ref(false);

  async function listJobs() {
    if (!novelId.value) {
      jobs.value = [];
      return jobs.value;
    }
    loading.value = true;
    try {
      jobs.value = await api.jobs.list(novelId.value, {
        failedOnly: options.failedOnly,
      });
      return jobs.value;
    } finally {
      loading.value = false;
    }
  }

  async function createJob(
    chapterIds: string[],
    options?: {
      operation?: "translate" | "refine";
      provider?: string;
      model?: string;
    },
  ) {
    const job = await api.jobs.create(novelId.value, chapterIds, options ?? {});
    emitJobChanged();
    return job;
  }

  async function updateJob(jobId: string, patch: Partial<TranslationJob>) {
    const updated = await api.jobs.update(jobId, patch);
    jobs.value = jobs.value.map((item) => (item.id === jobId ? updated : item));
    emitJobChanged();
    return updated;
  }

  watch(
    novelId,
    () => {
      if (options.autoLoad === false) return;
      void listJobs();
    },
    { immediate: true },
  );

  return {
    jobs,
    loading,
    listJobs,
    createJob,
    updateJob,
  };
}
