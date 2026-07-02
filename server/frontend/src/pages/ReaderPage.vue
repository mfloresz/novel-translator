<template>
  <div class="reader-shell">
    <div id="progress-bar" class="reader-progress-track" role="progressbar" :aria-valuenow="Math.round(progress)" aria-valuemin="0" aria-valuemax="100">
      <div class="reader-progress-bar" :style="{ width: `${progress}%` }" />
    </div>

    <header class="reader-header">
      <div class="reader-header-left">
        <Button
          icon="pi pi-arrow-left"
          severity="secondary"
          text
          rounded
          class="reader-back-btn"
          aria-label="Volver a la novela"
          @click="router.push(`/novels/${novelId}`)"
        />
        <Button
          icon="pi pi-bars"
          severity="secondary"
          text
          rounded
          class="reader-menu-btn"
          aria-label="Menú de capítulos"
          @click="drawerOpen = !drawerOpen"
        />
      </div>
      <div class="reader-header-title-group">
        <h1 class="reader-header-title">{{ novel ? getNovelDisplayTitle(novel) : 'Lector' }}</h1>
      </div>
      <Button
        icon="pi pi-cog"
        severity="secondary"
        text
        rounded
        class="reader-settings-btn"
        aria-label="Configuración"
        @click="settingsOpen = !settingsOpen"
      />
    </header>

    <div class="reader-layout">
      <div
        v-if="drawerOpen && !desktop"
        class="reader-drawer-overlay"
        @click="drawerOpen = false"
      />
      <nav v-if="desktop || drawerOpen" class="reader-sidebar">
        <div class="reader-sidebar-header" v-if="!desktop">
          <button class="reader-drawer-close" @click="drawerOpen = false">✕</button>
        </div>
        <ul class="reader-sidebar-list">
          <li v-for="(item, index) in summarySlots" :key="item?.id || index">
            <button
              v-if="item"
              type="button"
              class="reader-sidebar-link"
              :class="{ active: item.id === activeChapterId }"
              @click="selectChapter(item.id)"
              :disabled="!summaryHasVariantContent(item)"
            >
              <span class="reader-ch-title">{{ summaryDisplayTitle(item) }}</span>
            </button>
            <div v-else class="reader-sidebar-skeleton">
              <Skeleton width="100%" height="1rem" />
            </div>
          </li>
        </ul>
      </nav>

      <main ref="scrollContainer" class="reader-main">
        <Card v-if="showEmpty">
          <template #content>
            <div class="reader-empty-state">
              <h2>Sin contenido</h2>
              <p class="muted">
                <template v-if="variant === 'translated' && stats.totalChapters > 0">
                  No hay capítulos traducidos todavía. Puedes cambiar a originales.
                </template>
                <template v-else>
                  No hay capítulos disponibles para esta variante.
                </template>
              </p>
              <div class="reader-empty-actions">
                <Button v-if="variant === 'translated' && stats.totalChapters > 0" label="Ver originales" severity="secondary" outlined @click="variant = 'original'" />
                <Button label="Volver al proyecto" @click="router.push(`/novels/${novelId}`)" />
              </div>
            </div>
          </template>
        </Card>

        <Card v-else-if="chapterLoading">
          <template #content>
            <div class="reader-loading">
              <Skeleton width="10rem" height="1rem" />
              <Skeleton width="50%" height="2rem" />
              <Skeleton width="100%" height="8rem" borderRadius="12px" />
              <Skeleton width="100%" height="8rem" borderRadius="12px" />
            </div>
          </template>
        </Card>

        <article v-else-if="activeChapter" class="reader-article">
          <header class="reader-chapter-header">
            <h1 class="reader-chapter-heading">{{ chapterDisplayTitle(activeChapter) }}</h1>
            <div class="reader-chapter-ornament">❧ ✦ ❧</div>
          </header>
          <div class="reader-body markdown-preview" v-html="markdownToHtml(activeChapterContent)" />

          <nav class="reader-chapter-nav" aria-label="Navegación entre capítulos">
            <Button
              v-if="previousChapterId"
              icon="pi pi-arrow-left"
              label="Anterior"
              severity="secondary"
              outlined
              class="reader-nav-prev"
              @click="selectChapter(previousChapterId)"
            />
            <span v-else class="reader-nav-spacer" />
            <Button
              v-if="nextChapterId"
              label="Siguiente"
              icon="pi pi-arrow-right"
              iconPos="right"
              severity="primary"
              class="reader-nav-next"
              @click="selectChapter(nextChapterId)"
            />
            <span v-else class="reader-nav-spacer" />
          </nav>
        </article>
      </main>
    </div>

    <div
      v-if="drawerOpen && !desktop"
      class="reader-drawer-overlay-mobile"
      :class="{ open: drawerOpen && !desktop }"
      @click="drawerOpen = false"
    />
    <nav class="reader-drawer" :class="{ open: drawerOpen && !desktop }">
      <div class="reader-drawer-header">
        <h2>Contenido</h2>
        <button class="reader-drawer-close" @click="drawerOpen = false">✕</button>
      </div>
      <ul class="reader-sidebar-list">
        <li v-for="(item, index) in summarySlots" :key="item?.id || index">
          <button
            v-if="item"
            type="button"
            class="reader-sidebar-link"
            :class="{ active: item.id === activeChapterId }"
            @click="selectChapter(item.id); drawerOpen = false"
            :disabled="!summaryHasVariantContent(item)"
          >
            <span class="reader-ch-title">{{ summaryDisplayTitle(item) }}</span>
          </button>
        </li>
      </ul>
    </nav>

    <div class="reader-settings-popover" :class="{ open: settingsOpen }">
      <div class="reader-settings-row">
        <span class="reader-settings-label">Tamaño de texto</span>
        <div class="reader-typo-group">
          <button class="reader-typo-btn" @click="adjustFontSize(-1)" title="Reducir fuente">−</button>
          <span class="reader-typo-val">{{ fontSize }}px</span>
          <button class="reader-typo-btn" @click="adjustFontSize(1)" title="Aumentar fuente">+</button>
        </div>
      </div>
      <div class="reader-settings-row">
        <span class="reader-settings-label">Interlineado</span>
        <div class="reader-typo-group">
          <button class="reader-typo-btn" @click="adjustLineHeight(-0.05)" title="Reducir interlineado">−</button>
          <span class="reader-typo-val">{{ lineHeight.toFixed(2) }}</span>
          <button class="reader-typo-btn" @click="adjustLineHeight(0.05)" title="Aumentar interlineado">+</button>
        </div>
      </div>
      <div class="reader-settings-row">
        <span class="reader-settings-label">Ancho del texto</span>
        <div class="reader-typo-group">
          <button class="reader-typo-btn" @click="adjustContentWidth(-40)" title="Reducir ancho">−</button>
          <span class="reader-typo-val">{{ contentWidth }}px</span>
          <button class="reader-typo-btn" @click="adjustContentWidth(40)" title="Aumentar ancho">+</button>
        </div>
      </div>
      <div class="reader-settings-divider"></div>
      <div class="reader-settings-row">
        <span class="reader-settings-label">Idioma</span>
        <div class="reader-variant-group">
          <button
            class="reader-variant-btn"
            :class="{ active: variant === 'translated' }"
            @click="variant = 'translated'"
          >Traducido</button>
          <button
            class="reader-variant-btn"
            :class="{ active: variant === 'original' }"
            @click="variant = 'original'"
          >Original</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type CSSProperties } from "vue";
