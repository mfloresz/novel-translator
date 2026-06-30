import { computed, onScopeDispose, ref } from "vue";
import type { ApiClient } from "@/api/client";
import { useAppServices } from "@/app/services";
import { onJobChanged } from "@/utils/job-events";

const hasActiveState = ref(false);
const loading = ref(false);
let intervalId: number | null = null;
let inflight = false;
let listeners = 0;
let apiClient: ApiClient | null = null;
let unsubscribeJobChanged: (() => void) | null = null;

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
  if (hasActiveState.value) {
    if (intervalId === null) startPolling();
    return;
  }
  stopPolling();
}

async function refresh() {
  if (!apiClient || inflight) return;
  inflight = true;
  loading.value = true;
  try {
    const result = await apiClient.jobs.status();
    hasActiveState.value = result.hasActive;
  } catch {
    // ignore network errors while polling
  } finally {
    loading.value = false;
    inflight = false;
    syncPolling();
  }
}

export function useActiveJobStatus() {
  const { api } = useAppServices();
  apiClient = api;

  listeners++;
  if (listeners === 1) {
    unsubscribeJobChanged = onJobChanged(() => {
      void refresh();
    });
    void refresh();
  }

  onScopeDispose(() => {
    listeners = Math.max(0, listeners - 1);
    if (listeners === 0) {
      stopPolling();
      unsubscribeJobChanged?.();
      unsubscribeJobChanged = null;
      apiClient = null;
      hasActiveState.value = false;
      loading.value = false;
    }
  });

  return {
    hasActive: computed(() => hasActiveState.value),
    loading,
    refreshStatus: refresh,
  };
}
