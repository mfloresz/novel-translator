<template>
  <AppLayout>
    <template #back-button>
      <Button icon="pi pi-arrow-left" severity="secondary" text rounded @click="router.push('/')" aria-label="Volver a novelas" />
    </template>

    <div v-if="!novel && novelLoading" class="novel-detail-layout">
      <aside class="novel-sidebar">
        <Skeleton shape="rectangle" width="100%" height="320px" borderRadius="12px" />
        <div class="novel-sidebar-actions">
          <Skeleton width="100%" height="2.5rem" borderRadius="8px" />
          <Skeleton width="100%" height="2.5rem" borderRadius="8px" />
        </div>
        <div class="novel-sidebar-tags">
          <Skeleton width="5rem" height="1.5rem" borderRadius="9999px" />
          <Skeleton width="6rem" height="1.5rem" borderRadius="9999px" />
          <Skeleton width="7rem" height="1.5rem" borderRadius="9999px" />
        </div>
      </aside>

      <div class="novel-main">
        <header class="novel-main-header">
          <Skeleton width="60%" height="2rem" style="margin-bottom: 0.5rem" />
          <Skeleton width="30%" height="1rem" style="margin-bottom: 0.75rem" />
          <Skeleton width="20%" height="0.875rem" />
          <Skeleton width="90%" height="0.875rem" style="margin-top: 1rem" />
          <Skeleton width="75%" height="0.875rem" style="margin-top: 0.5rem" />
        </header>
        <div class="novel-tabs">
          <Skeleton width="5rem" height="2rem" borderRadius="8px" />
          <Skeleton width="5rem" height="2rem" borderRadius="8px" />
          <Skeleton width="5rem" height="2rem" borderRadius="8px" />
          <Skeleton width="5rem" height="2rem" borderRadius="8px" />
        </div>
        <div class="stack-sm">
          <div v-for="i in 6" :key="i" class="row-between" style="padding: 0.5rem 0; border-bottom: 1px solid var(--p-content-border-color)">
            <div class="row-wrap" style="flex: 1; min-width: 0">
              <Skeleton shape="rectangle" width="1.5rem" height="1.5rem" />
              <Skeleton width="2.5rem" height="1rem" />
              <Skeleton width="45%" height="1.1rem" />
              <Skeleton width="6rem" height="1.4rem" />
            </div>
            <div class="row-wrap">
              <Skeleton width="5rem" height="1rem" />
              <Skeleton shape="rectangle" width="2.25rem" height="2.25rem" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!novel" class="stack-md">
      <Message severity="warn">Novela no encontrada.</Message>
      <Button label="Volver" severity="secondary" outlined @click="router.push('/')" />
    </div>

    <div v-else class="novel-detail-layout">
      <aside class="novel-sidebar">
        <div class="novel-cover-large">
          <img v-if="novel.coverPath" :src="novel.coverPath" :alt="`Portada de ${getNovelDisplayTitle(novel)}`" loading="lazy" />
          <div v-else class="novel-cover-placeholder-large">
            <i class="pi pi-image" aria-hidden="true" />
          </div>
        </div>

        <div class="novel-sidebar-actions">
          <Button label="Leer" icon="pi pi-book" fluid @click="router.push(`/novels/${novel.id}/read`)" />
          <Button v-if="isOwner" label="Configuración" icon="pi pi-cog" severity="secondary" outlined fluid @click="settingsOpen = true" />
          <Button v-else label="Copiar novela" icon="pi pi-copy" severity="secondary" outlined fluid @click="copyCurrentNovel" />
          <Button v-if="isOwner" :label="novel.isPublic ? 'Despublicar' : 'Publicar'" icon="pi pi-globe" severity="secondary" outlined fluid @click="toggleVisibility" />
          <Button v-if="isOwner && novel.url" label="Actualizar desde URL" icon="pi pi-refresh" severity="secondary" outlined fluid @click="updateUrlOpen = true" />
        </div>

        <div class="novel-sidebar-tags">
          <Tag :severity="novelStatusSeverity(novel.status)" :value="novelStatusLabel(novel.status)" />
          <Tag severity="secondary" :value="`${chapterStats.totalChapters} capítulos`" />
          <Tag severity="contrast" :value="`${completedChapters} traducidos`" />
          <Tag severity="success" :value="`${novel.sourceLanguage} → ${novel.targetLanguage}`" />
        </div>
      </aside>

      <div class="novel-main">
        <header class="novel-main-header">
          <h1 class="novel-title">{{ getNovelDisplayTitle(novel) }}</h1>
          <div class="novel-meta">
            <span v-if="getNovelDisplayAuthor(novel)" class="muted">{{ getNovelDisplayAuthor(novel) }}</span>
            <span v-if="getNovelDisplaySeries(novel) || getNovelDisplayNumber(novel)" class="novel-series muted small">
              <i class="pi pi-bookmark" aria-hidden="true" />
              <span v-if="getNovelDisplaySeries(novel)">{{ getNovelDisplaySeries(novel) }}</span>
              <span v-if="getNovelDisplaySeries(novel) && getNovelDisplayNumber(novel)">·</span>
              <span v-if="getNovelDisplayNumber(novel)">#{{ getNovelDisplayNumber(novel) }}</span>
            </span>
          </div>
          <div v-if="getNovelDisplayDescription(novel)" class="novel-description-wrapper">
            <div
              ref="descriptionEl"
              class="markdown-preview muted small novel-description"
              :class="{ 'novel-description--collapsed': !descriptionExpanded }"
              v-html="markdownToHtml(getNovelDisplayDescription(novel))"
            />
            <button
              v-if="descriptionOverflow || descriptionExpanded"
              type="button"
              class="novel-description-toggle"
              @click="descriptionExpanded = !descriptionExpanded"
            >
              {{ descriptionExpanded ? 'Mostrar menos' : 'Mostrar más' }}
              <i :class="descriptionExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" />
            </button>
          </div>
          <div v-if="novel.tags.length > 0" class="novel-description-tags">
            <Tag v-for="tagItem in novel.tags" :key="tagItem" severity="info" :value="tagItem" />
          </div>
        </header>

        <div class="novel-tabs" role="tablist" aria-label="Secciones de la novela">
          <button
            v-for="tab in visibleTabs"
            :key="tab.value"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.value"
            class="novel-tab"
            :class="{ 'novel-tab--active': activeTab === tab.value }"
            @click="activeTab = tab.value"
          >
            {{ tab.label }}
          </button>
        </div>

      <section v-if="activeTab === 'chapters'" class="stack-md tab-panel" aria-labelledby="tab-chapters">
        <h2 id="tab-chapters" class="sr-only">Capítulos</h2>
        <ChapterList
          :chapters="chapterSummaries"
          :total="chapterSummaryTotal"
          :loading="chapterSummariesLoading"
          :page="chapterPage"
          :page-size="chapterPageSize"
          v-model:selected="selectedChapters"
          :is-owner="isOwner"
          @delete="onDeleteChapter"
          @bulk-delete="onBulkDeleteChapters"
          @create="openCreateChapter"
          @import="bulkImportOpen = true"
          @update:page="chapterPage = $event"
        />
      </section>

      <section v-else-if="activeTab === 'translate'" class="stack-md tab-panel" aria-labelledby="tab-translate">
        <h2 id="tab-translate" class="sr-only">{{ translateOperation === 'translate' ? 'Traducción' : 'Refinamiento' }}</h2>
        <Card>
          <template #title>{{ translateOperation === 'translate' ? 'Traducción automática' : 'Refinamiento' }}</template>
          <template #content>
            <div v-if="allSummariesLoading" class="stack-md">
              <Skeleton width="100%" height="8rem" borderRadius="12px" />
              <Skeleton width="100%" height="14rem" borderRadius="12px" />
            </div>
            <div v-else class="stack-md">
              <div class="row-between">
                <SelectButton v-model="translateOperation" :options="translateOperationOptions" optionLabel="label" optionValue="value" :allowEmpty="false" />
                <div class="row-wrap">
                  <Button :label="`Iniciar (${translateSelectedIds.size})`" icon="pi pi-play" :loading="translateSubmitting" :disabled="translateSelectedIds.size === 0 || translateSubmitting" @click="startTranslationJob" />
                </div>
              </div>

              <div class="row-wrap small muted">
                <Button size="small" severity="secondary" text label="Todos" @click="translateSelectedIds = new Set(eligibleChapters.map((chapter) => chapter.id))" />
                <Button size="small" severity="secondary" text label="Ninguno" @click="translateSelectedIds = new Set()" />
                <span>{{ eligibleChapters.length }} capítulos elegibles</span>
              </div>

              <div v-if="eligibleChapters.length === 0" class="muted small">Todos los capítulos ya fueron {{ translateOperation === 'translate' ? 'traducidos' : 'refinados' }}.</div>
              <div v-else style="border: 1px solid var(--p-content-border-color); border-radius: 12px; overflow: auto; max-height: 420px">
                <div v-for="chapter in eligibleChapters" :key="chapter.id" style="display: flex; gap: 0.75rem; align-items: center; padding: 0.875rem 1rem; border-bottom: 1px solid var(--p-content-border-color)">
                  <Checkbox :model-value="translateSelectedIds.has(chapter.id)" binary :disabled="translateSubmitting" @update:model-value="toggleTranslateChapter(chapter.id, $event)" />
                  <span class="mono small muted" style="width: 48px">#{{ chapter.chapterOrder }}</span>
                  <span style="flex: 1; min-width: 0">{{ chapter.title }}</span>
                  <Tag :severity="chapterSeverity(resolvedChapterStatus(chapter))" :value="chapterStatusLabel(resolvedChapterStatus(chapter))" />
                </div>
              </div>
            </div>
          </template>
        </Card>
      </section>

      <section v-else-if="activeTab === 'clean'" class="stack-md tab-panel" aria-labelledby="tab-clean">
        <h2 id="tab-clean" class="sr-only">Limpieza de texto</h2>
        <Card>
          <template #title>Limpieza de texto</template>
          <template #content>
            <div v-if="allSummariesLoading" class="stack-md">
              <Skeleton width="100%" height="8rem" borderRadius="12px" />
              <Skeleton width="100%" height="12rem" borderRadius="12px" />
            </div>
            <div v-else class="stack-md">
              <div class="row-wrap">
                <div style="min-width: 240px; flex: 1">
                  <label class="small muted">Modo de limpieza</label>
                  <Select v-model="cleanMode" :options="cleanModeOptions" optionLabel="label" optionValue="value" fluid />
                  <div class="small muted" style="margin-top: 0.4rem">{{ cleanModeDescription }}</div>
                </div>
                <div style="min-width: 220px; flex: 1">
                  <label class="small muted">Aplicar a</label>
                  <Select v-model="cleanApplyTo" :options="cleanApplyOptions" optionLabel="label" optionValue="value" fluid />
                </div>
              </div>

              <div class="row-wrap">
                <div style="min-width: 240px; flex: 1">
                  <label class="small muted">Buscar</label>
                  <InputText v-model="cleanSearchText" :disabled="cleanMode === 'remove_multiple_blanks'" fluid />
                </div>
                <div v-if="cleanMode === 'search_replace'" style="min-width: 240px; flex: 1">
                  <label class="small muted">Reemplazar con</label>
                  <InputText v-model="cleanReplaceText" fluid />
                </div>
              </div>

              <div class="row-wrap">
                <div style="display: flex; align-items: center; gap: 0.5rem">
                  <ToggleSwitch v-model="cleanCaseSensitive" />
                  <span class="small muted">Distinguir mayúsculas</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.5rem">
                  <ToggleSwitch v-model="cleanUseRegex" />
                  <span class="small muted">Usar regex</span>
                </div>
              </div>
            </div>
          </template>
        </Card>

        <Card>
          <template #title>Capítulos a limpiar</template>
          <template #content>
            <div class="stack-md">
              <div class="row-between">
                <div class="row-wrap small muted">
                  <Button size="small" severity="secondary" text label="Todos" @click="cleanSelectedIds = new Set(cleanEligibleChapters.map((chapter) => chapter.id))" />
                  <Button size="small" severity="secondary" text label="Ninguno" @click="cleanSelectedIds = new Set()" />
                </div>
                <Button :label="`Aplicar a ${cleanSelectedIds.size} capítulos`" icon="pi pi-save" :loading="cleanApplying" :disabled="cleanSelectedIds.size === 0" @click="applyCleaningToSelected" />
              </div>

              <Message v-if="cleanFeedback" severity="success">{{ cleanFeedback }}</Message>

              <div v-if="cleanEligibleChapters.length === 0" class="muted small">Selecciona primero el tipo de limpieza arriba para ver capítulos disponibles.</div>
              <div v-else style="border: 1px solid var(--p-content-border-color); border-radius: 12px; overflow: auto; max-height: 320px">
                <div v-for="chapter in cleanEligibleChapters" :key="chapter.id" style="display: flex; gap: 0.75rem; align-items: center; padding: 0.875rem 1rem; border-bottom: 1px solid var(--p-content-border-color)">
                  <Checkbox :model-value="cleanSelectedIds.has(chapter.id)" binary @update:model-value="toggleCleanChapter(chapter.id, $event)" />
                  <span class="mono small muted" style="width: 48px">#{{ chapter.chapterOrder }}</span>
                  <span style="flex: 1">{{ chapter.title }}</span>
                  <Button size="small" severity="secondary" outlined label="Previsualizar" @click="previewCleaning(chapter)" />
                </div>
              </div>

              <Card v-if="cleanPreview">
                <template #title>Vista previa · {{ cleanPreview.chapterTitle }}</template>
                <template #content>
                  <div class="row-wrap">
                    <div style="flex: 1; min-width: 280px">
                      <label class="small muted">Original</label>
                      <Textarea :model-value="cleanPreview.result.original" rows="12" readonly fluid class="mono" />
                    </div>
                    <div style="flex: 1; min-width: 280px">
                      <label class="small muted">Limpio</label>
                      <Textarea :model-value="cleanPreview.result.cleaned" rows="12" readonly fluid class="mono" />
                    </div>
                  </div>
                </template>
              </Card>
            </div>
          </template>
        </Card>
      </section>

      <section v-else-if="activeTab === 'export'" class="stack-md tab-panel" aria-labelledby="tab-export">
        <h2 id="tab-export" class="sr-only">Exportar</h2>
        <Card>
          <template #title>Exportar a EPUB</template>
          <template #content>
            <div class="stack-md">
              <div style="min-width: 220px; max-width: 320px">
                <label class="small muted">Fuente del contenido</label>
                <Select v-model="exportSource" :options="exportSourceOptions" optionLabel="label" optionValue="value" fluid />
              </div>

              <ProgressBar v-if="exportBuilding" :value="exportProgress" />
              <Message v-if="exportFeedback" :severity="exportFeedback.startsWith('Error:') ? 'error' : 'success'">{{ exportFeedback }}</Message>
              <Button label="Descargar EPUB" icon="pi pi-download" :loading="exportBuilding" :disabled="exportBuilding" @click="buildAndDownloadEpub" />
            </div>
          </template>
        </Card>
      </section>

      <section v-else class="stack-md tab-panel" aria-labelledby="tab-errors">
        <h2 id="tab-errors" class="sr-only">Historial de errores</h2>
        <Card v-if="failedJobs.length === 0">
          <template #content>
            <div class="stack-md" style="align-items: center; text-align: center; padding: 2rem 1rem">
              <i class="pi pi-clock" style="font-size: 2rem; color: var(--p-text-muted-color)" />
              <div>
                <h3 style="margin: 0 0 0.5rem">Aún no hay errores</h3>
                <p class="muted">Cuando un trabajo falle, verás los detalles aquí.</p>
              </div>
            </div>
          </template>
        </Card>
        <Card v-for="job in failedJobs" :key="job.id">
          <template #content>
            <div class="stack-md">
              <div class="row-between">
                <div>
                  <div style="font-weight: 600">{{ job.completedChapters }}/{{ job.totalChapters }} completados · {{ job.failedChapters }} fallidos</div>
                  <div class="small muted">{{ job.provider || 'provider por defecto' }} · {{ job.model || 'model por defecto' }} · {{ formatDate(job.createdAt) }}</div>
                </div>
                <div class="row-wrap">
                  <Tag :severity="jobSeverity(job.status)" :value="jobStatusLabel(job.status)" />
                  <Button v-if="job.status === 'running' || job.status === 'pending'" size="small" severity="danger" outlined label="Cancelar" @click="cancelFailedHistoryJob(job.id)" />
                </div>
              </div>
              <ProgressBar v-if="jobShowsCompletedProgress(job)" :value="jobProgress(job)" />
              <ProgressBar v-else mode="indeterminate" />
              <div v-if="jobCurrentActivityLabel(job)" class="small muted">
                {{ jobCurrentActivityLabel(job) }}
              </div>
              <Message v-if="job.errorMessage?.trim()" :severity="job.status === 'failed' ? 'error' : 'warn'" :closable="false">
                <div class="stack-sm" style="gap: 0.25rem">
                  <strong>{{ job.status === 'failed' ? 'Motivo del fallo del trabajo' : 'Aviso del trabajo' }}</strong>
                  <span class="mono small" style="white-space: pre-wrap; word-break: break-word">{{ job.errorMessage }}</span>
                </div>
              </Message>
              <div v-if="jobFailedChapters(job).length > 0" class="job-failed-chapters">
                <div class="row-between" @click="toggleJobFailedChapters(job.id)" style="cursor: pointer; user-select: none">
                  <div class="row-wrap">
                    <i :class="expandedJobId === job.id ? 'pi pi-chevron-down' : 'pi pi-chevron-right'" style="font-size: 0.85rem" />
                    <strong>Capítulos fallidos ({{ jobFailedChapters(job).length }})</strong>
                  </div>
                  <span class="small muted">{{ expandedJobId === job.id ? 'Ocultar' : 'Ver' }} detalles</span>
                </div>
                <div v-if="expandedJobId === job.id" class="stack-sm" style="margin-top: 0.5rem">
                  <div v-for="chapter in jobFailedChapters(job)" :key="chapter.id" class="job-failed-chapter-item">
                    <div class="row-between" style="align-items: flex-start; gap: 0.75rem">
                      <div style="min-width: 0; flex: 1">
                        <div class="row-wrap">
                          <span class="mono small muted">#{{ chapter.chapterOrder }}</span>
                          <Button link style="padding: 0; text-align: left" @click="router.push(`/novels/${chapter.novelId}/chapters/${chapter.id}`)">
                            {{ chapter.title }}
                          </Button>
                        </div>
                        <div v-if="chapter.errorMessage?.trim()" class="small job-failed-chapter-error mono">
                          {{ chapter.errorMessage }}
                        </div>
                        <div v-else class="small muted" style="font-style: italic">
                          Sin detalles disponibles para este error.
                        </div>
                      </div>
                      <Tag severity="danger" :value="chapterStatusLabel(resolvedChapterStatus(chapter))" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </Card>
      </section>
      </div>
    </div>

    <Dialog v-model:visible="chapterDialogOpen" modal :header="editingChapter ? 'Editar capítulo' : 'Nuevo capítulo'" :style="{ width: 'min(720px, 96vw)' }">
      <div class="stack-md">
        <div class="row-wrap">
          <FieldNumber v-model="chapterDraft.chapterOrder" label="N° capítulo" :min="1" wrapper-style="flex: 1; min-width: 160px" />
          <div style="flex: 2; min-width: 240px">
            <label class="small muted">Título</label>
            <InputText v-model="chapterDraft.title" fluid />
          </div>
        </div>
        <div>
          <label class="small muted">Contenido original (markdown)</label>
          <Textarea v-model="chapterDraft.originalContent" rows="12" fluid class="mono" />
        </div>
      </div>
      <template #footer>
        <Button severity="secondary" outlined label="Cancelar" @click="chapterDialogOpen = false" />
        <Button :label="editingChapter ? 'Guardar cambios' : 'Crear capítulo'" :loading="chapterSaving" :disabled="!chapterDraft.title.trim()" @click="saveChapter" />
      </template>
    </Dialog>

    <BulkImportDialog
      :open="bulkImportOpen"
      :next-order="nextChapterOrder"
      :on-import="handleBulkImport"
      :on-epub-files-imported="handleImportedEpubFiles"
      :preview-epub="previewEpub"
      @update:open="bulkImportOpen = $event"
    />

    <ProjectSettingsDialog
      v-if="novel"
      :open="settingsOpen"
      :novel="novel"
      :on-save-novel="saveProjectSettings"
      @update:open="settingsOpen = $event"
      @cover-updated="onCoverUpdated"
    />

    <UpdateUrlDialog
      v-if="novel && novel.url"
      :open="updateUrlOpen"
      :novel-id="novel.id"
      @update:open="updateUrlOpen = $event"
      @updated="onUrlUpdated"
    />

    <Popover ref="confirmDeletePopover">
      <div class="stack-md" style="max-width: 260px">
        <div>
          <div style="font-weight: 600">¿Eliminar este capítulo?</div>
          <div class="small muted" style="margin-top: 0.25rem">Esta acción no se puede deshacer.</div>
        </div>
        <div class="row-wrap" style="justify-content: flex-end">
          <Button size="small" severity="secondary" outlined label="Cancelar" @click="cancelDeleteChapter" />
          <Button size="small" severity="danger" label="Eliminar" :loading="deletingChapter" @click="confirmDeleteChapter" />
        </div>
      </div>
    </Popover>

    <Popover ref="bulkDeletePopover">
      <div class="stack-md" style="max-width: 300px">
        <div>
          <div style="font-weight: 600">¿Eliminar {{ selectedChapters.length }} capítulos?</div>
          <div class="small muted" style="margin-top: 0.25rem">Esta acción no se puede deshacer y eliminará los capítulos seleccionados junto con su contenido traducido y refinado.</div>
        </div>
        <div class="row-wrap" style="justify-content: flex-end">
          <Button size="small" severity="secondary" outlined label="Cancelar" @click="cancelBulkDeleteChapters" />
          <Button size="small" severity="danger" :label="`Eliminar ${selectedChapters.length}`" :loading="bulkDeleting" @click="confirmBulkDeleteChapters" />
        </div>
      </div>
    </Popover>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import AppLayout from "@/components/AppLayout.vue";
