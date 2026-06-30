export type CleanMode =
  | "remove_after"
  | "remove_duplicates"
  | "remove_line"
  | "remove_multiple_blanks"
  | "search_replace";

export type CleanOptions = {
  mode: CleanMode;
  searchText: string;
  replaceText?: string;
  caseSensitive?: boolean;
  useRegex?: boolean;
};

export type CleanResult = {
  original: string;
  cleaned: string;
  changed: boolean;
  removedLines: number;
};

export const CLEAN_MODE_LABELS: Record<CleanMode, string> = {
  remove_after: "Eliminar después de texto",
  remove_duplicates: "Eliminar duplicados",
  remove_line: "Eliminar líneas",
  remove_multiple_blanks: "Normalizar espacios",
  search_replace: "Buscar y reemplazar",
};

export const CLEAN_MODE_DESCRIPTIONS: Record<CleanMode, string> = {
  remove_after:
    "Borra todo el contenido desde la primera línea que comience con el texto indicado.",
  remove_duplicates:
    "Conserva solo la última línea que coincida; elimina las repeticiones anteriores.",
  remove_line: "Elimina cada línea que comience con el texto indicado.",
  remove_multiple_blanks: "Colapsa líneas en blanco consecutivas en una sola.",
  search_replace:
    "Reemplaza un texto por otro en todo el contenido (acepta regex).",
};
