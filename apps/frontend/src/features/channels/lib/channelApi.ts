import type { Channel, ChannelFilters, TrackItem } from "@/features/channels/types/channel";

function normalizePlaylist(raw: unknown[]): TrackItem[] {
  return raw.map((item) =>
    typeof item === "string"
      ? { url: item, title: "", artist: "" }
      : (item as TrackItem)
  );
}

function normalizeChannel(ch: Channel): Channel {
  return { ...ch, playlist: normalizePlaylist((ch.playlist as unknown[]) ?? []) };
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function buildQuery(filters?: ChannelFilters): string {
  if (!filters) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const q = params.toString();
  return q ? `?${q}` : "";
}

export async function getChannels(
  filters?: ChannelFilters,
  signal?: AbortSignal
): Promise<Channel[]> {
  const res = await fetch(`${API_BASE_URL}/api/channels${buildQuery(filters)}`, {
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new ApiError("Failed to load channels", res.status);
  }
  const channels = (await res.json()) as Channel[];
  return channels.map(normalizeChannel);
}

export async function getChannelBySlug(
  slug: string,
  signal?: AbortSignal
): Promise<Channel> {
  const res = await fetch(`${API_BASE_URL}/api/channels/${slug}`, {
    signal,
    cache: "no-store",
  });
  if (res.status === 404) {
    throw new ApiError("Channel not found", 404);
  }
  if (!res.ok) {
    throw new ApiError("Failed to load channel", res.status);
  }
  return normalizeChannel((await res.json()) as Channel);
}
