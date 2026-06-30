<template>
  <Drawer
    v-model:visible="visible"
    position="right"
    :pt="{ root: { style: { width: 'min(420px, 96vw)' } } }"
  >
    <template #header>
      <span style="font-weight: 600; font-size: 1.1rem">Trabajos activos</span>
    </template>

    <div class="stack-md">


      <div v-if="jobs.length === 0 && !loading" class="jobs-empty">
        <i class="pi pi-check-circle" style="font-size: 2rem; color: var(--p-text-muted-color)" />
        <div>
          <h3 style="margin: 0 0 0.35rem">Sin trabajos activos</h3>
          <p class="muted small" style="margin: 0">Inicia una traducción o refinamiento desde una novela para ver el progreso aquí.</p>
        </div>
      </div>

      <Card v-for="job in jobs" :key="job.id">
        <template #content>
          <div class="stack-md">
            <div class="row-between" style="align-items: flex-start">
              <div style="min-width: 0; flex: 1">
                <Button
                  link
                  style="padding: 0; font-weight: 600; text-align: left"
                  @click="openNovel(job)"
                >
                  {{ job.novelTitle || job.novelId }}
                </Button>
                <div class="small muted" style="margin-top: 0.2rem">
                  {{ job.operation === 'download' ? 'Descarga' : job.operation === 'refine' ? 'Refinamiento' : 'Traducción' }}
                  <span v-if="job.operation !== 'download' && (job.provider || job.model)"> · </span>
                  <span v-if="job.operation !== 'download' && job.provider">{{ job.provider }}</span>
                  <span v-if="job.operation !== 'download' && job.provider && job.model">/</span>
                  <span v-if="job.operation !== 'download' && job.model">{{ job.model }}</span>
                </div>
              </div>
              <Tag :severity="jobSeverity(job.status)" :value="jobStatusLabel(job.status)" />
            </div>

            <div class="stack-sm">
              <div class="row-between small">
                <span class="muted">Progreso</span>
                <span>
                  <strong>{{ job.completedChapters }}</strong>/{{ job.totalChapters }}
                  <span v-if="job.failedChapters > 0" style="color: var(--p-red-500)"> · {{ job.failedChapters }} fallidos</span>
                </span>
              </div>
              <ProgressBar v-if="jobShowsCompletedProgress(job)" :value="jobProgress(job)" />
              <ProgressBar v-else mode="indeterminate" />
              <div v-if="jobCurrentActivityLabel(job)" class="small muted">
                {{ jobCurrentActivityLabel(job) }}
              </div>
            </div>

            <div v-if="showAutoSegmentMeta(job)" class="stack-sm jobs-segment">
              <div class="small muted">
                {{ autoSegmentLabel(job) }}
              </div>
              <div v-if="showAutoSegmentProgress(job)" class="stack-sm">
                <div class="row-between small">
                  <span class="muted">Segmentos</span>
                  <span><strong>{{ segmentCompletedLabel(job) }}</strong>/{{ job.autoSegmentCount }}</span>
                </div>
                <ProgressBar :value="segmentProgress(job)" style="height: 0.5rem" />
              </div>
            </div>

            <div class="row-between small">
              <span class="muted mono">#{{ job.id }}</span>
              <Button
                v-if="job.status === 'running' || job.status === 'pending'"
                size="small"
                severity="danger"
                outlined
                icon="pi pi-stop"
                label="Cancelar"
                :loading="cancellingId === job.id"
                @click="cancel(job)"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
  </Drawer>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Card from "primevue/card";
import Drawer from "primevue/drawer";
import ProgressBar from "primevue/progressbar";
import Tag from "primevue/tag";
import { useActiveJobs } from "@/composables/useActiveJobs";
import type { TranslationJob } from "@/domain";

const router = useRouter();
const toast = useToast();
const visible = defineModel<boolean>('visible', { required: true });
const { jobs, loading, cancelJob } = useActiveJobs({ enabled: visible });
const cancellingId = ref<string | null>(null);

function jobFinishedChapterCount(job: TranslationJob) {
  return job.completedChapters + job.failedChapters;
}

