"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiUrl } from "@/lib/api";
import {
  SermonDetail,
  TranscriptSegment,
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  scoreColor,
  scoreBgColor,
} from "@/lib/types";
import dynamic from "next/dynamic";
import ScoreGauge from "@/components/ScoreGauge";
const RadarView = dynamic(() => import("@/components/RadarView"), {
  ssr: false,
  loading: () => <div className="h-[200px] flex items-center justify-center text-gray-400 text-sm">Loading chart...</div>,
});
import TranscriptViewer from "@/components/TranscriptViewer";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function CbvTooltip() {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-block mb-3">
      <button
        onClick={() => setShow(!show)}
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="text-sm font-medium text-gray-900 cursor-pointer"
      >
        ⛪ Church Beliefs and Values (CBV)
      </button>
      {show && (
        <span style={{ backgroundColor: "#ffffff", color: "#1a1a1a" }} className="absolute left-0 top-full mt-2 w-72 p-3 border border-gray-300 rounded-lg shadow-xl text-xs z-50">
          <strong className="block mb-1">Church Beliefs &amp; Values</strong>
          CBV is pulled from the church&apos;s official beliefs page (set by an admin). Each sermon transcript is analyzed by AI to determine which core beliefs were referenced. A ✅ means the belief was addressed in the sermon; a — means it wasn&apos;t. This helps pastors track doctrinal coverage over time.
        </span>
      )}
    </span>
  );
}

function ScoreTooltip({ score }: { score: number }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative">
      <span
        onClick={() => setShow(!show)}
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="cursor-pointer"
      >
        <ScoreGauge score={score} />
      </span>
      {show && (
        <span style={{ backgroundColor: "#ffffff", color: "#1a1a1a" }} className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-72 p-3 border border-gray-300 rounded-lg shadow-xl text-xs z-50">
          <strong className="block mb-1">PSR Score (0–100)</strong>
          The Pastor Sermon Rating is a composite score across 8 weighted categories: Biblical Accuracy (25%), Time in the Word (20%), Passage Focus (10%), Clarity (10%), Engagement (10%), Application (10%), Delivery (10%), and Emotional Range (5%). Scores are normalized by sermon type when confidence is high. Green = 70+, Yellow = 50–69, Red = below 50.
        </span>
      )}
    </span>
  );
}

function BonusTooltip() {
  const [show, setShow] = useState(false);
  return (
    <span className="relative">
      <button
        onClick={() => setShow(!show)}
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded cursor-pointer"
      >
        ⚙ Bonus
      </button>
      {show && (
        <span style={{ backgroundColor: "#ffffff", color: "#1a1a1a" }} className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-64 p-3 border border-gray-300 rounded-lg shadow-xl text-xs z-50">
          <strong className="block mb-1">Score Adjustment</strong>
          Admins can manually adjust the composite score with bonus points — rewarding exceptional elements the AI may have missed, or correcting edge cases.
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/bonus-sample.png" alt="Bonus points example" className="mt-2 rounded border border-gray-100 w-full" />
        </span>
      )}
    </span>
  );
}

