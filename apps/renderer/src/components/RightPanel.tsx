import React from "react";
import { ChannelData } from "../types";
import { Waveform } from "./Waveform";
import { FeatureRow } from "./FeatureRow";
import { FollowCard } from "./FollowCard";
import { BottomBar } from "./BottomBar";

const W = 1114;
const PAD_H = 52;
const INNER_W = W - PAD_H * 2;

interface RightPanelProps extends ChannelData {
  audioSrc: string | null;
}

const DiscIcon: React.FC = () => (
  <svg
    width={36}
    height={36}
    viewBox="0 0 24 24"
    fill="none"
    stroke="#a78bfa"
    strokeWidth={1.5}
    strokeLinecap="round"
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M6 12c0-1.7.7-3.2 1.8-4.2" />
    <circle cx="12" cy="12" r="2" />
    <path d="M18 12c0 1.7-.7 3.2-1.8 4.2" />
  </svg>
);

export const RightPanel: React.FC<RightPanelProps> = (props) => (
  <div
    style={{
      width: W,
      height: 1080,
      background: "#07050e",
      display: "flex",
      flexDirection: "column",
      padding: `44px ${PAD_H}px 0`,
      boxSizing: "border-box",
    }}
  >
    {/* WavePalace logo — top right */}
    <div
      style={{
        display: "flex",
        justifyContent: "flex-end",
        alignItems: "center",
        gap: 10,
        marginBottom: 28,
      }}
    >
      <DiscIcon />
      <span
        style={{
          fontSize: 34,
          fontWeight: 700,
          color: "#ece9ff",
          letterSpacing: "-0.02em",
        }}
      >
        Wave
        <span
          style={{
            background:
              "linear-gradient(120deg, #38e8ff 0%, #a78bfa 45%, #ff5cc8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          Palace
        </span>
      </span>
    </div>

    {/* NOW PLAYING badge */}
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        border: "1.5px solid rgba(167,139,250,0.35)",
        padding: "8px 18px",
        borderRadius: 4,
        marginBottom: 16,
        width: "fit-content",
      }}
    >
      <span
        style={{
          fontSize: 18,
          fontWeight: 600,
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "#a78bfa",
        }}
      >
        Now Playing
      </span>
    </div>

    {/* Track title */}
    <div
      style={{
        fontSize: 84,
        fontWeight: 800,
        color: "#ece9ff",
        letterSpacing: "-0.025em",
        lineHeight: 1.0,
        marginBottom: 14,
      }}
    >
      {props.songTitle}
    </div>

    {/* Artist name */}
    <div
      style={{
        fontSize: 36,
        fontWeight: 500,
        color: "#a78bfa",
        letterSpacing: "0.01em",
        marginBottom: 26,
      }}
    >
      {props.artistName}
    </div>

    {/* Full-width waveform */}
    <div style={{ height: 120, marginBottom: 24 }}>
      <Waveform audioSrc={props.audioSrc} width={INNER_W} height={120} />
    </div>

    {/* Feature row */}
    <FeatureRow width={INNER_W} />

    {/* Follow card */}
    <div style={{ marginTop: 20 }}>
      <FollowCard followCode={props.followCode} siteUrl={props.siteUrl} />
    </div>

    {/* Push bottom bar to bottom */}
    <div style={{ flex: 1 }} />

    {/* Bottom bar */}
    <BottomBar socialHandle={props.socialHandle} tags={props.tags} />
  </div>
);
