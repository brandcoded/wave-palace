import React from "react";
import { Img, OffthreadVideo, staticFile } from "remotion";
import { ChannelData } from "../types";

export const LeftPanel: React.FC<ChannelData> = (props) => {
  const useVideo = !!props.loopMediaPath;
  const mediaSrc = staticFile(
    useVideo
      ? props.loopMediaPath!
      : (props.fallbackImagePath ?? "channel-image.jpg")
  );

  return (
    <div
      style={{
        position: "relative",
        width: 806,
        height: 1080,
        flexShrink: 0,
        overflow: "hidden",
      }}
    >
      {/* Media layer */}
      {useVideo ? (
        <OffthreadVideo
          src={mediaSrc}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        <Img
          src={mediaSrc}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      )}

      {/* Dark gradient scrim */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(0deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 55%, transparent 100%)",
        }}
      />

      {/* Channel info */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          padding: "52px 48px 44px",
        }}
      >
        {/* CHANNEL label */}
        <div
          style={{
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            color: "#38e8ff",
            marginBottom: 12,
          }}
        >
          Channel
        </div>

        {/* Channel name */}
        <div
          style={{
            fontSize: 62,
            fontWeight: 800,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            color: "#ece9ff",
            lineHeight: 1.0,
            marginBottom: 20,
          }}
        >
          {props.channelName}
        </div>

        {/* HOSTED BY label */}
        <div
          style={{
            fontSize: 20,
            fontWeight: 600,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color: "#ff5cc8",
            marginBottom: 10,
          }}
        >
          Hosted by
        </div>

        {/* Host name — gradient text */}
        <div
          style={{
            fontSize: 68,
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            background:
              "linear-gradient(90deg, #38e8ff 0%, #a78bfa 50%, #ff5cc8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            lineHeight: 1.0,
            marginBottom: 30,
          }}
        >
          {props.hostName}
        </div>

        {/* Tagline pill */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            border: "1.5px solid rgba(236,233,255,0.25)",
            borderRadius: 40,
            padding: "10px 22px",
          }}
        >
          <span style={{ fontSize: 18, color: "#a78bfa" }}>♛</span>
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "rgba(236,233,255,0.7)",
            }}
          >
            Curated Vibes. Real Music. Always On.
          </span>
        </div>
      </div>
    </div>
  );
};