import ChapterList from "@/components/ChapterList.vue";
import FieldNumber from "@/components/FieldNumber.vue";
import BulkImportDialog from "@/features/novels/BulkImportDialog.vue";
import UpdateUrlDialog from "@/features/novels/UpdateUrlDialog.vue";
import ProjectSettingsDialog from "@/features/projects/ProjectSettingsDialog.vue";
import Button from "primevue/button";
import Card from "primevue/card";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Popover from "primevue/popover";
import ProgressBar from "primevue/progressbar";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Skeleton from "primevue/skeleton";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { markdownToHtml } from "@/utils/markdown";
import type { ChapterSummary } from "@/api/types";
import { useAppServices } from "@/app/services";
import { useChapters } from "@/composables/useChapters";
import { useNovels } from "@/composables/useNovels";
import { useActiveJobStatus } from "@/composables/useActiveJobStatus";
import { useTranslationJobs } from "@/composables/useTranslationJobs";
import {
  getNovelDisplayAuthor,
  getNovelDisplayDescription,
  getNovelDisplayNumber,
  getNovelDisplaySeries,
  getNovelDisplayTitle,
  type Chapter,
  type ChapterUpsertInput,
  type CreateNovelInput,
  type Novel,
  type NovelStatus,
  type TranslationJob,
} from "@/domain";
import { CLEAN_MODE_DESCRIPTIONS, CLEAN_MODE_LABELS, type CleanMode } from "@/utils/cleaner";

