import type { ComputedRef, Ref } from "vue";
import type { ProviderInfo } from "@/api/types";
import { useAppServices } from "@/app/services";

export function useProviders(): {
  providers: ComputedRef<ProviderInfo[]>;
  byId: ComputedRef<Map<string, ProviderInfo>>;
  loading: Ref<boolean>;
  reload: () => Promise<void>;
} {
  const { providers, providerById, providersLoading, loadProviders } = useAppServices();
  return {
    providers,
    byId: providerById,
    loading: providersLoading,
    reload: loadProviders,
  };
}
