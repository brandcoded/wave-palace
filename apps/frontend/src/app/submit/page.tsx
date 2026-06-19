"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Loader2, Plus, Trash2, UploadCloud } from "lucide-react";
import { MultiSelectChips } from "@/presentation/components/MultiSelectChips";
import { GlassPanel } from "@/presentation/components/GlassPanel";
import {
  getSubmissionOptions,
  submitProposal,
  uploadProfileImage,
} from "@/features/submissions/lib/submissionApi";
import type {
  SubmissionOptionsResponse,
  SubmissionResponse,
} from "@/features/submissions/types/submission";

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

const emptyOptions: SubmissionOptionsResponse = {
  genre: [],
  mood: [],
  energy: [],
  theme: [],
};

export default function SubmitPage() {
  const [options, setOptions] = useState<SubmissionOptionsResponse>(emptyOptions);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [optionsError, setOptionsError] = useState(false);
  const [submitterName, setSubmitterName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [channelTitle, setChannelTitle] = useState("");
  const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
  const [profilePreviewUrl, setProfilePreviewUrl] = useState<string | null>(null);
  const [imageUploading, setImageUploading] = useState(false);
  const [imageError, setImageError] = useState("");
  const [genre, setGenre] = useState<string[]>([]);
  const [mood, setMood] = useState<string[]>([]);
  const [energy, setEnergy] = useState<string[]>([]);
  const [theme, setTheme] = useState<string[]>([]);
  const [description, setDescription] = useState("");
  const [sampleLinks, setSampleLinks] = useState([""]);
  const [notes, setNotes] = useState("");
  const [rightsAttestation, setRightsAttestation] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [success, setSuccess] = useState<SubmissionResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    getSubmissionOptions()
      .then((loadedOptions) => {
        if (!mounted) return;
        setOptions(loadedOptions);
        setOptionsError(false);
      })
      .catch(() => {
        if (!mounted) return;
        setOptionsError(true);
      })
      .finally(() => {
        if (mounted) setOptionsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (profilePreviewUrl) URL.revokeObjectURL(profilePreviewUrl);
    };
  }, [profilePreviewUrl]);

  async function handleImageChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setImageError("");
    setProfileImageUrl(null);

    if (!ACCEPTED_IMAGE_TYPES.includes(file.type) || file.size > MAX_IMAGE_BYTES) {
      setImageError("Image upload failed — please try again.");
      event.target.value = "";
      return;
    }

    const nextPreviewUrl = URL.createObjectURL(file);
    if (profilePreviewUrl) URL.revokeObjectURL(profilePreviewUrl);
    setProfilePreviewUrl(nextPreviewUrl);
    setImageUploading(true);

    try {
      const response = await uploadProfileImage(file);
      setProfileImageUrl(response.url);
    } catch {
      setProfileImageUrl(null);
      setImageError("Image upload failed — please try again.");
    } finally {
      setImageUploading(false);
    }
  }

  function updateSampleLink(index: number, value: string) {
    setSampleLinks((current) =>
      current.map((link, currentIndex) => (currentIndex === index ? value : link))
    );
  }

  function removeSampleLink(index: number) {
    setSampleLinks((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  const trimmedLinks = useMemo(
    () => sampleLinks.map((link) => link.trim()).filter(Boolean),
    [sampleLinks]
  );

  const formValid =
    !optionsLoading &&
    !optionsError &&
    submitterName.trim().length > 0 &&
    contactEmail.trim().length > 0 &&
    channelTitle.trim().length > 0 &&
    genre.length > 0 &&
    mood.length > 0 &&
    energy.length > 0 &&
    theme.length > 0 &&
    description.trim().length >= 20 &&
    description.trim().length <= 500 &&
    trimmedLinks.length >= 1 &&
    trimmedLinks.length <= 5 &&
    notes.length <= 1000 &&
    rightsAttestation &&
    !imageUploading;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!formValid || submitting) return;

    setSubmitting(true);
    setSubmitError("");

    try {
      const response = await submitProposal({
        submitter_name: submitterName.trim(),
        contact_email: contactEmail.trim(),
        channel_title: channelTitle.trim(),
        profile_image_url: profileImageUrl,
        genre,
        mood,
        energy,
        theme,
        description: description.trim(),
        sample_links: trimmedLinks,
        rights_attestation: rightsAttestation,
        notes: notes.trim() || null,
      });
      setSuccess(response);
    } catch {
      setSubmitError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (optionsError) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-20">
        <GlassPanel className="p-8">
          <p className="text-sm font-medium text-rose-200">
            Could not load form options — please refresh.
          </p>
        </GlassPanel>
      </div>
    );
  }

  if (success) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-20">
        <GlassPanel className="p-8">
          <div className="flex items-start gap-4">
            <CheckCircle2 className="mt-1 h-6 w-6 flex-none text-wave-300" />
            <div>
              <p className="text-xl font-semibold text-white">Submission received</p>
              <p className="mt-3 text-sm leading-relaxed text-white/65">{success.message}</p>
            </div>
          </div>
        </GlassPanel>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-14 sm:py-20">
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-wave-300">
          Submit a channel
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
          DJ / Artist Submission
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-white/60">
          Send a channel proposal for WavePalace review. Nothing is auto-published.
        </p>
      </div>

      <GlassPanel className="p-5 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-7">
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="DJ / Artist / Host Name" required>
              <input
                value={submitterName}
                onChange={(event) => setSubmitterName(event.target.value)}
                required
                className="field-input"
              />
            </Field>
            <Field label="Contact Email" required>
              <input
                type="email"
                value={contactEmail}
                onChange={(event) => setContactEmail(event.target.value)}
                required
                className="field-input"
              />
            </Field>
          </div>

          <Field label="Profile Image / Logo">
            <div className="flex flex-wrap items-center gap-4">
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/75 transition hover:bg-white/10">
                {imageUploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <UploadCloud className="h-4 w-4" />
                )}
                Upload image
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleImageChange}
                  className="sr-only"
                />
              </label>
              {profilePreviewUrl && (
                <img
                  src={profilePreviewUrl}
                  alt=""
                  className="h-16 w-16 rounded-full border border-white/15 object-cover"
                />
              )}
              {imageUploading && (
                <span className="text-sm text-white/50">Uploading...</span>
              )}
            </div>
            {imageError && <p className="mt-2 text-sm text-rose-200">{imageError}</p>}
          </Field>

          <Field label="Proposed Channel Title" required>
            <input
              value={channelTitle}
              onChange={(event) => setChannelTitle(event.target.value)}
              required
              className="field-input"
            />
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <MultiSelectChips
              label="Genre"
              options={options.genre}
              selected={genre}
              onChange={setGenre}
              required
              loading={optionsLoading}
            />
            <MultiSelectChips
              label="Mood"
              options={options.mood}
              selected={mood}
              onChange={setMood}
              required
              loading={optionsLoading}
            />
            <MultiSelectChips
              label="Energy"
              options={options.energy}
              selected={energy}
              onChange={setEnergy}
              required
              loading={optionsLoading}
            />
            <MultiSelectChips
              label="Theme"
              options={options.theme}
              selected={theme}
              onChange={setTheme}
              required
              loading={optionsLoading}
            />
          </div>

          <Field label="Description" required>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              minLength={20}
              maxLength={500}
              required
              rows={5}
              className="field-input resize-y"
            />
            <p className="mt-2 text-right text-xs text-white/40">
              {description.length}/500
            </p>
          </Field>

          <Field label="Sample Links" required>
            <div className="space-y-3">
              {sampleLinks.map((link, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="url"
                    value={link}
                    onChange={(event) => updateSampleLink(index, event.target.value)}
                    required
                    className="field-input"
                  />
                  {sampleLinks.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeSampleLink(index)}
                      aria-label="Remove sample link"
                      className="inline-flex h-11 w-11 flex-none items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/60 transition hover:bg-white/10 hover:text-white"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
              {sampleLinks.length < 5 && (
                <button
                  type="button"
                  onClick={() => setSampleLinks((current) => [...current, ""])}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/75 transition hover:bg-white/10"
                >
                  <Plus className="h-4 w-4" />
                  Add another link
                </button>
              )}
            </div>
          </Field>

          <Field label="Notes">
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              maxLength={1000}
              rows={4}
              className="field-input resize-y"
            />
            <p className="mt-2 text-right text-xs text-white/40">
              {notes.length}/1000
            </p>
          </Field>

          <label className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm leading-relaxed text-white/70">
            <input
              type="checkbox"
              checked={rightsAttestation}
              onChange={(event) => setRightsAttestation(event.target.checked)}
              required
              className="mt-1 h-4 w-4 accent-wave-500"
            />
            <span>
              I confirm that I own or have cleared the rights to all content I am
              proposing for WavePalace.
            </span>
          </label>

          {submitError && <p className="text-sm text-rose-200">{submitError}</p>}

          <button
            type="submit"
            disabled={!formValid || submitting}
            className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-gradient-to-r from-wave-500 to-glow-magenta px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-wave-600/30 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:brightness-100 sm:w-auto"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Submit for Review
          </button>
        </form>
      </GlassPanel>
    </div>
  );
}

function Field({
  label,
  required = false,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-semibold uppercase tracking-widest text-white/40">
        {label}
        {required && <span className="text-wave-300"> *</span>}
      </span>
      {children}
    </label>
  );
}
