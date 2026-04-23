"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiUrl, tenantFetch } from "@/lib/api";
import Nav from "@/components/Nav";
import TenantMenu from "@/components/TenantMenu";
import SampleNav from "@/components/SampleNav";
import { resolveTenant } from "@/lib/tenant";
import { CATEGORY_LABELS, CATEGORY_ORDER } from "@/lib/types";

interface SermonData {
  id: string;
  title: string;
  pastor: string | null;
  compositePsr: number | null;
  totalScore?: number;
  date: string;
  duration?: number;
  status: string;
  categories?: Record<string, { score: number; weight: number; reasoning: string }>;
  improvements?: string[];
  strengths?: string[];
  inputType?: string;
}

function psr(s: SermonData) { return s.totalScore ?? s.compositePsr ?? 0; }
function color(score: number) { return score >= 74 ? "#22c55e" : score >= 60 ? "#eab308" : "#ef4444"; }

// ── Simple SVG Charts ──

function BarChart({ data, label, colorFn }: { data: { name: string; value: number; id?: string }[]; label: string; colorFn?: (v: number) => string }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  const cfn = colorFn || color;
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
              <rect x={x} y={h - barH} width={barW} height={barH} fill={cfn(d.value)} rx={3} />
              <text x={x + barW / 2} y={h - barH - 4} textAnchor="middle" className="text-[10px] fill-slate-600 font-bold">{d.value.toFixed(1)}</text>
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
              <text x={p.x} y={p.y - 10} textAnchor="middle" className="text-[9px] fill-slate-600 font-bold">{data[i].value.toFixed(1)}</text>
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
  const [churchBeliefs, setChurchBeliefs] = useState<string[]>([]);
  const [churchInfo, setChurchInfo] = useState<{ name: string; beliefsUrl: string } | null>(null);
  const [cbvResults, setCbvResults] = useState<Record<string, { title: string; referenced: boolean }[]>>({});
  const [transcripts, setTranscripts] = useState<Record<string, string>>({});
  const [isTenant, setIsTenant] = useState(false);

  useEffect(() => { setIsTenant(!!resolveTenant()); }, []);

  useEffect(() => {
    const loadData = (data: SermonData[]) => {
      setSermons(data);
      const detailMap: Record<string, SermonData> = {};
      const cbvMap: Record<string, { title: string; referenced: boolean }[]> = {};
      data.forEach((s: SermonData & { cbv?: { results?: { title: string; referenced: boolean }[] } }) => {
        detailMap[s.id] = s;
        if (s.cbv?.results) cbvMap[s.id] = s.cbv.results;
      });
      setDetails(detailMap);
      setCbvResults(cbvMap);
      setLoading(false);
    };

    tenantFetch(apiUrl("/api/sermons/dashboard"))
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((data: SermonData[]) => loadData(data))
      .catch(() => {
        // Fallback to static sample data on tenant subdomains
        fetch("/sample-dashboard.json")
          .then((r) => r.ok ? r.json() : [])
          .then((data: SermonData[]) => loadData(data))
          .catch(() => setLoading(false));
      });
  }, []);

  const pastors = [...new Set(sermons.map((s) => s.pastor).filter(Boolean))] as string[];
  const filtered = pastorFilter === "all" ? sermons : sermons.filter((s) => s.pastor === pastorFilter);
  const recent = [...filtered].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3);
  const last4 = [...filtered].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4);

  // Fetch church beliefs for the selected pastor
  useEffect(() => {
    if (pastorFilter === "all" || !pastorFilter) { setChurchBeliefs([]); setChurchInfo(null); return; }
    fetch(apiUrl("/api/churches")).then(r => r.json()).then((churches: { name: string; beliefsUrl?: string; beliefs?: ({ title: string } | string)[]; pastors: { name: string }[] }[]) => {
      const match = churches.find(c => c.pastors.some(p => p.name === pastorFilter));
      if (match?.beliefs?.length) {
        setChurchBeliefs(match.beliefs.map(b => typeof b === "string" ? b : b.title));
        setChurchInfo(match.beliefsUrl ? { name: match.name, beliefsUrl: match.beliefsUrl } : null);
      } else {
        setChurchBeliefs([]);
        setChurchInfo(null);
      }
    }).catch(() => { setChurchBeliefs([]); setChurchInfo(null); });
  }, [pastorFilter]);

  // Fetch transcripts for heatmap
  useEffect(() => {
    if (!filtered.length) return;
    const missing = filtered.filter(s => !transcripts[s.id]).slice(0, 10);
    if (!missing.length) return;
    Promise.all(missing.map(s =>
      fetch(apiUrl(`/api/sermons/${s.id}/transcript`)).then(r => r.ok ? r.json() : null).catch(() => null)
    )).then(results => {
      const newT = { ...transcripts };
      missing.forEach((s, i) => {
        const r = results[i];
        if (r?.fullText) newT[s.id] = r.fullText;
      });
      setTranscripts(newT);
    });
  }, [filtered.length, pastorFilter]); // eslint-disable-line react-hooks/exhaustive-deps

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
      <TenantMenu />
      {isTenant && <SampleNav />}
      {!isTenant && <Nav />}
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-gray-900">Dashboard</h1>
          <p className="text-xs text-gray-500">Pastor performance overview</p>
        </div>
        <div className="flex items-center gap-3">
          {isTenant ? (
            <span className="text-sm font-medium text-gray-700">{pastorFilter}</span>
          ) : (
          <select
            value={pastorFilter}
            onChange={(e) => setPastorFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded px-3 py-1.5 bg-white"
            aria-label="Filter by pastor"
          >
            <option value="all">All Pastors</option>
            {pastors.sort().map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <KpiCard label="Total Sermons" value={String(filtered.length)} />
        <KpiCard label="Avg PSR" value={avgPsr.toFixed(1)} color={color(avgPsr)} />
        <KpiCard label="Best Score" value={bestSermon ? psr(bestSermon).toFixed(1) : "—"} sub={bestSermon?.title} color={bestSermon ? color(psr(bestSermon)) : undefined} />
        <KpiCard label="Avg Duration" value={(() => { const w = filtered.filter(s => s.duration); return w.length ? `${Math.round(w.reduce((s, x) => s + (x.duration || 0), 0) / w.length / 60)}m` : "—"; })()} sub="minutes" color="#6366f1" />
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

      {/* Duration & Sermon Type Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <BarChart
            label="Sermon Duration (Last 6)"
            colorFn={() => "#3b82f6"}
            data={[...filtered].filter(s => s.duration).sort((a, b) => a.date.localeCompare(b.date)).slice(-6).map((s) => ({ name: s.title, value: Math.round((s.duration || 0) / 60) }))}
          />
          {(() => {
            const withDuration = filtered.filter(s => s.duration);
            const avg = withDuration.length ? Math.round(withDuration.reduce((sum, s) => sum + (s.duration || 0), 0) / withDuration.length / 60) : 0;
            return avg ? <p className="text-xs text-gray-500 mt-1 text-center">Average: {avg} min</p> : null;
          })()}
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          {(() => {
            const typeCounts: Record<string, number> = {};
            filtered.forEach(s => { const t = (s as unknown as { sermonType?: string }).sermonType || "unknown"; typeCounts[t] = (typeCounts[t] || 0) + 1; });
            const typeColors: Record<string, string> = { expository: "#3b82f6", topical: "#f59e0b", narrative: "#10b981", survey: "#8b5cf6", unknown: "#9ca3af" };
            const data = Object.entries(typeCounts).map(([name, value]) => ({ name, value, color: typeColors[name] || "#9ca3af" }));
            return data.length > 0 ? (
              <PieChart label="Sermon Types" data={data} />
            ) : (
              <p className="text-xs text-gray-400 p-4">No sermon type data</p>
            );
          })()}
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
        const texts = filtered
          .map((s) => transcripts[s.id] || (details[s.id] as unknown as { transcript?: { fullText?: string } })?.transcript?.fullText)
          .filter(Boolean) as string[];
        const bookCounts = texts.length > 0 ? extractBookCounts(texts) : {};
        return texts.length > 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <ScriptureHeatmap counts={bookCounts} />
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <p className="text-xs text-gray-400">Loading scripture heatmap...</p>
          </div>
        );
      })()}

      {/* CBV Missing — Last 4 Sermons */}
      {churchBeliefs.length > 0 && (() => {
        const loadedCbvs = last4.filter(s => cbvResults[s.id]);
        if (!loadedCbvs.length) return null;
        return (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <p className="text-xs font-bold text-gray-600 mb-3">Church Beliefs and Values (CBV) — Last 4 Sermons</p>
            {churchInfo && (
              <p className="text-xs text-blue-600 mb-3 -mt-1"><a href={churchInfo.beliefsUrl} target="_blank" rel="noopener noreferrer" className="hover:underline">{churchInfo.name}</a></p>
            )}
            <ul className="space-y-1.5">
              {churchBeliefs.map((title, i) => {
                const referenced = loadedCbvs.some(s =>
                  cbvResults[s.id]?.find(r => r.title === title)?.referenced
                );
                return (
                  <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                    <span className="shrink-0">{referenced ? "✅" : <span className="text-red-500">✕</span>}</span>
                    <span>{title}</span>
                  </li>
                );
              })}
            </ul>
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
