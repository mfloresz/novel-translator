<template>
  <Dialog v-model:visible="visible" modal header="Actualizar desde internet" :style="{ width: 'min(640px, 96vw)' }" @after-hide="reset">
    <div class="stack-md">
      <div v-if="loading" class="preview-loading">
        <ProgressSpinner style="width: 2.5rem; height: 2.5rem" stroke-width="4" />
        <span class="muted small">Buscando capítulos nuevos en la fuente…</span>
      </div>

      <div v-else-if="preview" class="preview-card">
        <div class="preview-cover">
          <img v-if="preview.coverURL" :src="preview.coverURL" :alt="preview.title" referrerpolicy="no-referrer" />
          <div v-else class="cover-placeholder">
            <i class="pi pi-image" />
          </div>
        </div>
        <div class="preview-info">
          <h3 style="margin: 0">{{ preview.title || "Sin título" }}</h3>
          <div v-if="preview.author" class="muted small">
            <i class="pi pi-user" style="margin-right: 0.25rem" />
            {{ preview.author }}
          </div>
          <div class="muted small">
            <i class="pi pi-list" style="margin-right: 0.25rem" />
            <strong>{{ preview.currentChapters }}</strong> capítulos locales · <strong>{{ preview.totalChapters }}</strong> disponibles en la fuente
          </div>
          <div v-if="preview.sourceURL" class="muted small" style="word-break: break-all">
            <i class="pi pi-link" style="margin-right: 0.25rem" />
            {{ preview.sourceURL }}
          </div>
        </div>
      </div>

      <div v-if="preview?.description">
        <label class="small muted">Descripción</label>
        <div class="description-box small">{{ preview.description }}</div>
      </div>

      <Message v-if="!loading && preview && preview.newChapters === 0" severity="success" :closable="false">
        La novela ya está al día. No hay capítulos nuevos para descargar.
      </Message>

      <div v-else-if="!loading && preview" class="stack-sm">
        <Message severity="info" :closable="false">
          Hay <strong>{{ preview.newChapters }}</strong> capítulos nuevos disponibles (del {{ preview.firstNewChapter }} al {{ preview.lastNewChapter }}).
        </Message>

        <div class="radio-option" :class="{ active: mode === 'all' }" @click="mode = 'all'">
          <RadioButton v-model="mode" inputId="all" value="all" />
          <label for="all">Descargar los {{ preview.newChapters }} capítulos nuevos</label>
        </div>
        <div class="radio-option" :class="{ active: mode === 'range' }" @click="mode = 'range'">
          <RadioButton v-model="mode" inputId="range" value="range" />
          <label for="range">Descargar un rango específico</label>
        </div>
      </div>

      <div v-if="mode === 'range' && preview" class="row-wrap">
        <div style="flex: 1; min-width: 120px">
          <FieldNumber
            v-model="startChapter"
            label="Capítulo inicial"
            :min="preview.firstNewChapter"
            :max="preview.lastNewChapter"
            :disabled="loading"
          />
        </div>
        <div style="flex: 1; min-width: 120px">
          <FieldNumber
            v-model="endChapter"
            label="Capítulo final"
            :min="startChapter"
            :max="preview.lastNewChapter"
            :disabled="loading"
          />
        </div>
      </div>

      <Message v-if="error" severity="error">{{ error }}</Message>
      <Message v-if="success" severity="success">{{ success }}</Message>
    </div>
    <template #footer>
      <Button severity="secondary" outlined label="Cancelar" :disabled="loading" @click="visible = false" />
      <Button
        :label="loading ? 'Descargando...' : 'Actualizar'"
        icon="pi pi-refresh"
        :loading="updating"
        :disabled="!canUpdate"
        @click="handleUpdate"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import FieldNumber from "@/components/FieldNumber.vue";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import RadioButton from "primevue/radiobutton";
import { useAppServices } from "@/app/services";
import type { UpdateUrlPreviewResult } from "@/api/types";

const props = defineProps<{ open: boolean; novelId: string }>();
const emit = defineEmits<{ "update:open": [value: boolean]; updated: [pending?: number] }>();

const { api } = useAppServices();
const toast = useToast();

const visible = computed({
  get: () => props.open,
  set: (value) => emit("update:open", value),
});

const mode = ref<"all" | "range">("all");
const startChapter = ref(1);
const endChapter = ref(1);
const loading = ref(false);
const updating = ref(false);
const error = ref<string | null>(null);
const success = ref<string | null>(null);
const preview = ref<UpdateUrlPreviewResult | null>(null);

const canUpdate = computed(() => {
  if (loading.value || updating.value) return false;
  if (!preview.value) return false;
  if (preview.value.newChapters === 0) return false;
  if (mode.value === "range") {
    return Boolean(startChapter.value && endChapter.value && startChapter.value <= endChapter.value);
  }
  return true;
});

function reset() {
  mode.value = "all";
  startChapter.value = 1;
  endChapter.value = 1;
  loading.value = false;
  updating.value = false;
  error.value = null;
  success.value = null;
  preview.value = null;
}

watch(visible, (open) => {
  if (open) {
    reset();
    void fetchPreview();
  }
});

async function fetchPreview() {
  loading.value = true;
  error.value = null;
  try {
    const result = await api.novels.updatePreviewFromUrl(props.novelId);
    preview.value = result;
    if (result.newChapters > 0) {
      startChapter.value = result.firstNewChapter;
      endChapter.value = result.lastNewChapter;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    preview.value = null;
  } finally {
    loading.value = false;
  }
}

async function handleUpdate() {
  if (!preview.value || preview.value.newChapters === 0) return;
  updating.value = true;
  error.value = null;
  success.value = null;
  try {
    const input: { startChapter?: number; endChapter?: number } = {};
    if (mode.value === "range") {
      input.startChapter = startChapter.value;
      input.endChapter = endChapter.value;
    }
    const result = await api.novels.updateFromUrl(props.novelId, input);
    const pending = (result as any).pendingChapters ?? result.chaptersAdded;
    if (pending > 0) {
      toast.add({
        severity: "success",
        summary: "Descarga iniciada",
        detail: `${pending} capítulos nuevos se están descargando en segundo plano.`,
        life: 4000,
      });
    } else {
      success.value = `${result.chaptersAdded} capítulos nuevos descargados.`;
    }
    emit("updated", pending);
    visible.value = false;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    updating.value = false;
  }
}
</script>

<style scoped>
.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 0;
}

.preview-card {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
}
.preview-cover {
  flex-shrink: 0;
  width: 90px;
}
.preview-cover img {
  width: 90px;
  height: 130px;
  object-fit: cover;
  border-radius: 6px;
  background: #f3f4f6;
}
.cover-placeholder {
  width: 90px;
  height: 130px;
  border-radius: 6px;
  background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 1.5rem;
}
.preview-info {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
  flex: 1;
}
.description-box {
  max-height: 120px;
  overflow: auto;
  padding: 0.6rem 0.75rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 6px;
  color: var(--p-text-muted-color);
  white-space: pre-wrap;
  line-height: 1.4;
}
.radio-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.radio-option.active {
  border-color: var(--p-primary-color);
}
.radio-option label {
  cursor: pointer;
  flex: 1;
}
</style>
