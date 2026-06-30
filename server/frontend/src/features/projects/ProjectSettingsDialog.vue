<template>
  <Dialog :visible="open" modal header="Configuración del proyecto" :style="{ width: 'min(1100px, 96vw)' }" @update:visible="emit('update:open', false)">
    <div class="stack-md">
      <div class="row-wrap">
        <Button
          v-for="tab in tabs"
          :key="tab.value"
          :label="tab.label"
          size="small"
          :outlined="activeTab !== tab.value"
          @click="activeTab = tab.value"
        />
      </div>

      <div v-if="activeTab === 'novel'" class="stack-md">
        <div class="row-wrap">
          <div style="min-width: 220px; flex: 1">
            <label class="small muted">Idioma origen</label>
            <InputText v-model="novelDraft.sourceLanguage" fluid />
          </div>
          <div style="min-width: 220px; flex: 1">
            <label class="small muted">Idioma destino</label>
            <InputText v-model="novelDraft.targetLanguage" fluid />
          </div>
        </div>

        <div class="row-wrap">
          <Card style="flex: 1; min-width: 280px">
            <template #title>Metadatos idioma origen</template>
            <template #content>
              <MetadataEditor
                :metadata-title="novelDraft.sourceTitle"
                :metadata-author="novelDraft.sourceAuthor"
                :metadata-description="novelDraft.sourceDescription"
                :metadata-series="novelDraft.sourceSeries"
                :metadata-number="novelDraft.sourceNumber"
                :status="novelDraft.status"
                :tags="novelDraft.tags"
                :tag-suggestions="tagSuggestions"
                :series-suggestions="seriesSuggestions"
                show-novel-meta
                :cover-path="novel.coverPath"
                cover-editable
                :novel-id="novel.id"
                is-owner
                @update:metadata-title="(v) => (novelDraft.sourceTitle = v)"
                @update:metadata-author="(v) => (novelDraft.sourceAuthor = v)"
                @update:metadata-description="(v) => (novelDraft.sourceDescription = v)"
                @update:metadata-series="(v) => (novelDraft.sourceSeries = v)"
                @update:metadata-number="(v) => (novelDraft.sourceNumber = v)"
                @update:status="(v) => (novelDraft.status = v)"
                @update:tags="(v) => (novelDraft.tags = v)"
                @select-cover="onSelectCover"
                @remove-cover="onRemoveCover"
                @delete="onDeleteNovel"
              />
            </template>
          </Card>

          <Card style="flex: 1; min-width: 280px">
            <template #title>Metadatos idioma destino</template>
            <template #content>
              <MetadataEditor
                :metadata-title="novelDraft.targetTitle"
                :metadata-author="novelDraft.targetAuthor"
                :metadata-description="novelDraft.targetDescription"
                :metadata-series="novelDraft.targetSeries"
                :metadata-number="novelDraft.targetNumber"
                :series-suggestions="seriesSuggestions"
                @update:metadata-title="(v) => (novelDraft.targetTitle = v)"
                @update:metadata-author="(v) => (novelDraft.targetAuthor = v)"
                @update:metadata-description="(v) => (novelDraft.targetDescription = v)"
                @update:metadata-series="(v) => (novelDraft.targetSeries = v)"
                @update:metadata-number="(v) => (novelDraft.targetNumber = v)"
              />
            </template>
          </Card>
        </div>

        <div class="row-wrap">
          <div style="min-width: 280px; flex: 1">
            <label class="small muted">URL fuente</label>
            <InputText v-model="novelDraft.url" fluid />
          </div>
          <div style="min-width: 280px; flex: 1">
            <label class="small muted">Custom commands</label>
            <Textarea v-model="novelDraft.customCommands" rows="5" fluid class="mono" />
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'glossary'" class="stack-md">
        <div class="row-between">
          <h4 style="margin: 0">Glosario</h4>
          <Button label="Añadir entrada" icon="pi pi-plus" size="small" @click="addGlossaryEntry" />
        </div>
        <div v-if="novelDraft.glossary.length === 0" class="muted small">Sin entradas de glosario.</div>
        <Card v-for="entry in novelDraft.glossary" :key="entry.id">
          <template #content>
            <div class="stack-md">
              <div class="row-wrap">
                <InputText v-model="entry.source" placeholder="Origen" style="flex: 1; min-width: 180px" />
                <InputText v-model="entry.target" placeholder="Destino" style="flex: 1; min-width: 180px" />
                <Button severity="danger" outlined icon="pi pi-trash" @click="removeGlossaryEntry(entry.id)" />
              </div>
              <InputText v-model="entry.context" placeholder="Contexto opcional" fluid />
            </div>
          </template>
        </Card>
      </div>

      <div v-else-if="activeTab === 'prompts'" class="stack-md">
        <Message severity="info">
          Edita un system prompt para crear un override en la novela. Déjalo vacío (o restáuralo al global) para usar el prompt configurado en Configuración general. El user prompt se genera automáticamente con los datos del capítulo y no se expone aquí.
        </Message>
        <PromptRoleEditor
          title="Traducción"
          :model-value="effectiveSystemPrompt('translation')"
          :global-value="globalSystemPrompt('translation')"
          :overridden="isOverridden('translation')"
          @update:model-value="setSystemPrompt('translation', $event)"
        />
        <PromptRoleEditor
          title="Refinamiento"
          :model-value="effectiveSystemPrompt('refine')"
          :global-value="globalSystemPrompt('refine')"
          :overridden="isOverridden('refine')"
          @update:model-value="setSystemPrompt('refine', $event)"
        />
        <PromptRoleEditor
          title="Verificación"
          :model-value="effectiveSystemPrompt('check')"
          :global-value="globalSystemPrompt('check')"
          :overridden="isOverridden('check')"
          @update:model-value="setSystemPrompt('check', $event)"
        />
      </div>

      <div v-else-if="activeTab === 'ai'" class="stack-md">
        <div class="row-wrap">
          <div style="min-width: 220px; flex: 1">
            <label class="small muted">Proveedor</label>
            <Select
              v-model="settingsDraft.ai.provider"
              :options="providerOptions"
              optionLabel="name"
              optionValue="id"
              :loading="providersLoading"
              :disabled="providersLoading"
              placeholder="Usar proveedor global"
              fluid
              showClear
              @change="onProviderChange"
            />
          </div>
          <div style="min-width: 220px; flex: 1">
            <label class="small muted">Modelo</label>
            <Select
              v-model="settingsDraft.ai.model"
              :options="modelOptions"
              :disabled="!settingsDraft.ai.provider || providersLoading"
              placeholder="Usar modelo global"
              fluid
              showClear
            />
          </div>
          <FieldNumber v-model="timeoutSec" label="Timeout (segundos)" :min="10" allow-clear placeholder="Usar global" wrapper-style="min-width: 180px; flex: 1" />
        </div>
        <Message severity="info">Si dejas estos campos vacíos, el backend usará la configuración global. El timeout aplica solo si se configura un valor.</Message>
      </div>

      <div v-else-if="activeTab === 'translation'" class="stack-md">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 1rem">
          <div>
            <div style="font-weight: 600">Auto segmentación</div>
            <div class="small muted">Divide capítulos largos antes de enviarlos al proveedor AI.</div>
          </div>
          <ToggleSwitch v-model="settingsDraft.translation.autoSegment" />
        </div>

        <div class="row-wrap">
          <FieldNumber v-model="settingsDraft.translation.thresholdChars" label="Umbral auto" :min="1000" wrapper-style="min-width: 180px; flex: 1" />
          <FieldNumber v-model="settingsDraft.translation.maxChars" label="Máx. por segmento" :min="500" wrapper-style="min-width: 180px; flex: 1" />
          <FieldNumber v-model="settingsDraft.translation.minChars" label="Mín. por segmento" :min="100" wrapper-style="min-width: 180px; flex: 1" />
          <FieldNumber v-model="settingsDraft.translation.maxRetries" label="Reintentos" :min="0" wrapper-style="min-width: 180px; flex: 1" />
        </div>

        <div style="display: flex; align-items: center; justify-content: space-between; gap: 1rem">
          <div>
            <div style="font-weight: 600">Enable check</div>
            <div class="small muted">Permite verificación adicional en el backend.</div>
          </div>
          <ToggleSwitch v-model="settingsDraft.translation.enableCheck" />
        </div>

        <div style="display: flex; align-items: center; justify-content: space-between; gap: 1rem">
          <div>
            <div style="font-weight: 600">Incluir títulos anteriores</div>
            <div class="small muted">Añade contexto de títulos previos al traducir.</div>
          </div>
          <ToggleSwitch v-model="settingsDraft.translation.includePreviousChapterTitles" />
        </div>
      </div>

      <div v-else class="stack-md">
        <label class="small muted">Notas del proyecto</label>
        <Textarea v-model="settingsDraft.notes" rows="10" fluid />
      </div>
    </div>

    <template #footer>
      <Button severity="secondary" outlined label="Cerrar" @click="emit('update:open', false)" />
      <Button severity="warn" outlined label="Reset" @click="reset" />
      <Button label="Guardar" :loading="saving" @click="save" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import Dialog from "primevue/dialog";
