/**
 * Deterministic 6-char follow code — must stay in sync with
 * apps/backend/app/services/code_service.py :: make_mux_code().
 *
 * Formula: 2-char channel prefix + 4-char track prefix.
 */

function _channelPrefix(slug: string): string {
  const initials = slug
    .split("-")
    .filter(Boolean)
    .map((w) => w[0].toUpperCase())
    .join("");
  if (initials.length >= 2) return initials.slice(0, 2);
  const clean = slug.replace(/[^A-Z0-9]/gi, "").toUpperCase();
  return (clean + "XX").slice(0, 2);
}

function _trackPrefix(title: string, idx: number): string {
  const clean = title.replace(/[^A-Z0-9]/gi, "").toUpperCase();
  if (clean.length >= 4) return clean.slice(0, 4);
  return (clean + `T${String(idx).padStart(3, "0")}`).slice(0, 4);
}

export function makeFollowCode(slug: string, title: string, idx: number): string {
  return _channelPrefix(slug) + _trackPrefix(title, idx);
}
