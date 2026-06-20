# Monetization Plan — WavePalace Ad & Sponsorship Surfaces

> Owner: Growth / Monetization PM. Status: **planning — not yet built.**
> Last updated: 2026-06-19.
> This doc defines WavePalace's ad/sponsorship inventory, the build sequence,
> and copy-paste build prompts. It does **not** authorize building anything
> beyond the slice marked 🔲 NEXT in `docs/STATUS.md`.

---

## Key insight

WavePalace already has the two things most music apps lack as ad surfaces:

1. **A visual layer on every channel** (cover image / `visualLoopUrl` + the
   `ChannelPlayer` gradient overlay).
2. **A mux pipeline that bakes that visual layer into the VRChat MP4**
   (`mux_service.py` → FFmpeg `drawtext` / image overlay, shipped in Slice 1B).

That means **sponsorship rides with the channel into a VRChat world**, not just
on the webpage. Almost all of it is visual → **near-zero impact on listening.**

## Two structural facts that shape what's buildable

| Surface | Property | How to sell it |
|---|---|---|
| **Web player** | Dynamic + measurable. Can rotate, target, and count impressions (extend the Slice 3 add-on `POST /api/channels/{slug}/play` event path). | CPM or flat |
| **VRChat MP4** | Baked + fixed. Cannot serve per-viewer ads or count impressions in-world, and the video player is **not clickable**. | Flat / time-based; QR code is the clickable bridge; sell on plays + QR scans, **never CPM** |

The drawtext overlay used for channel/host info (`mux_service.py`, Slice 1B
drawtext parity) is the exact mechanism that burns a sponsor line into the MP4.

---

## Ad inventory (ordered by listening-experience impact)

### Tier 1 — Zero audio impact
| Surface | What it is | Web / VRChat | Model |
|---|---|---|---|
| Logo bug / "presented by" | Persistent sponsor mark in a cover corner | Both | Flat/mo |
| Sponsored lower-third | "Brought to you by X" under now-playing (add a sponsor line to existing drawtext) | Both (web rotates, VRChat baked) | CPM (web) / flat (VRChat) |
| Intro splash (pre-roll frame) | 3–5s branded frame before music | Both | Flat/channel |
| Outro / loop splash | Branded frame when playlist loops to track 1 | Both | Flat |
| **Pause-screen takeover** | Full sponsor card on pause — the sleeper: zero audio cost, high intentional-dwell attention | Web | CPM (premium) |
| Idle / inactivity card | Sponsor backdrop after N minutes idle | Web | CPM |
| Sponsored backdrop / skin | The cinematic background *is* the sponsor's visual (just a different `coverImageUrl`/loop — no new code) | Both | High-value flat |

### Tier 2 — Channel & distribution level (zero impact, high ACV)
| Surface | What it is | Model |
|---|---|---|
| Title-sponsored / brand channel | "Red Bull presents — Late Night Drive." Sponsor owns the channel look + lower-third | Sponsorship deal |
| Directory placement + sponsor badge | Promoted slot in the grid with a "Sponsored" badge | Flat/slot |
| Sponsored share card (OG image) | Link-preview image carries the sponsor — travels with every Discord/Twitter share, zero in-player impact | Flat |
| Sponsored "Listen elsewhere" CTA | The existing `externalLinks` slot doubles as a sponsor/affiliate CTA | Affiliate + flat |

### Tier 3 — VRChat-native creative (the moat)
| Surface | What it is | Why it's clever |
|---|---|---|
| **QR-code bridge in the MP4 corner** | Small QR baked into the muxed video → scan with phone | VRChat video players aren't clickable; a QR is the only way to make a baked ad actionable |
| Event/world sponsor frame | "This set sponsored by X" intro baked into a live event's MP4 | Monetizes the exact moment a host drops a channel into a world |

### Tier 4 — Audio (use sparingly, opt-in only)
| Surface | Impact | Note |
|---|---|---|
| Between-track sonic logo / sting | Low–moderate | 1–2s **between tracks only**, never over music. Far cleaner with AzuraCast (Slice 4) than the static mux → deferred to the Full Ad Stack |
| Sponsored station ID | Moderate | "WavePalace, powered by X" once per loop |

---

## Sequencing decision: thin primitive **before** Slice 4

**Build the thin Sponsor Primitive (Slice 6) before Slice 4 (Live event
streaming). Then build Slice 4 with the Event-Sponsorship add-on baked in. Then
build the Full Ad Stack (Slice 6B).**

Why before:
1. **Slice 4 is a recurring cost center; ads are a recurring revenue line.**
   Live streaming depends on VPS provisioning (Hetzner CPX31, ~$16/mo always-on).
   Don't enter your first ongoing-cost slice with zero proven willingness-to-pay.
2. **The primitive is cheap and has no Slice 4 dependency.** Tier-1 surfaces
   reuse the existing drawtext overlay, mux pipeline, web player, and the Slice 3
   admin dashboard. It is one small schema add (`sponsor` object).
3. **It makes Slice 4 monetizable on day one.** A live DJ set is the most
   sponsorable thing WavePalace will ever have (time + scarcity + intentional
   audience). "This set sponsored by X" + QR bridge only exists if the sponsor
   object is already built.
