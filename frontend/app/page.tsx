"use client";

import { useRef, useState } from "react";

const API_BASE_URL = "http://localhost:8000";

type Mode = "free" | "smart" | "text";
type Targets = "all" | "faces" | "text";

const MODE_OPTIONS: { value: Mode; label: string }[] = [
  { value: "free", label: "Free" },
  { value: "smart", label: "Smart" },
  { value: "text", label: "Text only" },
];

const TARGETS_OPTIONS: { value: Targets; label: string }[] = [
  { value: "all", label: "Everything" },
  { value: "faces", label: "Faces only" },
  { value: "text", label: "Text only" },
];

function SegmentedControl<T extends string>({
  name,
  options,
  value,
  onChange,
}: {
  name: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div role="radiogroup" aria-label={name} className="inline-flex flex-wrap gap-1 rounded-lg border border-border bg-surface-2 p-1">
      {options.map((option) => {
        const active = value === option.value;
        return (
          <label
            key={option.value}
            className={`has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
              active ? "bg-accent text-white" : "text-muted hover:text-ink"
            }`}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={active}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            {option.label}
          </label>
        );
      })}
    </div>
  );
}

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3" />
      <path d="M12 4v11" />
      <path d="M7 8l5-5 5 5" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3" />
      <path d="M12 15V4" />
      <path d="M7 11l5 5 5-5" />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 9v4" />
      <path d="M10.3 3.9L2.7 17a1.6 1.6 0 001.4 2.4h15.8a1.6 1.6 0 001.4-2.4L13.7 3.9a1.6 1.6 0 00-2.8 0z" />
      <path d="M12 16.2h.01" />
    </svg>
  );
}

function Spinner({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`animate-spin ${className ?? ""}`}>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth={2.5} className="opacity-25" />
      <path d="M21 12a9 9 0 00-9-9" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" />
    </svg>
  );
}

function ErrorAlert({ message }: { message: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-danger-border bg-danger-bg px-4 py-3">
      <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
      <div className="flex flex-col gap-0.5 text-sm">
        <p className="font-medium text-danger">Redaction failed</p>
        <p className="text-ink/80">{message}</p>
      </div>
    </div>
  );
}

function Dropzone({
  file,
  previewUrl,
  onFile,
}: {
  file: File | null;
  previewUrl: string | null;
  onFile: (file: File | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  function pick(files: FileList | null) {
    const picked = files?.[0];
    if (picked && picked.type.startsWith("image/")) onFile(picked);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        pick(e.dataTransfer.files);
      }}
      className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-8 text-center transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
        dragActive ? "border-accent bg-accent/5" : "border-border bg-surface-2 hover:border-muted"
      }`}
    >
      <input ref={inputRef} type="file" accept="image/*" onChange={(e) => pick(e.target.files)} className="sr-only" />
      {previewUrl ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={previewUrl} alt="Selected image preview" className="max-h-40 rounded-lg border border-border object-contain" />
          <p className="text-sm text-ink">{file?.name}</p>
          <p className="text-xs text-muted">Click or drop to replace</p>
        </>
      ) : (
        <>
          <UploadIcon className="h-6 w-6 text-muted" />
          <p className="text-sm text-ink">Drag & drop a screenshot, or click to browse</p>
          <p className="text-xs text-muted">PNG, JPG, WEBP</p>
        </>
      )}
    </div>
  );
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("free");
  const [targets, setTargets] = useState<Targets>("all");
  const [blur, setBlur] = useState(15);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFileSelect(selected: File | null) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (resultUrl) URL.revokeObjectURL(resultUrl);
    setFile(selected);
    setPreviewUrl(selected ? URL.createObjectURL(selected) : null);
    setResultUrl(null);
    setError(null);
  }

  async function handleRedact() {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("mode", mode);
      formData.append("targets", targets);
      formData.append("blur", String(blur));

      const response = await fetch(`${API_BASE_URL}/redact`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const blob = await response.blob();
      if (resultUrl) URL.revokeObjectURL(resultUrl);
      setResultUrl(URL.createObjectURL(blob));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-12 sm:px-6">
      <header className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <ShieldIcon className="h-6 w-6 text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Redactly</h1>
        </div>
        <p className="text-sm text-muted">
          Local-first screenshot redaction. Nothing leaves your machine, except the image itself in Smart mode.
        </p>
      </header>

      <section className="flex flex-col gap-6 rounded-xl border border-border bg-surface p-6 ring-1 ring-white/5 shadow-2xl shadow-black/50">
        <Dropzone file={file} previewUrl={previewUrl} onFile={handleFileSelect} />

        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-ink">Mode</span>
          <SegmentedControl name="mode" options={MODE_OPTIONS} value={mode} onChange={setMode} />
          {mode === "smart" && (
            <p className="text-xs text-muted">
              Uses Gemini vision to also catch passwords, names, and hard-to-read IDs. May be rate-limited.
            </p>
          )}
          {mode === "free" && (
            <p className="text-xs text-muted">Catches emails, cards, IPs, and faces for free. May miss passwords and names.</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-ink">Targets</span>
          <SegmentedControl name="targets" options={TARGETS_OPTIONS} value={targets} onChange={setTargets} />
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-ink">Blur strength</span>
            <span className="rounded-md bg-surface-2 px-2 py-0.5 font-mono text-xs text-accent">{blur}</span>
          </div>
          <input
            type="range"
            min={5}
            max={60}
            value={blur}
            onChange={(e) => setBlur(Number(e.target.value))}
            className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-surface-2 accent-accent"
          />
        </div>

        <button
          onClick={handleRedact}
          disabled={!file || loading}
          className="mt-1 inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-accent-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? (
            <>
              <Spinner className="h-4 w-4" />
              Redacting...
            </>
          ) : (
            "Redact"
          )}
        </button>

        {error && <ErrorAlert message={error} />}
      </section>

      {resultUrl && (
        <section className="flex flex-col gap-4">
          <h2 className="text-sm font-medium text-ink">Result</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium text-muted">Original</span>
              <div className="overflow-hidden rounded-xl border border-border bg-surface">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={previewUrl ?? undefined} alt="Original, before redaction" className="w-full object-contain" />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium text-accent">Redacted</span>
              <div className="overflow-hidden rounded-xl border border-accent/40 bg-surface">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={resultUrl} alt="Redacted result" className="w-full object-contain" />
              </div>
              <a
                href={resultUrl}
                download={`redacted_${file?.name ?? "image.png"}`}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm font-medium text-ink transition-colors duration-150 hover:border-accent hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                <DownloadIcon className="h-4 w-4" />
                Download
              </a>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
