"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Nav from "@/components/Nav";
import { apiUrl, tenantFetch } from "@/lib/api";

const ALLOWED_AUDIO = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/wave", "audio/mp4", "audio/x-m4a"];
const ALLOWED_TEXT_EXT = [".txt", ".md", ".html", ".htm", ".rtf", ".xml", ".csv", ".docx", ".odt"];
const MAX_AUDIO_SIZE = 100 * 1024 * 1024;
const MAX_TEXT_SIZE = 10 * 1024 * 1024;
const YT_REGEX = /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|live\/)|youtu\.be\/)[\w-]+/;

type DetectedType = null | "audio" | "text" | "youtube";

function isTextFile(f: File): boolean {
  const ext = f.name.toLowerCase().slice(f.name.lastIndexOf("."));
  return ALLOWED_TEXT_EXT.includes(ext);
}

function isAudioFile(f: File): boolean {
  return ALLOWED_AUDIO.includes(f.type);
}

function detectFileType(f: File): "audio" | "text" | null {
  if (isAudioFile(f)) return "audio";
  if (isTextFile(f)) return "text";
  return null;
}

function Spinner() {
  return (
    <div className="flex flex-col items-center gap-4 py-8">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full border-[3px] border-gray-200" />
        <div className="absolute inset-0 rounded-full border-[3px] border-transparent border-t-blue-600 animate-spin" />
      </div>
      <p className="text-sm text-gray-500">Analyzing sermon…</p>
      <p className="text-xs text-gray-400">This usually takes about 5 minutes</p>
    </div>
  );
}

