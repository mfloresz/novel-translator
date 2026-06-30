<template>
  <article v-for="i in count" :key="i" class="library-card" aria-hidden="true">
    <Skeleton shape="rectangle" width="100%" class="library-cover-skeleton" borderRadius="16px" />
    <Skeleton width="80%" height="0.875rem" borderRadius="6px" />
    <Skeleton width="40%" height="0.75rem" borderRadius="6px" />
  </article>
</template>

<script setup lang="ts">
import Skeleton from "primevue/skeleton";

withDefaults(defineProps<{ count?: number }>(), { count: 12 });
</script>

<style scoped>
.library-cover-skeleton {
  aspect-ratio: 2 / 3;
}
</style>
