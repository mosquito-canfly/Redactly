"use client";

import { useState } from "react";

const API_BASE_URL = "http://localhost:8000";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
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
      formData.append("mode", "free");

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
    <main className="flex flex-col items-center gap-4 p-8">
      <h1 className="text-xl font-semibold">Redactly</h1>

      <input
        type="file"
        accept="image/*"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />

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
