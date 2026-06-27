const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export interface CodeInfo {
  code: string;
  entity_type: string;
  entity_id: string;
  display_name: string;
  host_name?: string | null;
  genre?: string[] | null;
  mood?: string[] | null;
  cover_image_url?: string | null;
  track_title?: string | null;
  track_artist?: string | null;
}

export interface FollowResult {
  follow_id: string;
  channel: string;
  confirmed: boolean;
}

export interface FollowView {
  id: string;
  entity_type: string;
  channel_slug: string;
  display_name: string;
  notification_channel: string;
  confirmed: boolean;
  created_at: string;
  notify_new_tracks: boolean;
  notify_channel_live: boolean;
  notify_digest: boolean;
  channel_created_at: string | null;
}

export async function resolveCode(code: string): Promise<CodeInfo | null> {
  const res = await fetch(`${API_BASE_URL}/api/codes/${code}`, {
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to resolve code");
  return res.json();
}

export async function submitFollow(
  code: string,
  body: {
    channel: string;
    discord_user_id?: string;
    discord_username?: string;
    email?: string;
    push_subscription?: object;
    vrchat_username?: string;
  }
): Promise<FollowResult> {
  const res = await fetch(`${API_BASE_URL}/api/codes/${code}/follow`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export async function getMyFollows(): Promise<FollowView[]> {
  const res = await fetch(`${API_BASE_URL}/api/follows`, {
    credentials: "include",
    cache: "no-store",
  });
  if (res.status === 401) return [];
  if (!res.ok) throw new Error("Failed to load follows");
  return res.json();
}

export async function deleteFollow(followId: string): Promise<void> {
  await fetch(`${API_BASE_URL}/api/follows/${followId}`, {
    method: "DELETE",
    credentials: "include",
  });
}

export type FollowMeResult = FollowResult & { already?: boolean };

export async function followAsMe(code: string): Promise<FollowMeResult> {
  const res = await fetch(`${API_BASE_URL}/api/codes/${code}/follow/me`, {
    method: "POST",
    credentials: "include",
  });
  if (res.status === 409) {
    return { follow_id: "", channel: "", confirmed: true, already: true };
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export interface FollowStatus {
  following: boolean;
  follow_id: string | null;
}

export async function getFollowStatus(channelSlug: string): Promise<FollowStatus> {
  const res = await fetch(`${API_BASE_URL}/api/me/follows/${channelSlug}`, {
    credentials: "include",
    cache: "no-store",
  });
  if (res.status === 401) return { following: false, follow_id: null };
  if (!res.ok) throw new Error("Failed to check follow status");
  return res.json();
}

export async function getFollowerCount(channelSlug: string): Promise<number> {
  const res = await fetch(`${API_BASE_URL}/api/channels/${channelSlug}/followers/count`, {
    cache: "no-store",
  });
  if (!res.ok) return 0;
  const data = await res.json();
  return data.count;
}

export async function updateFollowPrefs(
  followId: string,
  prefs: {
    notification_channel?: string;
    notify_new_tracks?: boolean;
    notify_channel_live?: boolean;
    notify_digest?: boolean;
  }
): Promise<FollowView> {
  const res = await fetch(`${API_BASE_URL}/api/follows/${followId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(prefs),
  });
  if (!res.ok) throw new Error("Failed to update preferences");
  return res.json();
}
