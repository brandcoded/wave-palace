import React from "react";
import { ChannelData } from "../types";
import { SplitScreenTemplate } from "./SplitScreen";
import { FullBleedTemplate } from "./FullBleed";

export interface TemplateDefinition {
  id: string;
  /** shown in the admin UI selector */
  label: string;
  component: React.FC<ChannelData>;
}

/**
 * Template registry. To add a template:
 *   1. add a component under src/templates/<Name>/
 *   2. add one entry here
 *   3. add a matching entry to the frontend TEMPLATE_OPTIONS list
 * Nothing else needs to change (Root.tsx + render.mjs read this registry).
 */
export const TEMPLATES: TemplateDefinition[] = [
  {
    id: "split-screen",
    label: "Split Screen",
    component: SplitScreenTemplate,
  },
  {
    id: "full-bleed",
    label: "Full Bleed Overlay",
    component: FullBleedTemplate,
  },
  // add future templates here
];

export function getTemplate(id: string | undefined): TemplateDefinition {
  return TEMPLATES.find((t) => t.id === id) ?? TEMPLATES[0];
}
