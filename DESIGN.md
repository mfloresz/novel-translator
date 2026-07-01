---
name: Yara
description: A self-hosted novel library, translation pipeline, and reader — reading always leads.
colors:
  warm-ink: "#141413"
  bone-paper: "#fafaf9"
  page-stone: "#f5f4f2"
  aged-stone: "#57544c"
  aged-stone-deep: "#3d3b35"
  block-elevated: "#e8e6e2"
  mock-surface: "#ddd9d3"
  info-blue: "#2563eb"
  success-green: "#16a34a"
  warn-amber: "#a16207"
  danger-red: "#dc2626"
typography:
  title:
    fontFamily: "Geist, Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Geist, Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  reading:
    fontFamily: "Geist, Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.05rem"
    fontWeight: 400
    lineHeight: 1.75
    letterSpacing: "normal"
  label:
    fontFamily: "Geist, Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  pill: "999px"
spacing:
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
components:
  button-primary:
    backgroundColor: "{colors.warm-ink}"
    textColor: "{colors.bone-paper}"
    rounded: "{rounded.pill}"
    padding: "0.5rem 1rem"
  button-primary-hover:
    backgroundColor: "#292524"
    textColor: "{colors.bone-paper}"
    rounded: "{rounded.pill}"
    padding: "0.5rem 1rem"
  button-secondary:
    backgroundColor: "{colors.page-stone}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.pill}"
    padding: "0.5rem 1rem"
  novel-cover-card:
    backgroundColor: "{colors.page-stone}"
    rounded: "{rounded.md}"
    padding: "0"
---

# Design System: Yara

## 1. Overview

**Creative North Star: "The Quiet Shelf"**

Yara is built on the calm materiality of a physical bookshelf: warm stone and ink tones, no color for color's sake, no chrome that competes with the spine of the book. Per PRODUCT.md, "chrome recedes; the text and cover art lead" — the interface behaves like Readest or Calibre for library polish, and like Mihon/Tachiyomi for the "manage and consume" duality across desktop and mobile. Nothing here performs for attention; everything is furniture in a reading room.

The palette is a single warm-neutral ramp (bone paper to warm ink) rather than a saturated brand hue, because the "brand" is the reading experience itself, not a marketing identity. Color is reserved almost entirely for semantic state (job status, danger actions) — never for decoration. This system explicitly rejects the dense "admin dashboard" look (data-tables-everywhere, SaaS metric cards) and any layout that treats mobile as a shrunk-down desktop view.

**Key Characteristics:**
- Warm-stone monochrome palette; color appears only as semantic signal, never decoration.
- Flat by default; the one deliberate exception is the novel cover, which gets real elevation because it's the object being handled, not the chrome around it.
- Full light/dark/system theming via a single token layer, not a bolted-on dark mode.
- Motion is short and functional (0.15–0.2s), never choreographed.

## 2. Colors

A single warm-stone ramp carries both light and dark modes; color only reappears for semantic states.