const router = useRouter();
const route = useRoute();
const toast = useToast();
const { api, auth } = useAppServices();
const { getNovel, updateNovel, replaceNovelInList } = useNovels();
const novelId = computed(() => String(route.params.novelId || ""));
const { chapters, loading: chaptersLoading, listChapters, createChapter, updateChapter, bulkCreateChapters, deleteChapter, bulkDeleteChapters } = useChapters(novelId, { autoLoad: false });
const { hasActive } = useActiveJobStatus();
const { jobs: failedJobs, listJobs: listFailedJobs, createJob, updateJob } = useTranslationJobs(novelId, { failedOnly: true, autoLoad: false });

const tabs = [
  { value: "chapters", label: "Capítulos" },
  { value: "translate", label: "Traducir" },
  { value: "clean", label: "Limpieza" },
  { value: "export", label: "Exportar" },
  { value: "jobs", label: "Trabajos" },
];

const activeTab = ref("chapters");
const settingsOpen = ref(false);
const bulkImportOpen = ref(false);
const updateUrlOpen = ref(false);
const chapterPageSize = 50;
const chapterPage = ref(0);
const chapterSummaries = ref<ChapterSummary[]>([]);
const chapterSummaryTotal = ref(0);
const chapterSummariesLoading = ref(false);
const allSummaries = ref<ChapterSummary[]>([]);
const allSummariesLoading = ref(false);
const allSummariesLoaded = ref(false);
const allSummariesDirty = ref(false);
const failedJobsLoaded = ref(false);
const failedJobsDirty = ref(false);
const fullChaptersLoaded = ref(false);
const selectedChapters = ref<ChapterSummary[]>([]);
const chapterDialogOpen = ref(false);
const chapterSaving = ref(false);
const editingChapter = ref<Chapter | null>(null);
const confirmDeletePopover = ref<InstanceType<typeof Popover> | null>(null);
const pendingDeleteChapterId = ref<string | null>(null);
const deletingChapter = ref(false);
const bulkDeletePopover = ref<InstanceType<typeof Popover> | null>(null);
const bulkDeleting = ref(false);
const chapterDraft = reactive<{ id?: string; chapterOrder: number; title: string; originalContent: string }>({
  chapterOrder: 1,
  title: "",
  originalContent: "",
});

