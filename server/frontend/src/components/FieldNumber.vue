<template>
  <div :style="wrapperStyle">
    <label class="small muted">{{ label }}</label>
    <InputNumber
      :model-value="modelValue"
      :min="allowClear ? undefined : min"
      :placeholder="placeholder"
      fluid
      :allow-empty="allowClear"
      @update:model-value="$emit('update:modelValue', allowClear ? ($event ?? null) : ($event ?? min))"
    />
  </div>
</template>

<script setup lang="ts">
import InputNumber from 'primevue/inputnumber';

withDefaults(
  defineProps<{
    label: string;
    modelValue: number | null;
    min?: number;
    placeholder?: string;
    allowClear?: boolean;
    wrapperStyle?: string;
  }>(),
  {
    min: 0,
    placeholder: undefined,
    allowClear: false,
    wrapperStyle: 'flex: 1; min-width: 220px',
  },
);

defineEmits<{ (e: 'update:modelValue', value: number | null): void }>();
</script>