export default function UploadPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [detected, setDetected] = useState<DetectedType>(null);
  const [file, setFile] = useState<File | null>(null);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [ytStart, setYtStart] = useState("");
  const [ytEnd, setYtEnd] = useState("");
  const [title, setTitle] = useState("");
  const [pastor, setPastor] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [pastors, setPastors] = useState<string[]>([]);
  const [isNewPastor, setIsNewPastor] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [inputValue, setInputValue] = useState("");

  useEffect(() => {
    tenantFetch(apiUrl("/api/sermons"))
      .then((r) => r.json())
      .then((data) => {
        const names = [...new Set(data.map((s: { pastor?: string }) => s.pastor).filter(Boolean))] as string[];
        setPastors(names.sort());
      })
      .catch(() => {});
  }, []);

  function handleFile(f: File) {
    setError("");
    const type = detectFileType(f);
    if (!type) {
      setError("Unsupported format. Upload MP3, WAV, M4A, TXT, DOCX, MD, RTF, ODT, HTML, CSV, or XML.");
      return;
    }
    if (type === "audio" && f.size > MAX_AUDIO_SIZE) {
      setError("File too large. Max 100MB for audio.");
      return;
    }
    if (type === "text" && f.size > MAX_TEXT_SIZE) {
      setError("File too large. Max 10MB for text files.");
      return;
    }
    setFile(f);
    setDetected(type);
  }

  function handleInputChange(value: string) {
    setInputValue(value);
    setError("");
    if (YT_REGEX.test(value)) {
      setYoutubeUrl(value.trim());
      setDetected("youtube");
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    const text = e.clipboardData.getData("text/plain");
    if (YT_REGEX.test(text)) {
      e.preventDefault();
      setYoutubeUrl(text.trim());
      setInputValue(text.trim());
      setDetected("youtube");
    }
  }

  function reset() {
    setDetected(null);
    setFile(null);
    setYoutubeUrl("");
    setYtStart("");
    setYtEnd("");
    setInputValue("");
    setError("");
    setProgress(0);
    setTitle("");
    setPastor("");
    setIsNewPastor(false);
  }

  async function handleSubmit() {
    if (detected === "youtube" && (!youtubeUrl.trim() || !ytStart.trim() || !ytEnd.trim())) return;
    if ((detected === "audio" || detected === "text") && !file) return;
    setUploading(true);
    setError("");
    try {
      if (detected === "youtube") {
        const res = await fetch(apiUrl("/api/sermons/youtube"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: youtubeUrl.trim(),
            start: ytStart.trim(),
            end: ytEnd.trim(),
            title: title.trim() || undefined,
            pastor: pastor.trim() || undefined,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          if (data.code === "IP_BLOCKED") {
            setError("YouTube is blocking our server. Open the video → click '...' → 'Show transcript' → copy the text → upload as a text file instead.");
          } else {
            throw new Error(data.error || "Something went wrong.");
          }
          setUploading(false);
          return;
        }
        router.push(`/sermons/${data.id}`);
        return;
      }

      const form = new FormData();
      form.append("file", file!);
      if (title.trim()) form.append("title", title.trim());
      if (pastor.trim()) form.append("pastor", pastor.trim());

      const endpoint = detected === "text" ? "/api/sermons/text" : "/api/sermons";

      const xhr = new XMLHttpRequest();
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
      };

      const res = await new Promise<{ id: string }>((resolve, reject) => {
        xhr.open("POST", apiUrl(endpoint));
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            try {
              const body = JSON.parse(xhr.responseText);
              reject(new Error(body.error || "Something went wrong. Try again."));
            } catch {
              reject(new Error("Something went wrong. Try again."));
            }
          }
        };
        xhr.onerror = () => reject(new Error("Upload failed. Check your connection and try again."));
        xhr.send(form);
      });

      router.push(`/sermons/${res.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong. Try again.");
      setUploading(false);
      setProgress(0);
    }
  }

  const typeBadge = detected === "youtube"
    ? <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-500">youtube</span>
    : detected === "text"
    ? <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-500">text</span>
    : detected === "audio"
    ? <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-500">audio</span>
    : null;

  const pastorInput = !isNewPastor ? (
    <select
      value={pastor}
      onChange={(e) => { if (e.target.value === "__new__") { setIsNewPastor(true); setPastor(""); } else { setPastor(e.target.value); } }}
      className="w-full border-b border-gray-200 bg-transparent py-2 text-sm outline-none focus:border-blue-600"
      aria-label="Pastor name"
    >
      <option value="">Select pastor *</option>
      {pastors.map((p) => <option key={p} value={p}>{p}</option>)}
      <option value="__new__">+ New pastor...</option>
    </select>
  ) : (
    <div className="flex items-center gap-2">
      <input type="text" placeholder="New pastor name *" aria-label="New pastor name"
        value={pastor} onChange={(e) => setPastor(e.target.value)} autoFocus
        className="flex-1 border-b border-gray-200 bg-transparent py-2 text-sm outline-none focus:border-blue-600" />
      <button type="button" onClick={() => { setIsNewPastor(false); setPastor(""); }} className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
    </div>
  );

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-[400px] mx-auto mt-6">
        <Nav />
        <h1 className="text-xl text-gray-900 font-semibold leading-tight mb-6">Upload Sermon</h1>
      </div>
      <div className="w-full max-w-[400px] mx-auto text-center">

        {!detected ? (
          /* ── Smart input zone ── */
          <div
            role="button"
            tabIndex={0}
            aria-label="Upload a sermon. Drop a file, click to browse, or paste a YouTube URL."
            className={`border-2 border-dashed rounded-lg p-10 cursor-pointer transition-colors ${
              dragOver ? "border-blue-400 bg-blue-50/50" : "border-gray-200 hover:border-gray-300"
            } focus:border-blue-400 focus:outline-none`}
            onClick={() => fileRef.current?.click()}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileRef.current?.click(); } }}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const text = e.dataTransfer.getData("text/plain") || e.dataTransfer.getData("text/uri-list");
              if (text) {
                const line = text.split("\n").find((l) => YT_REGEX.test(l));
                if (line) {
                  setYoutubeUrl(line.trim());
                  setInputValue(line.trim());
                  setDetected("youtube");
                  return;
                }
              }
              const f = e.dataTransfer.files[0];
              if (f) handleFile(f);
            }}
          >
            <p className="text-gray-500 mb-1">Drop a file or paste a link</p>
            <p className="text-xs text-gray-400">Audio · Text · YouTube URL</p>
            <input
              ref={fileRef}
              type="file"
              accept=".mp3,.wav,.m4a,.txt,.docx,.md,.rtf,.odt,.html,.htm,.csv,.xml"
              aria-hidden="true"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
            />
          </div>
        ) : detected === "youtube" ? (
          /* ── YouTube detected ── */
          <div className="space-y-4">
            <p className="text-sm text-left">
              <span className="text-red-500">▶️</span> {youtubeUrl}
              {typeBadge}
            </p>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-xs text-gray-500">Start *</label>
                <input type="text" placeholder="0:00:00" value={ytStart} onChange={(e) => setYtStart(e.target.value)}
                  className="w-full border border-gray-200 rounded px-3 py-2 text-sm outline-none focus:border-blue-400 text-center" aria-label="Start timestamp" />
              </div>
              <div className="flex-1">
                <label className="text-xs text-gray-500">End *</label>
                <input type="text" placeholder="1:00:00" value={ytEnd} onChange={(e) => setYtEnd(e.target.value)}
                  className="w-full border border-gray-200 rounded px-3 py-2 text-sm outline-none focus:border-blue-400 text-center" aria-label="End timestamp" />
              </div>
            </div>
            <input type="text" placeholder="Sermon title *" aria-label="Sermon title" required
              value={title} onChange={(e) => setTitle(e.target.value)}
              className="w-full border-b border-gray-200 bg-transparent py-2 text-sm outline-none focus:border-blue-600" />
            {pastorInput}
            <button onClick={handleSubmit} disabled={uploading || !title.trim() || !pastor.trim() || !ytStart.trim() || !ytEnd.trim()}
              className="w-full bg-blue-600 text-white rounded-lg py-3 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {uploading ? "Fetching transcript..." : "Analyze Sermon"}
            </button>
            {uploading && <Spinner />}
            <button onClick={reset} className="text-xs text-gray-400 hover:text-gray-600">Choose a different source</button>
          </div>
        ) : (
          /* ── File detected (audio or text) ── */
          <div className="space-y-4">
            <p className="text-sm text-left">
              <span className="text-green-500">✓</span> {file!.name}{" "}
              <span className="text-gray-400">({(file!.size / (1024 * 1024)).toFixed(1)} MB)</span>
              {typeBadge}
            </p>
            <input type="text" placeholder="Sermon title *" aria-label="Sermon title" required
              value={title} onChange={(e) => setTitle(e.target.value)}
              className="w-full border-b border-gray-200 bg-transparent py-2 text-sm outline-none focus:border-blue-600" />
            {pastorInput}
            <button onClick={handleSubmit} disabled={uploading || !title.trim() || !pastor.trim()}
              className="w-full bg-blue-600 text-white rounded-lg py-3 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {uploading ? "Uploading..." : "Analyze Sermon"}
            </button>
            {uploading && (
              <div role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress" className="w-full bg-gray-200 rounded-full h-1">
                <div className="bg-blue-600 h-1 rounded-full transition-all" style={{ width: `${progress}%` }} />
              </div>
            )}
            {uploading && <Spinner />}
            <button onClick={reset} className="text-xs text-gray-400 hover:text-gray-600">Choose a different file</button>
          </div>
        )}

        {/* YouTube URL input — always visible below drop zone when no detection yet */}
        {!detected && (
          <div className="mt-4">
            <input
              type="url"
              placeholder="or paste a YouTube URL here"
              value={inputValue}
              onChange={(e) => handleInputChange(e.target.value)}
              onPaste={handlePaste}
              className="w-full border border-gray-200 rounded px-3 py-2 text-sm outline-none focus:border-blue-400 text-center"
              aria-label="YouTube video URL"
            />
          </div>
        )}

        {error && <p role="alert" className="text-red-500 text-sm mt-4">{error}</p>}
      </div>
    </div>
  );
}