import Button from "primevue/button";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
import Message from "primevue/message";
import ToggleSwitch from "primevue/toggleswitch";
import Select from "primevue/select";
import MetadataEditor from "@/components/MetadataEditor.vue";
import PromptRoleEditor from "@/components/PromptRoleEditor.vue";
import FieldNumber from "@/components/FieldNumber.vue";
import { useProjectSettings } from "@/composables/useProjectSettings";
import { useProviders } from "@/composables/useProviders";
import { useNovels } from "@/composables/useNovels";
import { type Novel, type UpdateNovelInput } from "@/domain";
import { normalizeTranslationOptions } from "@/domain/project-settings";
import { useAppServices } from "@/app/services";

const props = defineProps<{
  open: boolean;
  novel: Novel;
  onSaveNovel: (patch: UpdateNovelInput) => Promise<void>;
}>();

const emit = defineEmits<{
  (e: "update:open", value: boolean): void;
  (e: "cover-updated", novel: Novel): void;
}>();

const { api, defaults } = useAppServices();
const router = useRouter();
const toast = useToast();
const { deleteNovel } = useNovels();
const novelRef = computed(() => props.novel);
const { settings, globalPrompts, loading: settingsLoading } = useProjectSettings(novelRef);
const { providers, byId, loading: providersLoading } = useProviders();
const activeTab = ref("novel");
const saving = ref(false);
const uploadingCover = ref(false);
const tagSuggestions = ref<string[]>([]);
const seriesSuggestions = ref<string[]>([]);
const novelDraft = ref<Novel>(JSON.parse(JSON.stringify(props.novel)) as Novel);
const settingsDraft = ref(JSON.parse(JSON.stringify(settings.value)));
const timeoutSec = ref<number | null>(null);
let pendingCoverFile: File | undefined;

