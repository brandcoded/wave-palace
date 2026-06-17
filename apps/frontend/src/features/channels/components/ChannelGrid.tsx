"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, SearchX } from "lucide-react";
import { getChannels } from "@/features/channels/lib/channelApi";
import type { Channel } from "@/features/channels/types/channel";
import { ChannelCard } from "./ChannelCard";
import { ChannelFilters, type FilterGroup } from "./ChannelFilters";

const FILTER_GROUPS: FilterGroup[] = [
  { key: "genre", label: "Genre", options: ["House", "Afro House", "Electronic"] },
  { key: "mood", label: "Mood", options: ["Late Night", "Warm", "Dark"] },
  { key: "energy", label: "Energy", options: ["Low", "Medium", "High"] },
  { key: "theme", label: "Theme", options: ["Lounge", "Futuristic Lounge", "VR Party"] },
];

type Status = "loading" | "ready" | "error";

export function ChannelGrid() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [active, setActive] = useState<Record<string, string | undefined>>({});

  const filters = useMemo(
    () => ({
      genre: active.genre,
      mood: active.mood,
      energy: active.energy,
      theme: active.theme,
    }),
    [active]
  );

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    getChannels(filters, controller.signal)
      .then((data) => {
        setChannels(data);
        setStatus("ready");
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        setStatus("error");
      });
    return () => controller.abort();
  }, [filters]);

  function handleChange(key: string, value: string | undefined) {
    setActive((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="flex flex-col gap-8">
      <ChannelFilters groups={FILTER_GROUPS} active={active} onChange={handleChange} />

      {status === "loading" && (
        <div className="flex items-center justify-center gap-2 py-20 text-white/50">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading channels…
        </div>
      )}

      {status === "error" && (
        <div className="rounded-2xl border border-amber-400/30 bg-amber-400/5 p-8 text-center text-amber-100">
          <p className="font-medium">We couldn&apos;t reach the WavePalace API.</p>
          <p className="mt-1 text-sm text-amber-100/70">
            Make sure the backend is running at the configured API base URL, then
            refresh.
          </p>
        </div>
      )}

      {status === "ready" && channels.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-20 text-center text-white/50">
          <SearchX className="h-8 w-8" />
          <p>No channels match these filters yet.</p>
        </div>
      )}

      {status === "ready" && channels.length > 0 && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {channels.map((channel) => (
            <ChannelCard key={channel.id} channel={channel} />
          ))}
        </div>
      )}
    </div>
  );
}
