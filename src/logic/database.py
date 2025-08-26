import sqlite3
import os
import json
from typing import List, Dict, Union, Optional
from datetime import datetime
from pathlib import Path

class TranslationDatabase:
    def __init__(self, directory: str):
        """
        Inicializa la base de datos en el directorio de trabajo.

        Args:
            directory (str): Directorio de trabajo donde se creará la base de datos
        """
        self.db_path = os.path.join(directory, '.translation_records.db')
        self.directory = directory # Guardar la ruta para los backups en JSON
        self.initialize_database()

    def _migrate_database(self, cursor: sqlite3.Cursor) -> None:
        """
        Migra la estructura de la base de datos de la versión antigua (basada en directorios)
        a la nueva (basada en un ID estático).
        """
        # Migración para book_metadata
        cursor.execute("PRAGMA table_info(book_metadata)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'directory' in columns:
            # Leer datos antiguos
            cursor.execute("SELECT title, author, description FROM book_metadata LIMIT 1")
            old_data = cursor.fetchone()

            # Renombrar tabla antigua
            cursor.execute("DROP TABLE book_metadata")

            # Crear tabla nueva
            cursor.execute('''
                CREATE TABLE book_metadata (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    author TEXT,
                    description TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insertar datos antiguos en la nueva tabla si existían
            if old_data:
                self.save_book_metadata(old_data[0], old_data[1], old_data[2] or "")

        # Migración para custom_terms
        cursor.execute("PRAGMA table_info(custom_terms)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'directory' in columns:
            # Leer datos antiguos
            cursor.execute("SELECT terms FROM custom_terms LIMIT 1")
            old_data = cursor.fetchone()

            # Renombrar tabla antigua
            cursor.execute("DROP TABLE custom_terms")

            # Crear tabla nueva
            cursor.execute('''
                CREATE TABLE custom_terms (
                    id TEXT PRIMARY KEY,
                    terms TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insertar datos antiguos en la nueva tabla si existían
            if old_data:
                self.save_custom_terms(old_data[0])

    def initialize_database(self) -> None:
        """Crea la base de datos y las tablas si no existen"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # --- Migración de Esquema ---
                self._migrate_database(cursor)

                # --- Creación de Tablas (si no existen) ---
                # Tabla de traducciones (sin cambios)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translations (
                        filename TEXT PRIMARY KEY,
                        source_lang TEXT,
                        target_lang TEXT,
                        status INTEGER DEFAULT 1,
                        translated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Tabla para términos personalizados (nuevo esquema)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS custom_terms (
                        id TEXT PRIMARY KEY,
                        terms TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Tabla para metadatos del libro (nuevo esquema)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS book_metadata (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        author TEXT,
                        description TEXT,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # --- Migraciones de Datos Antiguas (se mantienen por si acaso) ---
                try:
                    cursor.execute("ALTER TABLE translations ADD COLUMN status INTEGER DEFAULT 1")
                except sqlite3.OperationalError:
                    pass
                
                cursor.execute('''
                    UPDATE translations 
                    SET status = 1 
                    WHERE status IS NULL OR status = 0
                ''')

                try:
                    cursor.execute("ALTER TABLE book_metadata ADD COLUMN description TEXT")
                except sqlite3.OperationalError:
                    pass

                conn.commit()
        except sqlite3.Error as e:
            print(f"Error inicializando la base de datos: {e}")
            self._create_json_backup()

    def _create_json_backup(self) -> None:
        """Crea un archivo JSON como respaldo si SQLite falla"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        if not os.path.exists(json_path):
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({"translations": [], "custom_terms": "", "book_metadata": {}}, f)

    def is_file_translated(self, filename: str) -> bool:
        """Verifica si un archivo ya ha sido traducido."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT status FROM translations WHERE filename = ?",
                    (filename,)
                )
                result = cursor.fetchone()
                return result[0] == 1 if result else False
        except sqlite3.Error:
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
        """Registra una traducción exitosa."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO translations
                    (filename, source_lang, target_lang, status)
                    VALUES (?, ?, ?, 1)
                ''', (filename, source_lang, target_lang))
                conn.commit()
                return True
        except sqlite3.Error:
            return self._add_json_record(filename, source_lang, target_lang)

    def _add_json_record(self, filename: str, source_lang: str,
                        target_lang: str) -> bool:
        """Añade un registro al archivo JSON de respaldo"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            else:
                records = {"translations": [], "custom_terms": ""}

            record = {
                "filename": filename,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "translated_date": str(datetime.now())
            }

            translations = records.get('translations', [])
            translations.append(record)
            records['translations'] = translations

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2)
            return True
        except Exception as e:
            print(f"Error guardando en JSON: {e}")
            return False

    def get_all_translated_files(self) -> List[Dict[str, str]]:
        """Obtiene la lista de todos los archivos traducidos."""
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

    def save_custom_terms(self, terms: str) -> bool:
        """Guarda los términos personalizados para el proyecto actual."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO custom_terms (id, terms, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', ('project_settings', terms))
                conn.commit()
                return True
        except sqlite3.Error:
            return self._save_terms_to_json(terms)

    def get_custom_terms(self) -> str:
        """Recupera los términos personalizados para el proyecto actual."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT terms FROM custom_terms WHERE id = ?",
                    ('project_settings',)
                )
                result = cursor.fetchone()
                return result[0] if result else ""
        except sqlite3.Error:
            return self._get_terms_from_json()

    def _save_terms_to_json(self, terms: str) -> bool:
        """Guarda los términos en el archivo JSON de respaldo"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            else:
                records = {"translations": [], "custom_terms": ""}

            records['custom_terms'] = terms

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2)
            return True
        except Exception as e:
            print(f"Error guardando términos en JSON: {e}")
            return False

    def _get_terms_from_json(self) -> str:
        """Recupera los términos del archivo JSON de respaldo"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
                return records.get('custom_terms', "")
        except (FileNotFoundError, json.JSONDecodeError):
            return ""

    def save_book_metadata(self, title: str, author: str, description: str = "") -> bool:
        """Guarda los metadatos del libro para el proyecto actual."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO book_metadata (id, title, author, description, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', ('project_settings', title, author, description))
                conn.commit()
                return True
        except sqlite3.Error:
            return self._save_metadata_to_json(title, author, description)

    def get_book_metadata(self) -> Dict[str, str]:
        """Recupera los metadatos del libro para el proyecto actual."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT title, author, description FROM book_metadata WHERE id = ?",
                    ('project_settings',)
                )
                result = cursor.fetchone()
                if result:
                    return {"title": result[0] or "", "author": result[1] or "", "description": result[2] or ""}
                return {"title": "", "author": "", "description": ""}
        except sqlite3.Error:
            return self._get_metadata_from_json()

    def _save_metadata_to_json(self, title: str, author: str, description: str = "") -> bool:
        """Guarda los metadatos en el archivo JSON de respaldo"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            else:
                records = {"translations": [], "custom_terms": "", "book_metadata": {}}

            records['book_metadata'] = {
                "title": title,
                "author": author,
                "description": description,
                "last_updated": str(datetime.now())
            }

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2)
            return True
        except Exception as e:
            print(f"Error guardando metadatos en JSON: {e}")
            return False

    def _get_metadata_from_json(self) -> Dict[str, str]:
        """Recupera los metadatos del archivo JSON de respaldo"""
        json_path = os.path.join(self.directory, '.translation_records.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
                metadata = records.get('book_metadata', {})
                return {
                    "title": metadata.get('title', ''),
                    "author": metadata.get('author', ''),
                    "description": metadata.get('description', '')
                }
        except (FileNotFoundError, json.JSONDecodeError):
            return {"title": "", "author": "", "description": ""}