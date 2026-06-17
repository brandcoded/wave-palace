def test_list_returns_published_channels(client):
    res = client.get("/api/channels")
    assert res.status_code == 200
    channels = res.json()
    assert len(channels) == 3
    assert all(c["isPublished"] for c in channels)


def test_list_excludes_unpublished_channels(client):
    res = client.get("/api/channels")
    slugs = {c["slug"] for c in res.json()}
    assert "hidden-draft" not in slugs


def test_get_channel_by_slug(client):
    res = client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    assert res.json()["title"] == "Late Night House"


def test_missing_channel_returns_404(client):
    res = client.get("/api/channels/does-not-exist")
    assert res.status_code == 404


def test_unpublished_channel_by_slug_returns_404(client):
    res = client.get("/api/channels/hidden-draft")
    assert res.status_code == 404


def test_filter_by_genre(client):
    res = client.get("/api/channels", params={"genre": "House"})
    channels = res.json()
    assert len(channels) == 1
    assert channels[0]["slug"] == "late-night-house"


def test_filter_by_mood(client):
    res = client.get("/api/channels", params={"mood": "Dark"})
    channels = res.json()
    assert len(channels) == 1
    assert channels[0]["slug"] == "neon-afterhours"


def test_filter_is_case_insensitive(client):
    res = client.get("/api/channels", params={"genre": "house"})
    assert len(res.json()) == 1


def test_filter_combination_returns_empty(client):
    res = client.get("/api/channels", params={"genre": "House", "mood": "Dark"})
    assert res.json() == []
