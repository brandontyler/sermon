"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiUrl } from "@/lib/api";
import { CATEGORY_LABELS, CATEGORY_ORDER } from "@/lib/types";

interface SermonData {
  id: string;
  title: string;
  pastor: string | null;
  compositePsr: number | null;
  totalScore?: number;
  date: string;
  status: string;
  categories?: Record<string, { score: number; weight: number; reasoning: string }>;
  improvements?: string[];
  strengths?: string[];
  inputType?: string;
}

function psr(s: SermonData) { return s.totalScore ?? s.compositePsr ?? 0; }
function color(score: number) { return score >= 74 ? "#22c55e" : score >= 60 ? "#eab308" : "#ef4444"; }

// ── Simple SVG Charts ──

function BarChart({ data, label }: { data: { name: string; value: number; id?: string }[]; label: string }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  const h = 130, w = 400, barW = Math.min(40, (w - 40) / data.length - 8);
  const startX = (w - data.length * (barW + 8)) / 2;
  return (
    <div>
      <p className="text-xs font-bold text-gray-600 mb-2">{label}</p>
      <svg viewBox={`0 0 ${w} ${h + 30}`} className="w-full">
        {data.map((d, i) => {
          const barH = (d.value / max) * (h - 20);
          const x = startX + i * (barW + 8);
          const titleEl = (
            <text x={x + barW / 2} y={h + 14} textAnchor="middle" className={`text-[8px] ${d.id ? "fill-blue-600 cursor-pointer hover:underline" : "fill-gray-500"}`}>{d.name.length > 12 ? d.name.slice(0, 11) + "…" : d.name}</text>
          );
          return (
            <g key={i}>
              <rect x={x} y={h - barH} width={barW} height={barH} fill={color(d.value)} rx={3} />
              <text x={x + barW / 2} y={h - barH - 4} textAnchor="middle" className="text-[10px] fill-slate-300 font-bold">{d.value.toFixed(1)}</text>
              {d.id ? <a href={`/sermons/${d.id}`}>{titleEl}</a> : titleEl}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function LineChart({ data, label }: { data: { name: string; value: number; id?: string }[]; label: string }) {
  if (data.length < 2) return null;
  const max = Math.max(...data.map((d) => d.value), 1);
  const min = Math.min(...data.map((d) => d.value));
  const range = Math.max(max - min, 10);
  const h = 180, w = 400, pad = 30;
  const points = data.map((d, i) => ({
    x: pad + (i / (data.length - 1)) * (w - pad * 2),
    y: h - pad - ((d.value - min + 5) / (range + 10)) * (h - pad * 2),
  }));
  const line = points.map((p) => `${p.x},${p.y}`).join(" ");
  return (
    <div>
      <p className="text-xs font-bold text-gray-600 mb-2">{label}</p>
      <svg viewBox={`0 0 ${w} ${h + 20}`} className="w-full">
        <polyline points={line} fill="none" stroke="#3b82f6" strokeWidth={2.5} strokeLinejoin="round" />
        {points.map((p, i) => {
          const titleEl = (
            <text x={p.x} y={h + 10} textAnchor="middle" className={`text-[7px] ${data[i].id ? "fill-blue-600 cursor-pointer" : "fill-gray-500"}`}>{data[i].name.length > 10 ? data[i].name.slice(0, 9) + "…" : data[i].name}</text>
          );
          return (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r={4} fill={color(data[i].value)} stroke="#1e293b" strokeWidth={2} />
              <text x={p.x} y={p.y - 10} textAnchor="middle" className="text-[9px] fill-slate-300 font-bold">{data[i].value.toFixed(1)}</text>
              {data[i].id ? <a href={`/sermons/${data[i].id}`}>{titleEl}</a> : titleEl}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function PieChart({ data, label }: { data: { name: string; value: number; color: string }[]; label: string }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  let angle = -90;
  const slices = data.map((d) => {
    const sweep = (d.value / total) * 360;
    const start = angle;
    angle += sweep;
    return { ...d, start, sweep };
  });
  function arc(start: number, sweep: number) {
    const r = 70, cx = 90, cy = 90;
    const rad = (a: number) => (a * Math.PI) / 180;
    const x1 = cx + r * Math.cos(rad(start));
    const y1 = cy + r * Math.sin(rad(start));
    const x2 = cx + r * Math.cos(rad(start + sweep));
    const y2 = cy + r * Math.sin(rad(start + sweep));
    const large = sweep > 180 ? 1 : 0;
    return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
  }
  return (
    <div>
      <p className="text-xs font-bold text-gray-600 mb-2">{label}</p>
      <div className="flex items-center gap-4">
        <svg viewBox="0 0 180 180" className="w-36 h-36">
          {slices.map((s, i) => <path key={i} d={arc(s.start, s.sweep)} fill={s.color} />)}
        </svg>
        <div className="space-y-1">
          {data.map((d, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: d.color }} />
              <span className="text-gray-600">{d.name}: {d.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function HBarChart({ data, label }: { data: { name: string; value: number }[]; label: string }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div>
      <p className="text-xs font-bold text-gray-600 mb-3">{label}</p>
      <div className="space-y-2">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-xs text-gray-600 w-32 sm:w-40 text-right truncate">{d.name}</span>
            <div className="flex-1 bg-gray-100 rounded-full h-5 relative">
              <div className="h-5 rounded-full" style={{ width: `${d.value}%`, backgroundColor: color(d.value) }} />
            </div>
            <span className="text-xs font-bold w-10 text-right" style={{ color: color(d.value) }}>{d.value.toFixed(1)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const BIBLE_BOOKS = {
  OT: ["Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi"],
  NT: ["Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians","Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James","1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"],
};
const ALL_BOOKS = [...BIBLE_BOOKS.OT, ...BIBLE_BOOKS.NT];
const BOOK_ABBREV: Record<string, string> = {"Genesis":"Gen","Exodus":"Exo","Leviticus":"Lev","Numbers":"Num","Deuteronomy":"Deu","Joshua":"Jos","Judges":"Jdg","Ruth":"Rut","1 Samuel":"1Sa","2 Samuel":"2Sa","1 Kings":"1Ki","2 Kings":"2Ki","1 Chronicles":"1Ch","2 Chronicles":"2Ch","Ezra":"Ezr","Nehemiah":"Neh","Esther":"Est","Job":"Job","Psalms":"Psa","Proverbs":"Pro","Ecclesiastes":"Ecc","Song of Solomon":"SoS","Isaiah":"Isa","Jeremiah":"Jer","Lamentations":"Lam","Ezekiel":"Eze","Daniel":"Dan","Hosea":"Hos","Joel":"Joe","Amos":"Amo","Obadiah":"Oba","Jonah":"Jon","Micah":"Mic","Nahum":"Nah","Habakkuk":"Hab","Zephaniah":"Zep","Haggai":"Hag","Zechariah":"Zec","Malachi":"Mal","Matthew":"Mat","Mark":"Mrk","Luke":"Luk","John":"Jhn","Acts":"Act","Romans":"Rom","1 Corinthians":"1Co","2 Corinthians":"2Co","Galatians":"Gal","Ephesians":"Eph","Philippians":"Php","Colossians":"Col","1 Thessalonians":"1Th","2 Thessalonians":"2Th","1 Timothy":"1Ti","2 Timothy":"2Ti","Titus":"Tit","Philemon":"Phm","Hebrews":"Heb","James":"Jas","1 Peter":"1Pe","2 Peter":"2Pe","1 John":"1Jn","2 John":"2Jn","3 John":"3Jn","Jude":"Jud","Revelation":"Rev"};

function extractBookCounts(texts: string[]): Record<string, number> {
  const counts: Record<string, number> = {};
  const combined = texts.join(" ");
  for (const book of ALL_BOOKS) {
    const escaped = book.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const matches = combined.match(new RegExp(`\\b${escaped}\\b`, "gi"));
    if (matches) counts[book] = matches.length;
  }
  return counts;
}

function ScriptureHeatmap({ counts }: { counts: Record<string, number> }) {
  const max = Math.max(...Object.values(counts), 1);
  const intensity = (n: number) => {
    if (!n) return "bg-gray-100 text-gray-400";
    const pct = n / max;
    if (pct > 0.7) return "bg-blue-600 text-white";
    if (pct > 0.4) return "bg-blue-400 text-white";
    if (pct > 0.15) return "bg-blue-200 text-blue-800";
    return "bg-blue-100 text-blue-700";
  };
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-bold text-gray-600">Sermon-Level Insights: Scripture Heatmap</p>
        <p className="text-xs text-gray-400">{Object.keys(counts).length}/{ALL_BOOKS.length} books · {total} refs</p>
      </div>
      {(["OT", "NT"] as const).map((t) => (
        <div key={t} className="mb-3">
          <p className="text-[10px] font-medium text-gray-500 mb-1">{t === "OT" ? "Old Testament" : "New Testament"}</p>
          <div className="flex flex-wrap gap-1">
            {BIBLE_BOOKS[t].map((book) => (
              <div key={book} title={`${book}: ${counts[book] || 0}`}
                className={`w-8 h-8 rounded text-[9px] font-medium flex items-center justify-center cursor-default ${intensity(counts[book] || 0)}`}>
                {BOOK_ABBREV[book] || book.slice(0, 3)}
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="flex items-center gap-2 mt-2 text-[9px] text-gray-500">
        <span>Never</span>
        <span className="w-4 h-4 rounded bg-gray-100" />
        <span className="w-4 h-4 rounded bg-blue-100" />
        <span className="w-4 h-4 rounded bg-blue-200" />
        <span className="w-4 h-4 rounded bg-blue-400" />
        <span className="w-4 h-4 rounded bg-blue-600" />
        <span>Most</span>
      </div>
    </div>
  );
}

function KpiCard({ label, value, sub, color: c }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-2xl font-bold mt-1" style={{ color: c }}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function DashboardInner() {
  const searchParams = useSearchParams();
  const [sermons, setSermons] = useState<SermonData[]>([]);
  const [details, setDetails] = useState<Record<string, SermonData>>({});
  const [pastorFilter, setPastorFilter] = useState(searchParams.get("pastor") || "Mike Scheer");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(apiUrl("/api/sermons"))
      .then((r) => r.json())
      .then((data) => {
        setSermons(data.filter((s: SermonData) => s.status === "complete"));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const pastors = [...new Set(sermons.map((s) => s.pastor).filter(Boolean))] as string[];
  const filtered = pastorFilter === "all" ? sermons : sermons.filter((s) => s.pastor === pastorFilter);
  const recent = [...filtered].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3);

  // Load details for recent sermons + all filtered for heatmap
  useEffect(() => {
    const toLoad = [...new Set([...recent, ...filtered])];
    toLoad.forEach((s) => {
      if (!details[s.id]) {
        fetch(apiUrl(`/api/sermons/${s.id}`))
          .then((r) => r.json())
          .then((d) => setDetails((prev) => ({ ...prev, [s.id]: d })))
          .catch(() => {});
      }
    });
  }, [recent.map((s) => s.id).join(","), filtered.map((s) => s.id).join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  // KPIs
  const avgPsr = filtered.length ? filtered.reduce((s, x) => s + psr(x), 0) / filtered.length : 0;
  const bestSermon = filtered.length ? filtered.reduce((a, b) => psr(a) > psr(b) ? a : b) : null;
  const trend = recent.length >= 2 ? psr(recent[0]) - psr(recent[1]) : 0;

  // Category averages from loaded details
  const detailedRecent = recent.filter((s) => details[s.id]?.categories);
  const catAvgs: Record<string, number> = {};
  if (detailedRecent.length) {
    for (const key of CATEGORY_ORDER) {
      const scores = detailedRecent.map((s) => details[s.id]?.categories?.[key]?.score ?? 0);
      catAvgs[key] = scores.reduce((a, b) => a + b, 0) / scores.length;
    }
  }

  // Illustration counts from Pass 4 enrichment (LLM-classified)
  const illustrationCounts = { "Personal Story": 0, "Historical": 0, "Hypothetical": 0, "Humor": 0 };
  let hasEnrichmentIllustrations = false;
  for (const s of detailedRecent) {
    const d = details[s.id] as unknown as { enrichment?: { illustrations?: { byType?: Record<string, unknown[]> } } };
    const byType = d?.enrichment?.illustrations?.byType;
    if (!byType) continue;
    hasEnrichmentIllustrations = true;
    illustrationCounts["Personal Story"] += (byType.personalStory || []).length;
    illustrationCounts["Historical"] += (byType.historical || []).length;
    illustrationCounts["Hypothetical"] += (byType.hypothetical || []).length;
    illustrationCounts["Humor"] += (byType.humor || []).length;
  }
  const illustrationColors: Record<string, string> = { "Personal Story": "#3b82f6", "Historical": "#8b5cf6", "Hypothetical": "#f59e0b", "Humor": "#22c55e" };
  const hasIllustrations = hasEnrichmentIllustrations && Object.values(illustrationCounts).some((v) => v > 0);

  if (loading) return <p className="text-gray-400 text-sm text-center mt-20">Loading...</p>;

  return (
    <div className="max-w-[1100px] mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-gray-900">PSR Dashboard</h1>
          <p className="text-xs text-gray-500">Pastor performance overview</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={pastorFilter}
            onChange={(e) => setPastorFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded px-3 py-1.5 bg-white"
            aria-label="Filter by pastor"
          >
            <option value="all">All Pastors</option>
            {pastors.sort().map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <Link href="/sermons" className="text-sm text-blue-600 hover:underline">Sermons →</Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <KpiCard label="Total Sermons" value={String(filtered.length)} />
        <KpiCard label="Avg PSR" value={avgPsr.toFixed(1)} color={color(avgPsr)} />
        <KpiCard label="Best Score" value={bestSermon ? psr(bestSermon).toFixed(1) : "—"} sub={bestSermon?.title} color={bestSermon ? color(psr(bestSermon)) : undefined} />
        <KpiCard label="Trend" value={trend > 0 ? `+${trend.toFixed(1)}` : trend.toFixed(1)} sub="vs previous" color={trend > 0 ? "#22c55e" : trend < 0 ? "#ef4444" : "#9ca3af"} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          {hasIllustrations ? (
            <PieChart
              label="Illustration Tracker (Last 3)"
              data={Object.entries(illustrationCounts).filter(([, v]) => v > 0).map(([name, value]) => ({ name, value, color: illustrationColors[name] || "#9ca3af" }))}
            />
          ) : (
            <p className="text-xs text-gray-400 p-4">{hasEnrichmentIllustrations ? "No illustrations detected" : "Rescore sermons to enable illustration tracking"}</p>
          )}
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <BarChart
            label="Score Trend (Last 6)"
            data={[...filtered].sort((a, b) => a.date.localeCompare(b.date)).slice(-6).map((s) => ({ name: s.title, value: psr(s), id: s.id }))}
          />
        </div>
      </div>

      {/* Category Averages — full width */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        {Object.keys(catAvgs).length > 0 ? (
          <HBarChart
            label="Category Averages (Last 3)"
            data={CATEGORY_ORDER.map((k) => ({ name: CATEGORY_LABELS[k], value: catAvgs[k] || 0 }))}
          />
        ) : (
          <p className="text-xs text-gray-400">Loading category data...</p>
        )}
      </div>

      {/* Scripture Heatmap */}
      {(() => {
        const transcripts = filtered
          .filter((s) => (details[s.id] as unknown as { transcript?: { fullText?: string } })?.transcript?.fullText)
          .map((s) => (details[s.id] as unknown as { transcript?: { fullText?: string } }).transcript!.fullText!);
        const bookCounts = transcripts.length > 0 ? extractBookCounts(transcripts) : {};
        return transcripts.length > 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <ScriptureHeatmap counts={bookCounts} />
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <p className="text-xs text-gray-400">Loading scripture data...</p>
          </div>
        );
      })()}

      {/* Recent Sermons Detail Cards */}
      <h2 className="text-sm font-bold text-gray-700 mb-3">Recent Sermons</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {recent.map((s) => {
          const d = details[s.id];
          return (
            <Link key={s.id} href={`/sermons/${s.id}`} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-900 truncate">{s.title}</span>
                <span className="text-lg font-bold ml-2" style={{ color: color(psr(s)) }}>{psr(s).toFixed(1)}</span>
              </div>
              {s.pastor && <p className="text-xs text-gray-500 mb-2">{s.pastor} · {s.date}</p>}
              {d?.improvements && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-gray-600 mb-1">Areas to Improve:</p>
                  <ul className="space-y-1">
                    {d.improvements.map((imp, i) => (
                      <li key={i} className="text-xs text-gray-500 flex gap-1">
                        <span className="text-orange-400">→</span>
                        <span>{imp}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {d?.strengths && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-gray-600 mb-1">Strengths:</p>
                  <ul className="space-y-1">
                    {d.strengths.map((str, i) => (
                      <li key={i} className="text-xs text-gray-500 flex gap-1">
                        <span className="text-green-500">✓</span>
                        <span>{str}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return <Suspense><DashboardInner /></Suspense>;
}
