import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { useAudioData, visualizeAudio } from "@remotion/media-utils";

interface WaveformProps {
  audioSrc: string | null;
  width: number;
  height: number;
}

const BAR_COUNT = 80;

const barColor = (i: number) =>
  i % 9 === 4 ? "#ff5cc8" : i % 6 === 2 ? "#38e8ff" : "#a78bfa";

const staticBars = Array.from({ length: BAR_COUNT }, (_, i) => ({
  h: Math.abs(Math.sin(i * 0.28) * 0.7 + Math.sin(i * 0.11) * 0.3),
  c: barColor(i),
}));

export const Waveform: React.FC<WaveformProps> = ({ audioSrc, width, height }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const audioData = useAudioData(audioSrc ?? "");

  const bars: Array<{ h: number; c: string }> =
    audioData && audioSrc
      ? visualizeAudio({
          fps,
          frame,
          audioData,
          numberOfSamples: BAR_COUNT,
        }).map((v, i) => ({ h: v, c: barColor(i) }))
      : staticBars.map(({ h, c }, i) => ({
          h: h * 0.5 + Math.abs(Math.sin((frame + i * 4) / 18)) * 0.4,
          c,
        }));

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, width, height }}>
      {bars.map(({ h, c }, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            height: "100%",
            background: c,
            borderRadius: 1,
            opacity: 0.35 + h * 0.55,
            transform: `scaleY(${Math.max(0.05, h)})`,
            transformOrigin: "center center",
          }}
        />
      ))}
    </div>
  );
};
