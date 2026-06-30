<template>
  <AppLayout>
    <div v-if="!chapter" class="stack-md">
      <Button label="Volver" icon="pi pi-arrow-left" severity="secondary" text @click="router.push(`/novels/${novelId}`)" />
      <ProgressSpinner v-if="chaptersLoading || novelLoading" style="width: 48px; height: 48px" strokeWidth="4" />
      <Message v-else severity="warn">Capítulo no encontrado.</Message>
    </div>

    <div v-else class="stack-lg">
      <Button label="Volver a capítulos" icon="pi pi-arrow-left" severity="secondary" text @click="router.push(`/novels/${novelId}`)" />

      <div class="row-between">
        <div style="min-width: 0">
          <h1 style="margin: 0 0 0.25rem">{{ translatedTitle || title }}</h1>
          <div v-if="translatedTitle" class="small muted">{{ title }}</div>
          <div class="row-wrap" style="margin-top: 0.75rem">
            <Tag severity="secondary" :value="`#${chapter.chapterOrder}`" />
            <Tag :severity="chapterSeverity(displayStatus)" :value="chapterStatusLabel(displayStatus)" />
          </div>
        </div>
        <div class="row-wrap">
          <Button
            label="Traducir"
            icon="pi pi-sparkles"
            :loading="translateLoading"
            :disabled="!originalContent || chapterIsProcessing || translateLoading || refineLoading"
            @click="handleTranslate"
          />
          <Button
            label="Refinar"
            icon="pi pi-wand"
            severity="secondary"
            outlined
            :loading="refineLoading"
            :disabled="!translatedContent || chapterIsProcessing || translateLoading || refineLoading"
            @click="handleRefine"
          />
          <Button
            v-if="chapter.status === 'refined' || chapter.status === 'done'"
            label="Marcar completado"
            icon="pi pi-check"
            severity="success"
            outlined
            @click="handleMarkDone"
          />
          <Button label="Guardar" icon="pi pi-save" :loading="saving" @click="handleSave" />
        </div>
      </div>

      <Message v-if="error" severity="error">{{ error }}</Message>

      <Card>
        <template #content>
          <div class="stack-md">
            <div class="row-wrap">
              <div style="flex: 1; min-width: 240px">
                <label class="small muted">Título original</label>
                <InputText v-model="title" fluid />
              </div>
              <div style="flex: 1; min-width: 240px">
                <label class="small muted">Título traducido</label>
                <InputText v-model="translatedTitle" fluid />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <div class="stack-lg">
        <Card v-for="panel in panels" :key="panel.id">
          <template #title>{{ panel.label }}</template>
          <template #content>
            <div class="stack-md">
              <div class="row-between">
                <div class="small muted">{{ panel.languageLabel }} · {{ panel.value.length }} chars</div>
                <div class="row-wrap">
                  <SelectButton :model-value="contentViewMode[panel.id]" :options="viewModeOptions" optionLabel="label" optionValue="value" :allowEmpty="false" @update:model-value="setPanelMode(panel.id, $event)" />
                </div>
              </div>

              <template v-if="contentViewMode[panel.id] === 'plain'">
                <Textarea :model-value="panel.value" rows="14" fluid class="mono" @update:model-value="panel.onChange($event)" />
              </template>
              <template v-else>
                <div class="markdown-preview" style="border: 1px solid var(--p-content-border-color); border-radius: 12px; padding: 1rem; min-height: 220px" v-html="markdownToHtml(panel.value || panel.placeholder)" />
              </template>
            </div>
          </template>
        </Card>
      </div>

    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppLayout from "@/components/AppLayout.vue";
import Button from "primevue/button";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { useNovels } from "@/composables/useNovels";
import { useActiveJobStatus } from "@/composables/useActiveJobStatus";
import { useAppServices } from "@/app/services";
import { type Chapter, type Novel } from "@/domain";
import { emitJobChanged } from "@/utils/job-events";
import { markdownToHtml } from "@/utils/markdown";

const route = useRoute();
const router = useRouter();
const { api } = useAppServices();
const novelId = computed(() => String(route.params.novelId || ""));
const chapterId = computed(() => String(route.params.chapterId || ""));
const { getNovel } = useNovels();
const { hasActive } = useActiveJobStatus();
const novel = ref<Novel | null>(null);
const novelLoading = ref(false);
const chapter = ref<Chapter | null>(null);
const chaptersLoading = ref(false);

const title = ref("");
const translatedTitle = ref("");
const originalContent = ref("");
const translatedContent = ref("");
const refinedContent = ref("");
const saving = ref(false);
const translateLoading = ref(false);
const refineLoading = ref(false);
const error = ref<string | null>(null);
const toast = useToast();
const contentViewMode = reactive<Record<"original" | "translated" | "refined", "plain" | "markdown">>({
  original: "plain",
  translated: "plain",
  refined: "plain",
});

