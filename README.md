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
  - DeepInfra
- Soporte para múltiples idiomas:
  - Español
  - Inglés
  - Francés
  - Alemán
  - Italiano
- Funciones avanzadas:
  - Control de rango de capítulos
  - Sistema de pausas automáticas
  - Base de datos para registro de traducciones y términos personalizados
  - Gestión de errores y recuperación

**Pestaña Traducir:** Permite traducir archivos de texto utilizando APIs de traducción, con soporte para segmentación y revisión de la traducción.

*   **API Key:** Ingresa la clave de la API del proveedor de traducción que se utilizará.
*   **Proveedor:** Selecciona el proveedor de la API de traducción (ej: Google Gemini, Together AI, DeepInfra).
*   **Modelo:** Elige el modelo de traducción específico del proveedor seleccionado.
*   **Idioma Origen:** Selecciona el idioma original del texto a traducir.
*   **Idioma Destino:** Define el idioma al que se traducirá el texto.
*   **Segmentar texto (caracteres):** Divide el texto en segmentos más pequeños para optimizar la traducción. Puedes especificar la cantidad de caracteres por segmento.
*   **Términos Personalizados:** Ingresa términos específicos con su traducción para garantizar coherencia.
*   **Rango de Capítulos:** Define el rango de capítulos a traducir (desde - hasta).
*   **Traducir:** Inicia el proceso de traducción.
*   **Detener:** Interrumpe el proceso en curso.

### Limpieza de Archivos
![Limpieza](assets/clean.webp)

#### Modos de Limpieza
1. **Eliminar contenido después de texto específico**
   - Elimina todo el contenido del archivo a partir de un texto indicado
   - Útil para eliminar anuncios, notas, enlaces

2. **Eliminar duplicados**
   - Elimina secciones duplicadas que comienzan en un texto marcado

3. **Eliminar línea específica**
   - Elimina líneas que empiezan con un texto determinado

4. **Eliminar líneas en blanco múltiples**
   - Normaliza el espaciado eliminando líneas en blanco consecutivas

5. **Buscar y reemplazar texto**
   - Reemplaza todas las ocurrencias de un texto por otro

#### Control de Rango
- Procesamiento selectivo por rango de capítulos (todos o de - a)

#### Características adicionales
- Vista previa antes de aplicar cambios
- Procesamiento por lotes
- Respaldo automático de archivos originales
- Sistema de recuperación ante errores
- Registro de operaciones

### Creación de EPUB
![epub](assets/ebook.webp)
- Conversión de archivos de texto a EPUB
- Personalización de metadatos
- Soporte para imágenes de portada
- Numeración automática de capítulos
- Estilos CSS predefinidos

**Pestaña Ebook:** Facilita la creación de EPUBs a partir de los archivos de texto.

*   **Título:** Introduce el título del libro.
*   **Autor:** Ingresa el nombre del autor.
*   **Portada:**
    - Seleccionar imagen
    - Limpiar portada
*   **Rango de Capítulos:** Con opción de incluir todos los capítulos o definir uno específico (desde-hasta).
*   **Crear EPUB:** Inicia la generación del EPUB con las configuraciones proporcionadas.

## Requisitos

### Dependencias
```bash
pip install PyQt6 beautifulsoup4 pypub3 requests python-dotenv Pillow
```

### Sistemas Operativos
- Windows
- Linux (KDE, GNOME)
- macOS

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/usuario/novel-manager.git
cd novel-manager
```

2. Crea el entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

## Configuración

- Añade tus claves API en el archivo `.env` en la raíz del proyecto:
```
GEMINI_API_KEY=tu_clave_google_gemini
TOGETHER_API_KEY=tu_clave_together_ai
DEEPINFRA_API_KEY=tu_clave_deepinfra
```

## Uso

### Iniciar la aplicación
```bash
python main.py
```

### Flujo de trabajo básico

1. **Seleccionar Directorio**
   - Usa el botón "Navegar" para escoger la carpeta donde están tus textos.
   - Los archivos `.txt` se cargarán automáticamente, mostrando su estado.

2. **Limpiar Archivos**
   - En la pestaña "Limpiar", selecciona modo y rango.
   - Ajusta opciones y presiona "Limpiar" para aplicar cambios.

3. **Traducir**
   - En la pestaña "Traducir", configura la API, proveedor, modelos, idiomas.
   - Define rango de capítulos, términos personalizados.
   - Presiona "Traducir" para comenzar.
   - Puedes detener en cualquier momento con "Detener".

4. **Crear EPUB**
   - En la pestaña "Ebook", ingresa título, autor, portada opcional.
   - Define el rango de capítulos o todos.
   - Presiona "Crear EPUB" para generar el libro.
   - Se guardará en el directorio seleccionado.

### Funciones Adicionales
- **Vista previa:** en la misma interfaz, para ver detalles
- **Soporte de lotes:** gestionar múltiples archivos
- **Registros:** de operaciones para auditoría y recuperación

## Estructura del Proyecto

```
novel-manager/
│
├── src/
│   ├── gui/
│   │   ├── clean.py           # Interfaz de limpieza
│   │   ├── create.py          # interfaz creación EPUB
│   │   └── translate.py       # interfaz traducción
│   │
│   └── logic/
│       ├── cleaner.py         # lógica limpieza
│       ├── creator.py         # lógica creación EPUB
│       ├── database.py        # registros en SQLite y JSON
│       ├── functions.py       # funciones auxiliares
│       ├── get_path.py         # selección de directorio
│       ├── loader.py          # carga de archivos
│       ├── translation_manager.py # gestión de traducciones
│       └── translator.py      # lógica de traducción
│
├── main.py                     # entrada principal
├── requirements.txt            # dependencias
└── README.md                   # documentación actualizada
```
