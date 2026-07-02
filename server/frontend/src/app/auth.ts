import { computed, ref } from "vue";
import type { AuthResponse, AuthUser } from "@/api/types";

const THEME_KEY = "theme";

const user = ref<AuthUser | null>(null);
const ready = ref(false);

let systemThemeListenerAttached = false;

export const authState = {
  user,
  ready,
  isAuthenticated: computed(() => Boolean(user.value)),
};

export function getStoredTheme(): "light" | "dark" | "system" {
  return (
    (localStorage.getItem(THEME_KEY) as "light" | "dark" | "system" | null) ||
    "system"
  );
}

export function applyTheme(theme: "light" | "dark" | "system") {
  const root = document.documentElement;
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const effective =
    theme === "system" ? (media.matches ? "dark" : "light") : theme;

  root.classList.toggle("dark", effective === "dark");
  root.style.colorScheme = effective;
  localStorage.setItem(THEME_KEY, theme);

  if (!systemThemeListenerAttached) {
    media.addEventListener("change", () => {
      const storedTheme = getStoredTheme();
      if (storedTheme === "system") applyTheme("system");
    });
    systemThemeListenerAttached = true;
  }
}

export function setAuth(result: AuthResponse) {
  user.value = result.user;
  applyTheme(result.user.theme || "system");
}

export function setAuthReady() {
  ready.value = true;
}

export function clearAuth() {
  user.value = null;
  applyTheme(getStoredTheme());
}
