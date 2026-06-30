import { computed, onScopeDispose, ref, unref, watch, type Ref } from "vue";
import type { TranslationJob } from "@/domain";
import { useAppServices } from "@/app/services";
import { emitJobChanged, onJobChanged } from "@/utils/job-events";

export function useActiveJobs(
  options: { enabled?: boolean | Ref<boolean> } = {},
) {
  const { api } = useAppServices();
  const jobs = ref<TranslationJob[]>([]);
  const loading = ref(false);
  const activeCount = computed(() => jobs.value.length);
  const isEnabled = computed(() => unref(options.enabled) ?? true);

  let intervalId: number | null = null;
  let inflight = false;

  function stopPolling() {
    if (intervalId !== null) {
      window.clearInterval(intervalId);
      intervalId = null;
    }
  }

  function startPolling() {
    stopPolling();
    intervalId = window.setInterval(() => {
      void refresh();
    }, 2000);
  }

  function syncPolling() {
    if (!isEnabled.value) {
      stopPolling();
      return;
    }
    const hasActive = jobs.value.some(
      (job) => job.status === "pending" || job.status === "running",
    );
    if (hasActive) {
      if (intervalId === null) startPolling();
      return;
    }
    stopPolling();
  }

  async function refresh() {
    if (!isEnabled.value || inflight) return;
    inflight = true;
    loading.value = true;
    try {
      jobs.value = await api.jobs.listActive();
    } catch {
      // ignore network errors while polling
    } finally {
      loading.value = false;
      inflight = false;
      syncPolling();
    }
  }

  const unsubscribeJobChanged = onJobChanged(() => {
    if (!isEnabled.value) return;
    void refresh();
  });

  watch(
    isEnabled,
    (enabled) => {
      if (enabled) {
        void refresh();
        return;
      }
      stopPolling();
      loading.value = false;
      jobs.value = [];
    },
    { immediate: true },
  );

  onScopeDispose(() => {
    stopPolling();
    unsubscribeJobChanged();
  });

  async function listActiveJobs() {
    if (!isEnabled.value) {
      jobs.value = [];
      return jobs.value;
    }
    await refresh();
    return jobs.value;
  }

  async function cancelJob(jobId: string) {
    const updated = await api.jobs.update(jobId, { status: "cancelled" });
    jobs.value = jobs.value.filter((item) => item.id !== jobId);
    syncPolling();
    emitJobChanged();
    return updated;
  }

  return {
    jobs,
    loading,
    activeCount,
    listActiveJobs,
    cancelJob,
  };
}
