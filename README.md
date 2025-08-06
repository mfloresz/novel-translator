<h1 align="center">
  <img src="src/gui/icons/app.png" width="150" height="150" alt="App Icon" />
</h1>

# Novel Translator

Una aplicación de escritorio completa para gestionar, procesar y traducir novelas y documentos de texto. Diseñada específicamente para manejar proyectos literarios grandes con soporte para múltiples proveedores de IA, gestión avanzada de capítulos, creación de ebooks e importación de EPUBs.

## Características

### Gestión de Archivos
- Interfaz gráfica intuitiva para navegación y organización de archivos
- **Importación de archivos EPUB:** Convierte EPUBs existentes a archivos de texto para edición
- **Actualización automática:** Botón "Actualizar" para sincronizar la lista de archivos
- Vista previa y acceso rápido a documentos
- Soporte para archivos de texto (.txt)
- Sistema de seguimiento del estado de los archivos con colores identificativos
- **Gestión de metadatos:** Guarda y carga automáticamente título, autor y descripción del proyecto
- **Carpetas recientes:** Sistema de historial de directorios visitados para acceso rápido

### Importación de EPUB
- Conversión automática de archivos EPUB a archivos de texto (.txt)
- Extracción inteligente de capítulos y contenido
- Preservación de la estructura narrativa original
- Creación automática de directorio organizado
- Validación de archivos EPUB antes de la importación
- **Opciones de importación configurables:**
  - Añadir numeración automática al contenido
  - Insertar títulos de capítulos en el contenido

### Traducción Automática Avanzada
![Traducción](assets/translate.webp)

- **Múltiples proveedores de IA integrados:**
  - Google Gemini (Flash 2.5 Lite)
  - Chutes AI (Mistral Small 3.2, Skyfall V2)
  - Together AI (Llama 3.3 70B)
  - DeepInfra (Sao10K L3.3-70B-Euryale, Qwen 3 A3B)
  - OpenAI (GPT-4.1 Nano)
- **Soporte multilingüe:**
  - Español (México) con traducción contextual
  - Inglés
  - Detección automática de idioma
- **Funciones avanzadas de traducción:**
  - **Control granular de rango de capítulos** (individual o por lotes)
  - **Comprobación automática de calidad** con sistema de reintento
  - **Refinamiento automático** para mejorar la calidad del texto traducido
  - **Segmentación inteligente de texto** que respeta oraciones y párrafos
  - Sistema de pausas automáticas entre traducciones para evitar límites de API
  - Base de datos integrada para evitar retraducciones
  - **Términos personalizados por proyecto** con persistencia automática
  - Traducción individual por capítulo desde la interfaz principal
  - Sistema de logging detallado para monitoreo de traducciones

**Pestaña Traducir:** Permite traducir archivos de texto utilizando APIs de traducción, con soporte para segmentación, revisión y refinamiento de la traducción.

*   **API Key:** Ingresa la clave de la API del proveedor de traducción (se carga automáticamente desde .env).
*   **Proveedor:** Selecciona el proveedor de la API de traducción.
*   **Modelo:** Elige el modelo de traducción específico del proveedor seleccionado.
*   **Idioma Origen:** Selecciona el idioma original del texto a traducir.
*   **Idioma Destino:** Define el idioma al que se traducirá el texto.
*   **Segmentar texto:** Opción para dividir el texto en segmentos más pequeños para optimizar la traducción.
*   **Comprobar traducción:** Activa/desactiva la verificación automática de calidad después de la traducción.
*   **Refinar traducción:** Activa/desactiva el refinamiento automático para mejorar la calidad de la traducción inicial.
*   **Términos Personalizados:** Ingresa términos específicos con su traducción para garantizar coherencia (se guardan automáticamente).
*   **Rango de Capítulos:** Define el rango de capítulos a traducir (desde - hasta).
*   **Traducir:** Inicia el proceso de traducción por lotes.
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

### Creación de Ebooks EPUB
![epub](assets/ebook.webp)
- **Conversión profesional de TXT a EPUB** con estructura literaria
- **Gestión avanzada de metadatos:**
  - Guardado y carga automática de título, autor y descripción
  - Persistencia entre sesiones de trabajo
  - Sincronización con base de datos local
- **Detección inteligente de portadas:**
  - Búsqueda automática de archivos (cover.jpg, portada.png, etc.)
  - Soporte para múltiples formatos de imagen
  - Selección manual alternativa
- **Organización literativa:**
  - Numeración automática de capítulos
  - Estructura de navegación optimizada
  - Estilos CSS profesionales y responsivos
- **Manejo de metadatos completo** con respaldo automático