import "@fontsource-variable/merriweather";
import { useRoute, useRouter } from "vue-router";
import Button from "primevue/button";
import Card from "primevue/card";
import Skeleton from "primevue/skeleton";
import type { ChapterSummary } from "@/api/types";
import { useAppServices } from "@/app/services";
import { useNovels } from "@/composables/useNovels";
import { getNovelDisplayTitle, type Chapter, type Novel } from "@/domain";
import { markdownToHtml } from "@/utils/markdown";
import { useReadingProgress } from "@/composables/useReadingProgress";

const route = useRoute();
const router = useRouter();
const { api } = useAppServices();
const novelId = computed(() => String(route.params.novelId || ""));
const { getNovel } = useNovels();

const READER_STORAGE_KEY = "reader-settings";

function loadReaderSettings() {
  try {
    const raw = localStorage.getItem(READER_STORAGE_KEY);
    if (raw) return JSON.parse(raw) as { fontSize?: number; lineHeight?: number; contentWidth?: number; variant?: "translated" | "original" };
  } catch { /* ignore */ }
  return null;
}

function saveReaderSettings() {
  try {
    localStorage.setItem(READER_STORAGE_KEY, JSON.stringify({
      fontSize: fontSize.value,
      lineHeight: lineHeight.value,
      contentWidth: contentWidth.value,
      variant: variant.value,
    }));
  } catch { /* ignore */ }
}

