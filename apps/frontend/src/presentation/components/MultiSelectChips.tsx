"use client";

import { cn } from "@/shared/lib/cn";

interface MultiSelectChipsProps {
  options: string[];
  selected: string[];
  onChange: (values: string[]) => void;
  label: string;
  required?: boolean;
  loading?: boolean;
}

export function MultiSelectChips({
  options,
  selected,
  onChange,
  label,
  required = false,
  loading = false,
}: MultiSelectChipsProps) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-xs font-semibold uppercase tracking-widest text-white/40">
        {label}
        {required && <span className="text-wave-300"> *</span>}
      </legend>
      <div className="flex flex-wrap gap-2">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => (
              <span
                key={index}
                className="h-8 w-24 animate-pulse rounded-full border border-white/10 bg-white/5"
              />
            ))
          : options.map((option) => {
              const isSelected = selected.includes(option);
              return (
                <button
                  key={option}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() =>
                    onChange(
                      isSelected
                        ? selected.filter((value) => value !== option)
                        : [...selected, option]
                    )
                  }
                  className={cn(
                    "rounded-full border px-3.5 py-1.5 text-sm font-medium transition focus-visible:outline-none",
                    isSelected
                      ? "border-wave-400 bg-wave-500/20 text-white"
                      : "border-white/10 bg-white/5 text-white/60 hover:border-white/25 hover:text-white"
                  )}
                >
                  {option}
                </button>
              );
            })}
      </div>
    </fieldset>
  );
}
