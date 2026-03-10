"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SermonSummary, scoreColor } from "@/lib/types";
import { apiUrl } from "@/lib/api";

type SortKey = "compositePsr" | "date";

export default function SermonsPage() {
  const router = useRouter();
  const [sermons, setSermons] = useState<SermonSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortKey>("date");
  const [sortAsc, setSortAsc] = useState(false);
  const [typeFilter, setTypeFilter] = useState("all");

  useEffect(() => {
    let active = true;
    async function load(retries = 3) {
      for (let i = 0; i < retries; i++) {
        try {
          const r = await fetch(apiUrl("/api/sermons"));
          if (!active) return;
          if (!r.ok) throw new Error(`Server error (${r.status})`);
          setSermons(await r.json());
          setLoading(false);
          return;
        } catch {
          if (i < retries - 1) await new Promise((r) => setTimeout(r, 2000 * (i + 1)));
        }
      }
      if (active) { setError("Failed to load sermons. Try refreshing."); setLoading(false); }
    }
    load();
    return () => { active = false; };
  }, []);

  function toggleSort(key: SortKey) {
    if (sortBy === key) setSortAsc(!sortAsc);
    else { setSortBy(key); setSortAsc(false); }
  }

  const filtered = sermons.filter(
    (s) => typeFilter === "all" || s.sermonType === typeFilter
  );

  const sorted = [...filtered].sort((a, b) => {
    const dir = sortAsc ? 1 : -1;
    if (sortBy === "compositePsr") return (((a.totalScore ?? a.compositePsr ?? -1) - (b.totalScore ?? b.compositePsr ?? -1)) * dir);
    return a.date.localeCompare(b.date) * dir;
  });

  function formatDuration(sec: number | null) {
    if (!sec) return "—";
    return `${Math.round(sec / 60)} min`;
  }

  function formatDate(d: string) {
    const date = new Date(d + "T00:00:00");
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function formatType(t: string | null) {
    if (!t) return "";
    const map: Record<string, string> = { expository: "Expos.", topical: "Topical", survey: "Survey" };
    return map[t] || t;
  }

  return (
    <div className="max-w-[960px] mx-auto p-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-gray-900">PSR — Pastor Sermon Rating</h1>
        <Link href="/" className="text-sm text-blue-600 hover:underline">Upload →</Link>
      </div>

      <div className="mb-4">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filter by sermon type"
          className="text-sm border border-gray-200 rounded px-2 py-1 bg-white"
        >
          <option value="all">All Types</option>
          <option value="expository">Expository</option>
          <option value="topical">Topical</option>
          <option value="survey">Survey</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading...</p>
      ) : error ? (
        <p className="text-red-500 text-sm">{error}</p>
      ) : sorted.length === 0 ? (
        <p className="text-gray-400 text-sm">No sermons yet. <Link href="/" className="text-blue-600 hover:underline">Upload one.</Link></p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-gray-500">
                <th scope="col" role="columnheader" aria-sort={sortBy === "compositePsr" ? (sortAsc ? "ascending" : "descending") : "none"} tabIndex={0} className="p-3 w-16 cursor-pointer hover:text-gray-900" onClick={() => toggleSort("compositePsr")} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleSort("compositePsr"); } }}>
                  PSR {sortBy === "compositePsr" ? (sortAsc ? "↑" : "↓") : ""}
                </th>
                <th scope="col" className="p-3">Sermon</th>
                <th scope="col" className="p-3 hidden sm:table-cell">Type</th>
                <th scope="col" className="p-3 hidden sm:table-cell">Source</th>
                <th scope="col" className="p-3 hidden sm:table-cell">Duration</th>
                <th scope="col" role="columnheader" aria-sort={sortBy === "date" ? (sortAsc ? "ascending" : "descending") : "none"} tabIndex={0} className="p-3 cursor-pointer hover:text-gray-900" onClick={() => toggleSort("date")} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleSort("date"); } }}>
                  Date {sortBy === "date" ? (sortAsc ? "↑" : "↓") : ""}
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((s) => (
                <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer" onClick={() => router.push(`/sermons/${s.id}`)}>
                  <td className="p-3">
                    {s.status === "complete" && s.compositePsr != null ? (
                      <span className={`text-lg font-bold ${scoreColor(s.totalScore ?? s.compositePsr)}`}>
                        {(s.totalScore ?? s.compositePsr).toFixed(1)}
                      </span>
                    ) : s.status === "failed" ? (
                      <span className="text-xs text-red-500 font-medium">Failed</span>
                    ) : (
                      <span className="text-gray-400">···</span>
                    )}
                  </td>
                  <td className="p-3">
                    <div className="font-medium text-gray-900">{s.title}</div>
                    {s.pastor && <div className="text-xs text-gray-500"><a href={`/dashboard?pastor=${encodeURIComponent(s.pastor)}`} className="hover:text-blue-600 hover:underline" onClick={(e) => e.stopPropagation()}>{s.pastor}</a></div>}
                  </td>
                  <td className="p-3 hidden sm:table-cell">
                    {s.sermonType && (
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                        {formatType(s.sermonType)}
                      </span>
                    )}
                  </td>
                  <td className="p-3 hidden sm:table-cell">
                    <span className="text-xs text-gray-500">{s.inputType === "youtube" ? "▶️ YouTube" : s.inputType === "text" ? "📄 Text" : "🎙️ Audio"}</span>
                  </td>
                  <td className="p-3 text-gray-500 hidden sm:table-cell">{formatDuration(s.duration)}</td>
                  <td className="p-3 text-gray-500">{formatDate(s.date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
