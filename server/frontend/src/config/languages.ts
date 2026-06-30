export type LanguageInfo = {
  code: string;
  name: string;
  region?: string;
};

export const LANGUAGES: LanguageInfo[] = [
  { code: "auto", name: "Detección automática" },
  { code: "es", name: "Español" },
  { code: "es-MX", name: "Español (México)" },
  { code: "en", name: "Inglés" },
  { code: "en-US", name: "Inglés (EE.UU.)" },
  { code: "en-GB", name: "Inglés (Reino Unido)" },
  { code: "fr", name: "Francés" },
  { code: "de", name: "Alemán" },
  { code: "it", name: "Italiano" },
  { code: "pt", name: "Portugués" },
  { code: "pt-BR", name: "Portugués (Brasil)" },
  { code: "ja", name: "Japonés" },
  { code: "ko", name: "Coreano" },
  { code: "zh", name: "Chino" },
  { code: "zh-CN", name: "Chino simplificado" },
  { code: "ru", name: "Ruso" },
  { code: "ar", name: "Árabe" },
  { code: "nl", name: "Neerlandés" },
  { code: "pl", name: "Polaco" },
  { code: "tr", name: "Turco" },
  { code: "vi", name: "Vietnamita" },
  { code: "th", name: "Tailandés" },
  { code: "id", name: "Indonesio" }
];

const LANGUAGE_NAMES: Record<string, string> = LANGUAGES.reduce((acc, item) => {
  acc[item.code] = item.name;
  return acc;
}, {} as Record<string, string>);

export function getLanguageName(code: string): string {
  return LANGUAGE_NAMES[code] ?? code;
}
