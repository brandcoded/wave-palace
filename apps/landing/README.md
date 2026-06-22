# WavePalace Landing Page

Static marketing landing page for [wavepalace.live](https://wavepalace.live).

## Stack

- Next.js 14 (App Router, static export)
- Tailwind CSS v3
- Framer Motion
- Lucide React

## Getting started

```bash
cd apps/landing
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Build & export

```bash
npm run build
```

Static files are output to `out/`. Deploy the `out/` directory to any static host (Cloudflare Pages, Vercel, Render static site, etc.).

## Deploy on Render

Add a new **Static Site** service in Render:

| Setting | Value |
|---|---|
| Root directory | `apps/landing` |
| Build command | `npm install && npm run build` |
| Publish directory | `apps/landing/out` |

## Environment variables

None required for the landing page itself.