### Primary
- **Warm Ink** (#141413): primary text, primary button fill (light mode), the ink the whole system is measured against.
- **Aged Stone** (#57544c) / **Aged Stone Deep** (#3d3b35 hover): links and the one "accent" the system allows — a darker step of its own neutral, not an imported hue.

### Neutral
- **Bone Paper** (#fafaf9): elevated surfaces (cards, menus, dialogs).
- **Page Stone** (#f5f4f2): page background, muted surfaces.
- **Block Elevated** (#e8e6e2) / **Mock Surface** (#ddd9d3): stronger surface steps for headers and table rows.
- Text-secondary/tertiary, divider, and border-strong are derived at runtime via `color-mix(in oklab, var(--text-primary) N%, transparent)` rather than fixed hexes — the whole neutral system is generated off one ink value per color scheme, light or dark.

### Semantic (state only)
- **Info Blue** (#2563eb), **Success Green** (#16a34a), **Warn Amber** (#a16207), **Danger Red** (#dc2626): reserved for job status tags, destructive actions, and system feedback. Never used decoratively.

Dark mode inverts the ramp (ink `#f5f4f2` on page `#121110`) using the same token names — the palette doesn't gain new colors in dark mode, it flips lightness.

### Named Rules
**The One Ramp Rule.** There is exactly one hue family (warm stone/graphite). If a screen needs a second color, it must be a semantic state color from the fixed set above — never a new decorative hue.

## 3. Typography

**Body Font:** Geist (with Inter, system-ui fallback)
**Label/Mono Font:** SFMono-Regular, ui-monospace (code and technical snippets only)

**Character:** One sans family carries every role; hierarchy comes from size, weight, and letter-spacing, not from mixing typefaces — consistent with a system where typography stays quiet and the content (novel text) is the star.

### Hierarchy
- **Title** (700, 1.75rem → 1.5rem on mobile, letter-spacing -0.02em): page headers ("Biblioteca", novel titles).
- **Body** (400, 1rem, line-height 1.55): default UI copy, forms, lists.
- **Reading** (400, 1.05rem, line-height 1.75): chapter/reader content specifically — deliberately larger and looser than UI body text for long-form reading comfort.
- **Label** (400, 0.875rem): secondary/muted text, metadata, badges.

### Named Rules
**The One Voice Rule.** Geist is the only typeface in the system. Emphasis comes from weight (400/600/700) and size, never from switching families or adding a display serif.

## 4. Elevation

Flat by default: PrimeVue's cards, dialogs, drawers, and popovers explicitly zero out box-shadow and rely on a 1px border (`--divide`) plus tonal surface steps (`--surface-base` → `--surface-elevated` → `--surface-muted` → `--surface-strong`) for depth. The one deliberate exception is the novel cover — the object being handled — which gets a real ambient shadow that lifts on interaction.

### Shadow Vocabulary
- **Cover Rest** (`box-shadow: 0 8px 20px rgba(0,0,0,0.1)`): default state for novel cover art in the library grid.
- **Cover Lift** (`box-shadow: 0 14px 32px rgba(0,0,0,0.14)`, paired with `transform: translateY(-3px)`): hover/focus-visible state on a cover — the only place elevation responds to interaction.
- **Overlay Scrim** (`--surface-overlay`, `rgba(20,20,19,0.44)` light / `rgba(7,7,6,0.72)` dark): dialog and mobile-drawer backdrops.

### Named Rules
**The Flat-Except-The-Book Rule.** Every surface is flat and bordered at rest. The only thing allowed to lift off the page is a book cover, because that's the one object the user is meant to reach for.

## 5. Components

### Buttons
- **Shape:** full pill (`border-radius: 999px`).
- **Primary:** Warm Ink fill / Bone Paper text (`#1c1917` / `#fafaf9` in the live token set), hover darkens to `#292524`. No border, no shadow.
- **Secondary:** Page Stone fill, Warm Ink text, 1px `--divide` border.
- **Text/Ghost:** transparent, `--mock-row` tint on hover.
- **Hover / Focus:** background shift only — no lift, no shadow. Focus-visible gets a 2.5px `--accent-link` outline with a soft 4px color-mix ring, offset 2px.

### Cards / Containers
- **Corner Style:** 16px (`--radius-lg`) for generic surface cards; 12px (`--radius-md`) for the novel cover.
- **Background:** Bone Paper (`--surface-elevated`) on a Page Stone (`--page-bg`) canvas.
- **Shadow Strategy:** none, per the Flat-Except-The-Book Rule — except the cover itself (see Elevation).
- **Border:** 1px `--divide` on generic cards; the cover instead uses shadow to separate from the grid.

### Novel Cover Card (signature component)
The library's core object. A 2:3 cover image (or icon placeholder on Page Stone) in a 12px-radius frame, 1px bordered, resting at Cover Rest elevation and lifting to Cover Lift with a 3px upward translate on hover/focus. An ellipsis-menu button overlays the top-right corner at 0 opacity, appearing on hover/focus/touch via a blurred Bone-Paper chip (`backdrop-filter: blur(6px)`) so it never competes with the artwork at rest.

### Inputs / Fields
- **Style:** Surface Base background, `--divide` border, no radius drama (inherits PrimeVue defaults at `--radius-md`/`sm`).
- **Focus:** border/outline shift to `--accent-link`, matching the global focus-visible treatment — no glow, no color change beyond the neutral ramp.
- **Disabled:** 0.6 opacity, secondary text color.

### Navigation
- **Style:** sticky top bar at 92% opacity Bone Paper with `backdrop-filter: blur(12px)`, 1px bottom `--divide` border — translucent, not opaque, so it visually recedes over scroll content.
- **Mobile treatment:** the same nav collapses into a full-height slide-in drawer (`slideInLeft 0.2s ease-out`) from the left, with a matching scrim overlay; icon-first nav items sized to the 44px touch target.

## 6. Do's and Don'ts

### Do:
- **Do** keep the entire UI on one hue family (warm stone/graphite); introduce color only via the fixed semantic set (info/success/warn/danger).
- **Do** let the novel cover be the only element with real box-shadow and hover lift; every other surface stays flat with a 1px border.
- **Do** size touch targets to at least 44px and treat mobile layouts as first-class, not shrunk desktop (per PRODUCT.md).
- **Do** keep transitions short (0.15–0.2s) and purposeful — a hover lift, a drawer slide, a focus ring — never a choreographed entrance.
- **Do** use the pill radius (999px) for buttons and tags, and the 12–20px scale for cards/surfaces.
- **Do** respect `prefers-reduced-motion` for every transition, per PRODUCT.md's accessibility line.

### Don't:
- **Don't** introduce a second decorative hue or gradient — this is explicitly a one-ramp system.
- **Don't** build a dense "admin dashboard" look (data-tables-everywhere, SaaS metric cards) — PRODUCT.md names this as an anti-reference directly.
- **Don't** add drop shadows to generic cards, dialogs, or buttons — depth comes from tonal surface steps and borders, not shadow, except the novel cover.
- **Don't** mix in a second typeface for "display" moments — Geist carries every role via weight and size.
- **Don't** design mobile as an afterthought breakpoint; reading and library browsing must feel native-smooth on a phone.
- **Don't** use side-stripe borders, gradient text, or glassmorphism as decoration — the one blur in the system (topbar/menu-button backdrop-filter) is functional legibility-over-scroll, not decoration.
