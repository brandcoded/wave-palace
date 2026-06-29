import React from "react";

interface BottomBarProps {
  socialHandle: string;
  tags: string[];
}

const PLATFORMS = ["IG", "TT", "FB", "YT"];

export const BottomBar: React.FC<BottomBarProps> = ({ socialHandle, tags }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      borderTop: "1px solid rgba(255,255,255,0.06)",
      padding: "18px 0 22px",
    }}
  >
    {/* Social icons + handle */}
    <div
      style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}
    >
      {PLATFORMS.map((p) => (
        <div
          key={p}
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            border: "1.5px solid rgba(255,255,255,0.22)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            style={{ fontSize: 11, color: "#ece9ff", fontWeight: 700, letterSpacing: "0.02em" }}
          >
            {p}
          </span>
        </div>
      ))}
      <span
        style={{
          fontSize: 18,
          fontWeight: 600,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "rgba(236,233,255,0.5)",
          marginLeft: 6,
        }}
      >
        {socialHandle}
      </span>
    </div>

    {/* Mood tags — centered */}
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
      }}
    >
      {tags.map((tag, i) => (
        <React.Fragment key={tag}>
          <span
            style={{
              fontSize: 16,
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "rgba(236,233,255,0.35)",
            }}
          >
            {tag}
          </span>
          {i < tags.length - 1 && (
            <span style={{ color: "rgba(167,139,250,0.4)", fontSize: 10 }}>
              •
            </span>
          )}
        </React.Fragment>
      ))}
    </div>

    {/* Hashtag pill */}
    <div
      style={{
        border: "1.5px solid rgba(167,139,250,0.35)",
        padding: "8px 22px",
        borderRadius: 40,
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontSize: 18,
          fontWeight: 700,
          letterSpacing: "0.08em",
          color: "#a78bfa",
        }}
      >
        #WAVEPALACE
      </span>
    </div>
  </div>
);
