import type {
  ImageUploadResponse,
  SubmissionOptionsResponse,
  SubmissionRequest,
  SubmissionResponse,
} from "@/features/submissions/types/submission";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function readError(res: Response, fallback: string): Promise<never> {
  try {
    const body = await res.json();
    throw new ApiError(body.detail || fallback, res.status);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(fallback, res.status);
  }
}

export async function getSubmissionOptions(): Promise<SubmissionOptionsResponse> {
  const res = await fetch(`${API_BASE_URL}/api/submission-options`, {
    cache: "no-store",
  });
  if (!res.ok) {
    return readError(res, "Failed to load submission options");
  }
  return (await res.json()) as SubmissionOptionsResponse;
}

export async function uploadProfileImage(file: File): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/submissions/upload-image`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    return readError(res, "Failed to upload image");
  }
  return (await res.json()) as ImageUploadResponse;
}

export async function submitProposal(
  data: SubmissionRequest
): Promise<SubmissionResponse> {
  const res = await fetch(`${API_BASE_URL}/api/submissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    return readError(res, "Failed to submit proposal");
  }
  return (await res.json()) as SubmissionResponse;
}
