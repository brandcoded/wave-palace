# Prompt: Auto re-mux on publish when muxOutdated

**Goal:** When a music director publishes a channel that has `muxOutdated: true`,
automatically fire a background mux job so the VRChat MP4 stays in sync without
requiring a separate manual step.

**Trigger:** `PATCH /api/admin/channels/{slug}` with `isPublished: true` when the
resulting channel document has `muxOutdated: true`. No new endpoint needed.

**Non-goals:**
- Do NOT auto-mux on every track/title/cover save — only on publish
- Do NOT block the PATCH response — mux runs fully in the background
- Do NOT change the manual "Update All VR Videos" flow (it stays as-is)

---

## Context: what already exists

- `muxOutdated` is already set to `true` by `PATCH /{slug}` when overlay fields
  change (`_OVERLAY_FIELDS`: title, hostName, genre, mood, visualLoopUrl,
  coverImageUrl, playlist) and by sponsor changes
- `muxOutdated` is cleared to `false` by `mux_service.mux_channel()` on success
- `POST /api/channels/{slug}/mux` already fires an async background mux (202)
  and writes state into `_CHANNEL_JOBS[slug]` in `mux.py`
- `_run_mux_channel(slug, service)` is the background coroutine in `mux.py`
- `_CHANNEL_JOBS[slug]` holds `{state, url, error, started_at, finished_at}`
- 409 guard: if `_CHANNEL_JOBS.get(slug, {}).get("state") == "running"` → skip

---

## Files to change

### 1. `apps/backend/app/api/routes/admin_channels.py`

**Add imports:**
```python
import time
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from app.api.dependencies import get_channel_service, get_mux_service, get_user_repository
from app.services.mux_service import MuxService
```

(`BackgroundTasks` and `get_mux_service` are new; rest already imported.)

**Update `update_channel` signature** to inject `BackgroundTasks` and `MuxService`:

```python
@router.patch("/{slug}", response_model=dict)
async def update_channel(
    slug: str,
    body: ChannelPatchRequest,
    background_tasks: BackgroundTasks,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
    mux_service: MuxService = Depends(get_mux_service),
) -> dict:
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if patch.keys() & _OVERLAY_FIELDS:
        patch["muxOutdated"] = True
    updated = await service.update(slug, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Auto-mux: publishing a channel that has stale VRChat video.
    if patch.get("isPublished") is True and updated.get("muxOutdated"):
        from app.api.routes.mux import _CHANNEL_JOBS, _run_mux_channel
        if _CHANNEL_JOBS.get(slug, {}).get("state") != "running":
            _CHANNEL_JOBS[slug] = {
                "state": "running",
                "url": None,
                "error": None,
                "started_at": time.time(),
                "finished_at": None,
            }
            background_tasks.add_task(_run_mux_channel, slug, mux_service)

    return updated
```

**Update `update_channel_sponsor`** — sponsor changes always set `muxOutdated:
True`, so apply the same auto-mux logic there if the channel is already published:

```python
@router.patch("/{slug}/sponsor", response_model=dict)
async def update_channel_sponsor(
    slug: str,
    body: Annotated[Sponsor | None, Body()] = None,
    background_tasks: BackgroundTasks,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
    mux_service: MuxService = Depends(get_mux_service),
) -> dict:
    sponsor_data = body.model_dump() if body is not None else None
    updated = await service.update(slug, {
        "sponsor": sponsor_data,
        "muxOutdated": True,
    })
    if updated is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Auto-mux: sponsor overlay change on a live channel.
    if updated.get("isPublished") and updated.get("muxOutdated"):
        from app.api.routes.mux import _CHANNEL_JOBS, _run_mux_channel
        if _CHANNEL_JOBS.get(slug, {}).get("state") != "running":
            _CHANNEL_JOBS[slug] = {
                "state": "running",
                "url": None,
                "error": None,
                "started_at": time.time(),
                "finished_at": None,
            }
            background_tasks.add_task(_run_mux_channel, slug, mux_service)

    return updated
```

---

### 2. `apps/backend/app/tests/test_admin.py`

Add one new test after the existing channel management tests. It needs a
`channels_and_mux_client` fixture that overrides BOTH `get_channel_service` AND
`get_mux_service`:

```python
@pytest.fixture()
def channels_and_mux_client() -> TestClient:
    from app.api.dependencies import get_mux_service
    from app.services.mux_service import MuxService
    from app.api.routes import mux as mux_routes

    mux_routes._CHANNEL_JOBS.clear()

    repo = SeedChannelRepository()
    svc = ChannelService(repo)
    app.dependency_overrides[get_channel_service] = lambda: svc

    mock_mux = MagicMock(spec=MuxService)
    mock_mux.mux_channel = AsyncMock(return_value="https://stream.wavepalace.live/muxed/test.mp4")
    app.dependency_overrides[get_mux_service] = lambda: mock_mux

    client = _make_client(authed=True)
    yield client, mock_mux
    app.dependency_overrides.clear()
    mux_routes._CHANNEL_JOBS.clear()
```

