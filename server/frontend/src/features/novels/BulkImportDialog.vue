<template>
  <Dialog :visible="open" modal header="Importar capítulos" :style="{ width: 'min(900px, 96vw)' }" @update:visible="handleVisibleChange">
    <div class="stack-md">
      <p class="muted small">
        Importa varios archivos EPUB, TXT o Markdown y previsualiza antes de añadirlos a la novela.
      </p>

      <div v-if="!preview" class="stack-md">
        <input type="file" multiple accept=".epub,.txt,.md" @change="handleFileChange" />
        <Message v-if="loading" severity="info">Analizando archivos…</Message>
        <Message v-if="error" severity="error">{{ error }}</Message>
      </div>

      <div v-else class="stack-md">
        <Card>
          <template #title>Resumen</template>
          <template #content>
            <div class="stack-md small">
              <div v-if="preview.title"><strong>Título detectado:</strong> {{ preview.title }}</div>
              <div v-if="preview.author"><strong>Autor detectado:</strong> {{ preview.author }}</div>
              <div><strong>Capítulos encontrados:</strong> {{ preview.chapters.length }}</div>
            </div>
          </template>
        </Card>

        <div class="row-wrap" style="align-items: end">
          <div style="min-width: 180px; flex: 1">
            <label class="small muted">Número inicial</label>
            <InputNumber v-model="startOrder" :min="1" fluid />
          </div>
          <div style="display: flex; align-items: center; gap: 0.75rem; flex: 2">
            <ToggleSwitch v-model="asRefined" input-id="as-refined" />
            <label for="as-refined" class="small muted">
              Crear capítulos ya en estado <code>refined</code> y omitir traducción.
            </label>
          </div>
        </div>

        <div class="row-between">
          <h4 style="margin: 0">Capítulos a importar</h4>
          <div class="row-wrap">
            <Button size="small" severity="secondary" outlined label="Todos" @click="toggleAll(true)" />
            <Button size="small" severity="secondary" outlined label="Ninguno" @click="toggleAll(false)" />
          </div>
        </div>

        <div style="border: 1px solid var(--p-content-border-color); border-radius: 12px; max-height: 320px; overflow: auto">
          <div
            v-for="(chapter, index) in preview.chapters"
            :key="`${chapter.title}-${index}`"
            style="display: flex; gap: 0.75rem; padding: 0.875rem 1rem; border-bottom: 1px solid var(--p-content-border-color)"
          >
            <Checkbox :model-value="chapter.selected" binary @update:model-value="toggleChapter(index, $event)" />
            <div style="min-width: 0; flex: 1">
              <div style="font-weight: 600">{{ chapter.title }}</div>
              <div class="small muted" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden">
                {{ chapter.content.slice(0, 240) }}
              </div>
            </div>
          </div>
        </div>

        <Message v-if="asRefined" severity="warn">
          Los capítulos se crearán con <code>status: refined</code>.
        </Message>

        <Message v-if="error" severity="error">{{ error }}</Message>
      </div>
    </div>

    <template #footer>
      <Button severity="secondary" outlined label="Cancelar" :disabled="importing" @click="close" />
      <Button
        v-if="preview"
        :label="`Importar ${selectedCount} capítulos`"
        :loading="importing"
        :disabled="selectedCount === 0"
        @click="performImport"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import Dialog from "primevue/dialog";
import Card from "primevue/card";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Message from "primevue/message";
import InputNumber from "primevue/inputnumber";
import ToggleSwitch from "primevue/toggleswitch";
import type { ChapterUpsertInput } from "@/domain";
import type { EpubPreviewResult } from "@/api/types";
import { readTxtChapters } from "@/utils/epub-importer";

const props = defineProps<{
  open: boolean;
  nextOrder: number;
  onImport: (chapters: ChapterUpsertInput[]) => Promise<void>;
  onEpubFilesImported?: (files: File[]) => Promise<void>;
  previewEpub: (input: { file: Blob; fileName: string }) => Promise<EpubPreviewResult>;
}>();

