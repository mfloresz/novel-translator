<div align="center">
  <img src="src/gui/icons/app.png" width="150" height="150" alt="App Icon" />
  <h1>Novel Translator</h1>
  <p>
    <b>Una aplicación de escritorio completa para gestionar, procesar y traducir novelas y documentos de texto.</b>
  </p>
  <p>
    <i><a href="README.md">English Version</a>.</i>
  </p>
</div>

Una aplicación de escritorio completa para gestionar, procesar y traducir novelas y documentos de texto. Diseñada específicamente para manejar proyectos literarios grandes con soporte para múltiples proveedores de IA, gestión avanzada de capítulos, creación de ebooks e importación de EPUBs.

## Motivaciones

En sí lo hice porque tengo algunas novelas que aunque se tradujeron al español la calidad era muy mala y también para traducir novelas que aún no hay traducciones de calidad al español y me sirve para usarla junto con la herramienta LightNovel-Crawler(https://github.com/dipu-bd/lightnovel-crawler).

## Guía Rápida

### Requisitos
- Python 3.8+
- UV (gestor de paquetes de Python)
- PyQt6>=6.0.0
- Ver [Instalación](#instalación) para dependencias completas

### Instalación
1. Clona el repositorio:
```bash
git clone https://github.com/mfloresz/novel-manager.git
cd novel-manager
```

2. Crea entorno virtual:
```bash
uv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Instala dependencias:
```bash
uv pip install -r requirements.txt
```

4. Configura claves API (crea archivo `.env` desde `.env.example`)

5. Ejecuta la aplicación:
```bash
uv run python main.py
```

## Características Principales

### 📁 Gestión de Archivos
- Interfaz gráfica intuitiva para navegación de archivos
- **Importación EPUB**: Convierte EPUBs existentes a archivos de texto
- Sincronización y vista previa automáticas de archivos
- Seguimiento de estado con indicadores de color
- Historial de carpetas recientes para acceso rápido

### 🌐 Traducción Avanzada
![Translation](assets/translate.webp)

- **Múltiples Proveedores de IA**: Google Gemini, Chutes AI, Together AI, DeepInfra, OpenAI
- **Comprobación y Refinamiento**: Incluye opciones para verificar la calidad de la traducción contra el texto original y para mejorarla mediante un proceso adicional de refinamiento. Ambas opciones consumen una cantidad significativa de tokens adicionales.
- **Configuración Avanzada de Comprobación y Refinamiento**: Permite configurar un proveedor y modelo diferente para los pasos de comprobación y refinamiento. Esto se puede configurar de forma global en los ajustes o para una sola sesión desde el panel de traducción.
- **Términos Personalizados**: Terminología específica por proyecto con persistencia
- **Segmentación Inteligente**: Respeta la estructura narrativa
- **Base de Datos**: Evita retraducciones

### 🧹 Limpieza de Texto
![Translation](assets/clean.webp)

- **5 Modos de Limpieza**: Eliminar contenido después de texto, remover duplicados, eliminar líneas específicas, normalizar espacios, buscar y reemplazar
- **Control de Rango**: Procesar capítulos específicos o todos los archivos
- **Vista Previa y Respaldo**: Previsualizar cambios antes de aplicar y respaldo automático

### 📚 Creación de EPUB
![Translation](assets/ebook.webp)

- **Conversión Profesional**: TXT a EPUB con estructura literaria
- **Metadatos Inteligentes**: Gestión automática de título, autor y descripción
- **Detección de Portadas**: Búsqueda automática de imágenes de portada (cover.jpg, portada.png, etc.)
- **Diseño Responsivo**: Estilos CSS profesionales optimizados para lectores electrónicos

## Guía de Uso

### Flujo de Trabajo Básico
1. **Configuración**: Configura claves API y ajustes de traducción
2. **Importación**: Carga archivos existentes o importa desde EPUB
3. **Procesamiento**: Limpia texto, traduce capítulos o crea EPUBs
4. **Exportación**: Genera ebooks profesionales

### Vista General de la Interfaz
- **Panel Principal**: Navegador de archivos con indicadores de estado
- **Pestaña Traducir**: Configurar y ejecutar traducciones
- **Pestaña Limpiar**: Aplicar operaciones de limpieza de texto
- **Pestaña Ebook**: Crear EPUBs con metadatos y portadas

## Configuración

### Configuración de API
Crea un archivo `.env` con tus claves de API:
```env
GOOGLE_GEMINI_API_KEY=tu_clave_aqui
CHUTES_API_KEY=tu_clave_aqui
# Agrega otras claves de proveedores según sea necesario
```

### Ajustes de la Aplicación
- **Ubicación**: `src/config/config.json`
- **Personalizable**: Proveedor y modelo por defecto, idiomas, tamaño de segmentación
- **Persistencia**: Ajustes guardados automáticamente por proyecto

## Características Avanzadas

### 🏗️ Arquitectura
- **Base de Datos Híbrida**: SQLite con respaldo JSON automático
- **Procesamiento Asíncrono**: Traducciones en segundo plano sin bloquear la interfaz
- **Gestión Inteligente de Estados**: Seguimiento en tiempo real con persistencia
- **Diseño Modular**: Fácil de extender con nuevos proveedores y características

### 🔧 Detalles Técnicos
- **Rendimiento**: Optimizado para archivos grandes (100+ capítulos)
- **Manejo de Errores**: Mecanismos robustos de reintentos y logging
- **Gestión de Recursos**: Control automático de rate limits y monitoreo
- **Logging**: Registro detallado de sesiones con capacidades de exportación

## Estructura del Proyecto
```
novel-manager/
├── src/
│   ├── gui/           # Interfaz de Usuario
│   ├── logic/         # Lógica de Negocio
│   └── config/        # Archivos de Configuración
├── main.py            # Punto de Entrada
├── requirements.txt   # Dependencias
└── README.md          # Este Archivo
```

## Soporte Multilingüe
- **Idiomas de Interfaz**: Español (México), Inglés (EE.UU.)
- **Idiomas de Traducción**: Español, Inglés, con detección automática
- **Agregar Idiomas**: Crear archivos JSON en `src/config/i18n/`

## Descargo de Responsabilidad
Aunque este proyecto funciona, no puedo asegurar su funcionamiento ya que fue hecho con ayuda de la IA.
