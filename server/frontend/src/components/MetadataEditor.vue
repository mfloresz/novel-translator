<template>
  <div class="stack-md">
    <div v-if="coverEditable" class="cover-editor">
      <label class="small muted">Portada</label>
      <div class="cover-preview">
        <img v-if="displayCoverUrl" :src="displayCoverUrl" alt="Portada actual" />
        <div v-else class="cover-placeholder">
          <i class="pi pi-image" />
        </div>
      </div>
      <div class="row-wrap" style="margin-top: 0.5rem">
        <Button severity="secondary" outlined size="small" @click="triggerFileInput">
          {{ displayCoverUrl ? 'Cambiar portada' : 'Subir portada' }}
        </Button>
        <Button v-if="displayCoverUrl" severity="danger" outlined size="small" @click="removeCover">
          Eliminar
        </Button>
      </div>
      <input ref="fileInputRef" type="file" accept="image/*" hidden @change="onFileSelected" />
    </div>

    <div class="row-wrap">
      <div class="form-group" style="flex: 1; min-width: 180px">
        <label class="small muted">Título</label>
        <InputText :model-value="metadataTitle" fluid @update:model-value="emit('update:metadataTitle', String($event || ''))" />
      </div>
      <div class="form-group" style="flex: 1; min-width: 180px">
        <label class="small muted">Autor</label>
        <InputText :model-value="metadataAuthor" fluid @update:model-value="emit('update:metadataAuthor', String($event || ''))" />
      </div>
    </div>

    <div class="row-wrap">
      <div class="form-group" style="flex: 1; min-width: 180px; position: relative">
        <label class="small muted">Serie</label>
        <InputText
          ref="seriesInputRef"
          :model-value="metadataSeries"
          fluid
          placeholder="Nombre de la serie"
          @update:model-value="onSeriesInput"
          @focus="showSeriesSuggestions = true"
          @keydown.esc="showSeriesSuggestions = false"
          @blur="onSeriesBlur"
        />
        <div v-if="showSeriesSuggestionList" class="series-suggestions">
          <button
            v-for="suggestion in filteredSeriesSuggestions"
            :key="suggestion"
            type="button"
            class="series-suggestion-item"
            @mousedown.prevent="selectSeries(suggestion)"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>
      <div class="form-group" style="flex: 1; min-width: 180px">
        <label class="small muted">Número</label>
        <InputText :model-value="metadataNumber" fluid @update:model-value="emit('update:metadataNumber', String($event || ''))" />
      </div>
    </div>

    <div class="form-group">
      <label class="small muted">Descripción</label>
      <Textarea :model-value="metadataDescription" rows="4" fluid @update:model-value="emit('update:metadataDescription', String($event || ''))" />
    </div>

    <template v-if="showNovelMeta">
      <div class="form-group" style="max-width: 220px">
        <label class="small muted">Estatus</label>
        <Select
          :model-value="resolvedStatus"
          :options="statusOptions"
          optionLabel="label"
          optionValue="value"
          fluid
          @update:model-value="onStatusChange"
        />
      </div>

      <div class="tag-editor-section">
        <label class="small muted">Etiquetas</label>
        <div class="tag-editor" @click="focusTagInput">
          <div v-for="tag in resolvedTags" :key="tag" class="tag-chip">
            <span>{{ tag }}</span>
            <button type="button" class="tag-chip-remove" aria-label="Eliminar etiqueta" @click.stop="removeTag(tag)">
              <i class="pi pi-times" />
            </button>
          </div>
          <input
            ref="tagInputRef"
            v-model="tagInput"
            type="text"
            class="tag-input"
            placeholder="Escribe una etiqueta y presiona Enter"
            @focus="showSuggestions = true"
            @input="showSuggestions = true"
            @keydown.enter.prevent="addTagFromInput"
            @keydown.backspace="onTagBackspace"
            @keydown.esc="showSuggestions = false"
            @blur="onTagInputBlur"
          />
        </div>
        <div v-if="showSuggestionList" class="tag-suggestions">
          <button
            v-for="suggestion in filteredTagSuggestions"
            :key="suggestion"
            type="button"
            class="tag-suggestion-item"
            @mousedown.prevent="selectSuggestedTag(suggestion)"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>
    </template>

    <div v-if="novelId && isOwner" class="row-wrap" style="justify-content: flex-end; padding-top: 0.5rem; border-top: 1px solid var(--p-content-border-color)">
      <Button icon="pi pi-trash" label="Eliminar novela" severity="danger" outlined size="small" @click="confirmDelete" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import Select from 'primevue/select';
