"use client";

import { useState } from "react";

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

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<Mode>("free");
  const [targets, setTargets] = useState<Targets>("all");
  const [blur, setBlur] = useState(15);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRedact() {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResultUrl(null);

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
      setResultUrl(URL.createObjectURL(blob));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-col items-center gap-6 p-8">
      <h1 className="text-xl font-semibold">Redactly</h1>

      <input
        type="file"
        accept="image/*"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />

      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">Mode</span>
        <div className="flex gap-4">
          {MODE_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-center gap-1 text-sm">
              <input
                type="radio"
                name="mode"
                value={option.value}
                checked={mode === option.value}
                onChange={() => setMode(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
        {mode === "smart" && (
          <p className="text-xs text-gray-500">
            Uses Gemini vision to also catch passwords, names, and hard-to-read IDs. May be rate-limited.
          </p>
        )}
        {mode === "free" && (
          <p className="text-xs text-gray-500">
            Catches emails, cards, IPs, and faces for free. May miss passwords and names.
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">Targets</span>
        <div className="flex gap-4">
          {TARGETS_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-center gap-1 text-sm">
              <input
                type="radio"
                name="targets"
                value={option.value}
                checked={targets === option.value}
                onChange={() => setTargets(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2 w-full max-w-xs">
        <span className="text-sm font-medium">Blur strength: {blur}</span>
        <input
          type="range"
          min={5}
          max={60}
          value={blur}
          onChange={(e) => setBlur(Number(e.target.value))}
        />
      </div>

      <button
        onClick={handleRedact}
        disabled={!file || loading}
        className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
      >
        Redact
      </button>

      {loading && <p>Processing...</p>}
      {error && <p className="text-red-600">Error: {error}</p>}

      {resultUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={resultUrl} alt="Redacted result" className="max-w-full" />
      )}
    </main>
  );
}
