import React from "react";
import { getTemplate } from "./templates";
import { ChannelData } from "./types";

/**
 * Entry point used by the render script. Dispatches to the template selected by
 * `templateId`, falling back to the first registered template for unknown ids.
 */
export const ChannelTemplate: React.FC<ChannelData> = (props) => {
  const { component: Template } = getTemplate(props.templateId ?? "split-screen");
  return <Template {...props} />;
};
