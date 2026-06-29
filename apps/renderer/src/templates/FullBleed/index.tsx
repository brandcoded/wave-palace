import React from "react";
import { Audio, Img, OffthreadVideo, staticFile } from "remotion";
import { ChannelData } from "../../types";
import { Waveform } from "../../components/Waveform";

/**
 * Full Bleed Overlay template — 1920×1080.
 * Recreates the production VRChat mux look (apps/backend/app/services/mux_service.py):
 * full-frame backdrop + centered audioMotion-style visualizer + bottom info band.
 */
export const FullBleedTemplate: React.FC<ChannelData> = (props) => {
  const audioSrc = props.audioPath ? staticFile(props.audioPath) : null;
  const useVideo = !!props.loopMediaPath;
  const mediaSrc = staticFile(
    useVideo ? props.loopMediaPath! : (props.fallbackImagePath ?? "channel-image.jpg"),
  );

  const nowPlaying = [props.artistName, props.songTitle].filter(Boolean).join(" — ");
  const genreMood = props.tags.join(" · ");

  return (
    <div
      style={{
        position: "relative",
        width: 1920,
        height: 1080,
        background: "#07050e",
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        overflow: "hidden",
      }}
    >
      {audioSrc && <Audio src={audioSrc} />}

      {/* Full-bleed backdrop */}
      {useVideo ? (
        <OffthreadVideo src={mediaSrc} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : (
        <Img src={mediaSrc} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      )}

      {/* Centered visualizer — full width, vertically centered (matches mux _VIZ_POSITION) */}
      <div
        style={{
          position: "absolute",
          left: 64,
          right: 64,
          top: "50%",
          transform: "translateY(-50%)",
          height: 220,
        }}
      >
        <Waveform audioSrc={audioSrc} width={1792} height={220} />
      </div>

      {/* Bottom info band — dark scrim across the bottom ~28% */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 302,
          background:
            "linear-gradient(0deg, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.5) 60%, transparent 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          padding: "0 64px 56px",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        {/* Row 1: channel name */}
        <div
          style={{
            fontSize: 60,
            fontWeight: 800,
            color: "#ece9ff",
            lineHeight: 1.0,
            letterSpacing: "-0.01em",
          }}
        >
          {props.channelName}
        </div>

        {/* Row 2: hosted by */}
        <div style={{ fontSize: 30, fontWeight: 500, color: "rgba(236,233,255,0.8)" }}>
          Hosted by {props.hostName}
        </div>

        {/* Row 3: now-playing (left) + genre·mood (right) */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            gap: 24,
            marginTop: 4,
          }}
        >
          <span style={{ fontSize: 28, fontWeight: 600, color: "#ece9ff" }}>{nowPlaying}</span>
          {genreMood && (
            <span
              style={{
                fontSize: 24,
                fontWeight: 500,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "rgba(236,233,255,0.7)",
              }}
            >
              {genreMood}
            </span>
          )}
        </div>

        {/* Row 4: follow code — right-aligned */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
          <span style={{ fontSize: 26, fontWeight: 700, color: "rgba(236,233,255,0.85)" }}>
            <span style={{ color: "#38e8ff" }}>{props.followCode}</span>
            {`  ·  ${props.siteUrl}  follow code`}
          </span>
        </div>
      </div>
    </div>
  );
};
