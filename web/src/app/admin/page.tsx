"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { apiUrl } from "@/lib/api";
import { scoreColor } from "@/lib/types";

interface SermonItem {
  id: string;
  title: string;
  pastor: string | null;
  compositePsr: number | null;
  bonus?: number;
  totalScore?: number;
  status: string;
}

interface RowData {
  label: string;
  count: number;
  bonus: number;
  max: number;
  countEditable: boolean;
  tooltip?: string;
}

function BonusRow({ row, onChange }: { row: RowData; onChange: (patch: Partial<RowData>) => void }) {
  const total = Math.min(row.max, Math.abs(row.count * row.bonus)) * Math.sign(row.count * row.bonus);
  return (
    <div className="space-y-1">
      {/* Label — visible on mobile, hidden on desktop (shown in header row instead) */}
      <div className="sm:hidden text-xs font-medium text-gray-600">
        {row.label}
        {row.tooltip && (
          <span className="ml-1 cursor-help text-blue-500 font-bold" title={row.tooltip}>*</span>
        )}
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Label — desktop only */}
        <span className="hidden sm:block flex-1 text-sm text-gray-700 truncate min-w-0">
          {row.label}
          {row.tooltip && (
            <span className="ml-1 cursor-help text-blue-500 font-bold" title={row.tooltip}>*</span>
          )}
        </span>
        {/* Count */}
        {row.countEditable ? (
          <input
            type="number"
            value={row.count}
            onChange={(e) => onChange({ count: Math.max(0, parseInt(e.target.value) || 0) })}
            className="w-12 sm:w-16 border border-gray-200 rounded px-1 py-1.5 text-xs sm:text-sm text-center font-bold"
          />
        ) : (
          <span className="w-12 sm:w-16 text-xs sm:text-sm font-bold text-center">{row.count}</span>
        )}
        {/* Slider + value */}
        <input
          type="range"
          min={-row.max}
          max={row.max}
          step={0.5}
          value={row.bonus}
          onChange={(e) => onChange({ bonus: parseFloat(e.target.value) })}
          className="w-16 sm:w-24"
        />
        <span className={`text-xs sm:text-sm font-bold w-8 sm:w-10 text-center ${row.bonus > 0 ? "text-green-600" : row.bonus < 0 ? "text-red-500" : "text-gray-400"}`}>
          {row.bonus > 0 ? "+" : ""}{row.bonus}
        </span>
        {/* Max */}
        <input
          type="number"
          value={row.max}
          onChange={(e) => {
            const m = Math.max(1, parseInt(e.target.value) || 5);
            onChange({ max: m, bonus: Math.max(-m, Math.min(m, row.bonus)) });
          }}
          className="w-10 sm:w-14 border border-gray-200 rounded px-1 py-1.5 text-xs sm:text-sm text-center"
        />
        {/* Total */}
        <span className={`text-xs sm:text-sm font-bold w-10 sm:w-14 text-center ${total > 0 ? "text-green-600" : total < 0 ? "text-red-500" : "text-gray-400"}`}>
          {total !== 0 ? (total > 0 ? "+" : "") + total.toFixed(1) : "—"}
        </span>
      </div>
    </div>
  );
}

export default function AdminPage() {
  return <Suspense><AdminPageInner /></Suspense>;
}

