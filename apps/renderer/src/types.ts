/** Built-in template ids. The `string` fallback keeps the type open so future
 * templates can be added to the registry without a type change. */
export type TemplateId = "split-screen" | (string & {});

export interface ChannelData {
  channelName: string;
  hostName: string;
  songTitle: string;
  artistName: string;
  followCode: string;
  siteUrl: string;
  socialHandle: string;
  tags: string[];
  /** which template to render; defaults to "split-screen" */
  templateId?: TemplateId;
  /** filename (no path) inside public/ — e.g. "channel-loop.mp4". Omit to use image fallback. */
  loopMediaPath?: string;
  /** filename (no path) inside public/ — e.g. "channel-image.jpg" */
  fallbackImagePath?: string;
  /** filename (no path) inside public/ — e.g. "audio.mp3" */
  audioPath?: string;
  /** output path relative to renderer root — e.g. "dist/channel-template.mp4" */
  outputPath?: string;
}

export const defaultChannelData: ChannelData = {
  channelName: "Late Night Lofi",
  hostName: "Ty Skyy The DJ",
  songTitle: "Midnight Keys",
  artistName: "Henny Tha Bizness",
  followCode: "WVP6F2",
  siteUrl: "wavepalace.live",
  socialHandle: "@wavepalace",
  tags: ["LOFI", "CHILL", "SOULFUL", "AFTERHOURS", "GOOD PEOPLE"],
  templateId: "split-screen",
  fallbackImagePath: "channel-image.jpg",
  audioPath: "audio.mp3",
  outputPath: "dist/channel-template.mp4",
};