**Pestaña Ebook:** Facilita la creación de EPUBs a partir de los archivos de texto.

*   **Título:** Introduce el título del libro (se guarda automáticamente por proyecto).
*   **Autor:** Ingresa el nombre del autor (se guarda automáticamente por proyecto).
*   **Descripción:** Ingresa la descripción o sinopsis del libro (se guarda automáticamente por proyecto).
*   **Guardar Metadatos:** Botón para guardar manualmente título, autor y descripción del proyecto actual.
*   **Portada:**
    - Seleccionar imagen manualmente
    - Detección automática de portadas (cover.jpg, portada.png, etc.)
    - Limpiar portada seleccionada
*   **Rango de Capítulos:** Con opción de incluir todos los capítulos o definir uno específico (desde-hasta).
*   **Crear EPUB:** Inicia la generación del EPUB con las configuraciones proporcionadas.

## Requisitos del Sistema

### Dependencias del Proyecto
```bash
pip install PyQt6>=6.0.0 beautifulsoup4>=4.12.0 pypub3>=2.0.8 requests>=2.28.0 python-dotenv>=1.0.0 Pillow>=10.0.0
```

### Sistemas Operativos Soportados
- **Windows** 10/11
- **Linux** (KDE, GNOME, XFCE, Unity)
- **macOS** 10.14+

### Requisitos Adicionales
- Conexión a internet para servicios de traducción
- Al menos 500MB de espacio libre en disco
- RAM mínima: 4GB (recomendado 8GB+ para archivos grandes)

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

## Configuración Inicial

### Configuración de API Keys
Crea un archivo `.env` en la raíz del proyecto con tus claves de API:
```env
# Google Gemini
GEMINI_API_KEY=tu_clave_google_gemini

# Chutes AI
CHUTES_API_KEY=tu_clave_chutes_ai

# Together AI
TOGETHER_API_KEY=tu_clave_together_ai

# DeepInfra
DEEPINFRA_API_KEY=tu_clave_deepinfra

# OpenAI
OPENAI_API_KEY=tu_clave_openai
```

### Configuración de la Aplicación
La aplicación utiliza archivos de configuración JSON para personalizar su comportamiento:

- **[`src/config/config.json`](src/config/config.json)**: Configuración principal (proveedor, modelo, idiomas, directorio inicial)
- **[`src/config/models/translation_models.json`](src/config/models/translation_models.json)**: Modelos disponibles por proveedor
- **[`src/config/languages.json`](src/config/languages.json)**: Mapeo de idiomas para traducción

### Configuración Avanzada
Puedes personalizar:
- Proveedor y modelo de traducción por defecto
- Idiomas de origen y destino
- Directorio de trabajo inicial
- Tamaño de segmentación para traducciones largas
- Comportamiento de la interfaz de usuario

## Uso

### Iniciar la Aplicación
```bash
python main.py
```

### Flujo de Trabajo Recomendado

#### 1. **Configuración Inicial**
- Configura tus claves API en el archivo `.env`
- Ajusta la configuración de traducción en **Ajustes > Configuración**
- Selecciona tu directorio de trabajo preferido

#### 2. **Importación de Contenido**
**Opción A: Importar desde EPUB**
- Haz clic en "Importar EPUB" y selecciona tu archivo
- Elige opciones de importación (numeración, títulos de capítulos)
- La aplicación creará automáticamente una estructura organizada

**Opción B: Usar archivos existentes**
- Haz clic en "Abrir" y selecciona una carpeta con archivos `.txt`
- La aplicación detectará y organizará los capítulos automáticamente

#### 3. **Gestión de Proyecto**
- **Actualizar:** Sincroniza cambios manuales en los archivos
- **Abrir:** Accede al contenido completo de cualquier capítulo
- **Estado visual:** Colores indican traducciones completadas (verde), errores (rojo) o pendientes (negro)
- **Traducción individual:** Traduce capítulos específicos sin afectar otros
- **Carpetas recientes:** Accede rápidamente a proyectos recientes mediante el botón "Carpetas recientes"

#### 4. **Procesamiento Avanzado**
**Limpieza de Texto:**
- Elimina contenido después de texto específico
- Remueve duplicados y líneas no deseadas
- Busca y reemplaza texto masivamente
- Normaliza espacios y saltos de línea

**Traducción Profesional:**
- Configura proveedor y modelo de IA
- Define términos personalizados por proyecto
- Activa segmentación para textos largos
- Habilita comprobación de calidad y refinamiento
- Monitorea progreso con logging detallado

