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
        self.directory = Path(directory).as_posix()
        self.initialize_database()

    def initialize_database(self) -> None:
        """Crea la base de datos y las tablas si no existen"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Tabla de traducciones existente
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translations (
                        filename TEXT PRIMARY KEY,
                        source_lang TEXT,
                        target_lang TEXT,
                        status INTEGER DEFAULT 1,  -- 1 para archivos ya traducidos
                        translated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Nueva tabla para términos personalizados
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS custom_terms (
                        directory TEXT PRIMARY KEY,
                        terms TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Nueva tabla para metadatos del libro (título, autor y descripción)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS book_metadata (
                        directory TEXT PRIMARY KEY,
                        title TEXT,
                        author TEXT,
                        description TEXT,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Migración: agregar columna status si no existe
                try:
                    cursor.execute("ALTER TABLE translations ADD COLUMN status INTEGER DEFAULT 1")
                except sqlite3.OperationalError:
                    # La columna ya existe o hay otro error, continuar
                    pass
                
                # Migración: actualizar registros existentes que no tienen status
                # Si un registro existe en la tabla, asumimos que ya fue traducido (status = 1)
                cursor.execute('''
                    UPDATE translations 
                    SET status = 1 
                    WHERE status IS NULL OR status = 0
                ''')

                # Migración: agregar columna description si no existe
                try:
                    cursor.execute("ALTER TABLE book_metadata ADD COLUMN description TEXT")
                except sqlite3.OperationalError:
                    # La columna ya existe o hay otro error, continuar
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
        """
        Verifica si un archivo ya ha sido traducido.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT status FROM translations WHERE filename = ?",
                    (filename,)
                )
                result = cursor.fetchone()
                # 1 es el código para "Traducido"
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
            for i, existing in enumerate(translations):
                if existing['filename'] == filename:
                    translations[i] = record
                    break
            else:
                translations.append(record)
            records['translations'] = translations

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
        """
        Guarda los términos personalizados para el directorio actual.

        Args:
            terms (str): Términos personalizados a guardar

        Returns:
            bool: True si se guardaron correctamente, False en caso contrario
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO custom_terms (directory, terms, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (self.directory, terms))
                conn.commit()
                return True
        except sqlite3.Error:
            return self._save_terms_to_json(terms)

    def get_custom_terms(self) -> str:
        """
        Recupera los términos personalizados para el directorio actual.

        Returns:
            str: Términos personalizados guardados o cadena vacía si no hay
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT terms FROM custom_terms WHERE directory = ?",
                    (self.directory,)
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
        """
        Guarda los metadatos del libro (título, autor y descripción) para el directorio actual.

        Args:
            title (str): Título del libro
            author (str): Autor del libro
            description (str): Descripción del libro

        Returns:
            bool: True si se guardaron correctamente, False en caso contrario
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO book_metadata (directory, title, author, description, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (self.directory, title, author, description))
                conn.commit()
                return True
        except sqlite3.Error:
            return self._save_metadata_to_json(title, author, description)

    def get_book_metadata(self) -> Dict[str, str]:
        """
        Recupera los metadatos del libro para el directorio actual.

        Returns:
            Dict[str, str]: Diccionario con 'title', 'author' y 'description' o vacío si no hay datos
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT title, author, description FROM book_metadata WHERE directory = ?",
                    (self.directory,)
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
