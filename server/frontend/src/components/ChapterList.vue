<template>
  <div class="chapter-list">
    <div class="chapter-list-toolbar">
      <div class="chapter-list-selection">
        <Button size="small" severity="secondary" text label="Todos" @click="selectAll" />
        <Button size="small" severity="secondary" text label="Ninguno" @click="clearSelection" />
        <span v-if="selected.length > 0" class="small muted">{{ selected.length }} seleccionados</span>
      </div>
      <div v-if="isOwner" class="chapter-list-actions">
        <Button
          v-if="selected.length > 1"
          icon="pi pi-trash"
          :label="`Eliminar ${selected.length}`"
          severity="danger"
          outlined
          size="small"
          @click="emit('bulk-delete', $event)"
        />
        <Button icon="pi pi-upload" label="Importar" severity="secondary" outlined size="small" @click="emit('import')" />
        <Button icon="pi pi-plus" label="Nuevo" size="small" @click="emit('create')" />
      </div>
    </div>

    <Card v-if="loading && chapters.length === 0">
      <template #content>
        <div class="chapter-list-skeleton">
          <div v-for="i in 8" :key="i" class="chapter-list-item chapter-list-item--skeleton">
            <Skeleton shape="rectangle" width="1.25rem" height="1.25rem" borderRadius="4px" />
            <Skeleton width="2rem" height="0.875rem" borderRadius="4px" />
            <Skeleton width="55%" height="1rem" borderRadius="4px" />
            <Skeleton width="5rem" height="1.25rem" borderRadius="999px" />
          </div>
        </div>
      </template>
    </Card>

    <Card v-else-if="chapters.length === 0 && total === 0">
      <template #content>
        <div class="empty-state">
          <div class="empty-state-icon">
            <i class="pi pi-file" aria-hidden="true" />
          </div>
          <div>
            <h2 class="empty-state-title">Sin capítulos</h2>
            <p class="muted empty-state-body">Crea un capítulo manualmente o importa desde EPUB/TXT/Markdown.</p>
          </div>
          <div v-if="isOwner" class="empty-state-actions">
            <Button icon="pi pi-plus" label="Nuevo capítulo" @click="emit('create')" />
            <Button icon="pi pi-upload" label="Importar" severity="secondary" outlined @click="emit('import')" />
          </div>
        </div>
      </template>
    </Card>

    <div v-else class="chapter-list-items">
      <article
        v-for="chapter in chapters"
        :key="chapter.id"
        class="chapter-list-item"
        :class="{ 'chapter-list-item--selected': isSelected(chapter) }"
      >
        <Checkbox
          v-if="isOwner"
          :model-value="isSelected(chapter)"
          binary
          class="chapter-list-checkbox"
          :aria-label="`Seleccionar capítulo ${chapter.chapterOrder}`"
          @update:model-value="toggleSelected(chapter, $event)"
        />

        <RouterLink
          :to="`/novels/${chapter.novelId}/chapters/${chapter.id}`"
          class="chapter-list-link"
          :aria-label="`Editar capítulo ${chapter.chapterOrder}: ${chapter.title}`"
        >
          <span class="chapter-list-order mono small muted">#{{ String(chapter.chapterOrder).padStart(2, "0") }}</span>
          <span class="chapter-list-title line-clamp-2">{{ chapter.title }}</span>
        </RouterLink>

        <Tag
          :severity="chapterSeverity(resolvedStatus(chapter))"
          :value="chapterStatusLabel(resolvedStatus(chapter))"
          class="chapter-list-status"
        />

        <div v-if="isOwner" class="chapter-list-item-actions">
          <Button
            icon="pi pi-trash"
            text
            class="chapter-list-action-btn chapter-list-action-btn--delete touch-target"
            aria-label="Eliminar"
            @click="emit('delete', { event: $event, chapter })"
          />
        </div>
      </article>
    </div>

    <div class="chapter-list-footer">
      <span class="small muted">
        Mostrando {{ total === 0 ? 0 : page * pageSize + 1 }}-{{ Math.min((page + 1) * pageSize, total) }} de {{ total }} capítulos
      </span>
      <div class="chapter-list-pagination">
        <Button
          size="small"
          severity="secondary"
          text
          label="Anterior"
          :disabled="page === 0 || loading"
          @click="emit('update:page', page - 1)"
        />
        <Button
          size="small"
          severity="secondary"
          text
          label="Siguiente"
          :disabled="(page + 1) * pageSize >= total || loading"
          @click="emit('update:page', page + 1)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import Button from "primevue/button";