4. **It validates the buyer before committing infra.** If a sponsored channel
   won't sell on the cheap existing surface, live streaming won't fix that.

What NOT to do: don't build the Full Ad Stack (rotation, CPM measurement, audio
stings, reporting dashboard) before Slice 4 — that overbuilds ahead of audience
and violates the one-slice-at-a-time rule.

**The flip condition:** if the near-term objective is *audience growth, not
revenue* — i.e. live events are the headline feature that pulls in the hosts and
crowds who are the future sponsorship buyers — then build Slice 4 first, but
**still ship the `sponsor` object alongside it** so the launch event is
sponsorable. Either way, the sponsor primitive ships **no later than Slice 4.**

### Build order

| # | Slice | Contents | When |
|---|---|---|---|
| 1 | **Slice 6 — Sponsor Primitive** | `sponsor` schema + Tier-1 visual overlays (logo bug, lower-third) + pause-screen + share-card OG image + Featured directory slot/badge. Sell 1–2 sponsorships to validate. | 🔲 **NEXT (before Slice 4)** |
| 2 | **Slice 4 + Event-Sponsorship add-on** | Live event streaming as specced, plus event-sponsor intro frame + QR-code bridge (cheap because the primitive exists). | After Slice 6 |
| 3 | **Slice 6B — Full Ad Stack** | Dynamic rotation/targeting, web CPM measurement, intro/outro splash frames, idle card, opt-in audio stings (AzuraCast jingle rotation), sponsor reporting dashboard. | After Slice 4 |

---

## Planned data model (Slice 6)

```python
# apps/backend/app/schemas/sponsor.py
class Sponsor(BaseModel):
    name: str                       # "Red Bull"
    logoUrl: HttpUrl | None = None  # corner bug / lower-third logo
    text: str = ""                  # "Brought to you by Red Bull"
    clickUrl: HttpUrl | None = None # web CTA target + QR destination
    placement: str = "lower_third"  # "bug" | "lower_third" | "backdrop" | "intro" | "outro"
    startDate: datetime | None = None
    endDate: datetime | None = None
    isActive: bool = True
    isFeatured: bool = False         # promoted slot + "Sponsored" badge in directory
    impressionCount: int = 0         # web-measured only
    clickCount: int = 0
```

`Channel` gains `sponsor: Sponsor | None = None`. A sponsor is "live" when
`isActive and (startDate is None or now >= startDate) and (endDate is None or now <= endDate)`.

## Planned endpoints (Slice 6 / 6B)

| Method | Path | Slice | Purpose |
|---|---|---|---|
| `PATCH` | `/api/admin/channels/{slug}/sponsor` | 6 | Attach / update / clear a channel sponsor (JWT) |
| `POST` | `/api/channels/{slug}/sponsor/impression` | 6 | Web impression event (rate-limited like `/play`) |
| `POST` | `/api/channels/{slug}/sponsor/click` | 6 | Web CTA / QR click-through event |
| `GET` | `/api/admin/sponsors/report` | 6B | Impressions, clicks, QR scans, channel-time per sponsor (JWT) |

## Measurement reality (set sponsor expectations)

- **Web surfaces** → real impression/click counts (extend the existing
  play-count event path). Sell CPM or flat.
- **VRChat baked surfaces** → not per-impression measurable. Sell on
  **channel-time** (sponsored for a month) or **plays** (already counted), plus
  **QR scans** as the actionable metric. **Do not promise CPM on VRChat —
  promise reach + scans.**

---

## Build prompts (copy-paste, one slice at a time)

> Follow `AGENTS.md`: one vertical slice at a time, thin route handlers, services
> hold business rules, repositories hold data, tests for every backend change,
> docs + CHANGELOG updated, dark/cinematic visual direction. Do not start the
> next prompt until the previous slice is merged and smoke-tested.

### Prompt 1 — Slice 6: Sponsor Primitive (build this first, before Slice 4)

