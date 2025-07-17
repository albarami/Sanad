#

# Sanad v2 – Front‑End Guidelines & Design System

*Version 1.0  |  Date: 16 Jul 2025*

## 1  Purpose

This document standardises the visual language, component API, coding conventions, and quality gates for all Sanad v2 front‑end work. It targets:

*   **MVP pilot UI** (chat panel, dashboard, trace inspector)
*   Future SaaS console (multi‑tenant)
*   White‑label partner skins

Following these rules ensures brand consistency, a11y compliance, and rapid dev hand‑off.

## 2  Stack Summary

|                   |                                                         |                                                 |
| ----------------- | ------------------------------------------------------- | ----------------------------------------------- |
| Layer             | Choice                                                  | Rationale                                       |
| **Framework**     | **React 18** ‑‑ Vite 5 build                            | Modern JSX runtime, fast HMR, tree‑shaking      |
| **Styling**       | **Tailwind CSS v3.4**                                   | Utility‑first, 0 runtime, design‑token friendly |
| **Component lib** | **shadcn/ui** (Radix primitives)                        | Accessible, unstyled base + Tailwind variants   |
| **State mgr**     | **Zustand** for local, **TanStack Query** for API cache | Light, hooks‑centric, SSR‑safe                  |
| **Charts**        | **Recharts 2.x**                                        | Declarative, no custom colour calc required     |
| **i18n**          | **react‑i18next**                                       | Namespaced JSON, lazy‑load bundles              |
| **Icons**         | **lucide‑react**                                        | Stroke weight ≈ Inter font, tree‑shakeable      |
| **Form logic**    | **react‑hook‑form + zod**                               | Native validation, small bundle                 |
| **Testing**       | **Vitest + React Testing Library**, **Storybook 8**     | Unit coverage ≥ 80 %, visual diff CI            |

## 3  Design Tokens

Use **Tailwind config** (`tailwind.config.ts`) as single source for colour, spacing, typography.

`export const sanadTokens = { colors: { primary: { DEFAULT: '#1F4AFF', // Sanad Blue dark: '#172FCC', }, success: '#27C28B', warning: '#FFB020', error: '#FF4D4F', surface: '#F9FAFB', gray: { 50:'#F9FAFB',100:'#F2F3F5',200:'#E5E7EB',300:'#D1D5DB', 400:'#9CA3AF',500:'#6B7280',600:'#4B5563',700:'#374151',800:'#1F2937',900:'#111827' } }, radius: { sm:'4px', md:'6px', lg:'8px' }, fontFamily: { sans:['Inter','system-ui','sans-serif'], mono:['JetBrains Mono','monospace'] } }`

Apply tokens via Tailwind classes (`bg-primary`, `text-gray-700`, `rounded-md` ...). Do **not** hard‑code hex values in JSX.

## 4  Component Library

### 4.1 Required Core Components

|                |                      |                    |                         |                    |                            |                             |
| -------------- | -------------------- | ------------------ | ----------------------- | ------------------ | -------------------------- | --------------------------- |
| Component      | Source               | Extra props        | Notes                   |                    |                            |                             |
| `Button`       | shadcn/ui            | `variant:"primary  | ghost                   | danger"`           | Use `asChild` for `<Link>` |                             |
| `Badge`        | custom               | `tone:"success     | warning                 | error" size:"sm    | md"`                       | Displays Sanad‑score colour |
| `Tooltip`      | Radix Tooltip        | –                  | For score hover info    |                    |                            |                             |
| `Drawer`       | shadcn/ui            | –                  | Right‑side Sources pane |                    |                            |                             |
| `Card`         | shadcn/ui            | `elevated` boolean | Dashboard tiles         |                    |                            |                             |
| `DataTable`    | TanStack Table       | –                  | Query history list      |                    |                            |                             |
| `ProgressRing` | custom SVG           | `value` 0‑100      | Latency gauge           |                    |                            |                             |
| `CodeBlock`    | prism-react-renderer | `language:"json    | bash"`                  | Collapse long JSON |                            |                             |

### 4.2 Implementation Rules

*   All new components go into `src/components/ui/` and are exported via `index.ts` barrel.
*   Provide a **Storybook story** for every prop combination.
*   Run `npm run test:visual` (Chromatic snapshots) on PR.

