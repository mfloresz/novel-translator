<template>
  <AppLayout>
    <div class="stack-lg">
      <header class="page-header">
        <div>
          <h1 class="page-title">Biblioteca</h1>
          <p class="muted small">{{ novels.length }} novela{{ novels.length === 1 ? '' : 's' }}</p>
        </div>
        <div class="page-actions">
          <div class="sort-controls">
            <Select
              v-model="sortField"
              :options="sortOptions"
              optionLabel="label"
              optionValue="value"
              class="sort-select"
              @change="onSortChange"
            />
            <Button
              :icon="sortOrderIcon"
              severity="secondary"
              text
              rounded
              @click="toggleSortOrder"
            />
          </div>
          <Button
              :icon="groupBySeries ? 'pi pi-tag' : 'pi pi-tags'"
              :severity="groupBySeries ? 'primary' : 'secondary'"
              :outlined="!groupBySeries"
              text
              rounded
              class="group-toggle"
              title="Agrupar por serie"
              @click="groupBySeries = !groupBySeries"
            />
          <Button
              icon="pi pi-upload"
              label="Importar EPUB"
              severity="secondary"
              outlined
              class="page-action desktop-only"
              @click="importOpen = true"
            />
          <Button
            icon="pi pi-globe"
            label="Desde URL"
            severity="secondary"
            outlined
            class="page-action desktop-only"
            @click="importUrlOpen = true"
          />
          <Button
            icon="pi pi-plus"
            label="Nueva novela"
            class="page-action desktop-only"
            @click="createOpen = true"
          />
        </div>
      </header>

      <div v-if="loading" class="library-grid" role="status" aria-label="Cargando biblioteca">
        <LibrarySkeleton />
      </div>

      <Card v-else-if="sortedNovels.length === 0">
        <template #content>
          <div class="empty-state">
            <div class="empty-state-icon">
              <i class="pi pi-book" aria-hidden="true" />
            </div>
            <div>
              <h2 class="empty-state-title">Sin novelas</h2>
              <p class="muted empty-state-body">Crea una novela manualmente, importa un EPUB o descarga una desde internet.</p>
            </div>
            <div class="empty-state-actions">
              <Button icon="pi pi-plus" label="Nueva novela" @click="createOpen = true" />
              <Button icon="pi pi-upload" label="Importar EPUB" severity="secondary" outlined @click="importOpen = true" />
              <Button icon="pi pi-globe" label="Desde URL" severity="secondary" outlined @click="importUrlOpen = true" />
            </div>
          </div>
        </template>
      </Card>

      <template v-if="!groupBySeries">
        <div class="library-grid" role="list">
          <div v-if="sorting" class="sorting-overlay" aria-hidden="true">
            <LibrarySkeleton />
          </div>
          <template v-else>
          <NovelCard
            v-for="novel in sortedNovels"
            :key="novel.id"
            :novel="novel"
            @menu-click="openNovelMenu($event, novel)"
          />
          </template>
        </div>
      </template>
      <template v-else>
        <section v-for="group in groupedNovels.groups" :key="group.key" class="series-group">
          <div class="series-header">
            <span class="series-name">{{ group.series }}</span>
            <span class="series-author small muted">{{ group.author }}</span>
          </div>
          <div class="library-grid" role="group" :aria-label="`${group.series} — ${group.author}`">
            <NovelCard
              v-for="novel in group.novels"
              :key="novel.id"
              :novel="novel"
              @menu-click="openNovelMenu($event, novel)"
            />
          </div>
        </section>
        <section v-if="groupedNovels.ungrouped.length" class="series-group">
          <div class="series-header">
            <span class="series-name series-ungrouped"><i>Sin serie</i></span>
          </div>
          <div class="library-grid" role="group" aria-label="Novelas sin serie">
            <NovelCard
              v-for="novel in groupedNovels.ungrouped"
              :key="novel.id"
              :novel="novel"
              @menu-click="openNovelMenu($event, novel)"
            />
          </div>
        </section>
      </template>
    </div>

    <Menu ref="novelMenu" :model="novelMenuItems" :popup="true" />

    <Dialog v-model:visible="createOpen" modal header="Nueva novela" :style="{ width: 'min(620px, 96vw)' }">
      <div class="stack-md">
        <div class="row-wrap">
          <div style="flex: 1; min-width: 220px">
            <label class="small muted">Título</label>
            <InputText v-model="form.sourceTitle" fluid />
          </div>
          <div style="flex: 1; min-width: 220px">
            <label class="small muted">Autor</label>
            <InputText v-model="form.sourceAuthor" fluid />
          </div>
        </div>
        <div>
          <label class="small muted">Descripción</label>
          <Textarea v-model="form.sourceDescription" rows="4" fluid />
        </div>
        <div class="row-wrap">
          <div style="flex: 1; min-width: 220px">
            <label class="small muted">Idioma origen</label>
            <Select v-model="form.sourceLanguage" :options="languageOptions" optionLabel="name" optionValue="code" placeholder="Selecciona idioma" fluid />
          </div>
          <div style="flex: 1; min-width: 220px">
            <label class="small muted">Idioma destino</label>
            <Select v-model="form.targetLanguage" :options="languageOptionsNoAuto" optionLabel="name" optionValue="code" placeholder="Selecciona idioma" fluid />
          </div>
        </div>
        <Message v-if="createError" severity="error">{{ createError }}</Message>
      </div>
      <template #footer>
        <Button severity="secondary" outlined label="Cancelar" @click="createOpen = false" />
        <Button label="Crear" :loading="creating" :disabled="!canCreate" @click="submitCreate" />
      </template>
    </Dialog>

    <Dialog v-model:visible="importOpen" modal header="Importar novela desde EPUB" :style="{ width: 'min(640px, 96vw)' }">
      <div class="stack-md">
        <input type="file" accept=".epub" @change="handleImportFile" />
        <Message v-if="importPreviewLoading" severity="info">Analizando EPUB…</Message>

        <template v-if="importPreview">
          <Card>
            <template #content>
              <div class="stack-md small">
                <div><strong>Título detectado:</strong> {{ importPreview.title }}</div>
                <div v-if="importPreview.author"><strong>Autor detectado:</strong> {{ importPreview.author }}</div>
                <div><strong>Capítulos encontrados:</strong> {{ importPreview.chapterCount }}</div>
              </div>
            </template>
          </Card>

          <div class="row-wrap">
            <div style="flex: 1; min-width: 220px">
              <label class="small muted">Idioma origen</label>
              <Select v-model="importSourceLang" :options="languageOptions" optionLabel="name" optionValue="code" placeholder="Automático" fluid />
            </div>
            <div style="flex: 1; min-width: 220px">
              <label class="small muted">Idioma destino</label>
              <Select v-model="importTargetLang" :options="languageOptionsNoAuto" optionLabel="name" optionValue="code" placeholder="Requerido" fluid />
            </div>
          </div>
        </template>

        <Message v-if="importError" severity="error">{{ importError }}</Message>
      </div>
      <template #footer>
        <Button severity="secondary" outlined label="Cancelar" @click="resetImport" />
        <Button label="Importar" :loading="importing" :disabled="!importFile || !importTargetLang" @click="submitImport" />
      </template>
    </Dialog>

    <ImportUrlDialog
      :open="importUrlOpen"
      @update:open="importUrlOpen = $event"
      @preview="onUrlPreviewed"
    />

    <ImportUrlConfirmDialog
      :open="importUrlConfirmOpen"
      :preview="urlPreview"
      @update:open="importUrlConfirmOpen = $event"
      @back="onBackToUrlDialog"
    />
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import { useConfirm } from "primevue/useconfirm";
import AppLayout from "@/components/AppLayout.vue";
import Button from "primevue/button";
import Card from "primevue/card";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
import Select from "primevue/select";
import Message from "primevue/message";
import Menu from "primevue/menu";
import NovelCard from "@/components/NovelCard.vue";
import LibrarySkeleton from "@/components/LibrarySkeleton.vue";
import { useNovels } from "@/composables/useNovels";
import { LANGUAGES } from "@/config/languages";
import { getNovelDisplayTitle, getNovelDisplayAuthor, getNovelDisplaySeries, getNovelDisplayNumber, type Novel } from "@/domain";
import { useAppServices } from "@/app/services";
import ImportUrlDialog from "@/features/novels/ImportUrlDialog.vue";
import ImportUrlConfirmDialog from "@/features/novels/ImportUrlConfirmDialog.vue";
import type { PreviewUrlResult } from "@/api/types";

