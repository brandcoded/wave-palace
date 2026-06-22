import type { Channel } from "@/features/channels/types/channel";

export type UserRole = "admin" | "music_director";

export interface CurrentUser {
  id: string;
  display_name: string;
  email: string | null;
  avatar_url: string | null;
  roles: UserRole[];
  seedMode: boolean;
}

export interface AdminUser {
  id: string;
  display_name: string;
  email: string | null;
  avatar_url: string | null;
  roles: UserRole[];
  is_active: boolean;
  discord_user_id: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface ChannelStat {
  slug: string;
  title: string;
  host_name: string;
  play_count: number;
  follow_count: number;
  follow_breakdown: { discord: number; email: number; browser_push: number };
  active_code_count: number;
  is_published: boolean;
  streaming_active: boolean;
  mux_last_at: string | null;
}

export interface AnalyticsSummary {
  total_plays: number;
  total_follows: number;
  total_channels: number;
  published_channels: number;
  channels_with_sponsor: number;
  follow_breakdown: { discord: number; email: number; browser_push: number };
  top_channels: ChannelStat[];
  generated_at: string;
}

export interface AdminSubmission {
  id: string;
  submitter_name: string;
  contact_email: string;
  channel_title: string;
  profile_image_url: string | null;
  genre: string[];
  mood: string[];
  energy: string[];
  theme: string[];
  description: string;
  sample_links: string[];
  rights_attestation: boolean;
  notes: string | null;
  status: "pending" | "approved" | "rejected";
  submitted_at: string;
  reviewed_at: string | null;
  reviewer_notes: string | null;
}

export interface AdminChannel extends Channel {
  playCount: number;
}

export interface SubmissionOptions {
  genre: string[];
  mood: string[];
  energy: string[];
  theme: string[];
}

export interface URLCheckResult {
  url: string;
  ok: boolean;
  warnings: string[];
  checked_at: string;
}

export interface AdminTakedown {
  id: string;
  claimant_name: string;
  organization: string | null;
  email: string;
  role: "artist" | "label" | "attorney" | "other";
  infringing_url: string;
  description: string;
  proof: string | null;
  good_faith: boolean;
  accuracy: boolean;
  status: "pending" | "reviewed" | "actioned" | "dismissed";
  submitted_at: string;
  notes: string | null;
}

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
