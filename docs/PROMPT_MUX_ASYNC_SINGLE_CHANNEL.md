# Prompt: Convert single-channel mux to background task

**Problem:** `POST /api/channels/{slug}/mux` is synchronous — it holds the HTTP
connection open until FFmpeg finishes. On Render, large files (a 3.5-hour DJ mix
takes 20–40 min to encode) hit the platform-level HTTP timeout and return 502
even though the encode may still be running. `POST /api/mux/all` already handles
this correctly via `BackgroundTasks` + a polling status endpoint. Apply the same
pattern to the single-channel route.

---

## Files to change

### 1. `apps/backend/app/api/routes/mux.py`

**Add a per-slug job store** alongside the existing `_JOB` dict:

```python
# Per-slug state for single-channel async mux.
_CHANNEL_JOBS: dict[str, dict] = {}
```

State shape (identical to the per-channel entries inside `_JOB["channels"]`):
```python
{
    "state": "pending" | "running" | "done" | "error",
    "url": str | None,
    "error": str | None,
    "started_at": float | None,
    "finished_at": float | None,
}
```

**Replace the synchronous `mux_channel` route** — change it from returning 200 +
URL to returning 202 + poll URL, exactly like `/api/mux/all`:

```python
@router.post("/api/channels/{slug}/mux", status_code=202)
async def mux_channel(
    slug: str,
    background_tasks: BackgroundTasks,
    service: MuxService = Depends(get_mux_service),
) -> dict:
    if _CHANNEL_JOBS.get(slug, {}).get("state") == "running":
        raise HTTPException(status_code=409, detail="Mux already running for this channel.")
    _CHANNEL_JOBS[slug] = {
        "state": "running",
        "url": None,
        "error": None,
        "started_at": time.time(),
        "finished_at": None,
    }
    background_tasks.add_task(_run_mux_channel, slug, service)
    return {"slug": slug, "status": "accepted", "poll": f"/api/channels/{slug}/mux/status"}
```

**Add the background worker** (mirrors `_run_mux_all`):

```python
async def _run_mux_channel(slug: str, service: MuxService) -> None:
    try:
        url = await service.mux_channel(slug)
        _CHANNEL_JOBS[slug].update(state="done", url=url, finished_at=time.time())
    except Exception as exc:
        _CHANNEL_JOBS[slug].update(state="error", error=str(exc), finished_at=time.time())
        logger.error("MUX FAILED [%s]: %s", slug, exc)
```

**Add a status endpoint** for the single-channel job:

```python
@router.get("/api/channels/{slug}/mux/status")
async def mux_channel_status(slug: str) -> dict:
    job = _CHANNEL_JOBS.get(slug)
    if job is None:
        raise HTTPException(status_code=404, detail="No mux job found for this channel.")
    return {"slug": slug, **job}
```

**Also reset `_CHANNEL_JOBS` in the test fixture** — add this line next to where
`_JOB` is reset in `mux_client`:
```python
mux_routes._CHANNEL_JOBS.clear()
```

---

### 2. `apps/backend/app/tests/test_mux.py`

Update and extend the route tests. The existing
`test_mux_channel_returns_url` expects `200` — change it to `202`:

```python
def test_mux_channel_returns_202(mux_client):
    res = mux_client.post("/api/channels/late-night-house/mux")
    assert res.status_code == 202
    body = res.json()
    assert body["slug"] == "late-night-house"
    assert body["status"] == "accepted"
    assert "poll" in body
```

Add three new route tests:

```python
def test_mux_channel_status_done(mux_client):
    """After the background task completes, status endpoint returns done + url."""
    mux_client.post("/api/channels/late-night-house/mux")
    res = mux_client.get("/api/channels/late-night-house/mux/status")
    assert res.status_code == 200
    body = res.json()
    assert body["state"] == "done"
    assert body["url"] == _FAKE_URL

def test_mux_channel_status_404_when_never_started(mux_client):
    res = mux_client.get("/api/channels/never-started/mux/status")
    assert res.status_code == 404

def test_mux_channel_409_when_already_running(mux_client):
    """Second POST while state is 'running' returns 409."""
    from app.api.routes import mux as mux_routes
    mux_routes._CHANNEL_JOBS["late-night-house"] = {
        "state": "running", "url": None, "error": None,
        "started_at": time.time(), "finished_at": None,
    }
    res = mux_client.post("/api/channels/late-night-house/mux")
    assert res.status_code == 409
```

Add `import time` to the test file imports.

---

### 3. `apps/frontend/src/features/admin/lib/adminApi.ts`

`muxChannel` currently awaits a synchronous 200 response. Update it to:
1. POST → expect 202
2. Poll `GET /api/channels/{slug}/mux/status` every 3 seconds
3. Resolve when `state === "done"`, reject when `state === "error"`

```typescript
export async function muxChannel(
  slug: string
): Promise<{ slug: string; vrchatPlaybackUrl: string }> {
  const res = await apiFetch(`/api/channels/${slug}/mux`, { method: "POST" });
  if (res.status !== 202) throw new Error(`Mux start failed: ${res.status}`);

  const pollUrl = `/api/channels/${slug}/mux/status`;
  for (let attempt = 0; attempt < 120; attempt++) {   // up to 6 minutes
    await new Promise((r) => setTimeout(r, 3000));
    const status = await apiFetch(pollUrl);
    if (!status.ok) throw new Error("Mux status check failed");
    const data = await status.json();
    if (data.state === "done") return { slug, vrchatPlaybackUrl: data.url };
    if (data.state === "error") throw new Error(data.error ?? "Mux failed");
  }
  throw new Error("Mux timed out after 6 minutes");
}
```

---

## What NOT to change

- `POST /api/mux/all` and `GET /api/mux/status` — already async, leave them alone
- The admin channels page (`app/admin/channels/page.tsx`) — it only calls
  `/api/mux/all`, not `muxChannel`. No frontend page changes needed.
- `mux_service.py`, `r2_repository.py` — no changes needed
- `HANDOFF.md`, `CLAUDE.md`, `STATUS.md`, or any other docs

---

## Definition of done

- [ ] `POST /api/channels/{slug}/mux` returns 202 immediately with `poll` URL
- [ ] `GET /api/channels/{slug}/mux/status` returns current job state
- [ ] 409 returned when a mux is already running for that slug
- [ ] 404 returned when no job has ever been started for that slug
- [ ] `_run_mux_channel` stores `done` + URL on success, `error` + message on failure
- [ ] `mux_client` fixture resets `_CHANNEL_JOBS` between tests
- [ ] All existing mux tests pass; new tests cover 202, status done, 404, 409
- [ ] `adminApi.ts` `muxChannel` polls until done/error
- [ ] `pytest apps/backend/app/tests/test_mux.py` — all green
