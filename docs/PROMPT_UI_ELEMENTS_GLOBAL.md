# Prompt: Apply Landing Page UI Elements to Main App

## Context

The WavePalace monorepo has two Next.js apps:

- **`apps/frontend/`** — the main channel player and directory (live on `wavepalace.live`)
- **`apps/landing/`** — the new static marketing landing page (not yet deployed)

The landing page was recently built with a set of decorative UI elements that look great and should be ported into the main frontend app. The goal is to unify the visual language across both surfaces without redesigning any existing layout.

---

## Design token alignment

The landing page uses `wp-*` CSS variables (`--wp-violet`, `--wp-border`, etc.) defined in `apps/landing/src/app/globals.css`.

The main frontend uses `ink/wave/glow` Tailwind tokens defined in `apps/frontend/tailwind.config.ts`:

```
ink-950: #070512    (body background)
ink-900: #0c0a1f
ink-800: #141133
wave-400: #a78bfa   (violet light)
wave-500: #8b5cf6
wave-600: #7c3aed   (violet dark)
glow-cyan: #38e8ff
glow-magenta: #ff5cc8
glow-amber: #ffb347
```

**Do not change the main app's token system.** Use the existing `ink/wave/glow` tokens for all new elements. Do not introduce `wp-*` variables into the main app.

---

## Elements to port from the landing page

### 1. Waveform SVG decoration — add to `GradientBackdrop`

`apps/frontend/src/presentation/components/GradientBackdrop.tsx`

The landing page's hero has a subtle two-line SVG waveform at the bottom of sections. Add this to the `GradientBackdrop` as a fixed element in the lower portion of the screen so it appears globally across all pages. Use `wave-400` and `glow-cyan` stroke colors at very low opacity (0.06–0.08). The lines should not compete with content — they are purely atmospheric.

```tsx
// Add inside the existing GradientBackdrop div, near the bottom
<svg
  aria-hidden="true"
  className="pointer-events-none absolute bottom-0 left-0 w-full opacity-[0.07]"
  viewBox="0 0 1440 120"
  preserveAspectRatio="none"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
>
  <path
    d="M0 60 Q180 20 360 60 Q540 100 720 60 Q900 20 1080 60 Q1260 100 1440 60"
    stroke="#a78bfa"
    strokeWidth="1.5"
  />
  <path
    d="M0 85 Q240 45 480 85 Q720 125 960 85 Q1200 45 1440 85"
    stroke="#38e8ff"
    strokeWidth="1"
  />
</svg>
```

---

### 2. "On Air" badge — replace the channel player's Now Playing indicator

`apps/frontend/src/app/(site)/channels/[slug]/page.tsx`

Currently the channel player page shows a cyan ping-animation "Now Playing" badge:

```tsx
<span className="relative flex h-2.5 w-2.5">
  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-60" />
  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-cyan-400" />
</span>
<span className="text-xs font-semibold uppercase tracking-widest text-cyan-400">
  Now Playing
</span>
```

Replace this with the landing page's amber "● On Air" badge style:

```tsx
<span className="rounded px-2.5 py-1 text-xs font-semibold tracking-wide border"
  style={{
    color: "var(--glow-amber, #ffb347)",        // use Tailwind class: text-glow-amber
    backgroundColor: "rgba(255,179,71,0.12)",   // bg-glow-amber/10
    borderColor: "rgba(255,179,71,0.25)",        // border-glow-amber/25
  }}
>
  ● On Air
</span>
```

Use Tailwind classes, not inline styles: `rounded border border-glow-amber/25 bg-glow-amber/10 px-2.5 py-1 text-xs font-semibold tracking-wide text-glow-amber`.

---

### 3. Waveform bars in the channel player — add to `ChannelPlayer`

`apps/frontend/src/features/channels/components/ChannelPlayer.tsx`

The landing page's PlayerMock has a waveform bar visualization (20 bars of varying heights, violet fill) below the track info. Add a static version of this to the `ChannelPlayer` component, positioned below the track title/artist info and above the playback controls if they exist, or below if not. It should be subtle and decorative — not an interactive element.

Heights array to use (px values, multiply by 0.28 to scale):
`[40, 65, 30, 80, 55, 70, 35, 90, 50, 75, 45, 85, 38, 60, 78, 42, 68, 52, 82, 48]`

