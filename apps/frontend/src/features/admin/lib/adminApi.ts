import type { AdminChannel, AdminSubmission, Sponsor, SubmissionOptions, URLCheckResult } from "@/features/admin/types/admin";

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
  await apiFetch("/api/admin/logout", { method: "POST" });
}

export async function checkSession(): Promise<{ ok: boolean }> {
  const res = await apiFetch("/api/admin/me");
  if (!res.ok) throw new Error("Not authenticated");
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
  if (!res.ok) throw new Error("Mux failed");
  return res.json();
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