#### 5. **Generación de Ebooks**
- **Metadatos inteligentes:** Título, autor y descripción se guardan automáticamente
- **Portada automática:** Detección de imágenes de portada en múltiples formatos
- **Estructura profesional:** Navegación optimizada y estilos CSS responsivos
- **Exportación lista:** Compatible con la mayoría de lectores electrónicos

### Características Técnicas Avanzadas

#### Sistema de Base de Datos Híbrida
- **SQLite principal:** Almacenamiento eficiente de traducciones, términos personalizados y metadatos
- **Respaldo JSON automático:** Sistema de recuperación ante fallos de la base de datos
- **Gestión transaccional:** Operaciones atómicas para integridad de datos
- **Indexación optimizada:** Búsqueda rápida de archivos y traducciones

#### Gestión de Estados Inteligente
- **Sistema de colores en tiempo real:**
  - 🔴 **Error:** Problemas en procesamiento
  - 🟢 **Traducido:** Proceso completado exitosamente
  - ⚫ **Pendiente:** Sin procesar o en cola
- **Respaldo automático:** Persistencia de estados entre sesiones
- **Detección de cambios:** Sincronización con modificaciones externas

#### Optimización de Rendimiento
- **Procesamiento asíncrono:** Traducciones en segundo plano sin bloquear la interfaz
- **Segmentación inteligente:** Algoritmo que respeta estructura narrativa al dividir textos largos
- **Gestión de memoria:** Optimizada para archivos grandes (100+ capítulos)
- **Caché de traducciones:** Evita retraducciones innecesarias

#### Sistema de Logging y Monitoreo
- **Registro detallado de sesiones:** Todas las operaciones registradas con timestamps
- **Monitoreo de APIs:** Seguimiento de consumo de tokens y rate limits
- **Diagnóstico de errores:** Información completa para troubleshooting
- **Exportación de logs:** Archivos estructurados para análisis posterior

## Arquitectura del Proyecto

```
novel-manager/
│
├── 📁 src/
│   ├── 📁 gui/                          # Interfaz de Usuario
│   │   ├── 📄 clean.py                  # Panel de limpieza de archivos
│   │   ├── 📄 create.py                 # Panel de creación EPUB
│   │   ├── 📄 translate.py              # Panel de traducción avanzada
│   │   ├── 📄 settings_gui.py           # Diálogo de configuración
│   │   └── 📁 icons/                    # Recursos visuales de la aplicación
│   │
│   ├── 📁 logic/                        # Lógica de Negocio
│   │   ├── 📄 cleaner.py                # Procesamiento de texto
│   │   ├── 📄 creator.py                # Generación de EPUBs
│   │   ├── 📄 database.py               # Gestión de base de datos híbrida
│   │   ├── 📄 epub_importer.py          # Importación de EPUBs
│   │   ├── 📄 functions.py              # Utilidades y validaciones
│   │   ├── 📄 get_path.py               # Selección de directorios
│   │   ├── 📄 loader.py                 # Carga de archivos y metadatos
│   │   ├── 📄 session_logger.py         # Sistema de logging
│   │   ├── 📄 translation_manager.py    # Gestión de traducciones
│   │   ├── 📄 translator.py             # Motor de traducción
│   │   └── 📄 translator_req.py         # Comunicación con APIs
│   │
│   ├── 📁 config/                       # Configuración
│   │   ├── 📄 config.json               # Configuración principal
│   │   ├── 📄 languages.json            # Mapeo de idiomas
│   │   ├── 📁 models/
│   │   │   └── 📄 translation_models.json # Modelos de IA disponibles
│   │   └── 📁 prompts/
│   │       ├── 📄 translation.txt       # Plantilla de traducción
│   │       ├── 📄 check.txt             # Plantilla de verificación
│   │       └── 📄 refine.txt            # Plantilla de refinamiento
│   │
│   └── 📁 resources/                    # Recursos adicionales
│       └── 📄 preset_terms.json         # Términos predefinidos
│
├── 📄 .env                              # Variables de entorno (API keys)
├── 📄 .env.example                      # Plantilla de variables de entorno
├── 📄 main.py                           # Punto de entrada principal
├── 📄 requirements.txt                  # Dependencias del proyecto
├── 📄 install.sh                        # Script de instalación
├── 📄 run_nv.sh                         # Script de ejecución
└── 📄 README.md                         # Documentación completa
```

### Componentes Principales

#### 🎯 Interfaz de Usuario (GUI)
- **PyQt6:** Framework moderno para aplicaciones de escritorio
- **Detección automática de tema:** Soporte para temas claros/oscuros del sistema
- **Interfaz responsive:** Diseño adaptable a diferentes tamaños de pantalla
- **Iconos temáticos:** Sistema de iconos que se adaptan al tema del sistema