export default function SermonDetailClient({ sermonId, sample, preloadedData }: { sermonId?: string; sample?: boolean; preloadedData?: SermonDetail } = {}) {
  const params = useParams<{ id: string }>();
  // Static export bakes "placeholder" into RSC payload. Always read from URL.
  const [id, setId] = useState<string | null>(sermonId || null);
  const [sermon, setSermon] = useState<SermonDetail | null>(preloadedData || null);
  const [loading, setLoading] = useState(!preloadedData);
  const [transcriptLang, setTranscriptLang] = useState<"en" | "es">("en");
  const [spanishText, setSpanishText] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fullTranscript, setFullTranscript] = useState<{ fullText: string; segments?: unknown[]; translations?: Record<string, string> } | null>(null);
  const [loadingTranscript, setLoadingTranscript] = useState(false);
  const [churchUrl, setChurchUrl] = useState<{ name: string; url: string } | null>(null);
  const [churchBeliefs, setChurchBeliefs] = useState<string[] | null>(null);
  const [cbv, setCbv] = useState<{ title: string; referenced: boolean }[] | null>(null);

  // Resolve ID from URL on mount (avoids useParams "placeholder" race).
  // UUID guard prevents bogus API calls when SWA routing serves this page
  // for non-detail paths (e.g. /sermons → seg="sermons").
  useEffect(() => {
    if (sermonId) { setId(sermonId); return; }
    const seg = window.location.pathname.split("/").pop() || "";
    const resolved = UUID_RE.test(seg) ? seg : (params.id && UUID_RE.test(params.id)) ? params.id : null;
    setId(resolved);
    if (!resolved) { setLoading(false); }
  }, [params.id, sermonId]);

  useEffect(() => {
    if (!id || preloadedData) return;
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
          if (res.status === 404) {
            setError("Sermon not found.");
            setLoading(false);
            return;
          }
          // Transient 500s happen when Parselmouth OOM kills the worker — keep polling
          pollAttempts++;
          if (pollAttempts < MAX_POLL) { timeoutId = setTimeout(poll, 5000); return; }
          setError(`Server error (${res.status}). Try refreshing.`);
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
    fetch(apiUrl("/api/churches")).then(r => r.json()).then((churches: { name: string; url?: string; beliefs?: ({ title: string; description?: string } | string)[]; pastors: { name: string }[] }[]) => {
      const match = churches.find(c => c.pastors.some(p => p.name === sermon.pastor));
      if (match?.url) setChurchUrl({ name: match.name, url: /^https?:\/\//i.test(match.url) ? match.url : `https://${match.url}` });
      if (match?.beliefs?.length) {
        setChurchBeliefs(match.beliefs.map(b => typeof b === "string" ? b : b.title));
      }
    }).catch(() => {});
  }, [sermon?.pastor]);

  useEffect(() => {
    if (!id || !sermon || sermon.status !== "complete") return;
    fetch(apiUrl(`/api/sermons/${id}/cbv`)).then(r => r.ok ? r.json() : null).then(data => {
      if (data?.results) setCbv(data.results);
    }).catch(() => {});
  }, [id, sermon?.status]);

  if (loading) return <Shell>Loading...</Shell>;
  if (error) return <Shell>{error}</Shell>;
  if (!sermon) return <Shell>Sermon not found.</Shell>;

  return (
    <div className="max-w-[720px] mx-auto p-4 py-8">
      {!sample && <Link href="/sermons" className="text-sm text-blue-600 hover:underline">← Back to sermons</Link>}

      <div className="flex items-center gap-3 mt-4">
        <h1 className="text-2xl font-bold text-gray-900">{sermon.title}</h1>
        {sample ? (
          <BonusTooltip />
        ) : (
          <Link href={`/admin?sermon=${sermon.id}`} className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-2 py-1 rounded transition-colors">⚙ Bonus</Link>
        )}
      </div>
      <p className="text-sm text-gray-500 mt-1">
        {sermon.pastor && (
          <>{sample ? <span>{sermon.pastor}</span> : <Link href={`/dashboard?pastor=${encodeURIComponent(sermon.pastor)}`} className="hover:text-blue-600 hover:underline">{sermon.pastor}</Link>} · </>
        )}
        {churchUrl && (
          <>{sample ? <span className="text-gray-700">{churchUrl.name}</span> : <a href={churchUrl.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{churchUrl.name}</a>} · </>
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
            <Link href="/upload" className="text-sm text-blue-600 hover:underline">Try Again</Link>
            {!sample && <Link href="/sermons" className="text-sm text-gray-500 hover:underline">Back to sermons</Link>}
          </div>
        </div>
      )}

      {sermon.status === "complete" && sermon.categories && (
        <>
          <div className="mt-8 flex flex-col items-center">
            {sample ? (
              <ScoreTooltip score={sermon.compositePsr ?? 0} />
            ) : (
              <ScoreGauge score={sermon.compositePsr ?? 0} />
            )}
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

          {sermon.aiScore != null && <AiStoplight score={sermon.aiScore} reasoning={sermon.aiReasoning} />}

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

          {sermon.sermonSummary && (
            <div className="mt-10 bg-white border border-gray-200 rounded-lg p-5">
              <h3 className="text-sm font-medium text-gray-900 mb-3">📝 Sermon Summary</h3>
              <p className="text-sm text-gray-600 leading-relaxed">{sermon.sermonSummary.overview}</p>
              {sermon.sermonSummary.keyPoints?.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {sermon.sermonSummary.keyPoints.map((point, i) => (
                    <li key={i} className="text-sm text-gray-600 flex gap-2">
                      <span className="text-blue-400 mt-0.5 shrink-0">•</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {churchBeliefs && churchBeliefs.length > 0 && (
            <div className="mt-10 bg-white border border-gray-200 rounded-lg p-5">
              {sample ? (
                <CbvTooltip />
              ) : (
                <h3 className="text-sm font-medium text-gray-900 mb-3">⛪ Church Beliefs and Values (CBV)</h3>
              )}
              <ul className="space-y-1.5">
                {churchBeliefs.map((b, i) => {
                  const match = cbv?.find(c => c.title === b);
                  return (
                    <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                      <span className="shrink-0 w-5 text-center">
                        {match ? (match.referenced ? "✅" : "—") : <span className="text-gray-300">·</span>}
                      </span>
                      <span>{b}</span>
                    </li>
                  );
                })}
              </ul>
              {!cbv && <p className="text-xs text-gray-400 mt-2">Analyzing beliefs alignment…</p>}
            </div>
          )}

          {sermon.transcript && ((sermon.transcript.segments?.length ?? 0) > 0 || sermon.transcript.fullText || sermon.transcript.wordCount) && (
            <div className="mt-10">
              {!fullTranscript ? (
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-900">Transcript</h3>
                  <button
                    onClick={() => {
                      if (loadingTranscript) return;
                      setLoadingTranscript(true);
                      fetch(apiUrl(`/api/sermons/${sermon.id}/transcript`))
                        .then(r => r.json())
                        .then(data => { setFullTranscript(data); setLoadingTranscript(false); })
                        .catch(() => setLoadingTranscript(false));
                    }}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    {loadingTranscript ? "Loading…" : `Show Transcript${sermon.transcript.wordCount ? ` (${sermon.transcript.wordCount.toLocaleString()} words)` : ""}`}
                  </button>
                </div>
              ) : (
                <>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-medium text-gray-900">Transcript</h3>
                  {sample ? (
                    <span className="text-xs text-gray-500 italic">Spanish translation available.</span>
                  ) : (
                  <div className="flex rounded-md border border-gray-200 text-xs overflow-hidden">
                    <button
                      onClick={() => setTranscriptLang("en")}
                      className={`px-3 py-1 ${transcriptLang === "en" ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-50"}`}
                    >English</button>
                    <button
                      onClick={async () => {
                        setTranscriptLang("es");
                        if (spanishText || fullTranscript.translations?.es) {
                          if (!spanishText && fullTranscript.translations?.es) setSpanishText(fullTranscript.translations.es);
                          return;
                        }
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
                  )}
                </div>
                <button
                  onClick={() => {
                    const text = transcriptLang === "es" && spanishText
                      ? spanishText
                      : fullTranscript.fullText || (fullTranscript.segments || []).map((s: unknown) => (s as { text: string }).text).join("\n");
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
                  segments={fullTranscript.segments && (fullTranscript.segments as unknown[]).length > 0
                    ? fullTranscript.segments as unknown as TranscriptSegment[]
                    : [{ start: 0, end: 0, text: fullTranscript.fullText || "", type: "teaching" as const }]}
                />
              )}
                </>
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

function AiStoplight({ score, reasoning }: { score: 1 | 2 | 3; reasoning?: string | null }) {
  const config = {
    1: { color: "bg-green-500", ring: "ring-green-500/30", label: "Human", desc: "No AI detected" },
    2: { color: "bg-yellow-400", ring: "ring-yellow-400/30", label: "Uncertain", desc: "Possible AI" },
    3: { color: "bg-red-500", ring: "ring-red-500/30", label: "AI Detected", desc: "Likely AI-generated" },
  }[score];
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-6 flex flex-col items-center">
      <div className="bg-gray-100 border border-gray-200 rounded-full px-4 py-2 flex items-center gap-3">
        {[1, 2, 3].map((n) => (
          <div key={n} className={`w-4 h-4 rounded-full ${n === score ? `${config.color} ring-2 ${config.ring}` : "bg-gray-300"}`} />
        ))}
      </div>
      <span className="text-xs text-gray-500 mt-2">{config.label} — {config.desc}</span>
      {reasoning && (
        <>
          <button onClick={() => setOpen(!open)} className="text-xs text-gray-400 hover:text-gray-600 mt-1">
            {open ? "▾ Hide" : "▸ Why?"}
          </button>
          {open && <p className="text-xs text-gray-500 mt-1 text-center max-w-sm">{reasoning}</p>}
        </>
      )}
    </div>
  );
}
