export interface SubmissionOptionsResponse {
  genre: string[];
  mood: string[];
  energy: string[];
  theme: string[];
}

export interface ImageUploadResponse {
  url: string;
}

export interface SubmissionRequest {
  submitter_name: string;
  contact_email: string;
  channel_title: string;
  profile_image_url?: string | null;
  genre: string[];
  mood: string[];
  energy: string[];
  theme: string[];
  description: string;
  sample_links: string[];
  rights_attestation: boolean;
  notes?: string | null;
}

export interface SubmissionResponse {
  id: string;
  status: "pending";
  submitted_at: string;
  message: string;
}
