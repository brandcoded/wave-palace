import type { CurrentUser } from "@/features/admin/types/admin";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function getMe(): Promise<CurrentUser | null> {
  try {
    const res = await apiFetch("/api/auth/me");
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Listen history
// ---------------------------------------------------------------------------

export async function recordListenEvent(
  channelSlug: string,
  trackTitle: string | null,
  trackArtist: string | null,
  sessionKey: string | null,
): Promise<void> {
  apiFetch("/api/me/history", {
    method: "POST",
    body: JSON.stringify({
      channel_slug: channelSlug,
      track_title: trackTitle,
      track_artist: trackArtist,
      session_key: sessionKey,
    }),
  }).catch(() => {}); // fire-and-forget; never throw
}

export async function mergeListenHistory(sessionKey: string): Promise<number> {
  const res = await apiFetch("/api/me/history/merge", {
    method: "POST",
    body: JSON.stringify({ session_key: sessionKey }),
  });
  if (!res.ok) return 0;
  const data = await res.json();
  return data.merged ?? 0;
}

export interface ListenEvent {
  id: string;
  channel_slug: string;
  track_title: string | null;
  track_artist: string | null;
  started_at: string;
}

export interface HistoryResponse {
  recent: ListenEvent[];
  top_channel: string | null;
  last_channel: string | null;
}

export async function getHistory(): Promise<HistoryResponse> {
  const res = await apiFetch("/api/me/history");
  if (!res.ok) return { recent: [], top_channel: null, last_channel: null };
  return res.json();
}

// ---------------------------------------------------------------------------
// Saves
// ---------------------------------------------------------------------------

export async function getSaves(): Promise<string[]> {
  const res = await apiFetch("/api/me/saves");
  if (!res.ok) return [];
  const data = await res.json();
  return data.slugs ?? [];
}

export async function saveChannel(slug: string): Promise<void> {
  await apiFetch(`/api/me/saves/${slug}`, { method: "POST" });
}

export async function unsaveChannel(slug: string): Promise<void> {
  await apiFetch(`/api/me/saves/${slug}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface Notification {
  id: string;
  type: string;
  channel_slug: string | null;
  title: string;
  body: string | null;
  link: string | null;
  read: boolean;
  created_at: string;
}

export interface NotificationsResponse {
  notifications: Notification[];
  unread_count: number;
}

export async function getNotifications(): Promise<NotificationsResponse> {
  const res = await apiFetch("/api/me/notifications");
  if (!res.ok) return { notifications: [], unread_count: 0 };
  return res.json();
}

export async function markNotificationRead(id: string): Promise<void> {
  await apiFetch(`/api/me/notifications/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ read: true }),
  });
}

export async function markAllRead(): Promise<void> {
  await apiFetch("/api/me/notifications/mark-all-read", { method: "POST" });
}

export async function getUnreadCount(): Promise<number> {
  const res = await apiFetch("/api/me/notifications");
  if (!res.ok) return 0;
  const data = await res.json();
  return data.unread_count ?? 0;
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

export async function getRecommendations(): Promise<Record<string, unknown>[]> {
  const res = await apiFetch("/api/me/recommendations");
  if (!res.ok) return [];
  const data = await res.json();
  return data.recommendations ?? [];
}

// ---------------------------------------------------------------------------
// Followed channels
// ---------------------------------------------------------------------------

export async function getFollowedSlugs(): Promise<string[]> {
  const res = await apiFetch("/api/me/follows");
  if (!res.ok) return [];
  const data = await res.json();
  return data.slugs ?? [];
}

// ---------------------------------------------------------------------------
// Owned channels (creator panel)
// ---------------------------------------------------------------------------

export async function getOwnedChannels(): Promise<Record<string, unknown>[]> {
  const res = await apiFetch("/api/me/channels");
  if (!res.ok) return [];
  const data = await res.json();
  return data.channels ?? [];
}

// ---------------------------------------------------------------------------
// Session key helpers
// ---------------------------------------------------------------------------

export function getOrCreateSessionKey(): string {
  if (typeof window === "undefined") return "";
  let sk = localStorage.getItem("wp_listen_session");
  if (!sk) {
    sk = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
    localStorage.setItem("wp_listen_session", sk);
  }
  return sk;
}
