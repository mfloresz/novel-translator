<template>
  <Card>
    <template #title>
      <div class="row-between">
        <span>Actualización masiva desde internet</span>
        <span class="small muted" style="font-weight: 400">con delay para evitar rate limits</span>
      </div>
    </template>
    <template #content>
      <div class="stack-md">
        <div v-if="state === 'idle'" class="stack-sm">
          <p class="muted small">Verifica todas tus novelas con URL en busca de nuevos capítulos. El proceso es secuencial con delays aleatorios para evitar bloqueos de los sitios fuente.</p>
          <div class="row-wrap">
            <Button label="Verificar todas" icon="pi pi-search" :loading="checking" @click="handleCheckAll" />
          </div>
        </div>

        <div v-if="state === 'checking'" class="stack-sm">
          <ProgressBar mode="indeterminate" />
          <span class="muted small">Verificando...</span>
        </div>

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <div v-if="state === 'results' || state === 'downloaded'" class="stack-md">
          <div class="row-between">
            <div class="row-wrap small">
              <Button size="small" severity="secondary" text label="Todos" @click="selectAll" />
              <Button size="small" severity="secondary" text label="Ninguno" @click="selectedIds = new Set()" />
              <span v-if="selectedIds.size > 0" class="muted">{{ selectedIds.size }} seleccionadas</span>
            </div>
            <Button
              :label="`Descargar seleccionadas (${selectedIds.size})`"
              icon="pi pi-download"
              :disabled="selectedIds.size === 0 || downloading"
              :loading="downloading"
              @click="handleDownloadSelected"
            />
          </div>

          <div v-if="results.length > 0" style="border: 1px solid var(--p-content-border-color); border-radius: 12px; overflow-x: auto">
            <table style="width: 100%; border-collapse: collapse; min-width: 600px">
              <thead>
                <tr class="small muted" style="border-bottom: 1px solid var(--p-content-border-color)">
                  <th style="padding: 0.75rem 1rem; text-align: left; width: 40px"></th>
                  <th style="padding: 0.75rem 1rem; text-align: left">Novela</th>
                  <th style="padding: 0.75rem 1rem; text-align: center; width: 80px">Nuevos</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; min-width: 220px">Acción</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in results" :key="row.novelId" style="border-bottom: 1px solid var(--p-content-border-color)" :style="{ opacity: row.error ? 0.5 : 1 }">
                  <td style="padding: 0.75rem 1rem; text-align: left">
                    <Checkbox
                      v-if="!row.error && row.newChapters > 0"
                      :model-value="selectedIds.has(row.novelId)"
                      binary
                      @update:model-value="toggleSelect(row.novelId, $event)"
                    />
                  </td>
                  <td style="padding: 0.75rem 1rem">
                    <div class="row-wrap" style="gap: 0.5rem">
                      <img v-if="row.coverUrl" :src="row.coverUrl" alt="" style="width: 32px; height: 48px; object-fit: cover; border-radius: 4px; flex-shrink: 0" referrerpolicy="no-referrer" />
                      <div style="min-width: 0">
                        <div style="font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{{ row.sourceTitle }}</div>
                        <div v-if="row.sourceAuthor" class="small muted">{{ row.sourceAuthor }}</div>
                        <div v-if="!row.error" class="small muted">{{ row.currentChapters }} locales · {{ row.totalChapters }} fuente</div>
                      </div>
                    </div>
                  </td>
                  <td style="padding: 0.75rem 1rem; text-align: center">
                    <Tag v-if="row.error" severity="danger" value="Error" />
                    <Tag v-else-if="row.newChapters === 0" severity="success" value="Al día" />
                    <Tag v-else severity="info" :value="`+${row.newChapters}`" />
                  </td>
                  <td style="padding: 0.75rem 1rem">
                    <div v-if="row.newChapters > 0" class="stack-sm">
                      <Select
                        :model-value="getActionMode(row.novelId)"
                        :options="actionOptions"
                        optionLabel="label"
                        optionValue="value"
                        size="small"
                        fluid
                        @update:model-value="setActionMode(row.novelId, $event)"
                      />
                      <div v-if="getActionMode(row.novelId) === 'range'" class="row-wrap">
                        <InputNumber
                          :model-value="getActionStart(row.novelId)"
                          :min="row.firstNewChapter"
                          :max="getActionEnd(row.novelId) || row.lastNewChapter"
                          size="small"
                          style="width: 80px"
                          @update:model-value="setActionStart(row.novelId, $event)"
                        />
                        <span class="muted small">—</span>
                        <InputNumber
                          :model-value="getActionEnd(row.novelId)"
                          :min="getActionStart(row.novelId) || row.firstNewChapter"
                          :max="row.lastNewChapter"
                          size="small"
                          style="width: 80px"
                          @update:model-value="setActionEnd(row.novelId, $event)"
                        />
                      </div>
                    </div>
                    <span v-else-if="row.error" class="small muted">{{ row.error }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="small muted">
            {{ results.length }} novelas verificadas ·
            <template v-if="withUpdatesCount > 0">{{ withUpdatesCount }} con actualizaciones</template>
            <template v-else>ninguna con actualizaciones</template>
            <template v-if="errorsCount > 0"> · {{ errorsCount }} errores</template>
          </div>

          <Message v-if="downloadFeedback" severity="success" :closable="false">{{ downloadFeedback }}</Message>

          <div class="row-wrap">
            <Button label="Volver a verificar" icon="pi pi-refresh" severity="secondary" outlined :loading="checking" @click="handleCheckAll" />
          </div>
        </div>

        <div v-if="state === 'empty'" class="stack-sm">
          <Message severity="info" :closable="false">No tienes novelas con URL configurada. Importa novelas desde URL para usar esta función.</Message>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Card from "primevue/card";
import Checkbox from "primevue/checkbox";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import Select from "primevue/select";
import Tag from "primevue/tag";
import { useAppServices } from "@/app/services";
import type { BatchCheckNovelResult, BatchUpdateSelection } from "@/api/types";

type PanelState = "idle" | "checking" | "results" | "downloaded" | "empty";

const toast = useToast();
const { api } = useAppServices();

const state = ref<PanelState>("idle");
const checking = ref(false);
const downloading = ref(false);
const results = ref<BatchCheckNovelResult[]>([]);
const error = ref<string | null>(null);
const downloadFeedback = ref<string | null>(null);

const selectedIds = ref<Set<string>>(new Set());

const actionModes = ref<Map<string, "all" | "range">>(new Map());
const actionStarts = ref<Map<string, number>>(new Map());
const actionEnds = ref<Map<string, number>>(new Map());

const actionOptions = [
  { label: "Descargar todos", value: "all" },
  { label: "Rango específico", value: "range" },
];

const withUpdatesCount = computed(() => results.value.filter((r) => r.newChapters > 0).length);
const errorsCount = computed(() => results.value.filter((r) => r.error).length);

function getActionMode(novelId: string): "all" | "range" {
  return actionModes.value.get(novelId) ?? "all";
}

function getActionStart(novelId: string): number | undefined {
  return actionStarts.value.get(novelId);
}

function getActionEnd(novelId: string): number | undefined {
  return actionEnds.value.get(novelId);
}

function setActionMode(novelId: string, val: "all" | "range") {
  const next = new Map(actionModes.value);
  next.set(novelId, val);
  actionModes.value = next;
}

function setActionStart(novelId: string, val: number) {
  const next = new Map(actionStarts.value);
  next.set(novelId, val ?? undefined);
  actionStarts.value = next;
}

function setActionEnd(novelId: string, val: number) {
  const next = new Map(actionEnds.value);
  next.set(novelId, val ?? undefined);
  actionEnds.value = next;
}

function selectAll() {
  selectedIds.value = new Set(
    results.value.filter((r) => !r.error && r.newChapters > 0).map((r) => r.novelId),
  );
}

function toggleSelect(novelId: string, checked: boolean) {
  const next = new Set(selectedIds.value);
  if (checked) next.add(novelId);
  else next.delete(novelId);
  selectedIds.value = next;
}

async function handleCheckAll() {
  checking.value = true;
  error.value = null;
  downloadFeedback.value = null;
  state.value = "checking";
  try {
    const resp = await api.novels.checkBatchUpdates();
    results.value = resp.results;
    if (resp.results.length === 0) {
      state.value = "empty";
    } else {
      state.value = "results";
      const modes = new Map<string, "all" | "range">();
      const starts = new Map<string, number>();
      const ends = new Map<string, number>();
      for (const r of resp.results) {
        if (!r.error && r.newChapters > 0) {
          modes.set(r.novelId, "all");
          starts.set(r.novelId, r.firstNewChapter);
          ends.set(r.novelId, r.lastNewChapter);
        }
      }
      actionModes.value = modes;
      actionStarts.value = starts;
      actionEnds.value = ends;
      selectedIds.value = new Set();
      toast.add({
        severity: "info",
        summary: "Verificación completa",
        detail: `${resp.withUpdates} novelas con actualizaciones`,
        life: 3000,
      });
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    state.value = "results";
  } finally {
    checking.value = false;
  }
}

async function handleDownloadSelected() {
  if (selectedIds.value.size === 0) return;
  downloading.value = true;
  error.value = null;
  downloadFeedback.value = null;
  try {
    const selections: BatchUpdateSelection[] = results.value
      .filter((r) => selectedIds.value.has(r.novelId))
      .map((r) => {
        const mode = getActionMode(r.novelId);
        const sel: BatchUpdateSelection = {
          novelId: r.novelId,
          startOrder: r.startOrder,
          newChapterInfo: r.newChapterInfo,
        };
        if (mode === "range") {
          sel.startChapter = getActionStart(r.novelId) ?? r.firstNewChapter;
          sel.endChapter = getActionEnd(r.novelId) ?? r.lastNewChapter;
        }
        return sel;
      });
    const resp = await api.novels.batchUpdateFromUrl(selections);
    state.value = "downloaded";
    downloadFeedback.value = `${resp.jobs.length} descargas iniciadas (${resp.totalPending} capítulos en total)`;
    toast.add({
      severity: "success",
      summary: "Descargas iniciadas",
      detail: `${resp.totalPending} capítulos encolados`,
      life: 4000,
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    state.value = "results";
  } finally {
    downloading.value = false;
  }
}
</script>