type SortField = "title" | "created" | "chapters";

const sortOptions: { label: string; value: SortField }[] = [
  { label: "Título", value: "title" },
  { label: "Reciente", value: "created" },
  { label: "Capítulos", value: "chapters" },
];

const sortField = ref<SortField>("title");
const sortOrder = ref<"asc" | "desc">("asc");
const sorting = ref(false);
let sortTimeout: ReturnType<typeof setTimeout> | null = null;

const sortOrderIcon = computed(() =>
  sortOrder.value === "asc" ? "pi pi-sort-amount-up-alt" : "pi pi-sort-amount-down",
);

function toggleSortOrder() {
  sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
}

function onSortChange() {
  sorting.value = true;
  if (sortTimeout) clearTimeout(sortTimeout);
  sortTimeout = setTimeout(() => {
    sorting.value = false;
  }, 300);
}

const sortedNovels = computed(() => {
  const list = [...novels.value];
  const dir = sortOrder.value === "asc" ? 1 : -1;
  switch (sortField.value) {
    case "title":
      list.sort((a, b) => dir * getNovelDisplayTitle(a).localeCompare(getNovelDisplayTitle(b)));
      break;
    case "created":
      list.sort(
        (a, b) => dir * (new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()),
      );
      break;
    case "chapters":
      list.sort((a, b) => dir * (a.chapterCount - b.chapterCount));
      break;
  }
  return list;
});

