<template>
  <a href="#main-content" class="skip-link">Saltar al contenido principal</a>

  <div class="app-shell">
    <header class="app-topbar">
      <div class="page-container app-topbar-inner">
        <div class="app-topbar-start">
          <slot name="back-button" />
          <RouterLink to="/" class="app-brand" aria-label="Yara - Inicio">
            <span class="app-brand-icon" aria-hidden="true">
              <i class="pi pi-book" />
            </span>
            <span class="app-brand-text">Yara</span>
          </RouterLink>
        </div>

        <div class="app-topbar-end">
          <Button
            :icon="hasActive ? 'pi pi-spin pi-spinner' : 'pi pi-spinner-dotted'"
            :severity="hasActive ? 'info' : 'secondary'"
            :outlined="!hasActive"
            :aria-label="hasActive ? 'Hay trabajos activos' : 'No hay trabajos activos'"
            :aria-expanded="jobsOpen"
            aria-controls="jobs-drawer"
            text
            rounded
            class="touch-target"
            @click="jobsOpen = true"
          />

          <Button
            :icon="currentThemeIcon"
            severity="secondary"
            text
            rounded
            class="touch-target"
            :aria-label="`Cambiar tema (actual: ${themeLabel})`"
            @click="cycleTheme"
          />

          <Button
            icon="pi pi-user"
            severity="secondary"
            outlined
            rounded
            class="touch-target"
            aria-label="Menú de usuario"
            @click="userMenu.toggle($event)"
          />
          <Menu ref="userMenu" :model="userMenuItems" :popup="true" />

          <Button
            class="mobile-menu-btn touch-target"
            icon="pi pi-bars"
            severity="secondary"
            text
            rounded
            aria-label="Abrir menú de navegación"
            :aria-expanded="mobileNavOpen"
            aria-controls="mobile-nav-drawer"
            style="display: none"
            @click="mobileNavOpen = !mobileNavOpen"
          />
        </div>
      </div>
    </header>

    <Teleport to="body">
      <div
        v-if="mobileNavOpen"
        class="mobile-nav-overlay"
        aria-hidden="true"
        @click="mobileNavOpen = false"
      />
      <nav
        v-if="mobileNavOpen"
        id="mobile-nav-drawer"
        class="mobile-nav-drawer"
        aria-label="Navegación móvil"
      >
        <div class="mobile-nav-header">
          <span class="app-brand-text">Yara</span>
          <Button
            icon="pi pi-times"
            severity="secondary"
            text
            rounded
            class="touch-target"
            aria-label="Cerrar menú"
            @click="mobileNavOpen = false"
          />
        </div>
        <div class="mobile-nav-items">
          <button
            type="button"
            class="mobile-nav-item touch-target"
            @click="handleMobileNav(() => jobsOpen = true)"
          >
            <i class="pi pi-briefcase" aria-hidden="true" />
            <span>Trabajos</span>
            <span v-if="hasActive" class="mobile-nav-badge">•</span>
          </button>
          <button
            type="button"
            class="mobile-nav-item touch-target"
            @click="handleMobileNav(cycleTheme)"
          >
            <i :class="currentThemeIcon" aria-hidden="true" />
            <span>Tema: {{ themeLabel }}</span>
          </button>
          <button
            type="button"
            class="mobile-nav-item touch-target"
            @click="handleMobileNav(() => router.push('/settings'))"
          >
            <i class="pi pi-cog" aria-hidden="true" />
            <span>Configuración</span>
          </button>
          <button
            type="button"
            class="mobile-nav-item touch-target"
            @click="handleMobileNav(() => router.push('/operations'))"
          >
            <i class="pi pi-bolt" aria-hidden="true" />
            <span>Operaciones</span>
          </button>
          <div class="mobile-nav-divider" />
          <button
            type="button"
            class="mobile-nav-item mobile-nav-item--danger touch-target"
            @click="handleMobileNav(() => doLogout())"
          >
            <i class="pi pi-sign-out" aria-hidden="true" />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </nav>
    </Teleport>

    <main id="main-content" class="page-container" tabindex="-1">
      <slot />
    </main>

    <JobsDrawer id="jobs-drawer" v-model:visible="jobsOpen" />
  </div>
</template>