const chapterIsProcessing = computed(() => chapter.value?.status === "processing");
const displayStatus = computed<Chapter["status"]>(() => {
  if (chapterIsProcessing.value) return "processing";
  return chapter.value?.status ?? "pending";
});
const panels = computed(() => [
  {
    id: "original" as const,
    label: "Contenido original",
    languageLabel: novel.value?.sourceLanguage || "origen",
    value: originalContent.value,
    placeholder: "Sin contenido original",
    onChange: (value: string) => { originalContent.value = value; },
  },
  {
    id: "translated" as const,
    label: "Contenido traducido",
    languageLabel: novel.value?.targetLanguage || "destino",
    value: translatedContent.value,
    placeholder: "Sin contenido traducido",
    onChange: (value: string) => { translatedContent.value = value; },
  },
  {
    id: "refined" as const,
    label: "Contenido refinado",
    languageLabel: novel.value?.targetLanguage || "destino",
    value: refinedContent.value,
    placeholder: "Sin contenido refinado",
    onChange: (value: string) => { refinedContent.value = value; },
  },
]);
const viewModeOptions = [
  { label: "Texto plano", value: "plain" },
  { label: "Markdown", value: "markdown" },
];

async function loadNovel() {
  if (!novelId.value) {
    novel.value = null;
    return null;
  }
  novelLoading.value = true;
  try {
    novel.value = await getNovel(novelId.value, false);
    return novel.value;
  } finally {
    novelLoading.value = false;
  }
}

function syncChapterFields(next: Chapter, options: { replaceOriginalFields?: boolean } = {}) {
  const { replaceOriginalFields = true } = options;
  chapter.value = next;
  if (replaceOriginalFields) {
    title.value = next.title;
    originalContent.value = next.originalContent || "";
  }
  translatedTitle.value = next.translatedTitle || "";
  translatedContent.value = next.translatedContent || "";
  refinedContent.value = next.refinedContent || "";
}

function markChapterProcessing() {
  if (!chapter.value) return;
  syncChapterFields({
    ...chapter.value,
    status: "processing",
    errorMessage: "",
  }, { replaceOriginalFields: false });
}

async function loadChapter(options: { replaceOriginalFields?: boolean } = {}) {
  if (!novelId.value || !chapterId.value) {
    chapter.value = null;
    return null;
  }
  chaptersLoading.value = true;
  try {
    const next = await api.chapters.get(novelId.value, chapterId.value);
    if (!next) {
      chapter.value = null;
      return null;
    }
    syncChapterFields(next, options);
    return chapter.value;
  } finally {
    chaptersLoading.value = false;
  }
}

watch([novelId, chapterId], () => {
  translateLoading.value = false;
  refineLoading.value = false;
  error.value = null;
  void loadNovel();
  void loadChapter();
}, { immediate: true });

watch(hasActive, (active, previous) => {
  if (!previous || active || chapter.value?.status !== "processing") return;
  void loadChapter({ replaceOriginalFields: false });
});

function chapterStatusLabel(status: Chapter["status"]) {
  return {
    pending: "Pendiente",
    processing: "Procesando",
    translated: "Traducido",
    refined: "Refinado",
    done: "Completado",
    failed: "Error",
  }[status] || status;
}

function chapterSeverity(status: Chapter["status"]) {
  return {
    pending: "secondary",
    processing: "info",
    translated: "warn",
    refined: "help",
    done: "success",
    failed: "danger",
  }[status] as "secondary" | "info" | "warn" | "help" | "success" | "danger";
}

async function handleSave() {
  if (!chapter.value) return;
  saving.value = true;
  try {
    const updated = await api.chapters.upsert(novelId.value, {
      id: chapter.value.id,
      chapterOrder: chapter.value.chapterOrder,
      title: title.value,
      translatedTitle: translatedTitle.value || undefined,
      originalContent: originalContent.value || undefined,
      translatedContent: translatedContent.value || undefined,
      refinedContent: refinedContent.value || undefined,
    });
    syncChapterFields(updated);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    saving.value = false;
  }
}

async function handleTranslate() {
  if (!novel.value || !chapter.value || !originalContent.value) return;
  translateLoading.value = true;
  error.value = null;
  try {
    await api.jobs.create(novelId.value, [chapter.value.id], {
      operation: "translate",
      provider: novel.value.aiOptions.provider || undefined,
      model: novel.value.aiOptions.model || undefined,
    });
    markChapterProcessing();
    emitJobChanged();
  } catch (err) {
    toast.add({ severity: "error", summary: "Falló la traducción", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  } finally {
    translateLoading.value = false;
  }
}

async function handleRefine() {
  if (!novel.value || !chapter.value || !translatedContent.value) return;
  refineLoading.value = true;
  error.value = null;
  try {
    await api.jobs.create(novelId.value, [chapter.value.id], {
      operation: "refine",
      provider: novel.value.aiOptions.provider || undefined,
      model: novel.value.aiOptions.model || undefined,
    });
    markChapterProcessing();
    emitJobChanged();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    refineLoading.value = false;
  }
}

async function handleMarkDone() {
  if (!chapter.value) return;
  try {
    const updated = await api.chapters.upsert(novelId.value, {
      id: chapter.value.id,
      chapterOrder: chapter.value.chapterOrder,
      title: chapter.value.title,
      status: "done",
    });
    syncChapterFields(updated);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

function setPanelMode(id: "original" | "translated" | "refined", mode: "plain" | "markdown") {
  contentViewMode[id] = mode;
}
</script>
