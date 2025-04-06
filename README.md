# Novel Manager

Una aplicación de escritorio para gestionar, procesar y traducir novelas y documentos de texto, con funcionalidades específicas para el manejo de capítulos y creación de ebooks.

## Características

### Gestión de Archivos
- Interfaz gráfica intuitiva para navegación y organización de archivos
- Vista previa y acceso rápido a documentos
- Soporte para archivos de texto (.txt)
- Sistema de seguimiento del estado de los archivos

### Traducción Automática
![Traducción](assets/translate.webp)

- Integración con APIs de traducción:
  - Google Gemini
  - Together AI
- Soporte para múltiples idiomas:
  - Español
  - Inglés
  - Francés
  - Alemán
  - Italiano
- Funciones avanzadas:
  - Control de rango de capítulos
  - Sistema de pausas automáticas
  - Base de datos para registro de traducciones
  - Gestión de errores y recuperación

### Limpieza de Archivos
![Limpieza](assets/clean.webp)

- Múltiples modos de limpieza:
  - Eliminar contenido después de texto específico
  - Eliminar duplicados
  - Eliminar líneas específicas
  - Eliminar líneas en blanco múltiples
  - Buscar y reemplazar texto
- Vista previa de cambios
- Procesamiento por lotes

### Creación de EPUB
![epub](assets/ebook.webp)

- Conversión de archivos de texto a formato EPUB
- Personalización de metadatos
- Soporte para imágenes de portada
- Numeración automática de capítulos
- Estilos CSS predefinidos

## Requisitos

### Dependencias
```bash
PyQt6
ebooklib
requests
sqlite3
```

### Sistemas Operativos
- Windows
- Linux (KDE, GNOME)
- macOS

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/usuario/novel-manager.git
cd novel-manager
```

2. Crear entorno virtual:
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
   - Usar el botón "Navegar" para seleccionar la carpeta de trabajo
   - Los archivos .txt se cargarán automáticamente

2. **Limpieza de Archivos**
   - Seleccionar pestaña "Limpiar"
   - Elegir modo de limpieza
   - Especificar rango de capítulos (opcional)
   - Confirmar operación

3. **Traducción**
   - Seleccionar pestaña "Traducir"
   - Configurar API key y proveedor
   - Seleccionar idiomas de origen/destino
   - Iniciar traducción

4. **Creación de EPUB**
   - Seleccionar pestaña "Ebook"
   - Completar metadatos
   - Seleccionar imagen de portada (opcional)
   - Crear EPUB

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
