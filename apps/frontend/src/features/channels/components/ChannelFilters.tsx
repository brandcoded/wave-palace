"use client";

import { cn } from "@/shared/lib/cn";

export interface FilterGroup {
  key: "genre" | "mood" | "energy" | "theme";
  label: string;
  options: string[];
}

interface ChannelFiltersProps {
  groups: FilterGroup[];
  active: Record<string, string | undefined>;
  onChange: (key: string, value: string | undefined) => void;
}

export function ChannelFilters({ groups, active, onChange }: ChannelFiltersProps) {
  return (
    <div className="flex flex-col gap-4">
      {groups.map((group) => (
        <div key={group.key} className="flex flex-wrap items-center gap-2">
          <span className="mr-1 text-xs font-semibold uppercase tracking-widest text-white/40">
            {group.label}
          </span>
          {group.options.map((option) => {
            const isActive = active[group.key] === option;
            return (
              <button
                key={option}
                type="button"
                aria-pressed={isActive}
                onClick={() =>
                  onChange(group.key, isActive ? undefined : option)
                }
                className={cn(
                  "rounded-full border px-3.5 py-1.5 text-sm font-medium transition focus-visible:outline-none",
                  isActive
                    ? "border-wave-400 bg-wave-500/20 text-white"
                    : "border-white/10 bg-white/5 text-white/60 hover:border-white/25 hover:text-white"
                )}
              >
                {option}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
