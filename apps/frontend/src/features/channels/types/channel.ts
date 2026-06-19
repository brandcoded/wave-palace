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
}

export interface ChannelFilters {
  genre?: string;
  mood?: string;
  energy?: string;
  theme?: string;
}
