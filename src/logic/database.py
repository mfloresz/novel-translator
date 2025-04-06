import sqlite3
import os
import json
from typing import List, Dict, Union, Optional

class TranslationDatabase:
    def __init__(self, directory: str):
        """
        Inicializa la base de datos en el directorio de trabajo.

        Args:
            directory (str): Directorio de trabajo donde se creará la base de datos
        """
        self.directory = directory
        self.db_path = os.path.join(directory, '.translation_records.db')
        self.initialize_database()

    def initialize_database(self) -> None:
        """Crea la base de datos y la tabla si no existen"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translations (
                        filename TEXT PRIMARY KEY,
                        source_lang TEXT,
                        target_lang TEXT,
                        translated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error inicializando la base de datos: {e}")
            # Si falla SQLite, intentar crear un JSON como respaldo
            self._create_json_backup()

    def _create_json_backup(self) -> None:
        """Crea un archivo JSON como respaldo si SQLite falla"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        if not os.path.exists(json_path):
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({"translations": []}, f)

    def is_file_translated(self, filename: str) -> bool:
        """
        Verifica si un archivo ya ha sido traducido.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM translations WHERE filename = ?",
                    (filename,)
                )
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.Error:
            # Si falla SQLite, intentar leer del JSON
            return self._check_json_record(filename)

    def _check_json_record(self, filename: str) -> bool:
        """Verifica el registro en el archivo JSON de respaldo"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
                return any(record['filename'] == filename
                         for record in records.get('translations', []))
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    def add_translation_record(self, filename: str, source_lang: str,
                             target_lang: str) -> bool:
        """
        Registra una traducción exitosa.

        Args:
            filename (str): Nombre del archivo traducido
            source_lang (str): Idioma de origen
            target_lang (str): Idioma de destino

        Returns:
            bool: True si se registró correctamente, False en caso contrario
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO translations
                    (filename, source_lang, target_lang)
                    VALUES (?, ?, ?)
                ''', (filename, source_lang, target_lang))
                conn.commit()
                return True
        except sqlite3.Error:
            # Si falla SQLite, intentar guardar en JSON
            return self._add_json_record(filename, source_lang, target_lang)

    def _add_json_record(self, filename: str, source_lang: str,
                        target_lang: str) -> bool:
        """Añade un registro al archivo JSON de respaldo"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        try:
            # Leer registros existentes
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            else:
                records = {"translations": []}

            # Añadir nuevo registro
            record = {
                "filename": filename,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "translated_date": str(datetime.now())
            }

            # Actualizar o añadir registro
            translations = records.get('translations', [])
            for i, existing in enumerate(translations):
                if existing['filename'] == filename:
                    translations[i] = record
                    break
            else:
                translations.append(record)
            records['translations'] = translations

            # Guardar actualizaciones
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2)
            return True
        except Exception as e:
            print(f"Error guardando en JSON: {e}")
            return False

    def get_all_translated_files(self) -> List[Dict[str, str]]:
        """
        Obtiene la lista de todos los archivos traducidos.

        Returns:
            List[Dict[str, str]]: Lista de diccionarios con información de traducciones
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT filename, source_lang, target_lang, translated_date "
                    "FROM translations"
                )
                return [
                    {
                        "filename": row[0],
                        "source_lang": row[1],
                        "target_lang": row[2],
                        "translated_date": row[3]
                    }
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error:
            # Si falla SQLite, intentar leer del JSON
            return self._get_json_records()

    def _get_json_records(self) -> List[Dict[str, str]]:
        """Obtiene los registros del archivo JSON de respaldo"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
                return records.get('translations', [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def clear_records(self) -> bool:
        """
        Limpia todos los registros de traducción.

        Returns:
            bool: True si se limpiaron los registros correctamente
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM translations")
                conn.commit()
                return True
        except sqlite3.Error:
            return False
