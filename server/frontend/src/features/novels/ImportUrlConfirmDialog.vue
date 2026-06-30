<template>
  <Dialog v-model:visible="visible" modal header="Confirmar importación" :style="{ width: 'min(640px, 96vw)' }" @after-hide="reset">
    <div class="stack-md">
      <div v-if="preview" class="preview-card">
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
            <strong>{{ preview.totalChapters }}</strong> capítulos disponibles
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

      <div class="row-wrap">
        <div style="flex: 1; min-width: 140px">
          <label class="small muted">Idioma origen</label>
          <Select v-model="sourceLanguage" :options="languageOptions" optionLabel="name" optionValue="code" fluid :disabled="loading" />
        </div>
        <div style="flex: 1; min-width: 140px">
          <label class="small muted">Idioma destino</label>
          <Select v-model="targetLanguage" :options="languageOptionsNoAuto" optionLabel="name" optionValue="code" fluid :disabled="loading" />
        </div>
      </div>

      <div class="stack-sm">
        <div class="radio-option" :class="{ active: mode === 'all' }" @click="mode = 'all'">
          <RadioButton v-model="mode" inputId="all" value="all" />
          <label for="all">Descargar todos los {{ preview?.totalChapters ?? 0 }} capítulos</label>
        </div>
        <div class="radio-option" :class="{ active: mode === 'range' }" @click="mode = 'range'">
          <RadioButton v-model="mode" inputId="range" value="range" />
          <label for="range">Descargar un rango específico</label>
        </div>
      </div>

      <div v-if="mode === 'range'" class="row-wrap">
        <div style="flex: 1; min-width: 120px">
          <FieldNumber
            v-model="startChapter"
            label="Capítulo inicial"
            :min="1"
            :max="preview?.totalChapters ?? 1"
            :disabled="loading"
          />
        </div>
        <div style="flex: 1; min-width: 120px">
          <FieldNumber
            v-model="endChapter"
            label="Capítulo final"
            :min="startChapter"
            :max="preview?.totalChapters ?? 1"
            :disabled="loading"
          />
        </div>
      </div>

      <Message v-if="error" severity="error">{{ error }}</Message>
    </div>
    <template #footer>
      <Button severity="secondary" outlined label="Atrás" :disabled="loading" @click="handleBack" />
      <Button
        :label="loading ? 'Importando...' : 'Importar'"
        icon="pi pi-download"
        :loading="loading"
        :disabled="!targetLanguage || (mode === 'range' && (!startChapter || !endChapter || startChapter > endChapter))"
        @click="handleImport"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import FieldNumber from "@/components/FieldNumber.vue";
import Message from "primevue/message";
import RadioButton from "primevue/radiobutton";
import Select from "primevue/select";
import { LANGUAGES } from "@/config/languages";
import { useNovels } from "@/composables/useNovels";
import type { PreviewUrlResult } from "@/api/types";

const props = defineProps<{
  open: boolean;
  preview: PreviewUrlResult | null;
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  "imported": [];
  "back": [];
}>();

const router = useRouter();
const toast = useToast();
const { importNovelFromUrl } = useNovels();

const visible = computed({
  get: () => props.open,
  set: (value) => emit("update:open", value),
});

const languageOptions = LANGUAGES;
const languageOptionsNoAuto = LANGUAGES.filter((item) => item.code !== "auto");

const mode = ref<"all" | "range">("all");
const sourceLanguage = ref("en");
const targetLanguage = ref("es");
const startChapter = ref(1);
const endChapter = ref(1);
const loading = ref(false);
const error = ref<string | null>(null);

function reset() {
  mode.value = "all";
  sourceLanguage.value = "en";
  targetLanguage.value = "es";
  startChapter.value = 1;
  endChapter.value = 1;
  loading.value = false;
  error.value = null;
}

watch(visible, (open) => {
  if (open) {
    reset();
  }
});

watch(
  () => props.preview,
  (preview) => {
    if (preview) {
      endChapter.value = preview.totalChapters;
    }
  },
);

function handleBack() {
  visible.value = false;
  emit("back");
}

async function handleImport() {
  if (!props.preview || !targetLanguage.value) return;
  loading.value = true;
  error.value = null;
  try {
    const input: {
      url: string;
      sourceLanguage?: string;
      targetLanguage?: string;
      startChapter?: number;
      endChapter?: number;
    } = {
      url: props.preview.sourceURL,
      sourceLanguage: sourceLanguage.value,
      targetLanguage: targetLanguage.value,
    };
    if (mode.value === "range") {
      input.startChapter = startChapter.value;
      input.endChapter = endChapter.value;
    }
    const result = await importNovelFromUrl(input);
    toast.add({
      severity: "success",
      summary: "Novela creada",
      detail: result.downloadJob
        ? `Novela importada. Descargando ${result.downloadJob.totalChapters} capítulos restantes en segundo plano...`
        : `${result.chaptersImported} capítulos importados.`,
      life: 4000,
    });
    emit("imported");
    visible.value = false;
    await router.push(`/novels/${result.novel.id}`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
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
  max-height: 140px;
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
