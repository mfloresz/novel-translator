<template>
  <AppLayout>
    <div class="stack-lg" style="max-width: 960px; margin: 0 auto">
      <div class="row-between">
        <div>
          <h1 style="margin: 0 0 0.25rem">Configuración</h1>
          <p class="muted" style="margin: 0">Toda la configuración es por usuario y se persiste en el backend.</p>
        </div>
        <Button label="Guardar" icon="pi pi-save" :loading="saving" :disabled="!settings" @click="save" />
      </div>

      <Message v-if="error" severity="error">{{ error }}</Message>
      <ProgressSpinner v-if="loading" style="width: 48px; height: 48px" strokeWidth="4" />

      <template v-else-if="settings">
        <Card>
          <template #title>Tema</template>
          <template #content>
            <Select v-model="settings.theme" :options="themeOptions" optionLabel="label" optionValue="value" fluid />
          </template>
        </Card>

        <Card>
          <template #title>Proveedor de IA</template>
          <template #content>
            <div class="stack-md">
              <div class="row-wrap">
                <div style="flex: 1; min-width: 220px">
                  <label class="small muted">Proveedor activo</label>
                  <Select
                    v-model="settings.ai.provider"
                    :options="providerOptions"
                    optionLabel="name"
                    optionValue="id"
                    :loading="providersLoading"
                    fluid
                    @change="onProviderChange"
                  />
                </div>
                <div style="flex: 1; min-width: 220px">
                  <label class="small muted">Modelo</label>
                  <Select
                    v-model="settings.ai.model"
                    :options="modelOptions"
                    :disabled="!settings.ai.provider"
                    fluid
                  />
                </div>
              </div>
              <div>
                <label class="small muted">Base URL</label>
                <InputText v-model="settings.ai.baseUrl" fluid class="mono" />
              </div>
              <div>
                <label class="small muted">API Key</label>
                <Password v-model="providerApiKey" fluid toggleMask :feedback="false" :placeholder="providerConfigured ? '••••••••••••' : 'Pega una nueva API key'" />
                <div class="small muted" style="margin-top: 0.35rem">
                  <span v-if="providerConfigured">API key configurada{{ activeProvider?.apiKeyUpdatedAt ? ` · actualizada ${formatDate(activeProvider.apiKeyUpdatedAt)}` : '' }}</span>
                  <span v-else>No hay API key configurada para este provider.</span>
                </div>
                <div class="row-wrap" style="margin-top: 0.75rem">
                  <Button label="Reemplazar key" severity="secondary" outlined :disabled="!providerApiKey.trim()" :loading="replacingKey" @click="replaceKey" />
                  <Button label="Eliminar key" severity="danger" outlined :disabled="!providerConfigured" :loading="deletingKey" @click="deleteKey" />
                </div>
              </div>
              <div class="row-wrap">
                <FieldNumber v-model.number="timeoutSec" label="Timeout (segundos)" :min="10" wrapper-style="min-width: 180px; flex: 1" />
              </div>
            </div>
          </template>
        </Card>

        <Card>
          <template #title>Parámetros globales de traducción</template>
          <template #content>
            <div class="stack-md">
              <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem">
                <div>
                  <div style="font-weight: 600">Auto segmentación</div>
                  <div class="small muted">Divide capítulos largos antes de enviarlos al proveedor AI.</div>
                </div>
                <ToggleSwitch v-model="settings.translation.autoSegment" />
              </div>

              <div class="row-wrap">
                <FieldNumber v-model="settings.translation.thresholdChars" label="Umbral auto" :min="1000" />
                <FieldNumber v-model="settings.translation.maxChars" label="Máx. por segmento" :min="500" />
                <FieldNumber v-model="settings.translation.minChars" label="Mín. por segmento" :min="100" />
              </div>
              <div class="row-wrap">
                <FieldNumber v-model="settings.translation.maxRetries" label="Máx. reintentos" :min="0" />
                <FieldNumber v-model="settings.translation.concurrency" label="Concurrencia" :min="1" />
              </div>

              <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem">
                <div>
                  <div style="font-weight: 600">Enable check</div>
                  <div class="small muted">Activa verificación posterior en flujos compatibles.</div>
                </div>
                <ToggleSwitch v-model="settings.translation.enableCheck" />
              </div>

              <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem">
                <div>
                  <div style="font-weight: 600">Incluir títulos previos</div>
                  <div class="small muted">Añade títulos anteriores como contexto adicional.</div>
                </div>
                <ToggleSwitch v-model="settings.translation.includePreviousChapterTitles" />
              </div>
            </div>
          </template>
        </Card>

        <Card>
          <template #title>Prompts generales</template>
          <template #content>
            <Accordion :value="0">
              <AccordionPanel v-for="prompt in prompts" :key="prompt.id" :value="prompt.id">
                <AccordionHeader>
                  <div style="display: flex; align-items: center; gap: 0.75rem">
                    <strong>{{ prompt.label || prompt.key }}</strong>
                    <Tag :severity="prompt.active ? 'success' : 'secondary'" :value="prompt.active ? 'Activo' : 'Inactivo'" />
                  </div>
                </AccordionHeader>
                <AccordionContent>
                  <div class="stack-md">
                    <div>
                      <label class="small muted">System prompt</label>
                      <Textarea v-model="prompt.prompt.systemPrompt" rows="5" fluid class="mono" />
                    </div>
                    <div>
                      <label class="small muted">User prompt</label>
                      <Textarea v-model="prompt.prompt.userPrompt" rows="5" fluid class="mono" />
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem">
                      <span class="small muted">Activo</span>
                      <ToggleSwitch v-model="prompt.active" />
                    </div>
                  </div>
                </AccordionContent>
              </AccordionPanel>
            </Accordion>
          </template>
        </Card>
      </template>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useToast } from "primevue/usetoast";
