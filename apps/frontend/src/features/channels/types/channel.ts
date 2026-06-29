export interface Sponsor {
  name: string;
  logoUrl: string | null;
  text: string;
  clickUrl: string | null;
  placement: "lower_third" | "bug" | "backdrop";
  startDate: string | null;
  endDate: string | null;
  isActive: boolean;
  isFeatured: boolean;
  impressionCount: number;
  clickCount: number;
}

export interface ExternalLink {
  label: string;
  url: string;
}

export interface TrackItem {
  url: string;
  title: string;
  artist: string;
}

export interface Channel {
  id: string;
  slug: string;
  title: string;
  description: string;
  genre: string[];
  mood: string[];
  energy: string[];
  theme: string[];
  hostName: string;
  coverImageUrl: string;
  visualLoopUrl?: string | null;
  audioUrl: string;
  playlist: TrackItem[];
  vrchatPlaybackUrl: string;
  externalLinks: ExternalLink[];
  rightsStatus: string;
  isPublished: boolean;
  playCount: number;
  sponsor?: Sponsor | null;
  muxOutdated?: boolean;
  muxLastAt?: string | null;
  streamingActive?: boolean;
  vrchatFallbackUrl?: string | null;
  visualizer_style?: "none" | "waveform" | "bars" | "circular" | "blob" | "terrain";
  visualizer_theme?: "violet" | "teal" | "ember" | "rose" | "ice" | "frequency";
  visualizer_backdrop?: "overlay_video" | "overlay_image" | "replace";
  // Video Renderer Template — which Remotion template renders this channel's video.
  renderer_template?: string;
  // Public engagement metrics (populated by API at read time)
  follower_count?: number;
  listener_count?: number;
  worlds_count?: number;
  trending?: boolean;
}

export interface ChannelFilters {
  genre?: string;
  mood?: string;
  energy?: string;
  theme?: string;
}
