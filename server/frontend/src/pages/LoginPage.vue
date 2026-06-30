<template>
  <div class="auth-page">
    <Card class="auth-card">
      <template #title>Iniciar sesión</template>
      <template #content>
        <div class="stack-md">
          <div>
            <label class="small muted">Email</label>
            <InputText v-model="email" type="email" fluid />
          </div>
          <div>
            <label class="small muted">Contraseña</label>
            <Password v-model="password" fluid toggleMask :feedback="false" />
          </div>
          <Message v-if="error" severity="error">{{ error }}</Message>
          <Button label="Entrar" :loading="loading" @click="submit" />
          <Button label="Crear cuenta" severity="secondary" outlined @click="router.push('/register')" />
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import Button from "primevue/button";
import Message from "primevue/message";
import { useAppServices } from "@/app/services";

const router = useRouter();
const route = useRoute();
const { login } = useAppServices();
const email = ref("");
const password = ref("");
const loading = ref(false);
const error = ref<string | null>(null);

async function submit() {
  loading.value = true;
  error.value = null;
  try {
    await login({ email: email.value, password: password.value });
    await router.push(String(route.query.redirect || "/"));
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1rem;
}

.auth-card {
  width: 100%;
  max-width: 420px;
}

:deep(.p-card) {
  width: 100%;
  max-width: 100%;
}

:deep(.p-card-body),
:deep(.p-card-content),
:deep(.p-password),
:deep(.p-password-input),
:deep(.p-inputtext),
:deep(.p-button) {
  width: 100%;
  max-width: 100%;
}

@media (max-width: 640px) {
  .auth-page {
    padding: 0.75rem;
  }
}
</style>
