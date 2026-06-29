import React from "react";

const FEATURES = [
  { icon: "♪", title: "24/7", sub: "Always On" },
  { icon: "⊙", title: "Curated", sub: "By Real DJs" },
  { icon: "◉", title: "Listen", sub: "Anywhere" },
  { icon: "♡", title: "Support", sub: "The Culture" },
];

export const FeatureRow: React.FC<{ width: number }> = ({ width }) => (
  <div
    style={{
      display: "flex",
      width,
      borderTop: "1px solid rgba(255,255,255,0.08)",
      borderBottom: "1px solid rgba(255,255,255,0.08)",
      padding: "22px 0",
    }}
  >
    {FEATURES.map((f, i) => (
      <div
        key={f.title}
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
          borderRight:
            i < FEATURES.length - 1
              ? "1px solid rgba(255,255,255,0.08)"
              : "none",
        }}
      >
        <span style={{ fontSize: 26, color: "#a78bfa", lineHeight: 1 }}>
          {f.icon}
        </span>
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 20,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#ece9ff",
            }}
          >
            {f.title}
          </div>
          <div
            style={{
              fontSize: 14,
              letterSpacing: "0.07em",
              textTransform: "uppercase",
              color: "rgba(236,233,255,0.4)",
              marginTop: 2,
            }}
          >
            {f.sub}
          </div>
        </div>
      </div>
    ))}
  </div>
);
