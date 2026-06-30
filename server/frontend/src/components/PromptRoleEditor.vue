<template>
  <Card>
    <template #title>{{ title }}</template>
    <template #content>
      <div class="stack-md">
        <div>
          <div class="row-between" style="margin-bottom: 0.25rem">
            <label class="small muted">System prompt</label>
            <span v-if="overridden" class="small" style="color: var(--p-primary-color)">Override de la novela</span>
            <span v-else-if="globalValue" class="small muted">Usando prompt global</span>
          </div>
          <Textarea :model-value="modelValue" rows="6" fluid class="mono" @update:model-value="emit('update:modelValue', $event)" />
          <div v-if="!modelValue && globalValue" class="small muted" style="margin-top: 0.25rem">
            Vacío = usa el prompt global. Edita para crear un override.
          </div>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card';
import Textarea from 'primevue/textarea';

defineProps<{
  title: string;
  modelValue: string;
  globalValue?: string;
  overridden?: boolean;
}>();

const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>();
</script>
