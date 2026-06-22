export function Footer() {
  return (
    <footer
      className="border-t py-10"
      style={{ borderColor: "var(--wp-border)" }}
    >
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-6 sm:flex-row sm:justify-between">
        <p className="text-sm font-medium text-wp-white">
          Wave<span className="text-wp-violet">Palace</span>
        </p>
        <p className="text-center text-sm text-wp-muted">
          Creator-owned channels for VRChat and the web.
        </p>
        <a
          href="https://wavepalace.live"
          className="text-sm text-wp-violet transition hover:text-wp-white"
        >
          wavepalace.live
        </a>
      </div>
    </footer>
  );
}