const isMobile = window.innerWidth < 720;
const saved = loadReaderSettings();
const variant = ref<"translated" | "original">(saved?.variant ?? "translated");
const activeChapterId = ref<string | null>(null);
const activeChapter = ref<Chapter | null>(null);
const drawerOpen = ref(false);
const settingsOpen = ref(false);
const progress = ref(0);
const desktop = ref(window.innerWidth >= 720);
const scrollContainer = ref<HTMLElement | null>(null);
const summaryLoading = ref(false);
const chapterLoading = ref(false);
const summarySlots = ref<(ChapterSummary | null)[]>([]);
const SUMMARY_BATCH_SIZE = 50;
let backgroundLoadToken = 0;
let pendingSavedChapterRestore = false;

const fontSize = ref(saved?.fontSize ?? (isMobile ? 13 : 19));
const lineHeight = ref(saved?.lineHeight ?? 1.5);
const contentWidth = ref(saved?.contentWidth ?? 860);
const novel = ref<Novel | null>(null);
const {
  savedChapterId,
  savedScrollPercent,
  isLoaded: progressLoaded,
  load: loadReadingProgress,
  flush: flushReadingProgress,
  startAutoSave,
} = useReadingProgress(novelId, activeChapterId, progress);
const stats = computed(() => ({
  totalChapters: novel.value?.chapterCount ?? 0,
}));

const loadedSummaries = computed(() =>
  summarySlots.value.filter((item): item is ChapterSummary => Boolean(item)),
);
const visibleSummaries = computed(() =>
  loadedSummaries.value.filter((item) => summaryHasVariantContent(item)),
);
const activeChapterContent = computed(() => {
  if (!activeChapter.value) return "";
  if (variant.value === "translated") {
    return activeChapter.value.refinedContent || activeChapter.value.translatedContent || "";
  }
  return activeChapter.value.originalContent || "";
});
const activeVisibleIndex = computed(() =>
  visibleSummaries.value.findIndex((item) => item.id === activeChapterId.value),
);
const previousChapterId = computed(() =>
  activeVisibleIndex.value > 0 ? visibleSummaries.value[activeVisibleIndex.value - 1]?.id ?? null : null,
);
const nextChapterId = computed(() => {
  if (activeVisibleIndex.value < 0) return null;
  return visibleSummaries.value[activeVisibleIndex.value + 1]?.id ?? null;
});
const showEmpty = computed(() =>
  !chapterLoading.value && stats.value.totalChapters > 0 && visibleSummaries.value.length === 0,
);

onMounted(() => {
  void initializeReader();
  window.addEventListener("resize", handleResize);
  document.addEventListener("keydown", onKeydown);
  document.addEventListener("click", handleClickOutside);
  window.addEventListener("scroll", updateProgress, { passive: true });
});

onBeforeUnmount(() => {
  backgroundLoadToken++;
  window.removeEventListener("resize", handleResize);
  document.removeEventListener("keydown", onKeydown);
  document.removeEventListener("click", handleClickOutside);
  window.removeEventListener("scroll", updateProgress);
});

watch([activeChapterId, variant], () => {
  if (!activeChapterId.value) {
    void selectFirstAvailableChapter();
    return;
  }
  const currentSummary = loadedSummaries.value.find((item) => item.id === activeChapterId.value);
  if (currentSummary && !summaryHasVariantContent(currentSummary)) {
    void selectFirstAvailableChapter();
    return;
  }
  void loadActiveChapter(activeChapterId.value);
});

let initialScrollRestored = false;

watch(activeChapter, async () => {
  await nextTick();
  if (!initialScrollRestored && savedScrollPercent.value > 0) {
    const scrollRange = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    if (scrollRange > 0) {
      const targetScroll = (savedScrollPercent.value / 100) * scrollRange;
      window.scrollTo({ top: targetScroll, behavior: "auto" });
    }
    initialScrollRestored = true;
  } else {
    window.scrollTo({ top: 0, behavior: "auto" });
  }
  updateProgress();
});

