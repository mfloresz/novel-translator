import os
from .folder_structure import NovelFolderStructure

class CleanerLogic:
    def __init__(self):
        self.tasks = {
            "remove_after": self._remove_after_text,
            "remove_duplicates": self._remove_duplicates,
            "remove_line": self._remove_line,
            "remove_multiple_blanks": self._remove_multiple_blanks,
            "search_replace": self._search_replace
        }

    def clean_files(self, directory, files, clean_mode, search_text, replace_text=""):
        """Procesa una lista específica de archivos aplicando limpieza a ambas carpetas"""
        # Asegurar que la estructura de carpetas exista
        NovelFolderStructure.ensure_structure(directory)

        files_processed = 0
        files_modified = 0

        originals_path = NovelFolderStructure.get_originals_path(directory)
        translated_path = NovelFolderStructure.get_translated_path(directory)

        for filename in files:
            # Limpiar en 'translated' si el archivo existe
            translated_file = translated_path / filename
            if translated_file.exists():
                if self.clean_file(str(translated_file), str(translated_file), clean_mode, search_text, replace_text):
                    files_modified += 1

            # Limpiar en 'originals' si el archivo existe
            originals_file = originals_path / filename
            if originals_file.exists():
                if self.clean_file(str(originals_file), str(originals_file), clean_mode, search_text, replace_text):
                    files_modified += 1

            files_processed += 1

        return files_processed, files_modified

    def clean_file(self, input_path, output_path, clean_mode, search_text, replace_text=""):
        """Limpia un archivo según el modo especificado"""
        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                original_lines = file.readlines()

            lines = original_lines.copy()

            # Eliminar líneas en blanco al inicio
            while lines and not lines[0].strip():
                lines.pop(0)

            # Aplicar el modo de limpieza seleccionado
            if clean_mode in self.tasks:
                if clean_mode == "search_replace":
                    lines = self.tasks[clean_mode](lines, search_text, replace_text)
                else:
                    lines = self.tasks[clean_mode](lines, search_text)

            # Eliminar líneas en blanco al final
            while lines and not lines[-1].strip():
                lines.pop()

            # Verificar si el contenido cambió
            if lines == original_lines:
                return False  # No hubo cambios

            with open(output_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            return True  # Hubo cambios

        except Exception as e:
            print(f"Error processing {input_path}: {str(e)}")
            return False

    def _remove_after_text(self, lines, search_text):
        """Elimina todo el contenido después del texto especificado"""
        for i, line in enumerate(lines):
            if line.strip().startswith(search_text):
                return lines[:i]
        return lines

    def _remove_duplicates(self, lines, search_text):
        """Elimina líneas duplicadas, conservando solo la última occurrence"""
        if not search_text:
            return lines
        
        duplicates = []
        for i, line in enumerate(lines):
            if line.strip().startswith(search_text):
                duplicates.append(i)
        
        if len(duplicates) <= 1:
            return lines  # No hay duplicados o solo una occurrence
        
        # Eliminar todas las líneas duplicadas excepto la última
        lines_to_remove = duplicates[:-1]  # Todas excepto la última
        
        # Crear nueva lista sin las líneas duplicadas (excepto la última)
        result = []
        for i, line in enumerate(lines):
            if i not in lines_to_remove:
                result.append(line)
        
        return result

    def _remove_line(self, lines, search_text):
        """Elimina las líneas que comienzan con el texto especificado"""
        return [line for line in lines if not line.strip().startswith(search_text)]

    def _remove_multiple_blanks(self, lines, _):
        """Elimina líneas en blanco múltiples dejando solo una"""
        result = []
        prev_blank = False

        for line in lines:
            is_blank = not line.strip()
            if is_blank:
                if not prev_blank:
                    result.append(line)
                prev_blank = True
            else:
                result.append(line)
                prev_blank = False

        return result

    def _search_replace(self, lines, search_text, replace_text):
        """Busca y reemplaza texto en todas las líneas"""
        if not search_text:
            return lines
        return [line.replace(search_text, replace_text) for line in lines]