type NovelGroup = {
  key: string;
  author: string;
  series: string;
  novels: Novel[];
};

type GroupedResult = {
  groups: NovelGroup[];
  ungrouped: Novel[];
};

const groupBySeries = ref(false);

const groupedNovels = computed((): GroupedResult => {
  const groups = new Map<string, NovelGroup>();
  const ungrouped: Novel[] = [];

  for (const novel of sortedNovels.value) {
    const series = getNovelDisplaySeries(novel);
    const author = getNovelDisplayAuthor(novel);
    if (series) {
      const key = `${author}|${series}`;
      if (!groups.has(key)) {
        groups.set(key, { key, author, series, novels: [] });
      }
      groups.get(key)!.novels.push(novel);
    } else {
      ungrouped.push(novel);
    }
  }

  for (const group of groups.values()) {
    group.novels.sort((a, b) => {
      const numA = parseFloat(getNovelDisplayNumber(a));
      const numB = parseFloat(getNovelDisplayNumber(b));
      if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
      if (!isNaN(numA)) return -1;
      if (!isNaN(numB)) return 1;
      return getNovelDisplayTitle(a).localeCompare(getNovelDisplayTitle(b));
    });
  }

  const sortedGroups = [...groups.values()].sort((a, b) => {
    const cmp = a.author.localeCompare(b.author);
    if (cmp !== 0) return cmp;
    return a.series.localeCompare(b.series);
  });

  return { groups: sortedGroups, ungrouped };
});

const router = useRouter();
const toast = useToast();
const confirm = useConfirm();
const { api, auth } = useAppServices();
const { novels, loading, listNovels, createNovel, importNovelFromEpub, deleteNovel } = useNovels();

