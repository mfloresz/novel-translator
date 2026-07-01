# Clarify: UX Copy & Labels Implementation Summary

**Date:** 2026-07-01  
**Pages Modified:**
- `server/frontend/src/pages/DashboardPage.vue`
- `server/frontend/src/pages/NovelDetailPage.vue`

---

## Changes Applied

### DashboardPage.vue

#### 1. Sort Dropdown Label (HIGH PRIORITY)
- **Added:** `placeholder="Ordenar por"` to Select component
- **Impact:** Users now see a label indicating what the dropdown controls
- **Line:** 16

#### 2. Sort Order Button Accessibility (HIGH PRIORITY)
- **Replaced:** Static `title="..."` with dynamic `aria-label`
- **Content:** `"Cambiar a orden descendente"` / `"Cambiar a orden ascendente"`
- **Impact:** Screen readers and users understand the button's function; aria-label properly indicates state
- **Line:** 25

#### 3. Group by Series Button Accessibility (MEDIUM PRIORITY)
- **Replaced:** Static `title="Agrupar por serie"` with dynamic `aria-label`
- **Content:** `"Agrupar por serie"` / `"Desagrupar por serie"`
- **Impact:** Accessible label changes based on state; clearer for assistive tech
- **Line:** 36

#### 4. Empty State Copy (MEDIUM PRIORITY)
- **Changed:** "Crea una novela manualmente, importa un EPUB o descarga una desde internet."
- **To:** "Crea una novela manualmente, importa un EPUB o descarga uno desde internet."
- **Impact:** Grammatically clearer, better parallel structure
- **Line:** 76

---

### NovelDetailPage.vue

#### 1. "Actualizar" Button Label Clarification (HIGH PRIORITY)
- **Changed:** `label="Actualizar"` → `label="Actualizar desde URL"`
- **Impact:** User immediately understands what "Actualizar" does (update from URL source)
- **Line:** 71

#### 2. Section Accessibility & Semantic HTML (MEDIUM PRIORITY)
Added hidden section headings and aria-labelledby attributes to all major content sections:

**Chapters Section:**
- Added: `aria-labelledby="tab-chapters"` to section
- Added: `<h2 id="tab-chapters" class="sr-only">Capítulos</h2>`
- **Impact:** Screen reader announces section name clearly

**Translation Section:**
- Added: `aria-labelledby="tab-translate"` to section
- Added: `<h2 id="tab-translate" class="sr-only">{{ ... }}</h2>` (dynamic title)
- **Impact:** Dynamic title reflects current operation (Traducción/Refinamiento)

**Cleaning Section:**
- Added: `aria-labelledby="tab-clean"` to section
- Added: `<h2 id="tab-clean" class="sr-only">Limpieza de texto</h2>`

**Export Section:**
- Added: `aria-labelledby="tab-export"` to section
- Added: `<h2 id="tab-export" class="sr-only">Exportar</h2>`

**Error History Section:**
- Added: `aria-labelledby="tab-errors"` to section
- Added: `<h2 id="tab-errors" class="sr-only">Historial de errores</h2>`

**Lines:** 131–132, 149–150, 186–187, 277–278, 296–297

#### 3. Translation Eligible Chapters Empty State (HIGH PRIORITY)
- **Changed:** "No hay capítulos elegibles para esta operación."
- **To:** "Todos los capítulos ya fueron {{ translateOperation === 'translate' ? 'traducidos' : 'refinados' }}."
- **Impact:** Explains WHY chapters aren't eligible; clearer and more helpful
- **Line:** 172

#### 4. Cleaning Chapters Empty State (HIGH PRIORITY)
- **Changed:** "No hay capítulos con contenido para esta selección."
- **To:** "Selecciona primero el tipo de limpieza arriba para ver capítulos disponibles."
- **Impact:** Explains the prerequisite action; guides user toward solution
- **Line:** 247

#### 5. Export Button Label Simplification (LOW PRIORITY)
- **Changed:** `label="Construir y descargar EPUB"`
- **To:** `label="Descargar EPUB"`
- **Impact:** Simpler, shorter label; users understand the destination format
- **Line:** 290

#### 6. Error History Empty State (MEDIUM PRIORITY)
- **Changed:** "Sin historial con errores" → "Aún no hay errores"
- **Changed:** "Aquí solo se muestran trabajos que fallaron o tuvieron capítulos fallidos."
- **To:** "Cuando un trabajo falle, verás los detalles aquí."
- **Impact:** More positive tone ("Aún no hay") + forward-looking help text
- **Lines:** 303–304

#### 7. Job Failed Chapters Toggle Text (MEDIUM PRIORITY)
- **Changed:** `<span class="small muted">Click para {{ expandedJobId === job.id ? 'ocultar' : 'ver detalles' }}</span>`
- **To:** `<span class="small muted">{{ expandedJobId === job.id ? 'Ocultar' : 'Ver' }} detalles</span>`
- **Impact:** Removes English "Click" from Spanish UI; cleaner, more action-oriented
- **Line:** 339

#### 8. Failed Chapter Error Message Fallback (MEDIUM PRIORITY)
- **Changed:** "Sin mensaje de error registrado."
- **To:** "Sin detalles disponibles para este error."
- **Impact:** Less technical, more user-friendly tone
- **Line:** 350

---

## UX Writing Principles Applied

✓ **Specificity:** All changes make implicit actions explicit (e.g., "Actualizar" → "Actualizar desde URL")  
✓ **Clarity:** Empty states explain WHY rather than just stating WHAT (e.g., "Todos ya fueron traducidos" vs "No hay elegibles")  
✓ **Accessibility:** All icon-only buttons now have proper aria-labels; section headings are available to screen readers  
✓ **Tone:** Consistent with "The Quiet Shelf" brand (calm, content-first, unobtrusive)  
✓ **Actionability:** Users understand next steps or prerequisites  
✓ **Consistency:** Spanish language consistency throughout (removed English "Click")  

---

## Browser & Accessibility Testing

- ✅ No TypeScript/Vue compilation errors
- ✅ `.sr-only` utility class already exists in `server/frontend/src/app/styles.css` (line 206–216)
- ✅ All aria-label and aria-labelledby attributes follow W3C/WCAG patterns
- ✅ Dynamic content (like section titles reflecting operation state) properly handled

---

## Remaining Considerations

### Not Implemented (Optional / Design Decision Required)

1. **i18n Structure for aria-labels**  
   Currently all aria-labels are hardcoded Spanish. Recommend moving to translation keys (`aria.backToNovels`, etc.) for future EN/ES toggle support.

2. **"Configuración" Button Label**  
   Could be more specific as "Editar novela" (Edit novel) but "Configuración" (Settings) is also clear and conventional. Left as-is per conservative approach.

3. **Sort/Group Button Visual Feedback**  
   Currently icons change based on state. Consider adding a tooltip or visible state indicator for non-power users (optional enhancement).

---

## Files Modified

```
server/frontend/src/pages/DashboardPage.vue
server/frontend/src/pages/NovelDetailPage.vue
```

No CSS changes required — all classes (`.sr-only`) already exist in the design system.

---

## Validation

- ✅ No lint errors or warnings
- ✅ All syntax valid for Vue 3 + TypeScript
- ✅ All accessibility attributes properly formatted
- ✅ Ready for visual testing in browser
