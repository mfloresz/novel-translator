# Import Template

Estructura esperada para importar una novela desde un ZIP.

## Formato

```
novela.zip
├── metadata.json              # Metadatos de la novela (obligatorio)
├── cover.jpg                  # Portada (opcional)
├── originals/                 # Capítulos originales (obligatorio)
│   ├── Capítulo 001.txt       # .txt o .md
│   ├── Capítulo 002.txt
│   └── ...
└── translated/                # Capítulos traducidos (opcional)
    ├── Capítulo 001.txt       # Mismo nombre que en originals/
    ├── Capítulo 002.txt
    └── ...
```

## Reglas

- Los archivos en `originals/` se convierten en capítulos con `originalContent`.
- Si existe un archivo con el **mismo nombre** en `translated/`, ese capítulo se marca como `"translated"` y su contenido va a `translatedContent`.
- Si no existe en `translated/`, el capítulo queda como `"pending"`.
- El orden de capítulos se extrae del nombre del archivo (el primer número encontrado).
- El título del capítulo se extrae de la primera línea del contenido (sin marcadores de heading como `#` o `####`).
- Si `metadata.json` incluye `"url"`, la novela queda vinculada y se puede usar `update-from-url` para descargar capítulos nuevos.

## metadata.json

```json
{
  "title": "Título de la novela",
  "author": "Autor",
  "sourceLanguage": "en",
  "targetLanguage": "es",
  "url": "https://novelfire.net/novel/xxxxx",
  "description": "Descripción...",
  "sourceTitle": "Título original",
  "sourceAuthor": "Autor original",
  "sourceDescription": "Descripción original",
  "status": "completed",
  "isPublic": false
}
```

Valores válidos para `status`: `ongoing`, `completed`, `hiatus`, `cancelled`.

Solo `title`, `sourceLanguage` y `targetLanguage` son obligatorios.

## Cómo importar

### 1. Crear el ZIP

```bash
cd /ruta/a/tu/novela
zip -r novela.zip metadata.json cover.jpg originals/ translated/
```

### 2. Obtener token de autenticación

Si no tienes usuario, regístrate primero:

```bash
curl -X POST http://localhost:8090/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"tu@email.com","password":"tu_password","name":"Tu Nombre"}'
```

Luego inicia sesión para obtener el token:

```bash
curl -X POST http://localhost:8090/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"tu@email.com","password":"tu_password"}'
```

La respuesta incluye `token` y `user`. Guarda el token.

### 3. Importar

```bash
TOKEN="el_token_del_login"

curl -X POST http://localhost:8090/api/db/novels/import-from-zip \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@novela.zip"
```

### 4. Actualizar desde URL (si la novela tiene URL)

Si `metadata.json` incluye `"url"`, puedes descargar capítulos nuevos más tarde:

```bash
# Ver cuántos capítulos nuevos hay
curl http://localhost:8090/api/db/novels/{novel_id}/update-preview \
  -H "Authorization: Bearer $TOKEN"

# Descargar nuevos capítulos
curl -X POST http://localhost:8090/api/db/novels/{novel_id}/update-from-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```