const emit = defineEmits<{ (e: "update:open", value: boolean): void }>();

type PreviewState = {
  title: string;
  author: string;
  description: string;
  epubFiles: File[];
  chapters: Array<{ title: string; content: string; order: number; selected: boolean }>;
};

const preview = ref<PreviewState | null>(null);
const loading = ref(false);
const importing = ref(false);
const error = ref<string | null>(null);
const asRefined = ref(false);
const startOrder = ref(props.nextOrder);

const selectedCount = computed(() => preview.value?.chapters.filter((chapter) => chapter.selected).length ?? 0);

function reset() {
  preview.value = null;
  loading.value = false;
  importing.value = false;
  error.value = null;
  asRefined.value = false;
  startOrder.value = props.nextOrder;
}

function close() {
  reset();
  emit("update:open", false);
}

function handleVisibleChange(value: boolean) {
  if (!value) close();
}

async function handleFileChange(event: Event) {
  const files = (event.target as HTMLInputElement).files;
  if (!files || files.length === 0) return;

  error.value = null;
  loading.value = true;
  try {
    const aggregated: PreviewState = {
      title: "",
      author: "",
      description: "",
      epubFiles: [],
      chapters: [],
    };

    let counter = 0;
    for (const file of Array.from(files)) {
      const ext = file.name.toLowerCase().split(".").pop();
      if (ext === "epub") {
        aggregated.epubFiles.push(file);
        const book = await props.previewEpub({ file, fileName: file.name });
        aggregated.title = aggregated.title || book.title;
        aggregated.author = aggregated.author || book.author;
        aggregated.description = aggregated.description || book.description;
        for (const chapter of book.chapters) {
          counter++;
          aggregated.chapters.push({
            title: chapter.title,
            content: chapter.content,
            order: counter,
            selected: true,
          });
        }
      } else if (ext === "txt" || ext === "md") {
        const chapters = await readTxtChapters(file);
        for (const chapter of chapters) {
          counter++;
          aggregated.chapters.push({
            title: chapter.title,
            content: chapter.content,
            order: Number.isFinite(chapter.order) ? chapter.order : counter,
            selected: true,
          });
        }
      }
    }

    aggregated.chapters.sort((a, b) => a.order - b.order);
    if (aggregated.chapters.length === 0) {
      throw new Error("No se encontraron capítulos para importar.");
    }

    preview.value = aggregated;
    startOrder.value = props.nextOrder;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function toggleAll(selected: boolean) {
  if (!preview.value) return;
  preview.value = {
    ...preview.value,
    chapters: preview.value.chapters.map((chapter) => ({ ...chapter, selected })),
  };
}

function toggleChapter(index: number, value: boolean) {
  if (!preview.value) return;
  preview.value = {
    ...preview.value,
    chapters: preview.value.chapters.map((chapter, current) =>
      current === index ? { ...chapter, selected: value } : chapter,
    ),
  };
}

async function performImport() {
  if (!preview.value) return;

  const selected = preview.value.chapters.filter((chapter) => chapter.selected);
  if (selected.length === 0) return;

  importing.value = true;
  error.value = null;
  try {
    const inputs: ChapterUpsertInput[] = selected
      .sort((a, b) => a.order - b.order)
      .map((chapter, index) => ({
        chapterOrder: startOrder.value + index,
        title: chapter.title,
        originalContent: asRefined.value ? undefined : chapter.content,
        refinedContent: asRefined.value ? chapter.content : undefined,
        status: asRefined.value ? "refined" : "pending",
      }));

    await props.onImport(inputs);
    if (preview.value.epubFiles.length > 0 && props.onEpubFilesImported) {
      await props.onEpubFilesImported(preview.value.epubFiles);
    }
    close();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    importing.value = false;
  }
}
</script>
