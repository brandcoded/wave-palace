# Architecture — WavePalace

WavePalace is a two-app workspace with strict layer separation.

```
apps/
  frontend/   Next.js App Router + TypeScript + Tailwind
  backend/    FastAPI + Pydantic (Mongo-ready, seed fallback)
```

## Frontend structure

- `src/app` — App Router routes (`/` and `/channels/[slug]`) and layout.
- `src/presentation` — pure visual building blocks (AppShell, GradientBackdrop,
  GlassPanel, SectionHeading). No API/business logic.
- `src/shared` — cross-cutting helpers (e.g. `cn`).
- `src/features/channels` — the channel feature: typed API client (`lib`),
  TypeScript `types`, and feature `components` (ChannelGrid, ChannelCard,
  ChannelFilters, ChannelPlayer, CopyLinkButton, RightsNotice,
  CompatibilityNotice).

The home directory grid fetches on the client so filter chips feel instant. The
channel detail page fetches on the server so it can return a proper 404
(`not-found.tsx`) for missing/unpublished channels.

## Backend structure

- `app/api/routes` — thin HTTP handlers (presentation/transport).
- `app/api/dependencies.py` — wiring (builds the service + repository).
- `app/services` — **business layer**: published-only rule, filtering, URL
  presence validation.
- `app/repositories` — **data layer**: `ChannelRepository` interface with
  `SeedChannelRepository` and `MongoChannelRepository` implementations.
- `app/seed` — seed channel data.
- `app/schemas` — Pydantic models (the transport contract).
- `app/core` — configuration.

## Why seed fallback before a full production database

The MVP must run for anyone with zero setup. If `MONGODB_URI` is unset, the
repository factory returns the in-memory `SeedChannelRepository` and logs that
it is in seed mode. When a database is configured, the same service code talks
to `MongoChannelRepository` instead — no business-logic changes. This keeps the
walking skeleton runnable today while leaving a clean path to MongoDB Atlas.

## Layer rules

Route handlers never contain business logic. The service layer never reaches
into HTTP or the database driver directly. The presentation layer never embeds
API/business logic. This separation is the project's load-bearing constraint —
see `AGENTS.md`.