const createOpen = ref(false);
const creating = ref(false);
const createError = ref<string | null>(null);
const importOpen = ref(false);
const importUrlOpen = ref(false);
const importUrlConfirmOpen = ref(false);
const urlPreview = ref<PreviewUrlResult | null>(null);
const importing = ref(false);
const importPreviewLoading = ref(false);
const importError = ref<string | null>(null);
const importFile = ref<File | null>(null);
const importTargetLang = ref("");
const importSourceLang = ref("");
const importPreview = ref<{ title: string; author: string; description: string; language: string; chapterCount: number } | null>(null);
const novelMenu = ref();
const mobileActionsMenu = ref();
const selectedNovel = ref<Novel | null>(null);

const form = reactive({
  sourceTitle: "",
  sourceAuthor: "",
  sourceDescription: "",
  sourceLanguage: "",
  targetLanguage: "",
});

const languageOptions = LANGUAGES;
const languageOptionsNoAuto = LANGUAGES.filter((item) => item.code !== "auto");
const canCreate = computed(() => Boolean(form.sourceTitle.trim() && form.sourceLanguage && form.targetLanguage));

const mobileActions = computed(() => [
  { label: "Importar EPUB", icon: "pi pi-upload", command: () => { importOpen.value = true; } },
  { label: "Desde URL", icon: "pi pi-globe", command: () => { importUrlOpen.value = true; } },
]);

const novelMenuItems = computed(() => {
  const novel = selectedNovel.value;
  if (!novel) return [];
  const isOwner = novel.ownerId === auth.user.value?.id;
  const items: Array<{ label: string; icon: string; command?: () => void; class?: string }> = [
    { label: "Leer", icon: "pi pi-book", command: () => router.push(`/novels/${novel.id}/read`) },
  ];
  if (isOwner) {
    items.push(
      { label: "Editar", icon: "pi pi-pencil", command: () => router.push(`/novels/${novel.id}`) },
      { label: "Eliminar", icon: "pi pi-trash", class: "novel-menu-delete", command: () => askDeleteNovel(novel) },
    );
  } else {
    items.push({ label: "Copiar a mi biblioteca", icon: "pi pi-copy", command: () => copyNovel(novel.id) });
  }
  return items;
});

onMounted(() => {
  void listNovels(false, ["id", "sourceTitle", "targetTitle", "sourceAuthor", "targetAuthor", "sourceSeries", "targetSeries", "sourceNumber", "targetNumber", "coverPath", "ownerId"]);
});

function resetCreateForm() {
  form.sourceTitle = "";
  form.sourceAuthor = "";
  form.sourceDescription = "";
  form.sourceLanguage = "";
  form.targetLanguage = "";
  createError.value = null;
}

async function submitCreate() {
  if (!canCreate.value) return;
  creating.value = true;
  createError.value = null;
  try {
    const novel = await createNovel({
      sourceTitle: form.sourceTitle,
      sourceAuthor: form.sourceAuthor || undefined,
      sourceDescription: form.sourceDescription || undefined,
      sourceLanguage: form.sourceLanguage,
      targetLanguage: form.targetLanguage,
    });
    createOpen.value = false;
    resetCreateForm();
    await router.push(`/novels/${novel.id}`);
  } catch (err) {
    createError.value = err instanceof Error ? err.message : String(err);
  } finally {
    creating.value = false;
  }
}

async function handleImportFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  importError.value = null;
  importFile.value = file;
  importPreviewLoading.value = true;
  try {
    const data = await api.epubs.preview(file, file.name);
    importPreview.value = {
      title: data.title || file.name.replace(/\.epub$/i, ""),
      author: data.author || "",
      description: data.description || "",
      language: data.language || "",
      chapterCount: data.chapters?.length || 0,
    };
    importSourceLang.value = data.language || "";
  } catch (err) {
    importError.value = err instanceof Error ? err.message : String(err);
    importPreview.value = null;
  } finally {
    importPreviewLoading.value = false;
  }
}

