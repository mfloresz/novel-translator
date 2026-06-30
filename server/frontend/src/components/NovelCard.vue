<template>
  <article class="library-card" role="listitem">
    <RouterLink
      :to="`/novels/${novel.id}/read`"
      class="library-cover-link"
      :aria-label="`Leer ${getNovelDisplayTitle(novel)}`"
    >
      <div class="library-cover">
        <img
          v-if="novel.coverPath"
          :src="novel.coverPath"
          :alt="`Portada de ${getNovelDisplayTitle(novel)}`"
          loading="lazy"
        />
        <div v-else class="library-cover-placeholder">
          <i class="pi pi-image" aria-hidden="true" />
        </div>
      </div>
    </RouterLink>

    <div class="library-meta">
      <RouterLink
        :to="`/novels/${novel.id}/read`"
        class="library-title line-clamp-2"
        :title="getNovelDisplayTitle(novel)"
      >
        {{ getNovelDisplayTitle(novel) }}
      </RouterLink>
      <div class="library-subtitle small muted">
        <span v-if="getNovelDisplaySeries(novel)" class="novel-series-badge">
          {{ getNovelDisplaySeries(novel) }}<template v-if="getNovelDisplayNumber(novel)"> #{{ getNovelDisplayNumber(novel) }}</template>
        </span>
      </div>
    </div>

    <Button
      icon="pi pi-ellipsis-v"
      severity="secondary"
      text
      rounded
      class="library-menu-btn touch-target"
      :aria-label="`Opciones de ${getNovelDisplayTitle(novel)}`"
      @click="$emit('menu-click', $event)"
    />
  </article>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import Button from "primevue/button";
import { getNovelDisplayTitle, getNovelDisplaySeries, getNovelDisplayNumber, type Novel } from "@/domain";

defineProps<{
  novel: Novel;
}>();

defineEmits<{
  (e: "menu-click", event: Event): void;
}>();
</script>

<style scoped>
.library-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.library-cover-link {
  display: block;
  border-radius: var(--radius-md);
}

.library-cover-link:focus-visible {
  outline-offset: 2px;
}

.library-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--divide);
  background: var(--surface-muted);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.library-cover-link:hover .library-cover,
.library-cover-link:focus-visible .library-cover {
  transform: translateY(-3px);
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.14);
}

.library-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.library-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  color: var(--text-tertiary);
}

.library-meta {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.375rem 0.125rem 0;
  min-width: 0;
}

.library-title {
  font-weight: 600;
  font-size: 0.8125rem;
  line-height: 1.3;
  color: var(--foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.library-title:hover {
  color: var(--accent-link);
}

.library-subtitle {
  display: flex;
  align-items: center;
}

.library-menu-btn {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  z-index: 1;
  background: color-mix(in oklab, var(--surface-elevated) 88%, transparent);
  backdrop-filter: blur(6px);
  color: var(--foreground);
  opacity: 0;
  transition: opacity 0.15s ease;
}

.library-card:hover .library-menu-btn,
.library-card:focus-within .library-menu-btn,
.library-menu-btn:focus-visible {
  opacity: 1;
}

.novel-series-badge {
  display: inline-block;
  background: var(--surface-muted);
  padding: 0.0625rem 0.375rem;
  border-radius: var(--radius-sm);
  font-size: 0.6875rem;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  line-height: 1.4;
}

@media (max-width: 640px) {
  .library-menu-btn {
    opacity: 1;
  }

  .library-title {
    font-size: 0.75rem;
  }

  .library-meta {
    padding: 0.25rem 0 0;
    gap: 0.0625rem;
  }

  .novel-series-badge {
    font-size: 0.625rem;
    padding: 0 0.25rem;
  }
}
</style>
