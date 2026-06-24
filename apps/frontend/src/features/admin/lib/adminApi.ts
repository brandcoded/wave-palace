import type { AdminChannel, AdminSubmission, AdminTakedown, AdminUser, AnalyticsSummary, CurrentUser, Sponsor, SubmissionOptions, URLCheckResult, UserRole } from "@/features/admin/types/admin";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  return res;
}

// ------------------------------------------------------------------
// Auth
// ------------------------------------------------------------------

export async function login(secret: string): Promise<{ ok: boolean }> {
  const res = await apiFetch("/api/admin/login", {
    method: "POST",
    body: JSON.stringify({ secret }),
  });
  if (!res.ok) throw new Error("Incorrect secret");
  return res.json();
}

export async function logout(): Promise<void> {
  await apiFetch("/api/auth/logout", { method: "POST" });
}

export async function checkSession(): Promise<CurrentUser> {
  const res = await apiFetch("/api/auth/me");
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

export async function requestEmailLink(email: string): Promise<void> {
  const res = await apiFetch("/api/auth/email/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error("Failed to send magic link");
}

export function discordLoginUrl(): string {
  return `${API_BASE}/api/auth/discord/initiate?intent=login`;
}

// ------------------------------------------------------------------
// User management (admin-only)
// ------------------------------------------------------------------

export async function listUsers(): Promise<AdminUser[]> {
  const res = await apiFetch("/api/admin/users");
  if (!res.ok) throw new Error("Failed to list users");
  return res.json();
}

export async function updateUserRoles(id: string, roles: UserRole[]): Promise<AdminUser> {
  const res = await apiFetch(`/api/admin/users/${id}/roles`, {
    method: "PATCH",
    body: JSON.stringify({ roles }),
  });
  if (!res.ok) throw new Error("Failed to update roles");
  return res.json();
}

export async function updateUserActive(id: string, is_active: boolean): Promise<AdminUser> {
  const res = await apiFetch(`/api/admin/users/${id}/active`, {
    method: "PATCH",
    body: JSON.stringify({ is_active }),
  });
  if (!res.ok) throw new Error("Failed to update user");
  return res.json();
}

// ------------------------------------------------------------------
// Submissions
// ------------------------------------------------------------------

export async function listSubmissions(status = "pending"): Promise<AdminSubmission[]> {
  const res = await apiFetch(`/api/admin/submissions?status=${status}`);
  if (!res.ok) throw new Error("Failed to load submissions");
  return res.json();
}

export async function reviewSubmission(
  id: string,
  status: string,
  reviewer_notes?: string
): Promise<AdminSubmission> {
  const res = await apiFetch(`/api/admin/submissions/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status, reviewer_notes: reviewer_notes ?? null }),
  });
  if (!res.ok) throw new Error("Failed to update submission");
  return res.json();
}

// ------------------------------------------------------------------
// Channels
// ------------------------------------------------------------------

export async function listAdminChannels(): Promise<AdminChannel[]> {
  const res = await apiFetch("/api/admin/channels");
  if (!res.ok) throw new Error("Failed to load channels");
  return res.json();
}

export async function createChannel(data: Partial<AdminChannel>): Promise<AdminChannel> {
  const res = await apiFetch("/api/admin/channels", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create channel");
  return res.json();
}

export async function updateChannel(
  slug: string,
  data: Partial<AdminChannel>
): Promise<AdminChannel> {
  const res = await apiFetch(`/api/admin/channels/${slug}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update channel");
  return res.json();
}

export async function deleteChannel(slug: string): Promise<void> {
  const res = await apiFetch(`/api/admin/channels/${slug}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete channel");
}

export async function muxChannel(slug: string): Promise<{ slug: string; vrchatPlaybackUrl: string }> {
  const res = await apiFetch(`/api/channels/${slug}/mux`, { method: "POST" });

  // 200 = old sync backend (transitional compat during Render deploy window)
  if (res.status === 200) return res.json();
  if (res.status !== 202) throw new Error(`Mux failed to start (HTTP ${res.status})`);

  for (let attempt = 0; attempt < 120; attempt++) {   // up to 6 minutes
    await new Promise((r) => setTimeout(r, 3000));
    const st = await apiFetch(`/api/channels/${slug}/mux/status`);
    if (st.status === 404) throw new Error("Server restarted mid-mux — please try again.");
    if (!st.ok) throw new Error("Lost connection to mux status — please try again.");
    const data = await st.json();
    if (data.state === "done") return { slug, vrchatPlaybackUrl: data.url };
    if (data.state === "error") throw new Error(data.error ?? "Mux failed");
  }
  throw new Error("Mux is taking longer than 6 minutes — check back and try again.");
}

export async function updateChannelSponsor(
  slug: string,
  sponsor: Sponsor | null
): Promise<AdminChannel> {
  const res = await apiFetch(`/api/admin/channels/${slug}/sponsor`, {
    method: "PATCH",
    body: JSON.stringify(sponsor),
  });
  if (!res.ok) throw new Error("Failed to update sponsor");
  return res.json();
}

export async function validateChannelUrls(slug: string): Promise<URLCheckResult[]> {
  const res = await apiFetch(`/api/admin/channels/${slug}/validate-urls`, { method: "POST" });
  if (!res.ok) throw new Error("Validation failed");
  return res.json();
}

// ------------------------------------------------------------------
// Uploads
// ------------------------------------------------------------------

async function uploadFile(endpoint: string, file: File): Promise<{ url: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Upload failed");
  }
  return res.json();
}

export const uploadImage = (file: File) => uploadFile("/api/admin/upload/image", file);
export const uploadVideo = (file: File) => uploadFile("/api/admin/upload/video", file);
export const uploadAudio = (file: File) => uploadFile("/api/admin/upload/audio", file);

// ------------------------------------------------------------------
// Submission options
// ------------------------------------------------------------------

export async function getOptions(): Promise<SubmissionOptions> {
  const res = await apiFetch("/api/admin/options");
  if (!res.ok) throw new Error("Failed to load options");
  return res.json();
}

export async function updateOptions(field: string, options: string[]): Promise<void> {
  const res = await apiFetch(`/api/admin/options/${field}`, {
    method: "PATCH",
    body: JSON.stringify({ options }),
  });
  if (!res.ok) throw new Error("Failed to update options");
}

// ------------------------------------------------------------------
// Streaming toggle
// ------------------------------------------------------------------

export async function bulkSetStreaming(streamingActive: boolean): Promise<{ updated: number; streamingActive: boolean }> {
  const res = await apiFetch("/api/admin/channels/streaming/bulk", {
    method: "POST",
    body: JSON.stringify({ streamingActive }),
  });
  if (!res.ok) throw new Error("Bulk streaming toggle failed");
  return res.json();
}

// ------------------------------------------------------------------
// Follow codes (Slice 9)
// ------------------------------------------------------------------

export interface AdminCode {
  code: string;
  channel_slug: string;
  entity_type: string;
  entity_id: string;
  created_at: string;
  expires_at?: string | null;
  active: boolean;
}

export async function createCode(channelSlug: string, entityId: string): Promise<AdminCode> {
  const res = await apiFetch("/api/admin/codes", {
    method: "POST",
    body: JSON.stringify({ channel_slug: channelSlug, entity_type: "channel", entity_id: entityId }),
  });
  if (!res.ok) throw new Error("Failed to create code");
  return res.json();
}

export async function listCodes(): Promise<AdminCode[]> {
  const res = await apiFetch("/api/admin/codes");
  if (!res.ok) throw new Error("Failed to list codes");
  return res.json();
}

export async function deactivateCode(code: string): Promise<void> {
  await apiFetch(`/api/admin/codes/${code}`, { method: "DELETE" });
}

// ------------------------------------------------------------------
// Takedowns
// ------------------------------------------------------------------

export async function listTakedowns(): Promise<AdminTakedown[]> {
  const res = await apiFetch("/api/takedowns");
  if (!res.ok) throw new Error("Failed to list takedowns");
  return res.json();
}

export async function getTakedown(id: string): Promise<AdminTakedown> {
  const res = await apiFetch(`/api/takedowns/${id}`);
  if (!res.ok) throw new Error("Failed to fetch takedown");
  return res.json();
}

export async function updateTakedownStatus(
  id: string,
  status: AdminTakedown["status"],
  notes?: string,
): Promise<AdminTakedown> {
  const res = await apiFetch(`/api/takedowns/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, notes: notes ?? null }),
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

// ------------------------------------------------------------------
// Analytics
// ------------------------------------------------------------------

export async function getAnalytics(): Promise<AnalyticsSummary> {
  const res = await apiFetch("/api/admin/analytics");
  if (!res.ok) throw new Error("Failed to load analytics");
  return res.json();
}

// ------------------------------------------------------------------
// Host ownership + invites (Slice 11)
// ------------------------------------------------------------------

export interface ChannelOwner {
  id: string;
  display_name: string;
  email?: string | null;
  avatar_url?: string | null;
  roles: UserRole[];
}

export interface ChannelInvite {
  invite_url: string;
  expires_at: string;
  channel_slug: string;
}

export async function listChannelOwners(slug: string): Promise<ChannelOwner[]> {
  const res = await apiFetch(`/api/admin/channels/${slug}/owners`);
  if (!res.ok) throw new Error("Failed to load channel owners");
  return res.json();
}

export async function generateChannelInvite(slug: string): Promise<ChannelInvite> {
  const res = await apiFetch(`/api/admin/channels/${slug}/invites`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to generate invite link");
  return res.json();
}

export async function removeChannelOwner(
  slug: string,
  ownerIds: string[],
): Promise<AdminChannel> {
  return updateChannel(slug, { owner_ids: ownerIds });
}

export async function moveChannelOwner(
  fromSlug: string,
  userId: string,
  toSlug: string,
): Promise<void> {
  const res = await apiFetch(`/api/admin/channels/${fromSlug}/owners/${userId}/move`, {
    method: "POST",
    body: JSON.stringify({ to_slug: toSlug }),
  });
  if (!res.ok) throw new Error("Failed to move owner");
}

export async function acceptHostInvite(
  token: string,
): Promise<{ channel_slug: string; channel_title: string; message: string }> {
  const res = await apiFetch("/api/host/invite/accept", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Failed to accept invite");
  }
  return res.json();
}