const translateOperation = ref<"translate" | "refine">("translate");
const translateSelectedIds = ref<Set<string>>(new Set());
const translateSubmitting = ref(false);
let userTouchedTranslateSelection = false;
const expandedJobId = ref<string | null>(null);

const cleanMode = ref<CleanMode>("search_replace");
const cleanApplyTo = ref<"original" | "translated" | "refined" | "all">("translated");
const cleanSearchText = ref("");
const cleanReplaceText = ref("");
const cleanCaseSensitive = ref(true);
const cleanUseRegex = ref(false);
const cleanSelectedIds = ref<Set<string>>(new Set());
const cleanApplying = ref(false);
const cleanFeedback = ref<string | null>(null);
const cleanPreview = ref<{ chapterTitle: string; result: { original: string; cleaned: string; changed: boolean; removedLines: number } } | null>(null);

const exportSource = ref<"refined" | "translated" | "original">("refined");
const exportBuilding = ref(false);
const exportProgress = ref(0);
const exportFeedback = ref<string | null>(null);

const descriptionEl = ref<HTMLElement | null>(null);
const descriptionExpanded = ref(false);
const descriptionOverflow = ref(false);

const novelLoading = ref(true);
const novel = ref<Novel | null>(null);
const isOwner = computed(() => novel.value?.ownerId === auth.user.value?.id);
const visibleTabs = computed(() => isOwner.value ? tabs : tabs.filter((tab) => tab.value === 'chapters'));
const chapterStats = computed(() => ({
  totalChapters: novel.value?.chapterCount ?? 0,
  translatedChapters: novel.value?.translatedCount ?? 0,
  completedChapters: novel.value?.completedCount ?? 0,
  maxChapterOrder: novel.value?.maxChapterOrder ?? 0,
}));
const completedChapters = computed(() => chapterStats.value.translatedChapters);
const nextChapterOrder = computed(() => chapterStats.value.maxChapterOrder + 1);
const hasProcessingChapters = computed(() =>
  chapterSummaries.value.some((chapter) => chapter.status === "processing") ||
  allSummaries.value.some((chapter) => chapter.status === "processing"),
);