```
Build Slice 6 — Sponsor Primitive (thin monetization). This is the smallest
sponsor surface that works on BOTH the web player and the baked VRChat MP4, and
it must ship before Slice 4 (Live event streaming).

Scope (do not exceed):
1. Schema: add apps/backend/app/schemas/sponsor.py with the Sponsor model from
   docs/MONETIZATION_PLAN.md. Add `sponsor: Sponsor | None = None` to Channel.
   Add a service helper `sponsor_is_live(sponsor, now)` enforcing isActive +
   start/end date window. Keep route handlers thin.
2. Admin: PATCH /api/admin/channels/{slug}/sponsor (JWT) to attach/update/clear
   a sponsor. Add a "Sponsor" panel to the admin channel edit form (logo upload
   to R2, name, text, click URL, placement select, active toggle, date window,
   "Featured in directory" toggle). Match the existing admin UI style.
3. Web overlays (zero audio impact):
   - Logo bug: sponsor logo in a cover corner on ChannelPlayer.
   - Sponsored lower-third: append a "{sponsor.text}" line to the existing
     gradient overlay when a sponsor is live.
   - Pause-screen takeover: when the listener pauses, fade in a full sponsor
     card (logo + text + click CTA). Dismissible. No effect on audio.
   - Fire POST /api/channels/{slug}/sponsor/impression once per session
     (sessionStorage gate, same pattern as the play event) and
     /sponsor/click on CTA/logo click.
4. Sponsored share card: extend the channel page generateMetadata / OG image so
   the link-preview image carries the sponsor logo + "Sponsored by X" when a
   sponsor is live.
5. Directory: when sponsor.isFeatured and live, pin the channel to a promoted
   slot and show a small "Sponsored" badge on its card.
6. VRChat parity: in mux_service.py, when a sponsor is live, burn the sponsor
   lower-third line (drawtext) and, if logoUrl is set, overlay the logo bug into
   the muxed MP4 — reusing the existing drawtext/overlay path. No re-encode cost
   regression; keep -c:v copy on the video-loop final mux.
7. Events: add sponsor_impression and sponsor_click to the play-count event
   path so web impressions/clicks are counted.
8. Tests: sponsor_is_live window logic, the admin sponsor PATCH, impression/click
   rate-limit + dedupe, mux drawtext includes the sponsor line only when live.
9. Docs: update API_CONTRACT.md (new endpoints), CHANGELOG.md, STATUS.md,
   CLAUDE.md, HANDOFF.md, MVP_TO_LAUNCH_ROADMAP.md, and mark Slice 6 COMPLETE in
   FEATURE_SLICES.md.

Out of scope (do NOT build): dynamic multi-sponsor rotation, CPM billing, audio
stings, intro/outro splash frames, idle card, the sponsor reporting dashboard,
and the QR bridge — those are Slice 6B / the Slice 4 add-on.
```

### Prompt 2 — Slice 4 Event-Sponsorship add-on (build alongside Slice 4)

```
While building Slice 4 (Live event streaming — Link-In + ingest keys), add the
Event-Sponsorship add-on. It depends on Slice 6's Sponsor object already
existing, and on the SRS/FFmpeg streaming path from Slice 4.

Scope:
1. Event-sponsor intro frame: when a live event starts on a channel that has a
   live sponsor, prepend a 3–5s "This set sponsored by {sponsor.name}" frame
   (sponsor logo + text) to the event feed via the FFmpeg ingest/combiner path.
2. QR-code bridge: generate a QR encoding sponsor.clickUrl (or the channel's
   follow/code URL when set) and burn it into a corner of the live event video
   via FFmpeg overlay, so in-world VRChat viewers can scan it. Small, low-opacity,
   non-intrusive. Make it the only actionable element of a baked VRChat ad.
3. Admin: in the "Create Live Event" flow, show the event's active sponsor and a
   toggle for "Show sponsor intro frame" and "Show QR bridge."
4. Attribution: count QR scans by routing the QR to a /s/{token} endpoint that
   logs a sponsor_qr_scan event then 302-redirects to clickUrl.
5. Tests: intro frame + QR overlay are added only when a sponsor is live; QR
   redirect logs exactly one scan event and preserves the destination.
6. Docs: update API_CONTRACT.md, CHANGELOG.md, FEATURE_SLICES.md (Slice 4 add-on),
   STATUS.md.

Out of scope: dynamic rotation, CPM measurement, audio stings, reporting
dashboard (Slice 6B).
```

### Prompt 3 — Slice 6B: Full Ad Stack (build after Slice 4)

```
Build Slice 6B — Full Ad Stack. Only after Slice 4 is merged and live events are
pulling real audience worth selling against.

Scope:
1. Multi-sponsor rotation: a channel can hold multiple weighted sponsors; the web
   player rotates them by weight per session; the baked MP4 uses the highest-
   weight live sponsor. Migrate Channel.sponsor → Channel.sponsors: list.
2. Web measurement + CPM: per-sponsor impression/click rollups; add CPM/flat
   billing fields and a fill-rate concept. Extend the event path; nightly rollup
   into a sponsor_metrics collection.
3. Intro/outro splash frames for evergreen (non-live) channels: mux concatenates
   a branded pre-roll and a loop/outro frame around the playlist MP4.
4. Idle / inactivity card on the web player (after N minutes idle).
5. Audio (opt-in, host-gated): between-track sonic logo + sponsored station ID
   via AzuraCast jingle rotation (now cheap because Slice 4 provisioned
   AzuraCast). Never over music; between tracks only.
6. Sponsor reporting dashboard in admin: GET /api/admin/sponsors/report —
   impressions, clicks, QR scans, channel-time, est. VRChat reach per sponsor.
7. Tests + docs across the board.

Guardrails: audio surfaces are opt-in per channel and between-track only. Keep
VRChat sold on reach + scans, never CPM. Preserve the dark/cinematic direction.
```

---

## Related

- Revenue sizing: `WavePalace_Revenue_Model.xlsx` (local-only) — add an "Ad
  Inventory" tab keyed to the Tier 1–4 surfaces above.
- Slice specs: `docs/FEATURE_SLICES.md` (Slice 6, Slice 6B, Slice 4 add-on).
- Status: `docs/STATUS.md` (canonical) · compact copy in `CLAUDE.md`.