Add the test:

```python
def test_publish_outdated_channel_triggers_auto_mux(channels_and_mux_client):
    """Publishing a channel with muxOutdated=True fires a background mux job."""
    from app.api.routes import mux as mux_routes
    client, mock_mux = channels_and_mux_client

    # Force muxOutdated on the seed channel by patching a playlist field first.
    client.patch("/api/admin/channels/late-night-house", json={"title": "Late Night House v2"})
    assert mux_routes._CHANNEL_JOBS.get("late-night-house") is None or \
           mux_routes._CHANNEL_JOBS.get("late-night-house", {}).get("state") != "running"

    # Now publish — should trigger auto-mux.
    mux_routes._CHANNEL_JOBS.clear()
    res = client.patch("/api/admin/channels/late-night-house", json={"isPublished": True})
    assert res.status_code == 200

    # Background task runs synchronously in TestClient.
    job = mux_routes._CHANNEL_JOBS.get("late-night-house")
    assert job is not None
    assert job["state"] == "done"
    mock_mux.mux_channel.assert_called_with("late-night-house")


def test_publish_without_outdated_does_not_trigger_mux(channels_and_mux_client):
    """Publishing a channel that is already up to date does NOT mux."""
    from app.api.routes import mux as mux_routes
    client, mock_mux = channels_and_mux_client

    # SeedChannelRepository channels start with muxOutdated=False.
    mux_routes._CHANNEL_JOBS.clear()
    res = client.patch("/api/admin/channels/late-night-house", json={"isPublished": True})
    assert res.status_code == 200
    mock_mux.mux_channel.assert_not_called()
```

The imports needed at the top of test_admin.py — `AsyncMock` is already imported.
Add `get_mux_service` to the existing import from `app.api.dependencies` if not
already there.

---

### 3. `apps/frontend/src/app/admin/channels/page.tsx`

`togglePublish` currently awaits `updateChannel` and replaces the channel row.
After the auto-mux lands, `updated.muxOutdated` will still be `true` briefly
(the background task hasn't finished yet). Show a per-channel "VR updating…"
badge while the job runs, replacing the "VR outdated" badge.

Add per-channel mux tracking state and update `togglePublish`:

```tsx
const [channelMuxing, setChannelMuxing] = useState<Record<string, boolean>>({});

async function togglePublish(ch: AdminChannel) {
  const updated = await updateChannel(ch.slug, { isPublished: !ch.isPublished });
  setChannels((prev) => prev.map((c) => (c.slug === ch.slug ? { ...c, ...updated } : c)));

  // If we just published a stale channel, the backend auto-queued a mux.
  // Poll status until done so the badge updates without a full page reload.
  if (updated.isPublished && updated.muxOutdated) {
    setChannelMuxing((prev) => ({ ...prev, [ch.slug]: true }));
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/channels/${ch.slug}/mux/status`, {
          credentials: "include",
        });
        if (!res.ok) { clearInterval(interval); return; }
        const job = await res.json();
        if (job.state === "done" || job.state === "error") {
          clearInterval(interval);
          setChannelMuxing((prev) => ({ ...prev, [ch.slug]: false }));
          listAdminChannels().then(setChannels);
        }
      } catch { clearInterval(interval); }
    }, 3000);
  }
}
```

Update the "VR outdated" badge in both the desktop table and mobile card list to
show a spinner when `channelMuxing[ch.slug]` is true:

```tsx
{ch.muxOutdated && (
  channelMuxing[ch.slug]
    ? <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-amber-300">
        <Loader2 className="h-2.5 w-2.5 animate-spin" /> VR updating
      </span>
    : <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-amber-300">
        VR outdated
      </span>
)}
```

Apply this badge replacement in both the desktop table (`line ~192`) and the
mobile card list (`line ~239`). `Loader2` is already imported.

---

## What NOT to change

- `mux.py` — no changes; `_run_mux_channel` and `_CHANNEL_JOBS` are reused as-is
- `mux_service.py` — no changes
- `adminApi.ts` — no changes; this wires polling at the route level, not the API lib
- `HANDOFF.md`, `CLAUDE.md`, `STATUS.md`, or any other docs

---

## Definition of done

- [ ] `PATCH /{slug}` with `isPublished: true` on a `muxOutdated` channel fires
      `_run_mux_channel` as a background task and writes initial state to
      `_CHANNEL_JOBS[slug]`
- [ ] 409 guard respected: if mux is already running, do not stack a second job
- [ ] Sponsor update on a published channel also auto-fires mux
- [ ] Publish with `muxOutdated: false` does NOT trigger a mux
- [ ] `test_publish_outdated_channel_triggers_auto_mux` passes
- [ ] `test_publish_without_outdated_does_not_trigger_mux` passes
- [ ] All existing admin + mux tests still pass
- [ ] Frontend "VR outdated" badge transitions to "VR updating…" spinner on
      publish, then clears when job completes
- [ ] `pytest apps/backend/app/tests/` — all green
