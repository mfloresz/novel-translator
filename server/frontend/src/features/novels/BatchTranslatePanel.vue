<template>
  <Card>
    <template #title>
      <div class="row-between">
        <span>Traducción masiva</span>
        <span class="small muted" style="font-weight: 400">traduce capítulos pendientes de todas tus novelas</span>
      </div>
    </template>
    <template #content>
      <div class="stack-md">
        <div v-if="state === 'idle'" class="stack-sm">
          <p class="muted small">Verifica todas tus novelas en busca de capítulos pendientes de traducción. Selecciona las novelas que deseas traducir y se crearán trabajos de traducción automáticamente.</p>
          <div class="row-wrap">
            <Button label="Verificar todas" icon="pi pi-search" :loading="checking" @click="handleCheckAll" />
          </div>
        </div>

        <div v-if="state === 'checking'" class="stack-sm">
          <ProgressBar mode="indeterminate" />
          <span class="muted small">Verificando...</span>
        </div>

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <div v-if="state === 'results' || state === 'started'" class="stack-md">
          <div class="row-between">
            <div class="row-wrap small">
              <Button size="small" severity="secondary" text label="Todas" @click="selectAll" />
              <Button size="small" severity="secondary" text label="Ninguna" @click="selectedIds = new Set()" />
              <span v-if="selectedIds.size > 0" class="muted">{{ selectedIds.size }} seleccionadas</span>
            </div>
            <Button
              :label="`Traducir seleccionadas (${selectedIds.size})`"
              icon="pi pi-play"
              :disabled="selectedIds.size === 0 || starting"
              :loading="starting"
              @click="handleStartTranslation"
            />
          </div>

          <div v-if="results.length > 0" style="border: 1px solid var(--p-content-border-color); border-radius: 12px; overflow-x: auto">
            <table style="width: 100%; border-collapse: collapse; min-width: 600px">
              <thead>
                <tr class="small muted" style="border-bottom: 1px solid var(--p-content-border-color)">
                  <th style="padding: 0.75rem 1rem; text-align: left; width: 40px"></th>
                  <th style="padding: 0.75rem 1rem; text-align: left">Novela</th>
                  <th style="padding: 0.75rem 1rem; text-align: center; width: 100px">Pendientes</th>
                  <th style="padding: 0.75rem 1rem; text-align: center; width: 100px">Total</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in results" :key="row.novelId" style="border-bottom: 1px solid var(--p-content-border-color)">
                  <td style="padding: 0.75rem 1rem; text-align: left">
                    <Checkbox
                      v-if="row.pendingChapters > 0"
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
                      </div>
                    </div>
                  </td>
                  <td style="padding: 0.75rem 1rem; text-align: center">
                    <Tag v-if="row.pendingChapters === 0" severity="success" value="Al día" />
                    <Tag v-else severity="warn" :value="`${row.pendingChapters}`" />
                  </td>
                  <td style="padding: 0.75rem 1rem; text-align: center">
                    <span class="small muted">{{ row.totalChapters }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="small muted">
            {{ results.length }} novelas verificadas ·
            <template v-if="withPendingCount > 0">{{ withPendingCount }} con capítulos pendientes</template>
            <template v-else>todas al día</template>
          </div>

          <Message v-if="startFeedback" severity="success" :closable="false">{{ startFeedback }}</Message>

          <div class="row-wrap">
            <Button label="Volver a verificar" icon="pi pi-refresh" severity="secondary" outlined :loading="checking" @click="handleCheckAll" />
          </div>
        </div>

        <div v-if="state === 'empty'" class="stack-sm">
          <Message severity="info" :closable="false">No tienes novelas con capítulos pendientes de traducción.</Message>
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
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import Tag from "primevue/tag";
import { useAppServices } from "@/app/services";
import type { BatchTranslateNovelResult } from "@/api/types";

type PanelState = "idle" | "checking" | "results" | "started" | "empty";

const toast = useToast();
const { api } = useAppServices();

const state = ref<PanelState>("idle");
const checking = ref(false);
const starting = ref(false);
const results = ref<BatchTranslateNovelResult[]>([]);
const error = ref<string | null>(null);
const startFeedback = ref<string | null>(null);

const selectedIds = ref<Set<string>>(new Set());

const withPendingCount = computed(() => results.value.filter((r) => r.pendingChapters > 0).length);

function selectAll() {
  selectedIds.value = new Set(
    results.value.filter((r) => r.pendingChapters > 0).map((r) => r.novelId),
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
  startFeedback.value = null;
  state.value = "checking";
  try {
    const resp = await api.novels.batchTranslatePreview();
    results.value = resp.results;
    if (resp.results.length === 0) {
      state.value = "empty";
    } else {
      state.value = "results";
      selectedIds.value = new Set();
      toast.add({
        severity: "info",
        summary: "Verificación completa",
        detail: `${resp.withPending} novelas con capítulos pendientes`,
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

async function handleStartTranslation() {
  if (selectedIds.value.size === 0) return;
  starting.value = true;
  error.value = null;
  startFeedback.value = null;
  try {
    const selections = results.value
      .filter((r) => selectedIds.value.has(r.novelId))
      .map((r) => ({
        novelId: r.novelId,
      }));
    const resp = await api.novels.batchTranslate(selections);
    state.value = "started";
    startFeedback.value = `${resp.jobs.length} trabajos de traducción iniciados (${resp.totalPending} capítulos en total)`;
    toast.add({
      severity: "success",
      summary: "Traducciones iniciadas",
      detail: `${resp.totalPending} capítulos encolados`,
      life: 4000,
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    state.value = "results";
  } finally {
    starting.value = false;
  }
}
</script>
