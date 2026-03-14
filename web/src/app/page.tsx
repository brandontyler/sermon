"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiUrl } from "@/lib/api";

const ALLOWED_AUDIO = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/wave", "audio/mp4", "audio/x-m4a"];
const ALLOWED_TEXT_EXT = [".txt", ".md", ".html", ".htm", ".rtf", ".xml", ".csv", ".docx", ".odt"];
const MAX_AUDIO_SIZE = 100 * 1024 * 1024;
const MAX_TEXT_SIZE = 10 * 1024 * 1024;

type UploadMode = "audio" | "text" | "youtube";

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

function isTextFile(f: File): boolean {
  const ext = f.name.toLowerCase().slice(f.name.lastIndexOf("."));
  return ALLOWED_TEXT_EXT.includes(ext);
}

export default function UploadPage() {
  const router = useRouter();
  const audioRef = useRef<HTMLInputElement>(null);
  const textRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<UploadMode>("audio");
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

  useEffect(() => {
    fetch(apiUrl("/api/sermons"))
      .then((r) => r.json())
      .then((data) => {
        const names = [...new Set(data.map((s: { pastor?: string }) => s.pastor).filter(Boolean))] as string[];
        setPastors(names.sort());
      })
      .catch(() => {});
  }, []);

  function handleAudioFile(f: File) {
    setError("");
    if (!ALLOWED_AUDIO.includes(f.type)) {
      setError("Unsupported audio format. Upload MP3, WAV, or M4A.");
      return;
    }
    if (f.size > MAX_AUDIO_SIZE) {
      setError("File too large. Max 100MB.");
      return;
    }
    setFile(f);
    setMode("audio");
  }

  function handleTextFile(f: File) {
    setError("");
    if (!isTextFile(f)) {
      setError("Unsupported text format. Upload TXT, DOCX, MD, RTF, ODT, HTML, CSV, or XML.");
      return;
    }
    if (f.size > MAX_TEXT_SIZE) {
      setError("File too large. Max 10MB for text files.");
      return;
    }
    setFile(f);
    setMode("text");
  }

  async function handleSubmit() {
    if (!file && mode !== "youtube") return;
    if (mode === "youtube" && !youtubeUrl.trim()) return;
    setUploading(true);
    setError("");
    try {
      if (mode === "youtube") {
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
          setProgress(0);
          return;
        }
        router.push(`/sermons/${data.id}`);
        return;
      }

      const form = new FormData();
      form.append("file", file!);
      if (title.trim()) form.append("title", title.trim());
      if (pastor.trim()) form.append("pastor", pastor.trim());

      const endpoint = mode === "text" ? "/api/sermons/text" : "/api/sermons";

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

  return (
    <div className="min-h-screen p-4">
      <div className="w-full max-w-[400px] mx-auto text-center mt-8">

        {!file && mode !== "youtube" ? (
          <div className="space-y-4">
            {/* YouTube URL */}
            <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 transition-colors hover:border-gray-300">
              <p className="text-gray-500 mb-3">▶️ Paste a YouTube link</p>
              <input
                type="url"
                placeholder="https://www.youtube.com/watch?v=..."
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                className="w-full border border-gray-200 rounded px-3 py-2 text-sm outline-none focus:border-blue-400 mb-2"
                aria-label="YouTube video URL"
              />
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs text-gray-500">Start *</label>
                  <input
                    type="text"
                    placeholder="0:00:00"
                    value={ytStart}
                    onChange={(e) => setYtStart(e.target.value)}
                    className="w-full border border-gray-200 rounded px-3 py-2 text-sm outline-none focus:border-blue-400 text-center"
                    aria-label="Start timestamp"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-500">End *</label>
                  <input
                    type="text"
                    placeholder="1:00:00"
                    value={ytEnd}
                    onChange={(e) => setYtEnd(e.target.value)}
                    className="w-full border border-gray-200 rounded px-3 py-2 text-sm outline-none focus:border-blue-400 text-center"
                    aria-label="End timestamp"
                  />
                </div>
              </div>
              {youtubeUrl.trim() && ytStart.trim() && ytEnd.trim() && (
                <button
                  onClick={() => { setFile(null); setMode("youtube"); }}
                  className="mt-3 w-full bg-red-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-red-700 transition-colors"
                >
                  Use This Video
                </button>
              )}
              <p className="text-xs text-gray-400 mt-2">Uses YouTube&apos;s captions · English only · Format: H:MM:SS</p>
            </div>

            <p className="text-xs text-gray-400">— or —</p>

            {/* Audio upload */}
            <div
              role="button"
              tabIndex={0}
              aria-label="Upload sermon audio file. Drop file here or press Enter to browse."
              className="border-2 border-dashed border-gray-200 rounded-lg p-8 cursor-pointer hover:border-gray-300 focus:border-blue-400 focus:outline-none transition-colors"
              onClick={() => audioRef.current?.click()}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); audioRef.current?.click(); } }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleAudioFile(f); }}
            >
              <p className="text-gray-500">🎙️ Drop audio file here</p>
              <p className="text-gray-500">or click to browse</p>
              <p className="text-xs text-gray-400 mt-2">MP3, WAV, M4A · max 1hr</p>
              <input ref={audioRef} type="file" accept=".mp3,.wav,.m4a" aria-hidden="true" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleAudioFile(f); }} />
            </div>

            <p className="text-xs text-gray-400">— or —</p>

            {/* Text upload */}
            <div
              role="button"
              tabIndex={0}
              aria-label="Upload sermon text transcript. Drop file here or press Enter to browse."
              className="border-2 border-dashed border-gray-200 rounded-lg p-8 cursor-pointer hover:border-gray-300 focus:border-blue-400 focus:outline-none transition-colors"
              onClick={() => textRef.current?.click()}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); textRef.current?.click(); } }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleTextFile(f); }}
            >
              <p className="text-gray-500">📄 Drop text transcript here</p>
              <p className="text-gray-500">or click to browse</p>
              <p className="text-xs text-gray-400 mt-2">TXT, DOCX, MD, RTF, ODT, HTML, CSV, XML · max 10MB</p>
              <input ref={textRef} type="file" accept=".txt,.docx,.md,.rtf,.odt,.html,.htm,.csv,.xml" aria-hidden="true" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleTextFile(f); }} />
            </div>
          </div>
        ) : mode === "youtube" ? (
          <div className="space-y-4">
            <p className="text-sm">
              <span className="text-red-500">▶️</span> {youtubeUrl}
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-500">youtube</span>
              <span className="ml-1 text-xs text-gray-400">{ytStart} → {ytEnd}</span>
            </p>
            <input type="text" placeholder="Sermon title *" aria-label="Sermon title" required
              value={title} onChange={(e) => setTitle(e.target.value)}
              className="w-full border-b border-gray-200 bg-transparent py-2 text-sm outline-none focus:border-blue-600" />
            {!isNewPastor ? (
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
            )}
            <button onClick={handleSubmit} disabled={uploading || !title.trim() || !pastor.trim()}
              className="w-full bg-blue-600 text-white rounded-lg py-3 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {uploading ? "Fetching transcript..." : "Analyze Sermon"}
            </button>
            {uploading && <Spinner />}
            <button onClick={() => { setMode("audio"); setYoutubeUrl(""); setYtStart(""); setYtEnd(""); setError(""); }}
              className="text-xs text-gray-400 hover:text-gray-600">
              Choose a different source
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm">
              <span className="text-green-500">✓</span> {file!.name}{" "}
              <span className="text-gray-400">({(file!.size / (1024 * 1024)).toFixed(1)} MB)</span>
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                {mode === "text" ? "text" : "audio"}
              </span>
            </p>
            <input type="text" placeholder="Sermon title *" aria-label="Sermon title" required
              value={title} onChange={(e) => setTitle(e.target.value)}
              className="w-full border-b border-gray-200 bg-transparent py-2 text-sm outline-none focus:border-blue-600" />
            {!isNewPastor ? (
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
            )}
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
            <button onClick={() => { setFile(null); setError(""); setProgress(0); }}
              className="text-xs text-gray-400 hover:text-gray-600">
              Choose a different file
            </button>
          </div>
        )}

        {error && <p role="alert" className="text-red-500 text-sm mt-4">{error}</p>}
      </div>
    </div>
  );
}
