"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiUrl } from "@/lib/api";
import {
  SermonDetail,
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  scoreColor,
  scoreBgColor,
} from "@/lib/types";
import ScoreGauge from "@/components/ScoreGauge";
import RadarView from "@/components/RadarView";
import TranscriptViewer from "@/components/TranscriptViewer";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function SermonDetailClient() {
  const params = useParams<{ id: string }>();
  // Static export bakes "placeholder" into RSC payload. Always read from URL.
  const [id, setId] = useState<string | null>(null);
  const [sermon, setSermon] = useState<SermonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [transcriptLang, setTranscriptLang] = useState<"en" | "es">("en");
  const [spanishText, setSpanishText] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [churchUrl, setChurchUrl] = useState<{ name: string; url: string } | null>(null);

  // Resolve ID from URL on mount (avoids useParams "placeholder" race).
  // UUID guard prevents bogus API calls when SWA routing serves this page
  // for non-detail paths (e.g. /sermons → seg="sermons").
  useEffect(() => {
    const seg = window.location.pathname.split("/").pop() || "";
    const resolved = UUID_RE.test(seg) ? seg : UUID_RE.test(params.id) ? params.id : null;
    setId(resolved);
    if (!resolved) { setLoading(false); }
  }, [params.id]);

  useEffect(() => {
    if (!id) return;
    let active = true;
    let timeoutId: ReturnType<typeof setTimeout>;
    let pollAttempts = 0;
    const MAX_POLL = 120;
    const MAX_RETRIES = 3; // retry on network errors (cold start)

    async function fetchWithRetry(): Promise<Response> {
      for (let i = 0; i < MAX_RETRIES; i++) {
        try {
          return await fetch(apiUrl(`/api/sermons/${id}`));
        } catch {
          if (i === MAX_RETRIES - 1) throw new Error("Network error");
          await new Promise((r) => setTimeout(r, 2000 * (i + 1)));
        }
      }
      throw new Error("Network error");
    }

    async function poll() {
      try {
        const res = await fetchWithRetry();
        if (!active) return;
        if (!res.ok) {
          setError(res.status === 404 ? "Sermon not found." : `Server error (${res.status}). Try refreshing.`);
          setLoading(false);
          return;
        }
        const data: SermonDetail = await res.json();
        if (!active) return;
        setSermon(data);
        setLoading(false);
        if (data.status === "processing") {
          pollAttempts++;
          if (pollAttempts >= MAX_POLL) {
            setError("Analysis is taking longer than expected. Try refreshing in a few minutes.");
            return;
          }
          timeoutId = setTimeout(poll, 5000);
        }
      } catch {
        if (!active) return;
        setError("Network error. Check your connection and try refreshing.");
        setLoading(false);
      }
    }

    poll();
    return () => { active = false; clearTimeout(timeoutId); };
  }, [id]);

  useEffect(() => {
    if (!sermon?.pastor) return;
    fetch(apiUrl("/api/churches")).then(r => r.json()).then((churches: { name: string; url?: string; pastors: { name: string }[] }[]) => {
      const match = churches.find(c => c.pastors.some(p => p.name === sermon.pastor));
      if (match?.url) setChurchUrl({ name: match.name, url: /^https?:\/\//i.test(match.url) ? match.url : `https://${match.url}` });
    }).catch(() => {});
  }, [sermon?.pastor]);

  if (loading) return <Shell>Loading...</Shell>;
  if (error) return <Shell>{error}</Shell>;
  if (!sermon) return <Shell>Sermon not found.</Shell>;

  return (
    <div className="max-w-[720px] mx-auto p-4 py-8">
      <Link href="/sermons" className="text-sm text-blue-600 hover:underline">← Back to sermons</Link>

      <div className="flex items-center gap-3 mt-4">
        <h1 className="text-2xl font-bold text-gray-900">{sermon.title}</h1>
        <Link href={`/admin?sermon=${sermon.id}`} className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-2 py-1 rounded transition-colors">⚙ Bonus</Link>
      </div>
      <p className="text-sm text-gray-500 mt-1">
        {sermon.pastor && (
          <><Link href={`/dashboard?pastor=${encodeURIComponent(sermon.pastor)}`} className="hover:text-blue-600 hover:underline">{sermon.pastor}</Link> · </>
        )}
        {churchUrl && (
          <><a href={churchUrl.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{churchUrl.name}</a> · </>
        )}
        {[
          sermon.date && new Date(sermon.date + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
          sermon.duration && `${Math.round(sermon.duration / 60)} min`,
        ].filter(Boolean).join(" · ")}
        {sermon.sermonType && (
          <> · <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs">{sermon.sermonType}</span></>
        )}
        {sermon.youtubeUrl && (
          <> · <a href={sermon.youtubeUrl} target="_blank" rel="noopener noreferrer" className="text-red-500 hover:text-red-600 text-xs">▶ YouTube</a></>
        )}
      </p>

      {sermon.status === "processing" && (
        <div aria-live="polite" className="mt-12 text-center text-gray-500">
          <div className="flex justify-center mb-6">
            <div className="relative w-14 h-14">
              <div className="absolute inset-0 rounded-full border-[3px] border-gray-200" />
              <div className="absolute inset-0 rounded-full border-[3px] border-transparent border-t-blue-600 animate-spin" />
            </div>
          </div>
          <p className="text-lg font-medium text-gray-900 mb-4">Analyzing sermon...</p>
          <div className="space-y-2 text-sm">
            {["Transcribing audio", "Analyzing biblical content", "Evaluating structure", "Scoring delivery"].map((step, i) => (
              <p key={i} className="animate-pulse" style={{ animationDelay: `${i * 0.3}s` }}>⏳ {step}</p>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-6">This usually takes about 5 minutes.</p>
        </div>
      )}

      {sermon.status === "failed" && (
        <div role="alert" className="mt-12 text-center">
          <p className="text-lg font-medium text-gray-900 mb-2">Something went wrong analyzing this sermon.</p>
          {sermon.error && <p className="text-sm text-gray-500 mb-6">Error: {sermon.error}</p>}
          <div className="flex gap-4 justify-center">
            <Link href="/" className="text-sm text-blue-600 hover:underline">Try Again</Link>
            <Link href="/sermons" className="text-sm text-gray-500 hover:underline">Back to sermons</Link>
          </div>
        </div>
      )}

      {sermon.status === "complete" && sermon.categories && (
        <>
          <div className="mt-8 flex flex-col items-center">
            <ScoreGauge score={sermon.compositePsr ?? 0} />
            {sermon.bonus != null && sermon.bonus !== 0 && (
              <div className="flex items-center gap-2 mt-2 text-sm">
                <span className="text-gray-500">PSR {sermon.compositePsr?.toFixed(1)}</span>
                <span className={sermon.bonus > 0 ? "text-green-600 font-bold" : "text-red-500 font-bold"}>
                  {sermon.bonus > 0 ? "+" : ""}{sermon.bonus.toFixed(1)} bonus
                </span>
                <span className="text-gray-500">=</span>
                <span className="font-bold">{sermon.totalScore?.toFixed(1)}</span>
              </div>
            )}
            {sermon.summary && <p className="text-sm text-gray-500 italic mt-4 text-center max-w-md">{sermon.summary}</p>}
          </div>

          <div className="mt-10 flex justify-center">
            <RadarView categories={sermon.categories} />
          </div>

          <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {CATEGORY_ORDER.map((key) => {
              const cat = sermon.categories![key];
              if (!cat) return null;
              return <CategoryCard key={key} name={CATEGORY_LABELS[key]} weight={cat.weight} score={cat.score} reasoning={cat.reasoning} />;
            })}
          </div>

          {/* Radar chart moved above category cards for screenshot-friendly fold */}

          {(sermon.strengths || sermon.improvements) && (
            <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {sermon.strengths && (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <span className="text-green-500">✓</span> Strengths
                  </h3>
                  <ul className="space-y-2">
                    {sermon.strengths.map((s, i) => (
                      <li key={i} className="text-sm text-gray-600 flex gap-2">
                        <span className="text-green-400 mt-0.5 shrink-0">•</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {sermon.improvements && (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <span className="text-yellow-500">△</span> Areas to Improve
                  </h3>
                  <ul className="space-y-2">
                    {sermon.improvements.map((s, i) => (
                      <li key={i} className="text-sm text-gray-600 flex gap-2">
                        <span className="text-yellow-400 mt-0.5 shrink-0">•</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {sermon.transcript && (sermon.transcript.segments.length > 0 || sermon.transcript.fullText) && (
            <div className="mt-10">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-medium text-gray-900">Transcript</h3>
                  <div className="flex rounded-md border border-gray-200 text-xs overflow-hidden">
                    <button
                      onClick={() => setTranscriptLang("en")}
                      className={`px-3 py-1 ${transcriptLang === "en" ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-50"}`}
                    >English</button>
                    <button
                      onClick={async () => {
                        setTranscriptLang("es");
                        if (spanishText) return;
                        setTranslating(true);
                        try {
                          const r = await fetch(apiUrl(`/api/sermons/${sermon.id}/translate`), {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ language: "es" }),
                          });
                          const data = await r.json();
                          if (r.ok) setSpanishText(data.text);
                          else setSpanishText(null);
                        } catch {} finally { setTranslating(false); }
                      }}
                      className={`px-3 py-1 ${transcriptLang === "es" ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-50"}`}
                    >Español</button>
                  </div>
                </div>
                <button
                  onClick={() => {
                    const text = transcriptLang === "es" && spanishText
                      ? spanishText
                      : sermon.transcript!.fullText || sermon.transcript!.segments.map(s => s.text).join("\n");
                    const blob = new Blob([text], { type: "text/plain" });
                    const a = document.createElement("a");
                    a.href = URL.createObjectURL(blob);
                    a.download = `${sermon.title || "sermon"}-transcript-${transcriptLang}.txt`;
                    a.click();
                    URL.revokeObjectURL(a.href);
                  }}
                  className="text-xs text-blue-600 hover:underline"
                >
                  ⬇ Download .txt
                </button>
              </div>
              {transcriptLang === "es" ? (
                translating ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="relative w-10 h-10 mx-auto mb-3">
                      <div className="absolute inset-0 rounded-full border-[3px] border-gray-200" />
                      <div className="absolute inset-0 rounded-full border-[3px] border-transparent border-t-blue-600 animate-spin" />
                    </div>
                    <p className="text-sm">Translating to Spanish…</p>
                  </div>
                ) : spanishText ? (
                  <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap max-h-[500px] overflow-y-auto">
                    {spanishText}
                  </div>
                ) : (
                  <button onClick={async () => {
                    setTranslating(true);
                    try {
                      const r = await fetch(apiUrl(`/api/sermons/${sermon.id}/translate`), {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ language: "es" }),
                      });
                      const data = await r.json();
                      if (r.ok) setSpanishText(data.text);
                    } catch {} finally { setTranslating(false); }
                  }} className="text-sm text-blue-600 hover:underline text-center py-4 w-full">Translation failed — click to retry</button>
                )
              ) : (
                <TranscriptViewer
                  segments={sermon.transcript.segments.length > 0
                    ? sermon.transcript.segments
                    : [{ start: 0, end: 0, text: sermon.transcript.fullText, type: "teaching" }]}
                />
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="max-w-[720px] mx-auto p-4 py-8 text-gray-400 text-sm">{children}</div>;
}

function CategoryCard({ name, weight, score, reasoning }: { name: string; weight: number; score: number; reasoning: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex justify-between text-sm mb-2">
        <span className="font-medium text-gray-900">{name}</span>
        <span className="text-gray-400">{weight}%</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-gray-100 rounded-full h-2">
          <div className={`h-2 rounded-full ${scoreBgColor(score)}`} style={{ width: `${score}%` }} />
        </div>
        <span className={`text-sm font-bold ${scoreColor(score)}`}>{score}</span>
      </div>
      <button aria-expanded={open} onClick={() => setOpen(!open)} className="text-xs text-gray-400 hover:text-gray-600 mt-2">
        {open ? "▾ Hide reasoning" : "▸ View reasoning"}
      </button>
      {open && <p className="text-xs text-gray-500 mt-2 leading-relaxed">{reasoning}</p>}
    </div>
  );
}
