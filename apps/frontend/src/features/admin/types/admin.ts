import type { Channel } from "@/features/channels/types/channel";

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
