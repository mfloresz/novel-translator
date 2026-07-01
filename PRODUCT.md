# Product

## Register

product

## Users

Personal / small-team users managing a library of novels — importing, translating (AI-assisted), refining, and reading them. Context spans desktop and mobile; reading sessions in particular need to work well on phone.

## Product Purpose

A self-hosted novel library + translation pipeline + reader. Users import novels (EPUB/URL/ZIP), run AI translation/refinement/QA jobs, manage chapters, and read the result — all in one app. Success = a reading experience on par with dedicated reader apps (Readest, Calibre), with translation/management tooling that doesn't get in the way (Mihon/Tachiyomi-style: content-first, functional chrome).

## Brand Personality

Calm, content-first, unobtrusive. Reader-app DNA (Readest/Calibre for library & reading polish, Mihon/Tachiyomi for the "manage + consume" duality on mobile). Chrome recedes; the text and cover art lead.

## Anti-references

Heavy "admin dashboard" look (dense data-tables-everywhere, SaaS-metric cards). Anything that treats mobile as an afterthought — reading and library browsing must feel native-app-smooth on a phone, not a shrunk desktop layout.

## Design Principles

1. Reading is the primary act — every other screen (dashboard, jobs, settings) is scaffolding around it and should stay quiet.
2. Mobile is a first-class target, not a breakpoint afterthought — touch targets, thumb reach, and reading ergonomics matter as much as desktop.
3. Motion is smooth but restrained — transitions confirm state changes (page nav, job progress, sort/filter) without theatrics; respect reduced-motion.
4. Preserve the existing warm-neutral "Pixeo" palette and PrimeVue/Aura foundation already committed in the codebase — extend it, don't replace it.

## Accessibility & Inclusion

Respect `prefers-reduced-motion` (crossfade/instant fallback for all transitions). No stated WCAG level beyond sane defaults — aim for AA contrast as a baseline given long-form reading text.
