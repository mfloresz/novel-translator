import {
  computed,
  inject,
  ref,
  type ComputedRef,
  type InjectionKey,
  type Ref,
} from "vue";
import { createApiClient, type ApiClient } from "@/api/client";
import type { AuthResponse, ProviderInfo } from "@/api/types";
import type { ServerDefaults } from "@/domain/project-settings";
import { authState, clearAuth, setAuth, setAuthReady } from "@/app/auth";

export type AppServices = {
  api: ApiClient;
  defaults: Ref<ServerDefaults | null>;
  defaultsLoading: Ref<boolean>;
  loadDefaults: () => Promise<void>;
  providers: ComputedRef<ProviderInfo[]>;
  providerById: ComputedRef<Map<string, ProviderInfo>>;
  loadProviders: () => Promise<void>;
  providersLoading: Ref<boolean>;
  auth: typeof authState;
  restoreSession: () => Promise<void>;
  login: (input: { email: string; password: string }) => Promise<AuthResponse>;
  register: (input: {
    email: string;
    password: string;
    name?: string;
  }) => Promise<AuthResponse>;
  logout: () => Promise<void>;
};

export const appServicesKey: InjectionKey<AppServices> = Symbol("app-services");

export function createAppServices(): AppServices {
  const defaults = ref<ServerDefaults | null>(null);
  const defaultsLoading = ref(false);
  const api = createApiClient(defaults);
  const providerList = ref<ProviderInfo[]>([]);
  const providersLoading = ref(false);

  async function loadDefaults() {
    if (!authState.isAuthenticated.value) return;
    defaultsLoading.value = true;
    try {
      defaults.value = await api.defaults.get();
    } finally {
      defaultsLoading.value = false;
    }
  }

  async function loadProviders() {
    if (!authState.isAuthenticated.value) {
      providerList.value = [];
      return;
    }
    providersLoading.value = true;
    try {
      const res = await api.providers.list();
      providerList.value = res.providers;
    } finally {
      providersLoading.value = false;
    }
  }

  async function restoreSession() {
    if (!authState.token.value) {
      setAuthReady();
      return;
    }
    try {
      const result = await api.auth.refresh();
      setAuth(result);
      await Promise.all([loadDefaults(), loadProviders()]);
    } catch {
      clearAuth();
    } finally {
      setAuthReady();
    }
  }

  async function login(input: { email: string; password: string }) {
    const result = await api.auth.login(input);
    setAuth(result);
    await Promise.all([loadDefaults(), loadProviders()]);
    return result;
  }

  async function register(input: {
    email: string;
    password: string;
    name?: string;
  }) {
    const result = await api.auth.register(input);
    setAuth(result);
    await Promise.all([loadDefaults(), loadProviders()]);
    return result;
  }

  async function logout() {
    try {
      await api.auth.logout();
    } finally {
      clearAuth();
      providerList.value = [];
      defaults.value = null;
    }
  }

  const providers = computed(() => providerList.value);
  const providerById = computed(
    () => new Map(providerList.value.map((p) => [p.id, p])),
  );

  return {
    api,
    defaults,
    defaultsLoading,
    loadDefaults,
    providers,
    providerById,
    loadProviders,
    providersLoading,
    auth: authState,
    restoreSession,
    login,
    register,
    logout,
  };
}

export function useAppServices(): AppServices {
  const services = inject(appServicesKey);
  if (!services) {
    throw new Error("App services are not available");
  }
  return services;
}
