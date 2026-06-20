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
  genre: string;
  mood: string;
  energy: string;
  theme: string;
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
}

export interface ChannelFilters {
  genre?: string;
  mood?: string;
  energy?: string;
  theme?: string;
}
