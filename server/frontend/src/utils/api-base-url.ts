function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, "");
}

export function getApiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_URL || "").trim();
  if (!raw) return "";

  const withoutTrailingSlash = trimTrailingSlashes(raw);
  return withoutTrailingSlash.replace(/\/api$/, "");
}