## 5  Layouts & Pages

`src/ ├─ pages/ │ ├─ Chat.tsx ← chat /verify interface │ ├─ Dashboard.tsx ← metrics & charts │ ├─ History.tsx ← user query list │ └─ Admin/ ← settings, role mgr └─ layouts/ ├─ AppShell.tsx ← top‑nav + side‑nav └─ Public.tsx ← login / SSO callback`

*   **Max content width:** `max-w-[1080px] mx-auto`
*   **Grid spacing:** Tailwind `gap-6`; 8‑pt increments.
*   **Side‑nav width:** `w-72` (72 px) collapsed variant `w-20`.

## 6  Interaction Flows

### 6.1 Chat Verification Flow

1.  User types Q → `onSubmit` triggers REST `POST /verify`.
2.  UI shows shimmer + small spinner in button.
3.  Success → render answer card with:   • Plain text   • `Badge tone` based on `sanad_score`   • “Show Sources” link → open Drawer.
4.  Drawer lists passages, each collapsible; click “Open PDF” opens new tab with `page#` anchor.
5.  Feedback buttons 👍/👎 fire `/feedback` API.

### 6.2 Dashboard

*   Use React Query polling every 5 s for `/metrics/summary`.
*   Recharts line chart for p95 latency (10‑min window).
*   Histogram bar for score distribution.

## 7  Accessibility (WCAG 2.1 AA)

*   Colour contrast ≥ 4.5:1 – Tailwind plugin `@tailwindcss/typography` to preset.
*   Keyboard navigation: All interactive elements must have `tabIndex`, focus ring `outline-primary` 2 px.
*   Live region: `<div role="status" aria-live="polite">` for “verifying…” message.

## 8  Performance Budget (Laptop 4090 Pilot)

*   **Time to Interactive:** < 1.2 s (local).
*   Bundle size **≤ 300 kB gz**; use code‑splitting by route.
*   Avoid sending PDF blobs through React; serve via static file route.

## 9  Security

*   All fetches through `src/api.ts` which injects `Authorization` Bearer token.
*   CSRF not required (SPAs) but we add `SameSite=Lax` cookies for SSO.
*   Sanitise LLM answer HTML – use DOMPurify.

## 10  CI/CD Pipeline

|                |                                                                   |                        |
| -------------- | ----------------------------------------------------------------- | ---------------------- |
| Step           | Tool                                                              | Gate                   |
| Lint           | eslint + prettier                                                 | no warnings            |
| Unit tests     | Vitest                                                            | coverage ≥ 80 %        |
| Visual tests   | Chromatic                                                         | delta ≤ 1 px threshold |
| Build          | Vite                                                              | success                |
| Deploy (pilot) | `npm run build` → copy to `~/sanad_frontend/dist` served by Nginx | checksum verified      |

## 11  Internationalisation Road‑map

*   Prepare JSON namespace `common/en.json` with keys.
*   Use `t('score.verified')` not raw text.
*   RTL support via `dir="rtl"` attribute & Tailwind `rtl:` variants (phase v2.1).

## 12  White‑Labelling Guidelines

*   Expose `theme.json` override: primary hue, logo SVG, favicon.
*   Logo uses 24 × 24 icon slot; nav collapses gracefully.
*   Do not rename data-* attributes—they serve QA automation.

## 13  Open Tasks

|       |                                          |         |               |
| ----- | ---------------------------------------- | ------- | ------------- |
| ID    | Task                                     | Owner   | Due           |
| FE‑01 | Set up Tailwind config with sanadTokens  | FE Lead | Sprint 1 wk 1 |
| FE‑02 | Implement Button, Badge, Tooltip stories | FE Dev  | Sprint 1 wk 1 |
| FE‑03 | Integrate react‑i18next skeleton         | FE Dev  | Sprint 1 wk 2 |
| FE‑04 | Build Chat.tsx + Drawer                  | FE Lead | Sprint 1 wk 2 |
| FE‑05 | Connect dashboard polled metrics         | FE Dev  | Sprint 2 wk 5 |

*End of document – maintained by Front‑End Lead; update version on each major style or tooling change.*
