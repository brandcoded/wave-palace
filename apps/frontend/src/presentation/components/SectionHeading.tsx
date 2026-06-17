export function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="max-w-2xl">
      {eyebrow && (
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-wave-400">
          {eyebrow}
        </p>
      )}
      <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
        {title}
      </h2>
      {description && (
        <p className="mt-3 text-base leading-relaxed text-white/60">
          {description}
        </p>
      )}
    </div>
  );
}