function novelStatusLabel(status: NovelStatus) {
  switch (status) {
    case "completed":
      return "Completada";
    case "hiatus":
      return "Hiatus";
    case "cancelled":
      return "Cancelada";
    default:
      return "En curso";
  }
}

function novelStatusSeverity(status: NovelStatus) {
  switch (status) {
    case "completed":
      return "info";
    case "hiatus":
      return "warn";
    case "cancelled":
      return "danger";
    default:
      return "success";
  }
}

function resolvedChapterStatus(chapter: Chapter | ChapterSummary): Chapter["status"] {
  if (chapter.status === "processing") return "processing";
  return chapter.status;
}

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

const translateOperationOptions = [
  { label: "Traducir", value: "translate" },
  { label: "Refinar", value: "refine" },
];
const eligibleChapters = computed(() => allSummaries.value.filter((chapter) => {
  const status = resolvedChapterStatus(chapter);
  if (translateOperation.value === "translate") {
    return chapter.hasOriginalContent && (status === "pending" || status === "failed");
  }
  return chapter.hasTranslatedContent && (status === "translated" || status === "failed");
}));
const cleanModeOptions = Object.entries(CLEAN_MODE_LABELS).map(([value, label]) => ({ value, label }));
const cleanModeDescription = computed(() => CLEAN_MODE_DESCRIPTIONS[cleanMode.value]);
const cleanApplyOptions = [
  { value: "translated", label: "Traducción" },
  { value: "original", label: "Original" },
  { value: "refined", label: "Refinado" },
  { value: "all", label: "Todos (prioriza refinado)" },
];
const cleanEligibleChapters = computed(() => allSummaries.value.filter((chapter) => {
  if (cleanApplyTo.value === "all") return chapter.hasOriginalContent || chapter.hasTranslatedContent || chapter.hasRefinedContent;
  if (cleanApplyTo.value === "original") return chapter.hasOriginalContent;
  if (cleanApplyTo.value === "translated") return chapter.hasTranslatedContent;
  return chapter.hasRefinedContent;
}));
const exportSourceOptions = [
  { value: "refined", label: "Refinados" },
  { value: "translated", label: "Traducidos" },
  { value: "original", label: "Originales" },
];

onMounted(() => {
  void refreshNovelAndChapterMeta();
  checkDescriptionOverflow();
});

watch(novel, (current, prev) => {
  if (!current) return;
  if (!prev || prev.id !== current.id) {
    descriptionExpanded.value = false;
  }
  nextTick(checkDescriptionOverflow);
});

function checkDescriptionOverflow() {
  const el = descriptionEl.value;
  if (!el) {
    descriptionOverflow.value = false;
    return;
  }
  if (descriptionExpanded.value) return;
  descriptionOverflow.value = el.scrollHeight > el.clientHeight + 1;
}

let resizeTimer: ReturnType<typeof setTimeout> | null = null;
function debouncedCheckOverflow() {
  if (resizeTimer) clearTimeout(resizeTimer);
  resizeTimer = setTimeout(checkDescriptionOverflow, 150);
}
window.addEventListener("resize", debouncedCheckOverflow);

function tabNeedsFullChapters(_tab: string) {
  return false;
}

function tabNeedsAllSummaries(tab: string) {
  return tab === "clean" || tab === "translate" || tab === "jobs";
}

function patchSummaryStatus(
  items: ChapterSummary[],
  chapterIds: string[],
  status: Chapter["status"],
  errorMessage = "",
) {
  if (items.length === 0 || chapterIds.length === 0) return items;
  const idSet = new Set(chapterIds);
  let mutated = false;
  const next = items.map((chapter) => {
    if (!idSet.has(chapter.id)) return chapter;
    if (chapter.status === status && (chapter.errorMessage || "") === errorMessage) return chapter;
    mutated = true;
    return { ...chapter, status, errorMessage };
  });
  return mutated ? next : items;
}

function markAllSummariesDirty() {
  allSummariesDirty.value = true;
}

function markFailedJobsDirty() {
  failedJobsDirty.value = true;
}

async function ensureFailedJobsLoaded(force = false) {
  if (!novelId.value) {
    failedJobsLoaded.value = false;
    failedJobsDirty.value = false;
    return [];
  }
  if (!force && failedJobsLoaded.value && !failedJobsDirty.value) {
    return failedJobs.value;
  }
  const items = await listFailedJobs();
  failedJobsLoaded.value = true;
  failedJobsDirty.value = false;
  return items;
}

async function loadCurrentNovel() {
  if (!novelId.value) return;
  novelLoading.value = true;
  try {
    const current = await getNovel(novelId.value);
    if (!current) {
      novel.value = null;
      return;
    }
    novel.value = current;
    replaceNovelInList(current);
  } finally {
    novelLoading.value = false;
  }
}