function jobHasStartedWork(job: TranslationJob) {
  return job.status === "running" && (
    jobFinishedChapterCount(job) > 0 ||
    Boolean(job.autoSegmentActive) ||
    Boolean((job.autoSegmentChapterTitle || job.autoSegmentChapterId || "").trim())
  );
}

function jobShowsCompletedProgress(job: TranslationJob) {
  return !jobHasStartedWork(job) || jobFinishedChapterCount(job) > 0;
}

function jobProgress(job: TranslationJob) {
  if (job.totalChapters <= 0) return 0;
  return Math.round((jobFinishedChapterCount(job) / job.totalChapters) * 100);
}

function jobStatusLabel(status: TranslationJob["status"]) {
  return {
    pending: "Pendiente",
    running: "En progreso",
    done: "Completado",
    cancelled: "Cancelado",
    failed: "Fallido",
  }[status] || status;
}

function jobSeverity(status: TranslationJob["status"]) {
  return {
    pending: "secondary",
    running: "info",
    done: "success",
    cancelled: "warn",
    failed: "danger",
  }[status] as "secondary" | "info" | "warn" | "success" | "danger";
}

function showAutoSegmentMeta(job: TranslationJob) {
  return job.operation !== "refine" && job.operation !== "download" && Boolean(job.autoSegmentChapterTitle || (job.autoSegmentCount ?? 0) > 1);
}

function showAutoSegmentProgress(job: TranslationJob) {
  return (job.autoSegmentCount ?? 0) > 1;
}

function segmentCompletedLabel(job: TranslationJob) {
  const completed = job.autoSegmentCompletedCount ?? 0;
  const current = job.autoSegmentCurrentIndex ?? 0;
  return Math.max(completed, current > 0 ? current - 1 : 0);
}

function segmentProgress(job: TranslationJob) {
  const total = job.autoSegmentCount ?? 0;
  if (total <= 0) return 0;
  return Math.round((segmentCompletedLabel(job) / total) * 100);
}

function autoSegmentLabel(job: TranslationJob) {
  const count = job.autoSegmentCount ?? 0;
  const current = job.autoSegmentCurrentIndex ?? 0;
  const chapter = (job.autoSegmentChapterTitle || job.autoSegmentChapterId || "").trim();
  if (count > 1 && current > 0) return `${chapter} · segmento ${current} de ${count}`;
  if (count > 1) return `${chapter} · ${count} segmentos`;
  return chapter || "";
}

function jobCurrentActivityLabel(job: TranslationJob) {
  if (job.status === "pending") return "En cola…";
  if (job.status !== "running") return "";

  const chapter = (job.autoSegmentChapterTitle || job.autoSegmentChapterId || "").trim();
  const segmentCount = job.autoSegmentCount ?? 0;
  const currentSegment = job.autoSegmentCurrentIndex ?? 0;

  if (segmentCount > 1 && chapter) {
    if (currentSegment > 0) return `Traduciendo ${chapter} · segmento ${currentSegment} de ${segmentCount}`;
    return `Preparando ${chapter} · ${segmentCount} segmentos`;
  }

  if (segmentCount > 1) {
    if (currentSegment > 0) return `Traduciendo segmento ${currentSegment} de ${segmentCount}`;
    return `Preparando ${segmentCount} segmentos`;
  }

  if (job.totalChapters === 1 && chapter) return `Traduciendo capítulo actual: ${chapter}`;
  if (job.totalChapters === 1) return "Traduciendo capítulo actual…";
  if (chapter) return `Traduciendo capítulo actual: ${chapter}`;
  return "Traduciendo capítulos…";
}

function openNovel(job: TranslationJob) {
  visible.value = false;
  void router.push(`/novels/${job.novelId}`);
}

async function cancel(job: TranslationJob) {
  cancellingId.value = job.id;
  try {
    await cancelJob(job.id);
    toast.add({ severity: "success", summary: "Trabajo cancelado", life: 2500 });
  } catch (err) {
    toast.add({
      severity: "error",
      summary: "Error al cancelar trabajo",
      detail: err instanceof Error ? err.message : String(err),
      life: 4000,
    });
  } finally {
    cancellingId.value = null;
  }
}
</script>

<style scoped>
.jobs-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.75rem;
  padding: 2rem 1rem;
  border: 1px dashed var(--p-content-border-color);
  border-radius: 12px;
}

.stack-sm {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}


</style>
