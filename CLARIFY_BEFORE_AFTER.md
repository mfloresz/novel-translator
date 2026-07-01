# Before & After: Copy Improvements

## Dashboard Page

### Sort Controls
| Aspect | Before | After | Impact |
|--------|--------|-------|--------|
| **Sort Dropdown** | No label visible | `placeholder="Ordenar por"` | Users understand the control's purpose |
| **Sort Order Button** | No aria-label | `aria-label="Cambiar a orden..."` | Accessible, state-aware label |
| **Group Button** | `title="Agrupar por serie"` | Dynamic `aria-label` | Reflects actual state (Agrupar/Desagrupar) |

### Empty State
| Aspect | Before | After | Impact |
|--------|--------|-------|--------|
| Copy | "Crea una novela manualmente, importa un EPUB o descarga**una** desde internet." | "Crea una novela manualmente, importa un EPUB o descarga**uno** desde internet." | Better grammar and clarity |

---

## Novel Detail Page

### Action Buttons
| Button | Before | After | Impact |
|--------|--------|-------|--------|
| Update | `label="Actualizar"` | `label="Actualizar desde URL"` | User knows exactly what will happen |

### Section Headings (NEW)
| Section | Before | After | Impact |
|---------|--------|-------|--------|
| Chapters | No hidden heading | Added `<h2 id="tab-chapters" class="sr-only">Capítulos</h2>` | Screen readers announce section |
| Translation | No hidden heading | Dynamic: "Traducción" / "Refinamiento" | Reflects operation mode |
| Cleaning | No hidden heading | Added `<h2 id="tab-clean" class="sr-only">Limpieza de texto</h2>` | Accessibility |
| Export | No hidden heading | Added `<h2 id="tab-export" class="sr-only">Exportar</h2>` | Accessibility |
| Errors | No hidden heading | Added `<h2 id="tab-errors" class="sr-only">Historial de errores</h2>` | Accessibility |

### Translation Empty State
| Aspect | Before | After | Tone |
|--------|--------|-------|------|
| Copy | "No hay capítulos elegibles para esta operación." | "Todos los capítulos ya fueron {{ 'traducidos' \| 'refinados' }}." | Specific, explains WHY |

**Why Better:**  
- User understands: all chapters are already done, not that something is wrong
- Conditional message adapts to operation (translate vs refine)

### Cleaning Empty State
| Aspect | Before | After | Tone |
|--------|--------|-------|------|
| Copy | "No hay capítulos con contenido para esta selección." | "Selecciona primero el tipo de limpieza arriba para ver capítulos disponibles." | Actionable guidance |

**Why Better:**  
- "Contenido" was vague; new copy explains the prerequisite
- Guides user toward solution

### Export Button
| Aspect | Before | After | Impact |
|--------|--------|-------|--------|
| Label | "Construir y descargar EPUB" | "Descargar EPUB" | Simpler, clearer destination |

### Error History Empty State
| Aspect | Before | After | Tone |
|--------|--------|-------|------|
| Title | "Sin historial con errores" | "Aún no hay errores" | More positive ("Aún no" vs "Sin") |
| Message | "Aquí solo se muestran trabajos que fallaron o tuvieron capítulos fallidos." | "Cuando un trabajo falle, verás los detalles aquí." | Forward-looking, helpful |

### Job Failed Chapters Toggle
| Aspect | Before | After | Impact |
|--------|--------|-------|--------|
| Text | `Click para {{ expanded ? 'ocultar' : 'ver detalles' }}` | `{{ expanded ? 'Ocultar' : 'Ver' }} detalles` | Removes English "Click", more action-focused |

### Failed Chapter Error Fallback
| Aspect | Before | After | Tone |
|--------|--------|-------|------|
| Copy | "Sin mensaje de error registrado." | "Sin detalles disponibles para este error." | More user-friendly, less technical |

---

## Accessibility Improvements

### Screen Reader Enhancements

All section tabs now announce their purpose to screen reader users via semantic HTML:

```html
<!-- Before: No context for screen reader -->
<section v-if="activeTab === 'chapters'">
  <Card><template #title>...</template>

<!-- After: Clear context -->
<section v-if="activeTab === 'chapters'" aria-labelledby="tab-chapters">
  <h2 id="tab-chapters" class="sr-only">Capítulos</h2>
  <Card><template #title>...</template>
```

### Icon Button Labels

Sort and group buttons now have state-aware aria-labels:

```html
<!-- Before: No label for assistive tech -->
<Button :icon="sortOrderIcon" @click="toggleSortOrder" />

<!-- After: Context-aware label -->
<Button 
  :icon="sortOrderIcon"
  :aria-label="sortOrder === 'asc' ? 'Cambiar a orden descendente' : 'Cambiar a orden ascendente'"
  @click="toggleSortOrder"
/>
```

---

## Copy Tone & Voice

All changes maintain the "Quiet Shelf" brand voice:

✅ **Calm** — No urgent language, no alarmist empty states  
✅ **Content-first** — UI copy stays out of the way, guides to content  
✅ **Unobtrusive** — Suggestions are helpful, not pushy  
✅ **Specific** — Each message tells users exactly what to do next  

**Example:**  
- ❌ "Error: No chapters available" (technical, blaming)
- ✅ "Todos los capítulos ya fueron traducidos" (specific, explains state)

---

## Summary by Priority

### HIGH (Clarity Blockers) — 4 Changes
1. Sort dropdown label
2. Sort order button aria-label
3. "Actualizar" → "Actualizar desde URL"
4. Translation empty state explanation

### MEDIUM (Polish) — 8 Changes
1. Group button aria-label
2. All section headings (5 sections)
3. Cleaning empty state guidance
4. Error history empty state tone
5. Job details toggle text (remove "Click")

### LOW (Optional) — 2 Changes
1. Export button simplification
2. Error message fallback tone

---

**All changes are backward compatible, require no migrations, and improve UX for both sighted and assistive tech users.**
