# Prompt: Sync Landing Page Nav & Buttons to App UI Style

**Scope:** `apps/frontend/src/features/landing/` only.
Do not touch any files in `apps/frontend/src/app/(site)/`,
`apps/frontend/src/presentation/`, or `apps/frontend/src/features/channels/`.

The goal is to make the landing pages (`/creators`, `/listeners`) feel like they
belong to the same product as `wavepalace.live`. Right now the landing nav and
buttons use a separate `wp-*` design language. Update them to match the exact
tokens and class strings the live app already uses.

---

## 1. Nav — `src/features/landing/components/Nav.tsx`

### Logo

**Before:**
```tsx
<a href="/" className="text-base font-semibold tracking-tight text-wp-white" ...>
  Wave<span className="text-wp-violet">Palace</span>
</a>
```

**After** — add the `Disc3` icon from lucide-react and the `.text-gradient` class:
```tsx
import { Disc3 } from "lucide-react";

<a href="/" className="group flex items-center gap-2" aria-label="WavePalace home">
  <Disc3 className="h-6 w-6 text-wave-400 transition-transform group-hover:rotate-90" />
  <span className="text-lg font-semibold tracking-tight">
    Wave<span className="text-gradient">Palace</span>
  </span>
</a>
```

### Nav container

**Before:**
```tsx
<header
  className="sticky top-0 z-50 border-b bg-wp-black/80 backdrop-blur-sm"
  style={{ borderColor: "var(--wp-border)" }}
>
```

**After:**
```tsx
<header className="sticky top-0 z-50 border-b border-white/5 backdrop-blur-md">
```
Remove the inline `style` prop entirely.

### Nav links (For creators / For listeners)

**Before:**
```tsx
className={`text-sm transition ${pathname === "/creators" ? "text-wp-white" : "text-wp-muted hover:text-wp-white"}`}
```

**After:**
```tsx
className={`text-sm font-medium transition ${pathname === "/creators" ? "text-white" : "text-white/50 hover:text-white"}`}
```
Apply the same change to the `/listeners` link.

### "Browse channels" CTA button in nav

**Before:**
```tsx
<a href="/" className="rounded border border-wp-violet bg-wp-violet px-4 py-1.5 text-sm font-medium text-white transition hover:bg-wp-violet2">
  Browse channels
</a>
```

**After** — frosted glass pill matching the app nav buttons:
```tsx
<a
  href="/"
  className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10 hover:text-white"
>
  Browse channels
</a>
```

---

## 2. Section buttons — four component files

Apply these two class strings everywhere a CTA button appears in the landing
feature components. Do not change `href` values, text content, or any other
props.

### Primary button (filled, gradient)

Used for: "Start your channel", "Browse channels" (main CTA in hero/proof sections)

**Before:**
```tsx
className="rounded border border-wp-violet bg-wp-violet px-6 py-2.5 text-sm font-medium text-white transition hover:bg-wp-violet2"
```

**After:**
```tsx
className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-wave-500 to-glow-magenta px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-wave-600/30 transition hover:brightness-110"
```

### Secondary button (ghost, frosted)

Used for: "See live channels →", "How it works", "For creators →"

**Before:**
```tsx
className="rounded border px-6 py-2.5 text-sm font-medium text-wp-muted transition hover:border-wp-violet hover:text-wp-white"
style={{ borderColor: "var(--wp-border)" }}
```

**After** — remove the `style` prop entirely, replace className:
```tsx
className="rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white/80 transition hover:bg-white/10"
```

### Files to update

| File | Buttons present |
|---|---|
| `src/features/landing/components/Hero.tsx` | "Start your channel" (primary), "See live channels →" (secondary) |
| `src/features/landing/components/ListenerHero.tsx` | "Browse channels" (primary), "How it works" (secondary) |
| `src/features/landing/components/ProofLine.tsx` | "Start your channel" (primary) |
| `src/features/landing/components/ListenerProofLine.tsx` | "Browse channels" (primary), "For creators →" (secondary) |

---

## 3. Footer logo — `src/features/landing/components/Footer.tsx`

**Before:**
```tsx
<p className="text-sm font-medium text-wp-white">
  Wave<span className="text-wp-violet">Palace</span>
</p>
```

**After:**
```tsx
<span className="flex items-center gap-1.5">
  <Disc3 className="h-4 w-4 text-wave-400" />
  <span className="text-sm font-semibold tracking-tight">
    Wave<span className="text-gradient">Palace</span>
  </span>
</span>
```
Import `{ Disc3 }` from `"lucide-react"` at the top of the file.

---

## Token reference

All tokens below already exist in `apps/frontend/tailwind.config.ts`.
Do not add new tokens or modify any config files.

| Token | Value | Used for |
|---|---|---|
| `wave-400` | `#a78bfa` | Icon colour, subtle accents |
| `wave-500` | `#8b5cf6` | Gradient start |
| `wave-600` | `#7c3aed` | Button shadow colour |
| `glow-magenta` | `#ff5cc8` | Gradient end |
| `.text-gradient` | `globals.css` utility | "Palace" in logo |
| `border-white/5` | — | Nav border |
| `bg-white/5` | — | Ghost button fill |
| `border-white/10` | — | Ghost button border |
| `border-white/15` | — | Secondary button border |

---

## What NOT to change

- The `wp-*` CSS variables used for section backgrounds, card borders, and body
  copy (`text-wp-muted`, `bg-wp-s1`, `var(--wp-border)` on section dividers) —
  keep those as-is. Only nav and CTA buttons switch to the app token set.
- `tailwind.config.ts`, `globals.css` — no changes needed; both token sets are
  already present.
- Any files outside `src/features/landing/` — out of scope.
- The `LandingNav` wrapper `div` on each page (`style={{ backgroundColor: "var(--wp-black)" }}`)
  — keep the dark page background intact so the blurred nav sits over it correctly.