#### ⚙️ Motor de Traducción
- **Multi-proveedor:** Soporte para múltiples APIs de IA
- **Segmentación inteligente:** Algoritmo avanzado que preserva estructura narrativa
- **Sistema de calidad:** Comprobación y refinamiento automático
- **Gestión de errores:** Sistema robusto con reintentos y logging

#### 💾 Gestión de Datos
- **Base de datos híbrida:** SQLite + respaldo JSON automático
- **Persistencia:** Todos los datos se guardan automáticamente
- **Integridad:** Sistema de transacciones para datos críticos
- **Rendimiento:** Indexación optimizada para grandes volúmenes de datos

#### 🔌 Integración de APIs
- **Abstracción modular:** Diseño que facilita agregar nuevos proveedores
- **Manejo de rate limits:** Control automático de solicitudes
- **Monitoreo de consumo:** Seguimiento de tokens y costos
- **Sistema de fallback:** Manejo de errores de red y APIs

## Funciones Adicionales

### 🚀 Funcionalidades Destacadas

#### 📂 Sistema de Carpetas Recientes
- **Historial automático:** La aplicación guarda automáticamente los últimos 10 directorios visitados
- **Acceso rápido:** Botón "Carpetas recientes" en la interfaz principal para navegar proyectos anteriores
- **Gestión intuitiva:**
  - Visualización de nombres de carpetas con tooltips mostrando rutas completas
  - Botón de eliminación (×) para remover carpetas específicas del historial
  - Actualización automática al seleccionar una carpeta reciente
- **Persistencia:** Las carpetas recientes se guardan en `src/config/recents.json` entre sesiones
- **Funcionalidad:** Al seleccionar una carpeta reciente, la aplicación la carga automáticamente como directorio de trabajo actual

#### 📚 Sistema de Importación EPUB Avanzado
- **Validación integral:** Verifica estructura y contenido antes de importar
- **Extracción inteligente:** Convierte capítulos a archivos .txt numerados secuencialmente
- **Preservación narrativa:** Mantiene estructura y organización original
- **Metadatos automáticos:** Extrae título, autor y descripción del EPUB original
- **Portada inteligente:** Detección automática de imágenes de portada

#### 🔄 Sistema de Sincronización Inteligente
- **Detección de cambios en tiempo real:** Monitorea modificaciones externas
- **Preservación completa:** Mantiene estados, traducciones y metadatos
- **Gestión dinámica:** Detecta archivos nuevos, eliminados o modificados
- **Reajuste automático:** Mantiene consistencia en numeración y estados

#### 📊 Gestión Avanzada de Metadatos
- **Sistema multi-nivel:** Título, autor, descripción con persistencia total
- **Sincronización global:** Metadatos consistentes en toda la aplicación
- **Importación/exportación:** Compatibilidad con estándares EPUB
- **Historial de cambios:** Seguimiento de modificaciones en metadatos

#### ⚡ Sistema de Traducción de Alto Rendimiento
- **Motor multi-proveedor:** Soporte para múltiples APIs de IA simultáneamente
- **Segmentación narrativa:** Algoritmo avanzado que resporte estructura de historias
- **Sistema de calidad 3 niveles:**
  1. **Traducción inicial** con prompts optimizados
  2. **Refinamiento automático** para mejorar calidad
  3. **Verificación final** con validación cruzada
- **Gestión inteligente de recursos:**
  - Control automático de rate limits
  - Sistema de reintentos con backoff exponencial
  - Monitoreo de consumo de tokens
  - Pausas estratégicas entre solicitudes

#### 🔧 Sistema de Configuración Flexible
- **Configuración por proyecto:** Cada proyecto puede tener su propia configuración
- **Plantillas predefinidas:** Configuraciones optimizadas para diferentes tipos de texto
- **Actualización en caliente:** Cambios de configuración sin reiniciar la aplicación
- **Respaldo automático:** Todas las configuraciones se guardan automáticamente

#### 📈 Sistema de Monitoreo y Diagnóstico
- **Logging estructurado:** Registro detallado de todas las operaciones
- **Métricas de rendimiento:** Tiempos de procesamiento, consumo de recursos
- **Diagnóstico automático:** Detección y reporte de problemas comunes
- **Exportación de informes:** Generación de reportes detallados para análisis

#### 🛡️ Sistema de Respaldo y Recuperación
- **Base de datos híbrida:** SQLite + respaldo JSON automático
- **Puntos de recuperación:** Sistema de checkpoints para operaciones largas
- **Recuperación ante fallos:** Mecanismos automáticos de recuperación ante errores
- **Integridad de datos:** Verificación y reparación automática de datos corruptos