<script setup lang="ts">
import Button from "primevue/button";
import Menu from "primevue/menu";
import { computed, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import JobsDrawer from "@/components/JobsDrawer.vue";
import { applyTheme, getStoredTheme } from "@/app/auth";
import { useActiveJobStatus } from "@/composables/useActiveJobStatus";
import { useAppServices } from "@/app/services";

const router = useRouter();
const { hasActive } = useActiveJobStatus();
const { auth, logout } = useAppServices();
const jobsOpen = ref(false);
const mobileNavOpen = ref(false);
const userMenu = ref();

const theme = ref<"light" | "dark" | "system">(getStoredTheme());

const themeCycle: Array<"light" | "dark" | "system"> = ["system", "light", "dark"];

const themeLabels: Record<"light" | "dark" | "system", string> = {
  system: "Sistema",
  light: "Claro",
  dark: "Oscuro",
};

const themeIcons: Record<"light" | "dark" | "system", string> = {
  system: "pi pi-desktop",
  light: "pi pi-sun",
  dark: "pi pi-moon",
};

const themeLabel = computed(() => themeLabels[theme.value]);
const currentThemeIcon = computed(() => themeIcons[theme.value]);

function cycleTheme() {
  const nextIndex = (themeCycle.indexOf(theme.value) + 1) % themeCycle.length;
  theme.value = themeCycle[nextIndex];
  applyTheme(theme.value);
}

const userMenuItems = computed(() => [
  {
    label: auth.user.value?.email ?? "",
    disabled: true,
    class: "user-menu-email",
  },
  { separator: true },
  {
    label: "Configuración",
    icon: "pi pi-cog",
    command: () => router.push("/settings"),
  },
  {
    label: "Operaciones",
    icon: "pi pi-bolt",
    command: () => router.push("/operations"),
  },
  {
    label: "Cerrar sesión",
    icon: "pi pi-sign-out",
    command: () => doLogout(),
  },
]);

async function doLogout() {
  await logout();
  await router.push("/login");
}

function handleMobileNav(command?: () => void) {
  mobileNavOpen.value = false;
  command?.();
}
</script>

<style scoped>
.skip-link {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 10000;
  padding: 0.5rem 1rem;
  background: var(--btn-primary-bg);
  color: var(--btn-primary-fg);
  font-weight: 600;
  border-radius: 0 0 var(--radius-md) 0;
  clip: rect(0, 0, 0, 0);
  clip-path: inset(50%);
  height: 1px;
  overflow: hidden;
  white-space: nowrap;
  width: 1px;
}

.skip-link:focus {
  clip: auto;
  clip-path: none;
  height: auto;
  overflow: visible;
  width: auto;
}

.app-topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: color-mix(in oklab, var(--surface-elevated) 92%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--divide);
}

.app-topbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 56px;
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
}

.app-topbar-start,
.app-topbar-end {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.app-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.0625rem;
  color: var(--foreground);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-md);
}

.app-brand:hover {
  background: var(--mock-row);
}

.app-brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.875rem;
  height: 1.875rem;
  border-radius: var(--radius-sm);
  background: var(--btn-primary-bg);
  color: var(--btn-primary-fg);
}

.app-brand-text {
  font-weight: 700;
}

@media (max-width: 768px) {
  .app-topbar-inner {
    min-height: 52px;
  }

  .app-brand-text {
    display: none;
  }
}
</style>

<style>
.mobile-nav-overlay {
  position: fixed;
  inset: 0;
  background: var(--surface-overlay);
  z-index: 1000;
}

.mobile-nav-drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: min(280px, 80vw);
  background: var(--surface-elevated);
  border-right: 1px solid var(--divide);
  z-index: 1001;
  display: flex;
  flex-direction: column;
  animation: slideInLeft 0.2s ease-out;
}

.mobile-nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid var(--divide);
}

.mobile-nav-items {
  display: flex;
  flex-direction: column;
  padding: 0.5rem;
  overflow-y: auto;
  gap: 0.25rem;
}

.mobile-nav-item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  width: 100%;
  padding: 0.75rem;
  border: none;
  border-radius: var(--radius-md);
  background: none;
  color: var(--foreground);
  font-size: 0.9375rem;
  cursor: pointer;
  text-align: left;
}

.mobile-nav-item:hover,
.mobile-nav-item:focus-visible {
  background: var(--mock-row-strong);
}

.mobile-nav-item--danger {
  color: var(--red-500);
}

.mobile-nav-divider {
  height: 1px;
  background: var(--divide);
  margin: 0.5rem 0;
}

.mobile-nav-badge {
  margin-left: auto;
  background: var(--p-primary-500);
  color: var(--btn-primary-fg);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-pill);
}

@keyframes slideInLeft {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}
</style>