watch(novelId, () => {
  backgroundLoadToken++;
  initialScrollRestored = false;
  pendingSavedChapterRestore = false;
  summarySlots.value = [];
  activeChapterId.value = null;
  activeChapter.value = null;
  void initializeReader();
});

watch([fontSize, lineHeight, contentWidth, variant], saveReaderSettings);

function summaryHasVariantContent(summary: ChapterSummary) {
  return variant.value === "translated"
    ? summary.hasRefinedContent || summary.hasTranslatedContent
    : summary.hasOriginalContent;
}

function summaryDisplayTitle(summary: ChapterSummary) {
  if (variant.value === "translated" && summary.translatedTitle?.trim()) {
    return summary.translatedTitle;
  }
  return summary.title;
}

function chapterDisplayTitle(chapter: Chapter) {
  if (variant.value === "translated" && chapter.translatedTitle?.trim()) {
    return chapter.translatedTitle;
  }
  return chapter.title;
}

async function loadCurrentNovel() {
  if (!novelId.value) {
    novel.value = null;
    return;
  }
  novel.value = await getNovel(novelId.value, false);
}

async function initializeReader() {
  if (!novelId.value) return;
  const token = ++backgroundLoadToken;
  await loadCurrentNovel();
  if (token !== backgroundLoadToken) return;
  summarySlots.value = Array.from({ length: stats.value.totalChapters }, () => null);
  const initialBatch = Math.min(SUMMARY_BATCH_SIZE, stats.value.totalChapters);
  const apiTotal = await loadSummaryRange(0, initialBatch);
  if (token !== backgroundLoadToken) return;
  if (apiTotal > summarySlots.value.length) {
    summarySlots.value = Array.from({ length: apiTotal }, (_, i) =>
      i < summarySlots.value.length ? summarySlots.value[i] : null,
    );
  }
  await loadReadingProgress();
  if (token !== backgroundLoadToken) return;
  const savedCh = savedChapterId.value;
  const savedSummary = savedCh
    ? loadedSummaries.value.find((item) => item.id === savedCh)
    : null;
  if (savedSummary && summaryHasVariantContent(savedSummary)) {
    await selectChapter(savedCh!);
  } else {
    await selectFirstAvailableChapter();
    if (savedCh) pendingSavedChapterRestore = true;
  }
  if (token !== backgroundLoadToken) return;
  startAutoSave();
  if (summarySlots.value.length > initialBatch) {
    void loadRemainingSummariesInBackground(token);
  }
}

async function loadSummaryRange(first: number, last: number): Promise<number> {
  if (!novelId.value || stats.value.totalChapters === 0) return 0;
  const safeFirst = Math.max(0, first);
  const safeLast = Math.min(last, stats.value.totalChapters);
  if (safeFirst >= safeLast) return 0;
  let apiTotal = 0;
  summaryLoading.value = true;
  try {
    for (let offset = safeFirst; offset < safeLast; offset += SUMMARY_BATCH_SIZE) {
      const limit = Math.min(SUMMARY_BATCH_SIZE, safeLast - offset);
      const result = await api.chapters.listSummaries(novelId.value, { offset, limit });
      if (offset === 0 && result.total > 0) apiTotal = result.total;
      result.items.forEach((item, index) => {
        const slotIndex = offset + index;
        if (slotIndex < summarySlots.value.length) {
          summarySlots.value[slotIndex] = item;
        }
      });
    }
  } finally {
    summaryLoading.value = false;
  }
  return apiTotal;
}