import { useConfirm } from 'primevue/useconfirm';
import type { NovelStatus } from '@/domain';

const confirm = useConfirm();

const statusOptions: Array<{ label: string; value: NovelStatus }> = [
  { label: 'En curso', value: 'ongoing' },
  { label: 'Completada', value: 'completed' },
  { label: 'Hiatus', value: 'hiatus' },
  { label: 'Cancelada', value: 'cancelled' },
];

const props = defineProps<{
  metadataTitle: string;
  metadataAuthor: string;
  metadataDescription: string;
  metadataSeries: string;
  metadataNumber: string;
  status?: NovelStatus;
  tags?: string[];
  tagSuggestions?: string[];
  seriesSuggestions?: string[];
  showNovelMeta?: boolean;
  coverPath?: string;
  coverEditable?: boolean;
  novelId?: string;
  isOwner?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:metadataTitle', value: string): void;
  (e: 'update:metadataAuthor', value: string): void;
  (e: 'update:metadataDescription', value: string): void;
  (e: 'update:metadataSeries', value: string): void;
  (e: 'update:metadataNumber', value: string): void;
  (e: 'update:status', value: NovelStatus): void;
  (e: 'update:tags', value: string[]): void;
  (e: 'selectCover', file: File): void;
  (e: 'removeCover'): void;
  (e: 'delete'): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const tagInputRef = ref<HTMLInputElement | null>(null);
const localCoverUrl = ref<string | undefined>();
const tagInput = ref('');
const showSuggestions = ref(false);
const seriesInputRef = ref<any>(null);
const showSeriesSuggestions = ref(false);

const displayCoverUrl = computed(() => localCoverUrl.value || props.coverPath);
const resolvedStatus = computed<NovelStatus>(() => props.status ?? 'ongoing');
const resolvedTags = computed(() => Array.isArray(props.tags) ? props.tags : []);

const filteredTagSuggestions = computed(() => {
  const query = tagInput.value.trim().toLowerCase();
  const selected = new Set(resolvedTags.value.map((tag) => tag.toLowerCase()));
  const available = (props.tagSuggestions ?? []).filter((tag) => !selected.has(tag.toLowerCase()));
  if (!query) return available.slice(0, 8);
  const startsWith = available.filter((tag) => tag.toLowerCase().startsWith(query));
  const contains = available.filter((tag) => !tag.toLowerCase().startsWith(query) && tag.toLowerCase().includes(query));
  return [...startsWith, ...contains].slice(0, 8);
});

const showSuggestionList = computed(() => showSuggestions.value && filteredTagSuggestions.value.length > 0);

const filteredSeriesSuggestions = computed(() => {
  const query = props.metadataSeries.trim().toLowerCase();
  const available = props.seriesSuggestions ?? [];
  if (!query) return available.slice(0, 8);
  const startsWith = available.filter((s) => s.toLowerCase().startsWith(query));
  const contains = available.filter((s) => !s.toLowerCase().startsWith(query) && s.toLowerCase().includes(query));
  return [...startsWith, ...contains].slice(0, 8);
});

const showSeriesSuggestionList = computed(() => showSeriesSuggestions.value && filteredSeriesSuggestions.value.length > 0);

watch(() => props.coverPath, () => {
  localCoverUrl.value = undefined;
});

function triggerFileInput() {
  fileInputRef.value?.click();
}

function onFileSelected(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  localCoverUrl.value = URL.createObjectURL(file);
  emit('selectCover', file);
}

function removeCover() {
  if (localCoverUrl.value) {
    URL.revokeObjectURL(localCoverUrl.value);
  }
  localCoverUrl.value = undefined;
  emit('removeCover');
}

function onStatusChange(value: NovelStatus | null | undefined) {
  emit('update:status', value ?? 'ongoing');
}

function normalizeTag(raw: string) {
  const cleaned = raw.trim().replace(/\s+/g, ' ');
  if (!cleaned) return '';

  const existing = [...resolvedTags.value, ...(props.tagSuggestions ?? [])].find(
    (tag) => tag.toLowerCase() === cleaned.toLowerCase(),
  );

  return existing ?? cleaned;
}

function addTag(tag: string) {
  const normalized = normalizeTag(tag);
  if (!normalized) return;
  if (resolvedTags.value.some((current) => current.toLowerCase() === normalized.toLowerCase())) {
    tagInput.value = '';
    showSuggestions.value = false;
    return;
  }
  emit('update:tags', [...resolvedTags.value, normalized]);
  tagInput.value = '';
  showSuggestions.value = false;
}

function addTagFromInput() {
  addTag(tagInput.value);
}

function selectSuggestedTag(tag: string) {
  addTag(tag);
  focusTagInput();
}

function removeTag(tag: string) {
  emit('update:tags', resolvedTags.value.filter((current) => current !== tag));
}

function onTagBackspace() {
  if (tagInput.value.trim() || resolvedTags.value.length === 0) return;
  emit('update:tags', resolvedTags.value.slice(0, -1));
}

function focusTagInput() {
  tagInputRef.value?.focus();
}

function onTagInputBlur() {
  window.setTimeout(() => {
    showSuggestions.value = false;
  }, 120);
}

function onSeriesInput(value: string | undefined) {
  emit('update:metadataSeries', value ?? '');
  showSeriesSuggestions.value = true;
}

function selectSeries(value: string) {
  emit('update:metadataSeries', value);
  showSeriesSuggestions.value = false;
  nextTick(() => {
    const el = seriesInputRef.value?.$el;
    const input: HTMLElement | null = el?.tagName === 'INPUT' ? el : el?.querySelector('input') ?? null;
    input?.focus();
  });
}

function onSeriesBlur() {
  window.setTimeout(() => {
    showSeriesSuggestions.value = false;
  }, 120);
}

function confirmDelete() {
  confirm.require({
    message: '¿Eliminar esta novela y todos sus capítulos?',
    header: 'Confirmar eliminación',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Cancelar',
    acceptLabel: 'Eliminar',
    acceptClass: 'p-button-danger',
    accept: () => emit('delete'),
  });
}
</script>

<style scoped>
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}
.cover-editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.cover-preview {
  width: 140px;
  height: 200px;
  aspect-ratio: 2 / 3;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--divide);
  background: var(--surface-muted);
  display: flex;
  align-items: center;
  justify-content: center;
}
.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.cover-placeholder {
  font-size: 2rem;
  color: var(--text-secondary);
}
.tag-editor-section {
  position: relative;
}
.tag-editor {
  min-height: 2.75rem;
  border: 1px solid var(--divide);
  border-radius: var(--radius-md);
  padding: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  background: var(--surface-base);
  cursor: text;
}
.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border-radius: var(--radius-pill);
  padding: 0.35rem 0.7rem;
  background: var(--btn-primary-bg);
  color: var(--btn-primary-fg);
  font-size: 0.875rem;
  line-height: 1;
}
.tag-chip-remove {
  border: 0;
  background: transparent;
  color: inherit;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  opacity: 0.8;
  transition: opacity 0.15s ease-out;
}
.tag-chip-remove:hover {
  opacity: 1;
}
.tag-input {
  flex: 1;
  min-width: 180px;
  border: 0;
  outline: none;
  background: transparent;
  color: inherit;
  font: inherit;
  padding: 0.25rem 0;
}
.tag-suggestions,
.series-suggestions {
  position: absolute;
  top: calc(100% + 0.35rem);
  left: 0;
  right: 0;
  z-index: 20;
  border: 1px solid var(--divide);
  border-radius: var(--radius-md);
  background: var(--surface-base);
  box-shadow: 0 4px 12px color-mix(in oklab, var(--text-primary) 10%, transparent);
  overflow: hidden;
}
.tag-suggestion-item,
.series-suggestion-item {
  width: 100%;
  border: 0;
  background: transparent;
  text-align: left;
  padding: 0.75rem 0.9rem;
  cursor: pointer;
  color: inherit;
  font: inherit;
  transition: background 0.15s ease-out;
}
.tag-suggestion-item:hover,
.series-suggestion-item:hover {
  background: var(--mock-row);
}
</style>