function resetImport() {
  importOpen.value = false;
  importing.value = false;
  importPreviewLoading.value = false;
  importError.value = null;
  importPreview.value = null;
  importFile.value = null;
  importTargetLang.value = "";
  importSourceLang.value = "";
}

async function submitImport() {
  if (!importFile.value || !importTargetLang.value) return;
  importing.value = true;
  importError.value = null;
  try {
    const result = await importNovelFromEpub({
      file: importFile.value,
      fileName: importFile.value.name,
      sourceLanguage: importSourceLang.value || undefined,
      targetLanguage: importTargetLang.value,
    });
    resetImport();
    await router.push(`/novels/${result.novel.id}`);
  } catch (err) {
    importError.value = err instanceof Error ? err.message : String(err);
  } finally {
    importing.value = false;
  }
}

async function copyNovel(novelId: string) {
  try {
    await api.novels.copy(novelId);
    await listNovels(true, ["id", "sourceTitle", "targetTitle", "sourceAuthor", "targetAuthor", "sourceSeries", "targetSeries", "sourceNumber", "targetNumber", "coverPath", "ownerId"]);
    toast.add({ severity: "success", summary: "Novela copiada a tu biblioteca", life: 2500 });
  } catch (err) {
    toast.add({ severity: "error", summary: "Error al copiar", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  }
}

function openNovelMenu(event: Event, novel: Novel) {
  selectedNovel.value = novel;
  novelMenu.value?.toggle(event);
}

function askDeleteNovel(novel: Novel) {
  confirm.require({
    message: `¿Eliminar "${getNovelDisplayTitle(novel)}"? Esta acción no se puede deshacer.`,
    header: "Eliminar novela",
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Eliminar",
    rejectLabel: "Cancelar",
    acceptClass: "p-button-danger",
    acceptIcon: "pi pi-trash",
    accept: async () => {
      try {
        await deleteNovel(novel.id);
        toast.add({ severity: "success", summary: "Novela eliminada", life: 2500 });
      } catch (err) {
        toast.add({ severity: "error", summary: "Error al eliminar", detail: err instanceof Error ? err.message : String(err), life: 4000 });
      }
    },
  });
}

function onUrlPreviewed(preview: PreviewUrlResult) {
  urlPreview.value = preview;
  importUrlOpen.value = false;
  importUrlConfirmOpen.value = true;
}

function onBackToUrlDialog() {
  importUrlConfirmOpen.value = false;
  urlPreview.value = null;
  importUrlOpen.value = true;
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.page-action {
  white-space: nowrap;
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.sort-select {
  min-width: 8rem;
}

.mobile-only {
  display: none;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 1rem;
  padding: 2.5rem 1rem;
}

.empty-state-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3.5rem;
  height: 3.5rem;
  border-radius: var(--radius-lg);
  background: var(--surface-muted);
  color: var(--text-secondary);
  font-size: 1.5rem;
}

.empty-state-title {
  margin: 0 0 0.25rem;
  font-size: 1.25rem;
}

.empty-state-body {
  margin: 0;
  max-width: 48ch;
}

.empty-state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
}

.library-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1.5rem;
}

.series-group {
  margin-bottom: 2rem;
}

.series-header {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--divide);
}

.series-name {
  font-weight: 700;
  font-size: 1.125rem;
}

.series-author {
  color: var(--text-tertiary);
}

.series-ungrouped {
  color: var(--text-tertiary);
  font-style: italic;
}

.sorting-overlay {
  display: contents;
}

@media (max-width: 640px) {
  .desktop-only {
    display: none;
  }

  .mobile-only {
    display: inline-flex;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .library-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
}

@media (max-width: 380px) {
  .library-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

:global(.novel-menu-delete) {
  color: var(--p-red-500);
}

:global(.novel-menu-delete .p-menuitem-icon) {
  color: var(--p-red-500);
}
</style>
