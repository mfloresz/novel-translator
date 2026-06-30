<template>
  <AppLayout>
    <div class="stack-lg" style="max-width: 960px; margin: 0 auto">
      <div>
        <h1 style="margin: 0 0 0.25rem">Operaciones</h1>
        <p class="muted" style="margin: 0">Actualizaciones y traducciones masivas.</p>
      </div>

      <BatchUpdatePanel />
      <BatchTranslatePanel />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from "@/components/AppLayout.vue";
import BatchUpdatePanel from "@/features/novels/BatchUpdatePanel.vue";
import BatchTranslatePanel from "@/features/novels/BatchTranslatePanel.vue";
</script>
