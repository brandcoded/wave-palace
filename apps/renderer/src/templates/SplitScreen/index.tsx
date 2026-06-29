import React from "react";
import { Audio, staticFile } from "remotion";
import { ChannelData } from "../../types";
import { LeftPanel } from "../../components/LeftPanel";
import { RightPanel } from "../../components/RightPanel";

/**
 * Split Screen template — 1920×1080.
 * Left 1080×1080 square art panel + right 840px info panel.
 * Shared building blocks live in src/components/ so future templates can reuse them.
 */
export const SplitScreenTemplate: React.FC<ChannelData> = (props) => {
  const hasAudio = !!props.audioPath;
  const audioSrc = hasAudio ? staticFile(props.audioPath!) : null;

  return (
    <div
      style={{
        width: 1920,
        height: 1080,
        display: "flex",
        background: "#07050e",
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {audioSrc && <Audio src={audioSrc} />}
      <LeftPanel {...props} />
      <RightPanel {...props} audioSrc={audioSrc} />
    </div>
  );
};
