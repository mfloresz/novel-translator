# Novel Manager

Una aplicación de escritorio para gestionar, procesar y traducir novelas y documentos de texto, con funcionalidades específicas para el manejo de capítulos y creación de ebooks.

## Características Principales

### 1. Gestión de Archivos
- Interfaz gráfica intuitiva para navegación de archivos
- Visualización organizada de capítulos
- Vista previa y acceso rápido a archivos
- Soporte para múltiples formatos de texto

### 2. Traducción Automática

![Traducción](../assets/translate.webp)

- Integración con API de Google Gemini
- Soporte para múltiples idiomas:
  - Español
  - Inglés
  - Francés
  - Alemán
  - Italiano
- Control de rango de capítulos
- Seguimiento del estado de traducción
- Base de datos para registro de traducciones
- Pausas automáticas entre traducciones

### 3. Limpieza de Archivos

![Limpieza](../assets/clean.webp)

- Múltiples modos de limpieza:
  - Eliminar contenido después de texto específico
  - Eliminar duplicados
  - Eliminar líneas específicas
  - Eliminar líneas en blanco múltiples
- Procesamiento por lotes
- Vista previa de cambios

### 4. Creación de EPUB

![epub](../assets/ebook.webp)

- Conversión de archivos de texto a EPUB
- Personalización de metadatos:
  - Título
  - Autor
  - Portada
- Estilización automática del contenido
- Soporte para imágenes de portada
- Numeración automática de capítulos

## Requisitos del Sistema

### Dependencias
```bash
PyQt6
ebooklib
requests
sqlite3
```

### Sistemas Operativos Soportados
- Windows
- Linux (KDE, GNOME)
- macOS

## Instalación

1. Clonar el repositorio:
```bash
git clone [URL-del-repositorio]
cd novel-manager
```

2. Crear y activar entorno virtual (opcional pero recomendado):
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Uso

### Iniciar la Aplicación
```bash
python main.py
```

### Flujo de Trabajo Básico

1. **Selección de Directorio**
   - Clic en "Navegar" para seleccionar el directorio de trabajo
   - Los archivos .txt se cargarán automáticamente

2. **Limpieza de Archivos**
   - Seleccionar la pestaña "Limpiar"
   - Elegir modo de limpieza
   - Especificar rango de capítulos (opcional)
   - Clic en "Limpiar"

3. **Traducción**
   - Seleccionar la pestaña "Traducir"
   - Ingresar API key de Google
   - Seleccionar idiomas de origen y destino
   - Especificar rango de capítulos
   - Clic en "Traducir"

4. **Creación de EPUB**
   - Seleccionar la pestaña "Ebook"
   - Completar metadatos
   - Seleccionar imagen de portada (opcional)
   - Especificar rango de capítulos (opcional)
   - Clic en "Crear EPUB"

## Estructura del Proyecto

```
novel-manager/
│
├── src/
│   ├── gui/
│   │   ├── clean.py
│   │   ├── create.py
│   │   └── translate.py
│   │
│   └── logic/
│       ├── cleaner.py
│       ├── creator.py
│       ├── database.py
│       ├── functions.py
│       ├── get_path.py
│       ├── loader.py
│       ├── translation_manager.py
│       └── translator.py
│
├── main.py
├── requirements.txt
└── README.md
```