async function loadRemainingSummariesInBackground(token: number) {
  const total = summarySlots.value.length;
  for (let offset = SUMMARY_BATCH_SIZE; offset < total; offset += SUMMARY_BATCH_SIZE) {
    if (token !== backgroundLoadToken || !novelId.value) return;
    const limit = Math.min(SUMMARY_BATCH_SIZE, total - offset);
    let retries = 3;
    while (retries > 0) {
      if (token !== backgroundLoadToken || !novelId.value) return;
      try {
        const result = await api.chapters.listSummaries(novelId.value, { offset, limit });
        if (token !== backgroundLoadToken) return;
        result.items.forEach((item, index) => {
          const slotIndex = offset + index;
          if (slotIndex < summarySlots.value.length) {
            summarySlots.value[slotIndex] = item;
          }
        });
        break;
      } catch {
        retries--;
        if (retries === 0) return;
        await new Promise<void>((resolve) => setTimeout(resolve, 1000 * (3 - retries)));
      }
    }
    if (pendingSavedChapterRestore && savedChapterId.value) {
      const savedNow = loadedSummaries.value.find((item) => item.id === savedChapterId.value);
      if (savedNow && summaryHasVariantContent(savedNow)) {
        pendingSavedChapterRestore = false;
        await selectChapter(savedChapterId.value);
        continue;
      }
    }
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  }
}

async function selectFirstAvailableChapter() {
  const firstAvailable = loadedSummaries.value.find((item) => summaryHasVariantContent(item));
  if (firstAvailable) {
    await selectChapter(firstAvailable.id);
    return;
  }
  if (summarySlots.value.length > SUMMARY_BATCH_SIZE) {
    await loadSummaryRange(0, Math.min(SUMMARY_BATCH_SIZE * 2, summarySlots.value.length));
    const expandedAvailable = loadedSummaries.value.find((item) => summaryHasVariantContent(item));
    if (expandedAvailable) {
      await selectChapter(expandedAvailable.id);
      return;
    }
  }
  activeChapterId.value = null;
  activeChapter.value = null;
}

async function selectChapter(chapterId: string) {
  activeChapterId.value = chapterId;
  await loadActiveChapter(chapterId);
}

async function loadActiveChapter(chapterId: string) {
  if (!novelId.value) return;
  chapterLoading.value = true;
  try {
    activeChapter.value = await api.chapters.get(novelId.value, chapterId);
  } finally {
    chapterLoading.value = false;
  }
}

function handleResize() {
  desktop.value = window.innerWidth >= 720;
  if (desktop.value) drawerOpen.value = false;
}

function updateProgress() {
  const scrollTop = window.scrollY || document.documentElement.scrollTop || 0;
  const scrollRange = document.documentElement.scrollHeight - document.documentElement.clientHeight;
  progress.value = scrollRange > 0 ? Math.min(100, (scrollTop / scrollRange) * 100) : 0;
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "ArrowRight" || event.key === "ArrowDown") {
    event.preventDefault();
    if (nextChapterId.value) selectChapter(nextChapterId.value);
  } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
    event.preventDefault();
    if (previousChapterId.value) selectChapter(previousChapterId.value);
  } else if (event.key === "Escape") {
    drawerOpen.value = false;
    settingsOpen.value = false;
  }
}

function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (settingsOpen.value && !target.closest(".reader-settings-popover") && !target.closest(".reader-settings-btn")) {
    settingsOpen.value = false;
  }
}

function adjustFontSize(delta: number) {
  fontSize.value = Math.min(26, Math.max(13, fontSize.value + delta));
  applyTypography();
}

function adjustLineHeight(delta: number) {
  lineHeight.value = parseFloat(Math.min(2.6, Math.max(1.3, lineHeight.value + delta)).toFixed(2));
  applyTypography();
}

function adjustContentWidth(delta: number) {
  contentWidth.value = Math.min(1100, Math.max(520, contentWidth.value + delta));
  applyTypography();
}

function applyTypography() {
  document.documentElement.style.setProperty("--reader-fs-body", `${fontSize.value}px`);
  document.documentElement.style.setProperty("--reader-lh-body", `${lineHeight.value}`);
  document.documentElement.style.setProperty("--reader-content-w", `${contentWidth.value}px`);
}
</script>

<style scoped>
:root {
  --reader-fs-body: 19px;
  --reader-lh-body: 1.5;
  --reader-content-w: 860px;
}

@media (max-width: 720px) {
  :root {
    --reader-fs-body: 13px;
  }
}

.reader-shell {
  min-height: 100vh;
  background: var(--background);
  --reader-ink: var(--foreground);
  --reader-paper: var(--background);
  --reader-gold: var(--accent-link);
  --reader-text-muted: var(--text-secondary);
  color: var(--foreground);
  font-family: inherit;
  line-height: inherit;
}