Bars to the left of the midpoint (index < 10) get `opacity-80`, rest get `opacity-30`. Bar color: `bg-wave-400`. Width: `w-1` with `flex-1` in a flex row. Wrap in `role="img" aria-label="waveform"`.

---

### 4. Concentric arc decoration — add to channel player backdrop

`apps/frontend/src/features/channels/components/ChannelPlayer.tsx`

The landing page's PlayerMock has two concentric SVG arcs (one solid, one dashed) centered at the bottom of the backdrop area. Add these to the cover image / backdrop area of `ChannelPlayer`. Use `wave-400` for the solid arc and `glow-cyan` for the dashed arc, both at `opacity-20`. They should sit behind the cover art / play button, not on top.

```tsx
<svg
  aria-hidden="true"
  className="absolute inset-0 h-full w-full opacity-20 pointer-events-none"
  viewBox="0 0 600 300"
  fill="none"
>
  <circle cx="300" cy="300" r="180" stroke="#a78bfa" strokeWidth="1" />
  <circle cx="300" cy="300" r="240" stroke="#38e8ff" strokeWidth="0.75" strokeDasharray="4 8" />
</svg>
```

---

### 5. Section eyebrow label — standardize across site pages

Several site pages have ad-hoc heading styles. Standardize the eyebrow + title + description pattern already in `SectionHeading` by using it wherever a section header currently exists. Pages to audit:

- `apps/frontend/src/app/(site)/submit/page.tsx` — already has a `p` + `h1` pattern above the form; wrap with `SectionHeading` component.
- `apps/frontend/src/app/(site)/legal/page.tsx` — check for any raw headings and wrap.
- `apps/frontend/src/app/(site)/host/join/page.tsx` — same audit.

`SectionHeading` signature:
```tsx
<SectionHeading
  eyebrow="Submit a channel"   // small violet uppercase label
  title="Request a Channel"
  description="For hosts, DJs, artists..."
/>
```

---

### 6. Border divider pattern — home page sections

`apps/frontend/src/app/(site)/page.tsx`

The landing page uses `border-t` with a subtle border color to cleanly separate sections. The home page currently has no visual break between the hero and the channel directory. Add a `border-t border-white/10` divider between the hero `<section>` and the directory `<section>` to match the landing page's section rhythm.

---

## What NOT to change

- Do not change any auth, admin, or backend files
- Do not change the `GlassPanel`, `AppShell`, or `GradientBackdrop` structural layout — only add the waveform SVG to `GradientBackdrop`
- Do not change the `tailwind.config.ts` token set — use existing tokens only
- Do not add framer-motion animations to the main app (it doesn't currently use it for these components)
- Do not change any channel data fetching logic
- Keep the `ChannelPlayer` waveform bars purely decorative — no audio visualization wiring
- The "On Air" badge is purely cosmetic — do not change any state or playback logic

---

## Files to modify (summary)

| File | Change |
|---|---|
| `apps/frontend/src/presentation/components/GradientBackdrop.tsx` | Add waveform SVG decoration |
| `apps/frontend/src/app/(site)/channels/[slug]/page.tsx` | Replace "Now Playing" badge with "On Air" badge |
| `apps/frontend/src/features/channels/components/ChannelPlayer.tsx` | Add waveform bars + concentric arc decoration |
| `apps/frontend/src/app/(site)/page.tsx` | Add `border-t` divider between hero and directory |
| `apps/frontend/src/app/(site)/submit/page.tsx` | Replace manual heading with `SectionHeading` |
| `apps/frontend/src/app/(site)/legal/page.tsx` | Audit and standardize headings if needed |
| `apps/frontend/src/app/(site)/host/join/page.tsx` | Audit and standardize headings if needed |

---

## After making changes

1. Run `npx tsc --noEmit` in `apps/frontend/` — must pass with no errors
2. Start the dev server (`npm run dev` in `apps/frontend/`) and visually verify:
   - Home page: waveform SVG visible in backdrop, border divider between hero and grid
   - Channel player page: "On Air" badge, waveform bars, arc decoration
   - Submit page: `SectionHeading` eyebrow visible
3. Update `docs/STATUS.md` and `CLAUDE.md` if this constitutes a tracked change (it does not — this is a polish pass, not a new slice)
