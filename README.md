# Novel Translator

Aplicación para gestionar, procesar y traducir novelas literarias con soporte para múltiples proveedores de IA.

El proyecto ofrece **dos versiones** con la misma funcionalidad central pero diferentes paradigmas de despliegue:

| Versión | Tecnología | Tipo | Lectura |
|---------|-----------|------|---------|
| **PyQt6** | Python, PyQt6, SQLite | Aplicación de escritorio nativa | [README](pyqt6-version/README.md) |
| **Server** | Go + PocketBase + Vue 3 | Servidor web con frontend SPA | [README](server/README.md) |

## Arquitectura General

```
novel-translator/
├── pyqt6-version/       # Desktop app (Python/PyQt6)
│   ├── main.py          # Entry point (QMainWindow)
│   ├── src/gui/         # UI panels (translate, refine, clean, create)
│   ├── src/logic/       # Business logic (translation, EPUB, cleaning)
│   └── src/config/      # Prompts, i18n, provider definitions
│
├── server/              # Web server (Go + PocketBase + Vue 3)
│   ├── cmd/server/      # Entry point
│   ├── internal/        # Backend: API, store, AI, scrapers, EPUB
│   └── frontend/        # Vue 3 SPA (PrimeVue)
│
├── docs/CODEMAPS/       # Arquitectura detallada
└── README.md            # Este archivo
```

## Funcionalidades Compartidas

- **Traducción literaria** con segmentación inteligente y verificación de calidad
- **Múltiples proveedores IA**: OpenAI-compatible, Gemini, etc.
- **Importación EPUB**: extrae capítulos y metadatos
- **Generación EPUB**: crea libros electrónicos desde capítulos traducidos
- **Limpieza de texto**: modos múltiples (eliminar duplicados, normalizar, buscar/reemplazar)
- **Refinamiento**: mejora post-traducción con herramientas o prompts
- **Gestión de proyectos**: metadatos, glosario, términos personalizados

## Documentación Técnica

- [Arquitectura del proyecto](docs/CODEMAPS/INDEX.md)
- [Desktop (PyQt6) — Frontend](pyqt6-version/docs/CODEMAPS/frontend.md)
- [Desktop (PyQt6) — Backend](pyqt6-version/docs/CODEMAPS/backend.md)
- [Desktop (PyQt6) — Base de datos](pyqt6-version/docs/CODEMAPS/database.md)
- [Desktop (PyQt6) — Workers](pyqt6-version/docs/CODEMAPS/workers.md)
- [Desktop (PyQt6) — Integraciones](pyqt6-version/docs/CODEMAPS/integrations.md)
- [Server — Backend](server/docs/CODEMAPS/backend.md)
- [Server — Frontend](server/docs/CODEMAPS/frontend.md)
- [Server — Base de datos](server/docs/CODEMAPS/database.md)
- [Server — Workers](server/docs/CODEMAPS/workers.md)
- [Server — Integraciones](server/docs/CODEMAPS/integrations.md)