/* ── Progress bar ── */
.reader-progress-track {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  width: 100%;
  background: var(--surface-strong);
  z-index: 9999;
}

.reader-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-link), var(--btn-primary-bg));
  transition: width 0.1s linear;
}

/* ── Header ── */
.reader-header {
  background: color-mix(in oklab, var(--surface-elevated) 92%, var(--background));
  color: var(--foreground);
  padding: 0 20px;
  height: 62px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--divide);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  box-shadow: 0 1px 3px color-mix(in oklab, var(--foreground) 8%, transparent);
  backdrop-filter: blur(14px);
}

.reader-header-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.reader-back-btn,
.reader-menu-btn {
  color: var(--foreground) !important;
}

.reader-back-btn:hover,
.reader-menu-btn:hover {
  background: var(--surface-muted) !important;
}

.reader-header-title-group {
  display: flex;
  align-items: center;
  flex: 1;
  justify-content: center;
}

.reader-header-title {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--foreground);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

/* ── Settings button ── */
.reader-settings-btn {
  color: var(--foreground) !important;
}

.reader-settings-btn:hover {
  background: var(--surface-muted) !important;
}

/* ── Layout ── */
.reader-layout {
  display: flex;
  margin-top: 62px;
  min-height: calc(100vh - 62px);
  position: relative;
  z-index: 1;
}

/* ── Sidebar ── */
.reader-sidebar {
  width: 272px;
  min-width: 272px;
  background: var(--surface-elevated);
  color: var(--foreground);
  padding: 0 0 32px;
  height: calc(100vh - 62px);
  position: sticky;
  top: 62px;
  overflow-y: auto;
  border-right: 1px solid var(--divide);
}

.reader-sidebar-header {
  padding: 22px 22px 14px;
  border-bottom: 1px solid var(--divide);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reader-sidebar-header h2 {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--text-secondary);
  font-weight: 600;
  margin: 0;
}

.reader-sidebar-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.reader-sidebar-list li {
  border-bottom: 1px solid var(--divide);
}

.reader-sidebar-list li:last-child {
  border-bottom: none;
}

.reader-sidebar-link {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 12px 20px 12px 22px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.95rem;
  transition: background 0.2s, color 0.2s, border-color 0.15s;
  border-left: 2px solid transparent;
  cursor: pointer;
  line-height: 1.45;
  background: none;
  border-top: none;
  border-right: none;
  border-bottom: none;
  width: 100%;
  text-align: left;
}

.reader-ch-title {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: inherit;
}

.reader-sidebar-link:hover {
  background: var(--surface-muted);
  color: var(--foreground);
}

.reader-sidebar-link.active {
  background: var(--surface-muted);
  color: var(--foreground);
  border-left-color: var(--accent-link);
}

.reader-sidebar-link.active .reader-ch-title {
  color: var(--foreground);
}

.reader-sidebar-link:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.reader-sidebar-skeleton {
  padding: 12px 22px;
}

/* ── Main content ── */
.reader-main {
  flex: 1;
  max-width: var(--reader-content-w);
  margin: 0 auto;
  padding: 56px 64px 100px;
  min-width: 0;
  background: var(--background);
}

/* ── Article ── */
.reader-article {
  max-width: 100%;
  font-family: 'Merriweather Variable', 'Merriweather', 'Georgia', serif;
  font-size: var(--reader-fs-body);
  line-height: var(--reader-lh-body);
  color: var(--reader-ink);
}

.reader-chapter-header {
  text-align: center;
  margin-bottom: 44px;
}

.reader-chapter-heading {
  font-family: 'Merriweather Variable', 'Merriweather', serif;
  font-size: 2.6em;
  font-weight: 700;
  font-style: italic;
  text-align: center;
  margin: 0 0 12px;
  color: var(--reader-ink);
  line-height: 1.2;
  letter-spacing: 0.01em;
}

.reader-chapter-ornament {
  text-align: center;
  color: var(--accent-link);
  font-size: 1.2em;
  letter-spacing: 0.3em;
  margin: 0;
  opacity: 0.65;
}

/* ── Body typography ── */
.reader-body {
  font-size: 1.09em;
  line-height: var(--reader-lh-body);
}

.reader-body :deep(p) {
  margin-bottom: 1.4em;
  text-align: justify;
  hyphens: auto;
  -webkit-hyphens: auto;
  orphans: 3;
  widows: 3;
}