import Card from "primevue/card";
import Checkbox from "primevue/checkbox";
import Skeleton from "primevue/skeleton";
import Tag from "primevue/tag";
import type { ChapterSummary } from "@/api/types";
import type { Chapter } from "@/domain";

const props = defineProps<{
  chapters: ChapterSummary[];
  total: number;
  loading: boolean;
  page: number;
  pageSize: number;
  selected: ChapterSummary[];
  isOwner: boolean;
}>();

const emit = defineEmits<{
  (e: "update:page", page: number): void;
  (e: "update:selected", selected: ChapterSummary[]): void;
  (e: "delete", payload: { event: Event; chapter: ChapterSummary }): void;
  (e: "bulk-delete", event: Event): void;
  (e: "create"): void;
  (e: "import"): void;
}>();

const selectedIds = computed(() => new Set(props.selected.map((item) => item.id)));

function resolvedStatus(chapter: ChapterSummary): Chapter["status"] {
  if (chapter.status === "processing") {
    return "processing";
  }
  return chapter.status;
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

function isSelected(chapter: ChapterSummary) {
  return selectedIds.value.has(chapter.id);
}

function toggleSelected(chapter: ChapterSummary, checked: boolean) {
  const next = new Set(selectedIds.value);
  if (checked) next.add(chapter.id);
  else next.delete(chapter.id);
  emit("update:selected", props.chapters.filter((item) => next.has(item.id)));
}

function selectAll() {
  emit("update:selected", [...props.chapters]);
}

function clearSelection() {
  emit("update:selected", []);
}
</script>

<style scoped>
.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.chapter-list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.chapter-list-selection {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.chapter-list-actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.chapter-list-items {
  border: 1px solid var(--divide);
  border-radius: var(--radius-md);
  background: var(--surface-base);
  overflow: hidden;
}

.chapter-list-item {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.5rem;
  border-bottom: 1px solid var(--divide);
  transition: background 0.12s ease;
  font-size: 0.875rem;
}

.chapter-list-item:last-child {
  border-bottom: none;
}

.chapter-list-item:hover,
.chapter-list-item--selected {
  background: var(--mock-row);
}

.chapter-list-item--skeleton {
  grid-template-columns: auto auto 1fr auto;
}

.chapter-list-link {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  min-width: 0;
  color: var(--foreground);
  border-radius: var(--radius-sm);
}

.chapter-list-link:hover {
  color: var(--accent-link);
}

.chapter-list-order {
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
  width: 1.75rem;
  font-size: 0.8125rem;
}

.chapter-list-title {
  font-weight: 500;
  min-width: 0;
}

.chapter-list-status {
  flex-shrink: 0;
  font-size: 0.6875rem;
}

.chapter-list-status :deep(.p-tag) {
  padding: 0.125rem 0.35rem;
}

.chapter-list-status :deep(.p-tag-value) {
  padding: 0;
}

.chapter-list-item-actions {
  display: flex;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
}

.chapter-list-action-btn :deep(.p-button) {
  width: 1.625rem;
  height: 1.625rem;
  padding: 0;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.chapter-list-action-btn :deep(.p-button-icon) {
  font-size: 0.85rem;
}

.chapter-list-action-btn--delete :deep(.p-button) {
  color: var(--p-red-500) !important;
}

.chapter-list-action-btn--delete :deep(.p-button:hover) {
  background: color-mix(in oklab, var(--p-red-500) 10%, transparent) !important;
}

.chapter-list-checkbox :deep(.p-checkbox-box) {
  width: 1.125rem;
  height: 1.125rem;
}

.chapter-list-checkbox :deep(.p-checkbox-icon) {
  font-size: 0.7rem;
}

.chapter-list-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding-top: 0.25rem;
}

.chapter-list-pagination {
  display: flex;
  align-items: center;
  gap: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.75rem;
  padding: 1.5rem 1rem;
}

.empty-state-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: var(--radius-md);
  background: var(--surface-muted);
  color: var(--text-secondary);
  font-size: 1rem;
}

.empty-state-title {
  margin: 0 0 0.25rem;
  font-size: 1rem;
}

.empty-state-body {
  margin: 0;
  max-width: 48ch;
  font-size: 0.875rem;
}

.empty-state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
}

@media (max-width: 640px) {
  .chapter-list-item {
    grid-template-columns: auto 1fr auto;
    gap: 0.5rem;
    padding: 0.5rem;
  }

  .chapter-list-status {
    grid-column: 3;
    grid-row: 1;
  }

  .chapter-list-item-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }

  .chapter-list-link {
    flex-direction: row;
    align-items: center;
    gap: 0.375rem;
    min-width: 0;
  }

  .chapter-list-order {
    display: none;
  }

  .chapter-list-title {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
