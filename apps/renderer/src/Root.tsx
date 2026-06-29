import React from "react";
import { Composition } from "remotion";
import { TEMPLATES } from "./templates";
import { defaultChannelData } from "./types";

/** One Composition per registered template, so Remotion Studio lists them all. */
export const RemotionRoot: React.FC = () => (
  <>
    {TEMPLATES.map((t) => (
      <Composition
        key={t.id}
        id={t.id}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        component={t.component as any}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ ...defaultChannelData, templateId: t.id }}
      />
    ))}
  </>
);