.reader-body :deep(p:first-of-type)::first-letter {
  font-family: 'Merriweather Variable', 'Merriweather', serif;
  font-size: 4.2em;
  font-weight: 700;
  color: var(--accent-link);
  float: left;
  line-height: 0.78;
  margin: 0.08em 0.08em 0 0;
  padding: 0;
}

.reader-body :deep(h1) {
  font-family: 'Merriweather Variable', 'Merriweather', serif;
  font-size: 2.6em;
  font-weight: 700;
  font-style: italic;
  text-align: center;
  margin: 0 0 12px;
  color: var(--reader-ink);
  line-height: 1.2;
  letter-spacing: 0.01em;
}

.reader-body :deep(h2) {
  font-family: 'Merriweather Variable', 'Merriweather', serif;
  font-size: 1.75em;
  font-weight: 600;
  font-style: italic;
  margin: 52px 0 20px;
  color: var(--reader-ink);
  text-align: center;
}

.reader-body :deep(h2)::before,
.reader-body :deep(h2)::after {
  content: ' — ';
  color: var(--accent-link);
  font-style: normal;
  font-size: 0.7em;
}

.reader-body :deep(h3) {
  font-family: 'Merriweather Variable', 'Merriweather', serif;
  font-size: 1.3em;
  font-weight: 600;
  margin: 36px 0 14px;
  color: var(--reader-ink);
  letter-spacing: 0.04em;
}

.reader-body :deep(h4),
.reader-body :deep(h5),
.reader-body :deep(h6) {
  font-family: 'Merriweather Variable', 'Merriweather', serif;
  font-size: 1.05em;
  font-weight: 600;
  font-variant: small-caps;
  letter-spacing: 0.12em;
  margin: 28px 0 12px;
  color: var(--reader-text-muted);
}

.reader-body :deep(hr) {
  border: none;
  text-align: center;
  margin: 44px 0;
  color: var(--accent-link);
  font-size: 1.1em;
  letter-spacing: 0.4em;
  opacity: 0.6;
}

.reader-body :deep(hr)::after {
  content: '❧  ✦  ❧';
}

.reader-body :deep(strong) {
  font-weight: 700;
  color: var(--reader-ink);
}

/* ── Scrollbar ── */
.reader-shell :deep(::-webkit-scrollbar) {
  width: 7px;
}

.reader-shell :deep(::-webkit-scrollbar-track) {
  background: var(--surface-muted);
}

.reader-shell :deep(::-webkit-scrollbar-thumb) {
  background: color-mix(in oklab, var(--foreground) 24%, transparent);
  border-radius: 3px;
}

.reader-shell :deep(::-webkit-scrollbar-thumb:hover) {
  background: color-mix(in oklab, var(--foreground) 38%, transparent);
}

/* ── Empty / Loading states ── */
.reader-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 2rem 1rem;
  gap: 1rem;
}

.reader-empty-state h2 {
  margin: 0;
}

.reader-empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
}

.reader-loading {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

/* ── Drawer overlay (mobile) ── */
.reader-drawer-overlay {
  display: none;
}

.reader-drawer-overlay-mobile {
  position: fixed;
  inset: 0;
  background: var(--surface-overlay);
  z-index: 200;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
}

/* ── Drawer (mobile) ── */
.reader-drawer {
  position: fixed;
  top: 0;
  left: 0;
  width: 300px;
  max-width: 80vw;
  height: 100vh;
  background: var(--surface-elevated);
  z-index: 201;
  transform: translateX(-100%);
  transition: transform 0.3s ease;
  overflow-y: auto;
  padding: 0 0 32px;
  color: var(--foreground);
  border-right: 1px solid var(--divide);
}

.reader-drawer.open {
  transform: translateX(0);
  box-shadow: 2px 0 24px color-mix(in oklab, var(--foreground) 18%, transparent);
}

.reader-drawer-overlay-mobile.open {
  opacity: 1;
  pointer-events: auto;
}

.reader-drawer-header {
  padding: 20px 22px 14px;
  border-bottom: 1px solid var(--divide);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reader-drawer-header h2 {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--text-secondary);
  font-weight: 600;
  margin: 0;
}

.reader-drawer-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1.2em;
  padding: 4px 8px;
  line-height: 1;
  transition: color 0.15s, background 0.15s;
  border-radius: var(--radius-sm);
}