function shallowSummaryEquals(a: ChapterSummary, b: ChapterSummary): boolean {
  return (
    a.id === b.id &&
    a.novelId === b.novelId &&
    a.chapterOrder === b.chapterOrder &&
    a.title === b.title &&
    a.translatedTitle === b.translatedTitle &&
    a.status === b.status &&
    a.errorMessage === b.errorMessage &&
    a.hasOriginalContent === b.hasOriginalContent &&
    a.hasTranslatedContent === b.hasTranslatedContent &&
    a.hasRefinedContent === b.hasRefinedContent &&
    a.originalChars === b.originalChars &&
    a.translatedChars === b.translatedChars &&
    a.refinedChars === b.refinedChars &&
    a.createdAt === b.createdAt &&
    a.updatedAt === b.updatedAt
  );
}

function mergeChapterSummaries(fresh: ChapterSummary[]) {
  const current = chapterSummaries.value;
  if (current.length === 0) {
    chapterSummaries.value = fresh;
    return;
  }
  const currentById = new Map(current.map((item) => [item.id, item]));
  const next: ChapterSummary[] = [];
  let mutated = false;
  for (const item of fresh) {
    const existing = currentById.get(item.id);
    if (existing && shallowSummaryEquals(existing, item)) {
      next.push(existing);
    } else {
      next.push(item);
      mutated = true;
    }
  }
  if (next.length !== current.length) mutated = true;
  if (mutated) {
    chapterSummaries.value = next;
  }
}

async function loadChapterSummaries() {
  if (!novelId.value) {
    chapterSummaries.value = [];
    chapterSummaryTotal.value = 0;
    return;
  }
  chapterSummariesLoading.value = true;
  try {
    const result = await api.chapters.listSummaries(novelId.value, {
      limit: chapterPageSize,
      offset: chapterPage.value * chapterPageSize,
    });
    chapterSummaryTotal.value = result.total;
    mergeChapterSummaries(result.items);
    selectedChapters.value = selectedChapters.value.filter((selected) =>
      result.items.some((item) => item.id === selected.id),
    );
  } finally {
    chapterSummariesLoading.value = false;
  }
}

async function loadAllSummaries(force = false) {
  if (!novelId.value) {
    allSummaries.value = [];
    allSummariesLoaded.value = false;
    allSummariesDirty.value = false;
    return;
  }
  if (!force && allSummariesLoaded.value && !allSummariesDirty.value) {
    return;
  }
  allSummariesLoading.value = true;
  try {
    allSummaries.value = await api.chapters.list(novelId.value);
    allSummariesLoaded.value = true;
    allSummariesDirty.value = false;
  } finally {
    allSummariesLoading.value = false;
  }
}

async function ensureFullChaptersLoaded(force = false) {
  if (!novelId.value) return [];
  if (fullChaptersLoaded.value && !force) return chapters.value;
  const items = await listChapters();
  fullChaptersLoaded.value = true;
  return items;
}

async function refreshNovelAndChapterMeta() {
  await Promise.all([loadCurrentNovel(), loadChapterSummaries()]);
}

async function refreshChapterViews() {
  await refreshNovelAndChapterMeta();
  if (tabNeedsAllSummaries(activeTab.value)) {
    await loadAllSummaries(true);
  }
  if (fullChaptersLoaded.value || tabNeedsFullChapters(activeTab.value)) {
    await ensureFullChaptersLoaded(true);
  }
}

watch(activeTab, (tab) => {
  if (tabNeedsFullChapters(tab)) {
    void ensureFullChaptersLoaded();
  }
  if (tabNeedsAllSummaries(tab)) {
    void loadAllSummaries();
  }
  if (tab === "jobs") {
    void ensureFailedJobsLoaded();
  }
});

watch(novelId, () => {
  chapterPage.value = 0;
  fullChaptersLoaded.value = false;
  selectedChapters.value = [];
  translateSubmitting.value = false;
  allSummaries.value = [];
  allSummariesLoaded.value = false;
  allSummariesDirty.value = false;
  failedJobsLoaded.value = false;
  failedJobsDirty.value = false;
  void refreshNovelAndChapterMeta();
});

watch(chapterPage, () => {
  void loadChapterSummaries();
});

watch(eligibleChapters, (items) => {
  if (userTouchedTranslateSelection) return;
  translateSelectedIds.value = new Set(items.map((chapter) => chapter.id));
}, { immediate: true });

watch(translateOperation, () => {
  userTouchedTranslateSelection = false;
  translateSelectedIds.value = new Set(eligibleChapters.value.map((chapter) => chapter.id));
});

watch(hasActive, (active, previous) => {
  if (!previous || active || !hasProcessingChapters.value) return;
  markFailedJobsDirty();
  if (activeTab.value === "jobs") {
    void Promise.all([refreshChapterViews(), ensureFailedJobsLoaded(true)]);
    return;
  }
  void refreshChapterViews();
});

onBeforeUnmount(() => {
  if (resizeTimer) clearTimeout(resizeTimer);
  window.removeEventListener("resize", debouncedCheckOverflow);
});

async function copyCurrentNovel() {
  if (!novel.value) return;
  const copy = await api.novels.copy(novel.value.id);
  replaceNovelInList(copy);
  toast.add({ severity: 'success', summary: 'Novela copiada', life: 2500 });
  await router.push(`/novels/${copy.id}`);
}

async function toggleVisibility() {
  if (!novel.value || !isOwner.value) return;
  await api.novels.updateVisibility(novel.value.id, !novel.value.isPublic);
  novel.value = { ...novel.value, isPublic: !novel.value.isPublic };
  replaceNovelInList(novel.value);
  toast.add({ severity: 'success', summary: novel.value.isPublic ? 'Novela despublicada' : 'Novela publicada', life: 2500 });
}

async function onUrlUpdated(pending?: number) {
  fullChaptersLoaded.value = false;
  markAllSummariesDirty();
  markFailedJobsDirty();
  if (activeTab.value === "jobs") {
    await Promise.all([refreshChapterViews(), ensureFailedJobsLoaded(true)]);
  } else {
    await refreshChapterViews();
  }
  if (!pending || pending <= 0) {
    toast.add({ severity: 'success', summary: 'Novela actualizada desde internet', life: 2500 });
  }
}

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
    processing: "warn",
    translated: "success",
    refined: "info",
    done: "success",
    failed: "danger",
  }[status] as "secondary" | "info" | "warn" | "help" | "success" | "danger";
}

function charsLabel(value?: string) {
  if (!value) return "-";
  return `${value.length.toLocaleString()} chars`;
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
  }[status] as "secondary" | "info" | "warn" | "help" | "success" | "danger";
}

function jobFailedChapters(job: TranslationJob) {
  if (!job.chapterIds || job.chapterIds.length === 0) return [];
  const idSet = new Set(job.chapterIds);
  return allSummaries.value
    .filter((chapter) => idSet.has(chapter.id) && chapter.status === "failed")
    .sort((a, b) => a.chapterOrder - b.chapterOrder);
}

