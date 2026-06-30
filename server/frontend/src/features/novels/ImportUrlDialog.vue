<template>
  <Dialog v-model:visible="visible" modal header="Importar novela desde URL" :style="{ width: 'min(520px, 96vw)' }" @after-hide="reset">
    <div class="stack-md">
      <div>
        <label class="small muted">URL de la novela</label>
        <InputText
          v-model="url"
          placeholder="https://novelfire.net/book/..."
          fluid
          :disabled="loading"
          @keydown.enter="handleSearch"
        />
        <div class="small muted" style="margin-top: 0.35rem">
          Sitios soportados: {{ supportedSites.join(", ") }}
        </div>
      </div>

      <Message v-if="error" severity="error">{{ error }}</Message>
    </div>
    <template #footer>
      <Button severity="secondary" outlined label="Cancelar" :disabled="loading" @click="visible = false" />
      <Button
        :label="loading ? 'Buscando...' : 'Buscar'"
        icon="pi pi-search"
        :loading="loading"
        :disabled="!url.trim()"
        @click="handleSearch"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { useNovels } from "@/composables/useNovels";
import type { PreviewUrlResult } from "@/api/types";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  "preview": [preview: PreviewUrlResult];
}>();

const { previewNovelFromUrl } = useNovels();

const visible = computed({
  get: () => props.open,
  set: (value) => emit("update:open", value),
});

const supportedSites = ["novelfire.net", "novelbin.com"];

const url = ref("");
const loading = ref(false);
const error = ref<string | null>(null);

function reset() {
  url.value = "";
  loading.value = false;
  error.value = null;
}

watch(visible, (open) => {
  if (open) reset();
});

async function handleSearch() {
  if (!url.value.trim()) return;
  loading.value = true;
  error.value = null;
  try {
    const preview = await previewNovelFromUrl(url.value.trim());
    emit("preview", preview);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}
</script>