import AppLayout from "@/components/AppLayout.vue";
import Button from "primevue/button";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import ToggleSwitch from "primevue/toggleswitch";
import Textarea from "primevue/textarea";
import Tag from "primevue/tag";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Accordion from "primevue/accordion";
import AccordionPanel from "primevue/accordionpanel";
import AccordionHeader from "primevue/accordionheader";
import AccordionContent from "primevue/accordioncontent";
import Select from "primevue/select";
import FieldNumber from "@/components/FieldNumber.vue";
import { applyTheme } from "@/app/auth";
import { useAppServices } from "@/app/services";
import { useProviders } from "@/composables/useProviders";
import type { GeneralPromptRecord, ServerSettings } from "@/api/types";

const toast = useToast();
const { api, loadProviders } = useAppServices();
const { providers, byId, loading: providersLoading, reload: reloadProviders } = useProviders();
const loading = ref(true);
const saving = ref(false);
const replacingKey = ref(false);
const deletingKey = ref(false);
const error = ref<string | null>(null);
const settings = ref<ServerSettings | null>(null);
const prompts = ref<GeneralPromptRecord[]>([]);
const providerApiKey = ref("");
const timeoutSec = ref(120);

const themeOptions = [
  { label: "Sistema", value: "system" },
  { label: "Claro", value: "light" },
  { label: "Oscuro", value: "dark" },
];

onMounted(() => {
  void load();
});

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const [settingsResponse, promptsResponse] = await Promise.all([
      api.settings.get(),
      api.prompts.list(),
      reloadProviders(),
    ]);
    settings.value = settingsResponse;
    prompts.value = promptsResponse;
    providerApiKey.value = "";
    timeoutSec.value = settingsResponse.ai.timeoutMs
      ? Math.round(settingsResponse.ai.timeoutMs / 1000)
      : 120;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

const providerOptions = computed(() => providers.value);
const activeProvider = computed(() => {
  if (!settings.value) return null;
  return providers.value.find((provider) => provider.id === settings.value?.ai.provider) ?? null;
});
const providerConfigured = computed(() => Boolean(activeProvider.value?.apiKeyConfigured));
const modelOptions = computed(() => {
  if (!settings.value) return [] as string[];
  const info = byId.value.get(settings.value.ai.provider);
  return info?.models ?? [];
});

function onProviderChange() {
  if (!settings.value) return;
  const info = byId.value.get(settings.value.ai.provider);
  if (!info) return;
  if (!info.models.includes(settings.value.ai.model)) {
    settings.value.ai.model = info.defaultModel;
  }
  settings.value.ai.baseUrl = info.baseUrl;
  providerApiKey.value = "";
}

async function replaceKey() {
  if (!settings.value || !providerApiKey.value.trim()) return;
  replacingKey.value = true;
  try {
    await api.providers.replaceKey(settings.value.ai.provider, providerApiKey.value.trim());
    providerApiKey.value = "";
    await loadProviders();
    toast.add({ severity: "success", summary: "API key actualizada", life: 2500 });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    replacingKey.value = false;
  }
}

async function deleteKey() {
  if (!settings.value) return;
  deletingKey.value = true;
  try {
    await api.providers.deleteKey(settings.value.ai.provider);
    await loadProviders();
    toast.add({ severity: "success", summary: "API key eliminada", life: 2500 });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    deletingKey.value = false;
  }
}

async function save() {
  if (!settings.value) return;
  saving.value = true;
  error.value = null;
  try {
    settings.value.ai.timeoutMs = timeoutSec.value * 1000;
    settings.value = await api.settings.update(settings.value);
    applyTheme(settings.value.theme);
    await Promise.all([
      api.providers.update(settings.value.ai.provider, {
        model: settings.value.ai.model,
        baseUrl: settings.value.ai.baseUrl,
        timeoutMs: settings.value.ai.timeoutMs,
      }),
      Promise.all(prompts.value.map((prompt) => api.prompts.upsert({
        key: prompt.key,
        label: prompt.label,
        description: prompt.description,
        prompt: prompt.prompt,
        active: prompt.active,
      }))),
    ]);
    await Promise.all([reloadProviders(), load()]);
    toast.add({ severity: "success", summary: "Configuración guardada", life: 2500 });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    saving.value = false;
  }
}

function formatDate(value?: string) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}
</script>