function toggleJobFailedChapters(jobId: string) {
  expandedJobId.value = expandedJobId.value === jobId ? null : jobId;
}

function openCreateChapter() {
  editingChapter.value = null;
  chapterDraft.id = undefined;
  chapterDraft.chapterOrder = nextChapterOrder.value;
  chapterDraft.title = "";
  chapterDraft.originalContent = "";
  chapterDialogOpen.value = true;
}

async function saveChapter() {
  chapterSaving.value = true;
  try {
    if (editingChapter.value) {
      await updateChapter({
        id: editingChapter.value.id,
        chapterOrder: chapterDraft.chapterOrder,
        title: chapterDraft.title,
        originalContent: chapterDraft.originalContent || undefined,
      });
    } else {
      await createChapter({
        chapterOrder: chapterDraft.chapterOrder,
        title: chapterDraft.title,
        originalContent: chapterDraft.originalContent || undefined,
        status: "pending",
      });
    }
    markAllSummariesDirty();
    chapterDialogOpen.value = false;
    await refreshChapterViews();
  } catch (err) {
    toast.add({ severity: "error", summary: "Error al guardar capítulo", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  } finally {
    chapterSaving.value = false;
  }
}

async function confirmDeleteChapter() {
  const id = pendingDeleteChapterId.value;
  if (!id) return;
  deletingChapter.value = true;
  try {
    await deleteChapter(id);
    markAllSummariesDirty();
    await refreshChapterViews();
  } catch (err) {
    toast.add({ severity: "error", summary: "Error al eliminar capítulo", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  } finally {
    deletingChapter.value = false;
    pendingDeleteChapterId.value = null;
    confirmDeletePopover.value?.hide();
  }
}

function onDeleteChapter({ event, chapter }: { event: Event; chapter: ChapterSummary }) {
  pendingDeleteChapterId.value = chapter.id;
  confirmDeletePopover.value?.show(event);
}

function askDeleteChapter(event: Event, id: string) {
  pendingDeleteChapterId.value = id;
  confirmDeletePopover.value?.show(event);
}

function cancelDeleteChapter() {
  pendingDeleteChapterId.value = null;
  confirmDeletePopover.value?.hide();
}

function onBulkDeleteChapters(event: Event) {
  if (selectedChapters.value.length <= 1) return;
  bulkDeletePopover.value?.show(event);
}

function askBulkDeleteChapters(event: Event) {
  if (selectedChapters.value.length <= 1) return;
  bulkDeletePopover.value?.show(event);
}

function cancelBulkDeleteChapters() {
  bulkDeletePopover.value?.hide();
}

async function confirmBulkDeleteChapters() {
  const ids = selectedChapters.value.map((chapter) => chapter.id);
  if (ids.length === 0) {
    bulkDeletePopover.value?.hide();
    return;
  }
  bulkDeleting.value = true;
  try {
    const { deleted, requested } = await bulkDeleteChapters(ids);
    markAllSummariesDirty();
    await refreshChapterViews();
    selectedChapters.value = [];
    bulkDeletePopover.value?.hide();
    if (deleted === requested) {
      toast.add({
        severity: "success",
        summary: "Capítulos eliminados",
        detail: `${deleted} ${deleted === 1 ? "capítulo eliminado" : "capítulos eliminados"}.`,
        life: 3000,
      });
    } else {
      toast.add({
        severity: "warn",
        summary: "Eliminación parcial",
        detail: `${deleted} de ${requested} capítulos eliminados.`,
        life: 4500,
      });
    }
  } catch (err) {
    toast.add({ severity: "error", summary: "Error al eliminar capítulos", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  } finally {
    bulkDeleting.value = false;
  }
}

async function handleBulkImport(inputs: ChapterUpsertInput[]) {
  try {
    await bulkCreateChapters(inputs);
    markAllSummariesDirty();
    await refreshChapterViews();
  } catch (err) {
    toast.add({ severity: "error", summary: "Error en importación masiva", detail: err instanceof Error ? err.message : String(err), life: 4000 });
    throw err;
  }
}

async function previewEpub(input: { file: Blob; fileName: string }) {
  return api.epubs.preview(input.file, input.fileName);
}

async function handleImportedEpubFiles(files: File[]) {
  if (!novel.value) return;
  for (const file of files) {
    await api.epubs.save({
      novelId: novel.value.id,
      fileKind: "original",
      sourceVariant: "original",
      fileName: file.name,
      blob: file,
    });
  }
}

async function saveProjectSettings(patch: Partial<CreateNovelInput>) {
  if (!novel.value) return;
  try {
    const updated = await updateNovel(novel.value.id, patch);
    novel.value = updated;
    toast.add({ severity: "success", summary: "Proyecto actualizado", life: 2500 });
  } catch (err) {
    toast.add({ severity: "error", summary: "Error al guardar configuración", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  }
}

function onCoverUpdated(updated: Novel) {
  novel.value = updated;
  replaceNovelInList(updated);
}

function toggleTranslateChapter(id: string, checked: boolean) {
  userTouchedTranslateSelection = true;
  const next = new Set(translateSelectedIds.value);
  if (checked) next.add(id); else next.delete(id);
  translateSelectedIds.value = next;
}

async function startTranslationJob() {
  if (!novel.value) return;
  const target = allSummaries.value.filter((chapter) => translateSelectedIds.value.has(chapter.id));
  if (target.length === 0) return;
  translateSubmitting.value = true;
  try {
    const targetIds = target.map((chapter) => chapter.id);
    await createJob(targetIds, {
      operation: translateOperation.value,
      provider: novel.value.aiOptions.provider || undefined,
      model: novel.value.aiOptions.model || undefined,
    });
    allSummaries.value = patchSummaryStatus(allSummaries.value, targetIds, "processing");
    chapterSummaries.value = patchSummaryStatus(chapterSummaries.value, targetIds, "processing");
    translateSelectedIds.value = new Set(
      Array.from(translateSelectedIds.value).filter((id) => !targetIds.includes(id)),
    );
    markFailedJobsDirty();
  } catch (err) {
    toast.add({ severity: "error", summary: "Error al iniciar trabajo", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  } finally {
    translateSubmitting.value = false;
  }
}

async function previewCleaning(chapter: ChapterSummary) {
  try {
    const res = await api.chapters.cleanPreview(novelId.value, {
      chapterId: chapter.id,
      mode: cleanMode.value,
      searchText: cleanSearchText.value,
      replaceText: cleanReplaceText.value,
      caseSensitive: cleanCaseSensitive.value,
      useRegex: cleanUseRegex.value,
      applyTo: cleanApplyTo.value,
    });
    cleanPreview.value = { chapterTitle: res.chapterTitle, result: res };
  } catch (err) {
    toast.add({ severity: "error", summary: "Error al previsualizar", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  }
}

function toggleCleanChapter(id: string, checked: boolean) {
  const next = new Set(cleanSelectedIds.value);
  if (checked) next.add(id); else next.delete(id);
  cleanSelectedIds.value = next;
}

async function applyCleaningToSelected() {
  cleanApplying.value = true;
  cleanFeedback.value = null;
  try {
    const chapterIds = Array.from(cleanSelectedIds.value);
    const result = await api.chapters.clean(novelId.value, {
      chapterIds,
      mode: cleanMode.value,
      searchText: cleanSearchText.value,
      replaceText: cleanReplaceText.value,
      caseSensitive: cleanCaseSensitive.value,
      useRegex: cleanUseRegex.value,
      applyTo: cleanApplyTo.value,
    });
    markAllSummariesDirty();
    await Promise.all([loadAllSummaries(true), loadChapterSummaries()]);
    cleanFeedback.value = `Limpieza aplicada a ${result.modified} capítulos.`;
    const issues: string[] = [];
    if (result.skipped) issues.push(`${result.skipped} sin contenido aplicable`);
    if (result.notFound) issues.push(`${result.notFound} no encontrados`);
    if (result.failed) issues.push(`${result.failed} fallaron al guardar`);
    if (issues.length > 0) {
      toast.add({ severity: "warn", summary: issues.join(", ") + ".", life: 5000 });
    }
  } catch (err) {
    cleanFeedback.value = null;
    toast.add({ severity: "error", summary: "Error al aplicar limpieza", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  } finally {
    cleanApplying.value = false;
  }
}

async function buildAndDownloadEpub() {
  if (!novel.value) return;
  exportBuilding.value = true;
  exportFeedback.value = null;
  exportProgress.value = 10;
  try {
    const result = await api.epubs.build({
      novelId: novel.value.id,
      source: exportSource.value,
    });
    exportProgress.value = 80;
    const blob = await api.epubs.download(result.id, result.updatedAt);
    const fileName = result.fileName || `${novel.value.sourceTitle || "libro"}.epub`;
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(anchor.href);
    exportProgress.value = 100;
    exportFeedback.value = `EPUB generado y guardado en el servidor.`;
  } catch (err) {
    exportFeedback.value = `Error: ${err instanceof Error ? err.message : String(err)}`;
  } finally {
    exportBuilding.value = false;
    window.setTimeout(() => {
      exportProgress.value = 0;
    }, 1500);
  }
}

async function cancelFailedHistoryJob(jobId: string) {
  try {
    await updateJob(jobId, { status: "cancelled" });
    markFailedJobsDirty();
    await ensureFailedJobsLoaded(true);
  } catch (err) {
    toast.add({ severity: "error", summary: "Error al cancelar trabajo", detail: err instanceof Error ? err.message : String(err), life: 4000 });
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}
</script>

<style scoped>
.novel-detail-layout {
  display: grid;
  grid-template-columns: minmax(150px, 200px) minmax(0, 1fr);
  gap: 1.5rem;
  align-items: start;
}

.novel-sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.novel-cover-large {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--divide);
  background: var(--surface-muted);
}

.novel-cover-large img {
  width: 100%;
  height: auto;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  display: block;
}

.novel-cover-placeholder-large {
  width: 100%;
  aspect-ratio: 2 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  font-size: 2.5rem;
}

.novel-sidebar-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.novel-sidebar-actions :deep(.p-button) {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.novel-sidebar-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.novel-sidebar-tags :deep(.p-tag) {
  font-size: 0.75rem;
}

.novel-main {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}

.novel-main-header {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.novel-title {
  margin: 0;
  font-size: 1.625rem;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.novel-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.875rem;
  font-size: 0.875rem;
}

.novel-description-wrapper {
  margin: 0.375rem 0 0;
  position: relative;
}

.novel-description {
  font-size: 0.875rem;
  line-height: 1.3;
}

.novel-description--collapsed {
  max-height: calc(0.875rem * 1.3 * 5);
  overflow: hidden;
  mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
}

.novel-description :deep(p) {
  margin: 0 0 0.5rem;
}

.novel-description :deep(p:last-child) {
  margin-bottom: 0;
}

.novel-description-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: none;
  border: none;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0.2rem 0;
  transition: color 0.15s ease;
}

.novel-description-toggle:hover {
  color: var(--foreground);
}

.novel-description-toggle i {
  font-size: 0.7rem;
}

.novel-description-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  margin-top: 0.375rem;
}

.novel-description-tags :deep(.p-tag) {
  font-size: 0.75rem;
}

.novel-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.125rem;
  padding: 0.2rem;
  background: var(--surface-muted);
  border: 1px solid var(--divide);
  border-radius: var(--radius-md);
  width: fit-content;
  max-width: 100%;
}

.novel-tab {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 500;
  padding: 0.4rem 0.7rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.novel-tab:hover {
  color: var(--foreground);
  background: var(--mock-row);
}

.novel-tab--active {
  background: var(--surface-elevated);
  color: var(--foreground);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.tab-panel {
  content-visibility: auto;
  contain-intrinsic-size: auto 400px;
}

.novel-series {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--text-secondary);
}

.novel-series i {
  font-size: 0.8rem;
  color: var(--accent-link);
}

.job-failed-chapters {
  border: 1px solid var(--divide);
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  background: color-mix(in oklab, var(--text-primary) 4%, transparent);
}

.job-failed-chapter-item {
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--divide);
}

.job-failed-chapter-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.job-failed-chapter-error {
  margin-top: 0.35rem;
  padding: 0.5rem 0.65rem;
  background: color-mix(in oklab, #dc2626 10%, transparent);
  border-left: 3px solid #dc2626;
  border-radius: var(--radius-sm);
  color: #7f1d1d;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .novel-detail-layout {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .novel-sidebar {
    display: grid;
    grid-template-columns: 100px 1fr;
    gap: 0.75rem;
    align-items: start;
  }

  .novel-cover-large {
    max-width: 100px;
  }

  .novel-sidebar-actions {
    gap: 0.375rem;
  }

  .novel-sidebar-actions :deep(.p-button) {
    font-size: 0.8rem;
    padding: 0.4rem 0.6rem;
    min-height: 40px;
  }

  .novel-sidebar-tags {
    grid-column: 1 / -1;
  }

  .novel-title {
    font-size: 1.375rem;
  }

  .novel-description {
    font-size: 0.8125rem;
  }

  .novel-tabs {
    width: 100%;
  }

  .novel-tab {
    flex: 1 1 auto;
    text-align: center;
    padding: 0.35rem 0.5rem;
    font-size: 0.8rem;
  }
}
</style>
