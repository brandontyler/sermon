"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiUrl } from "@/lib/api";

const ALLOWED_AUDIO = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/wave", "audio/mp4", "audio/x-m4a"];
const ALLOWED_TEXT_EXT = [".txt", ".md", ".html", ".htm", ".rtf", ".xml", ".csv", ".docx", ".odt"];
const MAX_AUDIO_SIZE = 100 * 1024 * 1024;
const MAX_TEXT_SIZE = 10 * 1024 * 1024;

type UploadMode = "audio" | "text";

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
  const [title, setTitle] = useState("");
  const [pastor, setPastor] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

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
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
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
    <div className="flex items-center justify-center min-h-screen p-4">
      <div className="w-full max-w-[400px] text-center">
        <p className="text-sm text-gray-600 leading-relaxed mb-6">
          Welcome to a new way of strengthening your voice in ministry. Our platform provides pastors and speakers with thoughtful, data‑driven insights by analyzing uploaded sermon audio and comparing it against a carefully trained communication model. The goal isn&apos;t to critique or diminish—it&apos;s to illuminate strengths, highlight opportunities for growth, and support every pastor in delivering clearer, more impactful messages. With a warm, encouraging approach, we help communicators refine their craft so their words can reach hearts with even greater clarity and purpose.
        </p>
        <h1 className="text-xl text-gray-900 font-semibold">PSR</h1>
        <p className="text-sm text-gray-500 mb-8">Pastor Sermon Rating</p>

        {!file ? (
          <div className="space-y-4">
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
        ) : (
          <div className="space-y-4">
            <p className="text-sm">
              <span className="text-green-500">✓</span> {file.name}{" "}
              <span className="text-gray-400">({(file.size / (1024 * 1024)).toFixed(1)} MB)</span>
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                {mode === "text" ? "text" : "audio"}
              </span>
            </p>
            <input type="text" placeholder="Sermon title (optional)" aria-label="Sermon title"
              value={title} onChange={(e) => setTitle(e.target.value)}
              className="w-full border-b border-gray-200 bg-transparent py-2 text-sm outline-none focus:border-blue-600" />
            <input type="text" placeholder="Pastor name (optional)" aria-label="Pastor name"
              value={pastor} onChange={(e) => setPastor(e.target.value)}
              className="w-full border-b border-gray-200 bg-transparent py-2 text-sm outline-none focus:border-blue-600" />
            <button onClick={handleSubmit} disabled={uploading}
              className="w-full bg-blue-600 text-white rounded-lg py-3 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {uploading ? "Uploading..." : "Analyze Sermon"}
            </button>
            {uploading && (
              <div role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress" className="w-full bg-gray-200 rounded-full h-1">
                <div className="bg-blue-600 h-1 rounded-full transition-all" style={{ width: `${progress}%` }} />
              </div>
            )}
            <button onClick={() => { setFile(null); setError(""); setProgress(0); }}
              className="text-xs text-gray-400 hover:text-gray-600">
              Choose a different file
            </button>
          </div>
        )}

        {error && <p role="alert" className="text-red-500 text-sm mt-4">{error}</p>}

        <Link href="/sermons" className="inline-block mt-8 text-sm text-blue-600 hover:underline">
          View All Sermons →
        </Link>
      </div>
    </div>
  );
}
