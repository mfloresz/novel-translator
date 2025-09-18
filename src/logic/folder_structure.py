import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, List

class NovelFolderStructure:
    """
    Gestiona la estructura de carpetas para novelas con rutas relativas.
    Estructura esperada:
    novela/
    ├── originals/          # Archivos TXT originales
    ├── translated/         # Archivos TXT traducidos
    ├── cover.*             # Portada (copiada automáticamente)
    └── .translation_records.db  # Base de datos
    """

    ORIGINALS_DIR = "originals"
    TRANSLATED_DIR = "translated"
    DB_FILE = ".translation_records.db"

    @staticmethod
    def ensure_structure(novel_path: str) -> bool:
        """
        Asegura que la estructura de carpetas exista para una novela.
        Crea las carpetas necesarias si no existen.

        Args:
            novel_path: Ruta absoluta al directorio de la novela

        Returns:
            bool: True si la estructura está correcta, False si hay error
        """
        try:
            novel_path = Path(novel_path)

            # Crear carpetas principales
            originals_path = novel_path / NovelFolderStructure.ORIGINALS_DIR
            translated_path = novel_path / NovelFolderStructure.TRANSLATED_DIR

            originals_path.mkdir(exist_ok=True)
            translated_path.mkdir(exist_ok=True)

            return True
        except Exception as e:
            print(f"Error creando estructura de carpetas: {e}")
            return False

    @staticmethod
    def get_originals_path(novel_path: str) -> Path:
        """Obtiene la ruta a la carpeta originals"""
        return Path(novel_path) / NovelFolderStructure.ORIGINALS_DIR

    @staticmethod
    def get_translated_path(novel_path: str) -> Path:
        """Obtiene la ruta a la carpeta translated"""
        return Path(novel_path) / NovelFolderStructure.TRANSLATED_DIR

    @staticmethod
    def get_db_path(novel_path: str) -> Path:
        """Obtiene la ruta al archivo de base de datos"""
        return Path(novel_path) / NovelFolderStructure.DB_FILE

    @staticmethod
    def to_relative_path(novel_path: str, absolute_path: str) -> str:
        """
        Convierte una ruta absoluta a relativa respecto al directorio de la novela.

        Args:
            novel_path: Ruta absoluta al directorio de la novela
            absolute_path: Ruta absoluta a convertir

        Returns:
            str: Ruta relativa (ej: '/originals/file.txt')
        """
        try:
            novel_path = Path(novel_path)
            absolute_path = Path(absolute_path)

            # Si la ruta absoluta está dentro del directorio de la novela
            if absolute_path.is_relative_to(novel_path):
                relative_path = absolute_path.relative_to(novel_path)
                return f"/{relative_path}"
            else:
                # Si no está dentro, devolver la ruta absoluta (para compatibilidad)
                return str(absolute_path)
        except Exception:
            return str(absolute_path)

    @staticmethod
    def to_absolute_path(novel_path: str, relative_path: str) -> str:
        """
        Convierte una ruta relativa a absoluta.

        Args:
            novel_path: Ruta absoluta al directorio de la novela
            relative_path: Ruta relativa (ej: '/originals/file.txt')

        Returns:
            str: Ruta absoluta
        """
        try:
            if relative_path.startswith('/'):
                # Es una ruta relativa a la novela
                return str(Path(novel_path) / relative_path[1:])
            else:
                # Es una ruta absoluta o relativa al directorio actual
                return relative_path
        except Exception:
            return relative_path

    @staticmethod
    def copy_cover_to_root(novel_path: str, cover_source: str) -> Optional[str]:
        """
        Copia una imagen de portada al directorio raíz de la novela.

        Args:
            novel_path: Ruta al directorio de la novela
            cover_source: Ruta absoluta a la imagen de portada fuente

        Returns:
            Optional[str]: Ruta relativa a la portada copiada, o None si falla
        """
        try:
            novel_path = Path(novel_path)
            cover_source = Path(cover_source)

            if not cover_source.exists():
                return None

            # Determinar extensión del archivo
            cover_ext = cover_source.suffix
            cover_dest = novel_path / f"cover{cover_ext}"

            # Copiar la imagen
            shutil.copy2(cover_source, cover_dest)

            # Retornar ruta relativa
            return f"/cover{cover_ext}"

        except Exception as e:
            print(f"Error copiando portada: {e}")
            return None

    @staticmethod
    def find_cover_in_novel(novel_path: str) -> Optional[str]:
        """
        Busca archivos de portada en el directorio de la novela.

        Args:
            novel_path: Ruta al directorio de la novela

        Returns:
            Optional[str]: Ruta relativa a la portada encontrada, o None
        """
        try:
            novel_path = Path(novel_path)

            # Patrones comunes de nombres de portada
            cover_patterns = [
                'cover.jpg', 'cover.jpeg', 'cover.png',
                'portada.jpg', 'portada.jpeg', 'portada.png'
            ]

            for pattern in cover_patterns:
                cover_path = novel_path / pattern
                if cover_path.exists():
                    return f"/{pattern}"

            return None

        except Exception:
            return None

    @staticmethod
    def get_original_files(novel_path: str) -> List[str]:
        """
        Obtiene lista de archivos TXT en la carpeta originals.

        Args:
            novel_path: Ruta al directorio de la novela

        Returns:
            List[str]: Lista de nombres de archivos
        """
        try:
            originals_path = NovelFolderStructure.get_originals_path(novel_path)
            if not originals_path.exists():
                return []

            return [f for f in os.listdir(originals_path)
                   if f.lower().endswith('.txt') and (originals_path / f).is_file()]

        except Exception:
            return []

    @staticmethod
    def get_translated_files(novel_path: str) -> List[str]:
        """
        Obtiene lista de archivos TXT en la carpeta translated.

        Args:
            novel_path: Ruta al directorio de la novela

        Returns:
            List[str]: Lista de nombres de archivos
        """
        try:
            translated_path = NovelFolderStructure.get_translated_path(novel_path)
            if not translated_path.exists():
                return []

            return [f for f in os.listdir(translated_path)
                   if f.lower().endswith('.txt') and (translated_path / f).is_file()]

        except Exception:
            return []

    @staticmethod
    def move_file_to_originals(novel_path: str, file_path: str) -> bool:
        """
        Mueve un archivo al directorio originals.

        Args:
            novel_path: Ruta al directorio de la novela
            file_path: Ruta absoluta al archivo a mover

        Returns:
            bool: True si se movió correctamente
        """
        try:
            NovelFolderStructure.ensure_structure(novel_path)

            file_path = Path(file_path)
            originals_path = NovelFolderStructure.get_originals_path(novel_path)

            # Mover archivo
            shutil.move(str(file_path), str(originals_path / file_path.name))

            return True

        except Exception as e:
            print(f"Error moviendo archivo a originals: {e}")
            return False

    @staticmethod
    def copy_file_to_originals(novel_path: str, file_path: str) -> bool:
        """
        Copia un archivo al directorio originals.

        Args:
            novel_path: Ruta al directorio de la novela
            file_path: Ruta absoluta al archivo a copiar

        Returns:
            bool: True si se copió correctamente
        """
        try:
            NovelFolderStructure.ensure_structure(novel_path)

            file_path = Path(file_path)
            originals_path = NovelFolderStructure.get_originals_path(novel_path)

            # Copiar archivo
            shutil.copy2(str(file_path), str(originals_path / file_path.name))

            return True

        except Exception as e:
            print(f"Error copiando archivo a originals: {e}")
            return False