function onSelectCover(file: File) {
  pendingCoverFile = file;
}

async function onRemoveCover() {
  pendingCoverFile = undefined;
}

async function onDeleteNovel() {
  try {
    await deleteNovel(props.novel.id);
    emit("update:open", false);
    toast.add({ severity: "success", summary: "Novela eliminada", life: 2500 });
    await router.push("/");
  } catch (err) {
    toast.add({
      severity: "error",
      summary: "No se pudo eliminar la novela",
      detail: err instanceof Error ? err.message : String(err),
      life: 4000,
    });
  }
}

const providerOptions = computed(() => providers.value);

const modelOptions = computed(() => {
  const info = byId.value.get(settingsDraft.value.ai.provider);
  if (info) return [...info.models];
  return [];
});

function onProviderChange(event: { value: string }) {
  const info = byId.value.get(event.value);
  if (!info) return;
  if (!info.models.includes(settingsDraft.value.ai.model)) {
    settingsDraft.value.ai.model = info.defaultModel;
  }
}

type PromptRole = "translation" | "refine" | "check";

const globalSystemPrompts = computed<Record<PromptRole, string | undefined>>(() => {
  const map: Record<PromptRole, string | undefined> = { translation: undefined, refine: undefined, check: undefined };
  for (const p of globalPrompts.value) {
    if (!p.active) continue;
    if (p.key === "translation" || p.key === "refine" || p.key === "check") {
      map[p.key] = p.prompt.systemPrompt;
    }
  }
  return map;
});

function globalSystemPrompt(role: PromptRole): string {
  return globalSystemPrompts.value[role] ?? "";
}

function effectiveSystemPrompt(role: PromptRole): string {
  return novelDraft.value.prompts[role]?.systemPrompt ?? globalSystemPrompts.value[role] ?? "";
}

function isOverridden(role: PromptRole): boolean {
  return novelDraft.value.prompts[role]?.systemPrompt != null;
}