function AdminPageInner() {
  const [adminKey, setAdminKey] = useState("");
  const [sermons, setSermons] = useState<SermonItem[]>([]);
  const [selected, setSelected] = useState<SermonItem | null>(null);
  const [transcript, setTranscript] = useState("");
  const [rows, setRows] = useState([
    { word: "Jesus", count: 0, bonus: 0, max: 5 },
    { word: "", count: 0, bonus: 0, max: 5 },
    { word: "", count: 0, bonus: 0, max: 5 },
  ]);
  const [langRow, setLangRow] = useState<RowData>({ label: "Hebrew / Greek / Aramaic", count: 0, bonus: 0, max: 5, countEditable: false });
  const [histRow, setHistRow] = useState<RowData>({
    label: "Church history",
    count: 0, bonus: 0, max: 5, countEditable: false,
    tooltip: "LLM-detected: historical figures (Augustine, Luther, Calvin, Spurgeon, etc.), events (Reformation, councils), creeds, and era references. Analyzed during scoring pipeline.",
  });
  const [baRow, setBaRow] = useState<RowData>({ label: "Biblical Accuracy", count: 0, bonus: 0, max: 5, countEditable: false });
  const [twRow, setTwRow] = useState<RowData>({ label: "Time in the Word", count: 0, bonus: 0, max: 5, countEditable: false });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const capTotal = (count: number, bonus: number, max: number) => Math.min(max, Math.abs(count * bonus)) * Math.sign(count * bonus);
  const totalBonus =
    rows.reduce((s, r) => s + capTotal(r.count, r.bonus, r.max), 0) +
    capTotal(langRow.count, langRow.bonus, langRow.max) +
    capTotal(histRow.count, histRow.bonus, histRow.max) +
    capTotal(1, baRow.bonus, baRow.max) +
    capTotal(1, twRow.bonus, twRow.max);

  const searchParams = useSearchParams();

  useEffect(() => {
    fetch(apiUrl("/api/sermons"))
      .then((r) => r.json())
      .then((data) => {
        const complete = data.filter((s: SermonItem) => s.status === "complete");
        setSermons(complete);
        const preselect = searchParams.get("sermon");
        if (preselect) {
          const match = complete.find((s: SermonItem) => s.id === preselect);
          if (match) selectSermon(match);
        }
      })
      .catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Count word occurrences
  useEffect(() => {
    setRows((prev) => prev.map((r) => {
      if (!transcript || !r.word.trim()) return { ...r, count: 0 };
      const regex = new RegExp(`\\b${r.word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "gi");
      return { ...r, count: (transcript.match(regex) || []).length };
    }));
  }, [rows.map((r) => r.word).join("|"), transcript]); // eslint-disable-line react-hooks/exhaustive-deps

  // Biblical language + church history counts come from API enrichment data (pass4)
  // No client-side regex needed

  function updateRow(i: number, patch: Partial<typeof rows[0]>) {
    setRows((prev) => prev.map((r, j) => j === i ? { ...r, ...patch } : r));
  }

  async function selectSermon(s: SermonItem) {
    setSelected(s);
    setMessage("");
    // Reset to defaults first
    setRows([{ word: "Jesus", count: 0, bonus: 0, max: 5 }, { word: "", count: 0, bonus: 0, max: 5 }, { word: "", count: 0, bonus: 0, max: 5 }]);
    setLangRow((p) => ({ ...p, bonus: 0, max: 5, count: 0 }));
    setHistRow((p) => ({ ...p, bonus: 0, max: 5, count: 0, tooltip: "LLM-detected: historical figures (Augustine, Luther, Calvin, Spurgeon, etc.), events (Reformation, councils), creeds, and era references. Analyzed during scoring pipeline." }));
    setBaRow((p) => ({ ...p, bonus: 0, max: 5, count: 0 }));
    setTwRow((p) => ({ ...p, bonus: 0, max: 5, count: 0 }));
    try {
      const r = await fetch(apiUrl(`/api/sermons/${s.id}`));
      const detail = await r.json();
      setTranscript(detail.transcript?.fullText || "");
      setBaRow((p) => ({ ...p, count: detail.categories?.biblicalAccuracy?.score ?? 0 }));
      setTwRow((p) => ({ ...p, count: detail.categories?.timeInTheWord?.score ?? 0 }));

      // Load enrichment data from pass4 (LLM-computed)
      const enrichment = detail.enrichment;
      setLangRow((p) => ({ ...p, count: enrichment?.biblicalLanguages?.count ?? 0 }));
      setHistRow((p) => ({ ...p, count: enrichment?.churchHistory?.count ?? 0 }));

      // Build tooltip from church history references if available
      const histRefs = enrichment?.churchHistory?.references;
      if (histRefs && histRefs.length > 0) {
        const refList = histRefs.map((r: { figure_or_event: string; era?: string }) =>
          r.era ? `${r.figure_or_event} (${r.era})` : r.figure_or_event
        ).join(", ");
        setHistRow((p) => ({ ...p, tooltip: `LLM-detected: ${refList}` }));
      }

      // Restore saved bonus row settings
      const saved = detail.bonusRows;
      if (saved) {
        if (saved.words) {
          setRows(saved.words.map((w: { word: string; count: number; bonus: number; max: number }) => ({
            word: w.word || "", count: w.count || 0, bonus: w.bonus || 0, max: w.max || 5,
          })));
        }
        if (saved.lang) setLangRow((p) => ({ ...p, bonus: saved.lang.bonus || 0, max: saved.lang.max || 5 }));
        if (saved.hist) setHistRow((p) => ({ ...p, bonus: saved.hist.bonus || 0, max: saved.hist.max || 5 }));
        if (saved.ba) setBaRow((p) => ({ ...p, bonus: saved.ba.bonus || 0, max: saved.ba.max || 5 }));
        if (saved.tw) setTwRow((p) => ({ ...p, bonus: saved.tw.bonus || 0, max: saved.tw.max || 5 }));
      }
    } catch {
      setTranscript("");
    }
  }

  async function applyBonus() {
    if (!selected || !adminKey) return;
    setSaving(true);
    setMessage("");
    try {
      const r = await fetch(apiUrl(`/api/sermons/${selected.id}/bonus`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "x-admin-key": adminKey },
        body: JSON.stringify({
          bonus: Math.round(totalBonus * 10) / 10,
          bonusRows: {
            words: rows.map((r) => ({ word: r.word, count: r.count, bonus: r.bonus, max: r.max })),
            lang: { count: langRow.count, bonus: langRow.bonus, max: langRow.max },
            hist: { count: histRow.count, bonus: histRow.bonus, max: histRow.max },
            ba: { bonus: baRow.bonus, max: baRow.max },
            tw: { bonus: twRow.bonus, max: twRow.max },
          },
        }),
      });
      const data = await r.json();
      if (!r.ok) { setMessage(`Error: ${data.error}`); return; }
      setMessage(`Applied! PSR ${data.compositePsr} + Bonus ${data.bonus > 0 ? "+" : ""}${data.bonus} = Total ${data.totalScore}`);
      setSermons((prev) => prev.map((s) => s.id === selected.id ? { ...s, bonus: data.bonus, totalScore: data.totalScore } : s));
      setSelected((prev) => prev ? { ...prev, bonus: data.bonus, totalScore: data.totalScore } : prev);
    } catch {
      setMessage("Failed to apply bonus.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-[820px] mx-auto px-3 sm:px-4 py-6 sm:py-8">
      <div className="flex items-center justify-between mb-4 sm:mb-6">
        <h1 className="text-base sm:text-lg font-semibold text-gray-900">Bonus Points</h1>
        <Link href="/admin/manage" className="text-sm text-blue-600 hover:underline">Manage</Link>
      </div>

      <input
        type="password"
        placeholder="Admin key"
        value={adminKey}
        onChange={(e) => setAdminKey(e.target.value)}
        className="w-full border border-gray-200 rounded px-3 py-2 text-sm mb-4 sm:mb-6"
      />

      <select
        value={selected?.id || ""}
        onChange={(e) => { const s = sermons.find((x) => x.id === e.target.value); if (s) selectSermon(s); }}
        className="w-full border border-gray-200 rounded px-3 py-2 text-sm mb-4 sm:mb-6"
        aria-label="Select sermon"
      >
        <option value="">Select a sermon...</option>
        {sermons.map((s) => (
          <option key={s.id} value={s.id}>
            {s.title} {s.pastor ? `— ${s.pastor}` : ""} {s.compositePsr != null ? `(${s.compositePsr})` : ""}
          </option>
        ))}
      </select>

      {selected && (
        <div className="space-y-4 sm:space-y-6">
          {/* Score summary */}
          <div className="flex items-center justify-center gap-3 sm:gap-4 text-center">
            <div>
              <span className={`text-2xl sm:text-3xl font-bold ${selected.compositePsr != null ? scoreColor(selected.compositePsr) : "text-gray-400"}`}>
                {selected.compositePsr?.toFixed(1) ?? "—"}
              </span>
              <p className="text-xs text-gray-500 mt-1">PSR</p>
            </div>
            <span className="text-gray-300 text-lg sm:text-xl">+</span>
            <div>
              <span className={`text-2xl sm:text-3xl font-bold ${(selected.bonus ?? 0) > 0 ? "text-green-600" : (selected.bonus ?? 0) < 0 ? "text-red-500" : "text-gray-400"}`}>
                {selected.bonus != null ? (selected.bonus > 0 ? "+" : "") + selected.bonus.toFixed(1) : "0"}
              </span>
              <p className="text-xs text-gray-500 mt-1">Bonus</p>
            </div>
            <span className="text-gray-300 text-lg sm:text-xl">=</span>
            <div>
              <span className={`text-2xl sm:text-3xl font-bold ${selected.totalScore != null ? scoreColor(selected.totalScore) : "text-gray-400"}`}>
                {selected.totalScore?.toFixed(1) ?? selected.compositePsr?.toFixed(1) ?? "—"}
              </span>
              <p className="text-xs text-gray-500 mt-1">Total</p>
            </div>
          </div>

          {/* Bonus rows */}
          <div className="bg-gray-50 rounded-lg p-3 sm:p-4 space-y-2 w-full">
            {/* Header — desktop only */}
            <div className="hidden sm:flex items-center gap-3 text-xs font-bold text-gray-700">
              <span className="flex-1">Word</span>
              <span className="w-16 text-center">Count</span>
              <span className="w-[calc(24px+2.5rem+1.5rem)] text-center">Bonus</span>
              <span className="w-14 text-center">Max</span>
              <span className="w-14 text-center">Total</span>
            </div>

            {/* Word search rows */}
            {rows.map((row, i) => {
              const rowTotal = Math.min(row.max, Math.abs(row.count * row.bonus)) * Math.sign(row.count * row.bonus);
              return (
                <div key={i} className="space-y-1">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <input
                      type="text"
                      value={row.word}
                      onChange={(e) => updateRow(i, { word: e.target.value })}
                      placeholder="Word..."
                      className="flex-1 min-w-0 border border-gray-200 rounded px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm"
                    />
                    <input
                      type="number"
                      value={row.count}
                      onChange={(e) => updateRow(i, { count: Math.max(0, parseInt(e.target.value) || 0) })}
                      className="w-12 sm:w-16 border border-gray-200 rounded px-1 py-1.5 text-xs sm:text-sm text-center font-bold"
                    />
                    <input
                      type="range"
                      min={-row.max}
                      max={row.max}
                      step={0.5}
                      value={row.bonus}
                      onChange={(e) => updateRow(i, { bonus: parseFloat(e.target.value) })}
                      className="w-16 sm:w-24"
                    />
                    <span className={`text-xs sm:text-sm font-bold w-8 sm:w-10 text-center ${row.bonus > 0 ? "text-green-600" : row.bonus < 0 ? "text-red-500" : "text-gray-400"}`}>
                      {row.bonus > 0 ? "+" : ""}{row.bonus}
                    </span>
                    <input
                      type="number"
                      value={row.max}
                      onChange={(e) => { const m = Math.max(1, parseInt(e.target.value) || 5); updateRow(i, { max: m, bonus: Math.max(-m, Math.min(m, row.bonus)) }); }}
                      className="w-10 sm:w-14 border border-gray-200 rounded px-1 py-1.5 text-xs sm:text-sm text-center"
                    />
                    <span className={`text-xs sm:text-sm font-bold w-10 sm:w-14 text-center ${rowTotal > 0 ? "text-green-600" : rowTotal < 0 ? "text-red-500" : "text-gray-400"}`}>
                      {rowTotal !== 0 ? (rowTotal > 0 ? "+" : "") + rowTotal.toFixed(1) : "—"}
                    </span>
                  </div>
                </div>
              );
            })}

            {/* Special rows */}
            <div className="border-t border-gray-200 pt-2 space-y-2">
              <BonusRow row={langRow} onChange={(p) => setLangRow((prev) => ({ ...prev, ...p }))} />
              <BonusRow row={histRow} onChange={(p) => setHistRow((prev) => ({ ...prev, ...p }))} />
              <BonusRow row={baRow} onChange={(p) => setBaRow((prev) => ({ ...prev, ...p }))} />
              <BonusRow row={twRow} onChange={(p) => setTwRow((prev) => ({ ...prev, ...p }))} />
            </div>

            {/* Summary */}
            <div className="flex items-center gap-2 sm:gap-3 border-t-2 border-gray-300 pt-2">
              <span className="flex-1 text-xs sm:text-sm font-bold text-gray-900">Total Bonus</span>
              <span className="w-12 sm:w-16" />
              <span className="w-16 sm:w-24" />
              <span className="w-8 sm:w-10" />
              <span className="w-10 sm:w-14" />
              <span className={`text-xs sm:text-sm font-bold w-10 sm:w-14 text-center ${totalBonus > 0 ? "text-green-600" : totalBonus < 0 ? "text-red-500" : "text-gray-400"}`}>
                {totalBonus !== 0 ? (totalBonus > 0 ? "+" : "") + totalBonus.toFixed(1) : "—"}
              </span>
            </div>
          </div>

          <button
            onClick={applyBonus}
            disabled={saving || !adminKey || totalBonus === 0}
            className="w-full bg-blue-600 text-white rounded-lg py-3 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Applying..." : "Apply"}
          </button>

          {message && (
            <p className={`text-sm text-center ${message.startsWith("Error") ? "text-red-500" : "text-green-600"}`}>
              {message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
