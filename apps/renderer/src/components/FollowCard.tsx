import React from "react";

interface FollowCardProps {
  followCode: string;
  siteUrl: string;
}

export const FollowCard: React.FC<FollowCardProps> = ({ followCode, siteUrl }) => (
  <div
    style={{
      display: "flex",
      border: "1.5px solid rgba(167,139,250,0.25)",
      background: "rgba(255,255,255,0.02)",
      borderRadius: 4,
    }}
  >
    {/* Left: follow code */}
    <div
      style={{
        flex: 1,
        padding: "32px 44px",
        borderRight: "1px solid rgba(167,139,250,0.15)",
      }}
    >
      <div
        style={{
          fontSize: 18,
          fontWeight: 600,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: "rgba(236,233,255,0.5)",
          marginBottom: 10,
        }}
      >
        Follow &amp; Save this channel
      </div>
      <div
        style={{
          fontSize: 16,
          fontWeight: 600,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "#a78bfa",
          marginBottom: 8,
        }}
      >
        Follow Code
      </div>
      <div
        style={{
          fontSize: 88,
          fontWeight: 800,
          letterSpacing: "0.1em",
          background:
            "linear-gradient(90deg, #38e8ff 0%, #a78bfa 50%, #ff5cc8 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
          lineHeight: 1,
        }}
      >
        {followCode}
      </div>
    </div>

    {/* Right: URL + instructions */}
    <div
      style={{
        flex: 1,
        padding: "32px 44px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div>
        <div
          style={{
            fontSize: 18,
            fontWeight: 600,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "#38e8ff",
            marginBottom: 12,
          }}
        >
          Visit
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: 800,
            textTransform: "uppercase",
            color: "#ece9ff",
            lineHeight: 1.1,
            letterSpacing: "0.04em",
          }}
        >
          {siteUrl}
        </div>
      </div>
      <div
        style={{
          fontSize: 16,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "rgba(236,233,255,0.3)",
          lineHeight: 1.6,
        }}
      >
        Enter code at {siteUrl}
        <br />
        to follow, save &amp; stay updated.
      </div>
    </div>
  </div>
);
