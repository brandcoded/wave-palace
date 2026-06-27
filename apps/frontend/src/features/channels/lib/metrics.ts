/**
 * Threshold-based display helpers for public engagement metrics.
 * All functions return null when the value is below the credibility threshold
 * so components can simply skip rendering rather than showing zeros.
 */

/** Min confirmed followers before we display a count. */
const FOLLOWER_THRESHOLD = 10;

/** Min listen events in the active window before we display "listening now". */
const LISTENER_THRESHOLD = 1;

/** Format a follower count for display. Returns null below threshold. */
export function displayFollowerCount(count: number | undefined): string | null {
  if (count == null || count < FOLLOWER_THRESHOLD) return null;
  if (count < 50) return `${count} followers`;
  if (count < 500) return "Growing";
  if (count < 1_000) return `${count} followers`;
  if (count < 1_000_000) return `${(count / 1_000).toFixed(1)}k followers`;
  return `${(count / 1_000_000).toFixed(1)}M followers`;
}

/** Format a play count for display. Returns null when 0. */
export function displayPlayCount(count: number | undefined): string | null {
  if (!count) return null;
  if (count < 1_000) return `${count} plays`;
  if (count < 1_000_000) return `${(count / 1_000).toFixed(1)}k plays`;
  return `${(count / 1_000_000).toFixed(1)}M plays`;
}

/** Returns the listener count string for "X listening now". Returns null below threshold. */
export function displayListenerCount(count: number | undefined): string | null {
  if (count == null || count < LISTENER_THRESHOLD) return null;
  return count === 1 ? "1 listening now" : `${count} listening now`;
}

/** Returns worlds count display string. Returns null when 0. */
export function displayWorldsCount(count: number | undefined): string | null {
  if (!count) return null;
  return count === 1 ? "in 1 world" : `in ${count} worlds`;
}