.reader-drawer-close:hover {
  color: var(--foreground);
  background: var(--surface-muted);
}

/* ── Settings popover ── */
.reader-settings-popover {
  display: none;
  position: fixed;
  top: 70px;
  right: 12px;
  background: var(--surface-elevated);
  border: 1px solid var(--divide);
  border-radius: var(--radius-md);
  padding: 14px;
  z-index: 202;
  min-width: 240px;
  box-shadow: 0 8px 32px color-mix(in oklab, var(--foreground) 18%, transparent);
  flex-direction: column;
  gap: 12px;
}

.reader-settings-popover.open {
  display: flex;
}

.reader-settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.reader-settings-label {
  font-size: 0.82rem;
  color: var(--foreground);
  white-space: nowrap;
  user-select: none;
}

.reader-settings-divider {
  height: 1px;
  background: var(--divide);
  margin: 2px 0;
}

.reader-typo-group {
  display: flex;
  align-items: center;
  gap: 0;
  border: 1px solid var(--divide);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.reader-typo-btn {
  background: none;
  border: none;
  color: var(--foreground);
  cursor: pointer;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95em;
  transition: background 0.15s, color 0.15s;
  padding: 0;
  line-height: 1;
}

.reader-typo-btn:hover {
  background: var(--surface-muted);
  color: var(--foreground);
}

.reader-typo-btn:active {
  background: var(--surface-strong);
}

.reader-typo-btn + .reader-typo-btn {
  border-left: 1px solid var(--divide);
}

.reader-typo-val {
  font-size: 0.75rem;
  color: var(--text-secondary);
  min-width: 36px;
  text-align: center;
  padding: 0 4px;
  border-left: 1px solid var(--divide);
  border-right: 1px solid var(--divide);
  line-height: 28px;
  height: 28px;
  user-select: none;
  font-variant-numeric: tabular-nums;
}

.reader-variant-group {
  display: flex;
  gap: 0;
  border: 1px solid var(--divide);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.reader-variant-btn {
  flex: 1;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 500;
  padding: 6px 12px;
  transition: background 0.15s, color 0.15s;
}

.reader-variant-btn + .reader-variant-btn {
  border-left: 1px solid var(--divide);
}

.reader-variant-btn:hover {
  background: var(--surface-muted);
  color: var(--foreground);
}

.reader-variant-btn.active {
  background: var(--surface-muted);
  color: var(--foreground);
  font-weight: 600;
}

/* ── Desktop safety: hide mobile-only elements ── */
@media (min-width: 721px) {
  .reader-menu-btn,
  .reader-drawer,
  .reader-drawer-overlay-mobile {
    display: none !important;
  }
}

/* ── Responsive: mobile ── */
@media (max-width: 720px) {
  .reader-sidebar {
    display: none;
  }

  .reader-menu-btn {
    display: flex !important;
  }

  .reader-main {
    padding: 30px 22px 60px;
  }

  .reader-header {
    padding: 0 12px;
  }

  .reader-header-title {
    font-size: 1em;
    max-width: 200px;
  }

  .reader-chapter-heading {
    font-size: 1.75em;
  }
}

@media (max-width: 480px) {
  .reader-main {
    padding: 24px 16px 50px;
  }

  .reader-header-title {
    font-size: 0.92em;
    max-width: 160px;
  }
}

/* ── Chapter navigation (prev/next) ── */
.reader-chapter-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 64px;
  padding-top: 32px;
  border-top: 1px solid var(--divide);
}

.reader-nav-spacer {
  flex: 1;
}

.reader-nav-next:not(:first-child) {
  margin-left: auto;
}

.reader-chapter-nav:has(.reader-nav-prev:only-child),
.reader-chapter-nav:has(.reader-nav-next:only-child) {
  justify-content: center;
}

@media (max-width: 480px) {
  .reader-chapter-nav {
    flex-direction: column;
  }
  .reader-nav-spacer {
    display: none;
  }
  .reader-chapter-nav .reader-nav-prev,
  .reader-chapter-nav .reader-nav-next {
    width: 100%;
  }
}
</style>
