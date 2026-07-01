import type { ApiErrorPayload } from "@/api/types";
import { clearAuth, getAuthToken } from "@/app/auth";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export type HttpClientConfig = {
  baseUrl: string;
};

export function createHttpClient(config: HttpClientConfig) {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers = new Headers(init?.headers ?? undefined);
    const isFormData =
      typeof FormData !== "undefined" && init?.body instanceof FormData;
    const token = getAuthToken();

    if (!isFormData && !headers.has("Content-Type") && init?.body) {
      headers.set("Content-Type", "application/json");
    }
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(`${config.baseUrl}${path}`, {
      ...init,
      headers,
    });

    if (!response.ok) {
      const payload = (await response
        .json()
        .catch(() => ({}))) as ApiErrorPayload;
      if (response.status === 401) {
        clearAuth();
      }
      throw new ApiError(
        payload.error?.message || payload.message || `HTTP ${response.status}`,
        response.status,
        payload.error?.code,
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  async function downloadBlob(path: string): Promise<Blob> {
    const headers = new Headers();
    const token = getAuthToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(`${config.baseUrl}${path}`, { headers });

    if (!response.ok) {
      if (response.status === 401) {
        clearAuth();
      }
      throw new ApiError(`HTTP ${response.status}`, response.status);
    }

    return response.blob();
  }

  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body?: BodyInit | object) =>
      request<T>(path, {
        method: "POST",
        body:
          body instanceof FormData || typeof body === "string"
            ? body
            : JSON.stringify(body ?? {}),
      }),
    put: <T>(path: string, body?: BodyInit | object) =>
      request<T>(path, {
        method: "PUT",
        body:
          body instanceof FormData || typeof body === "string"
            ? body
            : JSON.stringify(body ?? {}),
      }),
    patch: <T>(path: string, body?: BodyInit | object) =>
      request<T>(path, {
        method: "PATCH",
        body:
          body instanceof FormData || typeof body === "string"
            ? body
            : JSON.stringify(body ?? {}),
      }),
    delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
    downloadBlob: downloadBlob,
  };
}