function setSystemPrompt(role: PromptRole, value: string): void {
  const trimmed = value ?? "";
  const globalValue = globalSystemPrompts.value[role];
  const isCustom = trimmed.length > 0 && trimmed !== globalValue;
  const nextPrompts = { ...novelDraft.value.prompts };
  if (isCustom) {
    nextPrompts[role] = { ...(nextPrompts[role] ?? {}), systemPrompt: trimmed };
  } else {
    delete nextPrompts[role];
  }
  novelDraft.value = { ...novelDraft.value, prompts: nextPrompts };
}

const tabs = [
  { value: "novel", label: "Novela" },
  { value: "glossary", label: "Glosario" },
  { value: "prompts", label: "Prompts" },
  { value: "ai", label: "IA" },
  { value: "translation", label: "Traducción" },
  { value: "notes", label: "Notas" },
];

const draftInitialized = ref(false);

async function resetDraft() {
  const base = JSON.parse(JSON.stringify(props.novel)) as Novel;
  novelDraft.value = {
    ...base,
  };
  settingsDraft.value = JSON.parse(JSON.stringify(settings.value));
  activeTab.value = "novel";
  const ms = settingsDraft.value.ai.timeoutMs;
  timeoutSec.value = ms ? Math.round(ms / 1000) : null;
  draftInitialized.value = true;
  try {
    tagSuggestions.value = await api.novels.listTagSuggestions();
  } catch {
    tagSuggestions.value = [];
  }
  try {
    seriesSuggestions.value = await api.novels.listSeriesSuggestions();
  } catch {
    seriesSuggestions.value = [];
  }
}

watch(
  () => [props.open, settingsLoading.value, settings.value] as const,
  async () => {
    if (!props.open) {
      draftInitialized.value = false;
      return;
    }
    if (draftInitialized.value) return;
    if (settingsLoading.value) return;
    await resetDraft();
    draftInitialized.value = true;
  },
  { immediate: true },
);

function addGlossaryEntry() {
  novelDraft.value.glossary = [
    ...novelDraft.value.glossary,
    { id: crypto.randomUUID(), source: "", target: "", context: "" },
  ];
}

function removeGlossaryEntry(id: string) {
  novelDraft.value.glossary = novelDraft.value.glossary.filter((entry) => entry.id !== id);
}

function reset() {
  settingsDraft.value = {
    notes: "",
    glossary: [],
    prompts: {},
    ai: { provider: "", model: "", timeoutMs: undefined },
    translation: normalizeTranslationOptions(defaults.value?.translation),
    cleanupRules: [],
  };

  novelDraft.value = {
    ...props.novel,
    glossary: [],
    prompts: {},
    notes: "",
    aiOptions: { provider: "", model: "", timeoutMs: undefined },
    translationOptions: normalizeTranslationOptions(defaults.value?.translation),
    cleanupRules: [],
    url: "",
    customCommands: "",
  };
}

async function save() {
  saving.value = true;
  try {
    settingsDraft.value.ai.timeoutMs = timeoutSec.value != null ? timeoutSec.value * 1000 : undefined;
    await props.onSaveNovel({
      sourceLanguage: novelDraft.value.sourceLanguage,
      targetLanguage: novelDraft.value.targetLanguage,
      sourceTitle: novelDraft.value.sourceTitle,
      sourceAuthor: novelDraft.value.sourceAuthor,
      sourceDescription: novelDraft.value.sourceDescription,
      sourceSeries: novelDraft.value.sourceSeries,
      sourceNumber: novelDraft.value.sourceNumber,
      targetTitle: novelDraft.value.targetTitle,
      targetAuthor: novelDraft.value.targetAuthor,
      targetDescription: novelDraft.value.targetDescription,
      targetSeries: novelDraft.value.targetSeries,
      targetNumber: novelDraft.value.targetNumber,
      glossary: novelDraft.value.glossary,
      prompts: novelDraft.value.prompts,
      notes: settingsDraft.value.notes,
      aiOptions: settingsDraft.value.ai,
      translationOptions: settingsDraft.value.translation,
      cleanupRules: novelDraft.value.cleanupRules,
      url: novelDraft.value.url,
      customCommands: novelDraft.value.customCommands,
      status: novelDraft.value.status,
      tags: novelDraft.value.tags,
    });
    if (pendingCoverFile) {
      uploadingCover.value = true;
      const updated = await api.novels.uploadCover(props.novel.id, pendingCoverFile);
      pendingCoverFile = undefined;
      emit("cover-updated", updated);
    }
    emit("update:open", false);
  } finally {
    saving.value = false;
    uploadingCover.value = false;
  }
}
</script>
