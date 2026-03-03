import React from "react";
import { TranscriptSegment } from "@/lib/types";

const BORDER_COLORS: Record<string, string> = {
  scripture: "border-l-blue-500",
  teaching: "border-l-gray-300",
  application: "border-l-green-500",
  anecdote: "border-l-orange-400",
  illustration: "border-l-orange-400",
  prayer: "border-l-purple-400",
  transition: "border-l-gray-200",
};

const LEGEND = [
  { label: "Scripture", color: "bg-blue-500" },
  { label: "Teaching", color: "bg-gray-300" },
  { label: "Application", color: "bg-green-500" },
  { label: "Anecdote", color: "bg-orange-400" },
];

// Bold scripture references like "Romans 8:28", "1 John 3:16-18", "Genesis 1:1"
const SCRIPTURE_RE = /\b(\d?\s?[A-Z][a-z]+)\s+(\d{1,3}:\d{1,3}(?:-\d{1,3})?)/g;

function highlightScripture(text: string) {
  const parts = text.split(SCRIPTURE_RE);
  if (parts.length === 1) return text;
  const result: React.ReactNode[] = [];
  // split produces: [before, book, verse, between, book, verse, ...]
  for (let i = 0; i < parts.length; i += 3) {
    if (parts[i]) result.push(parts[i]);
    if (i + 2 < parts.length) {
      result.push(
        <strong key={i} className="text-gray-900">{parts[i + 1]} {parts[i + 2]}</strong>
      );
    }
  }
  return <>{result}</>;
}

export default function TranscriptViewer({ segments }: { segments: TranscriptSegment[] }) {
  return (
    <div>
      <div className="flex gap-4 mb-2 text-xs text-gray-500">
        {LEGEND.map((l) => (
          <span key={l.label} className="flex items-center gap-1">
            <span className={`inline-block w-2 h-2 rounded-full ${l.color}`} />
            {l.label}
          </span>
        ))}
      </div>
      <div className="bg-white border border-gray-200 rounded-lg max-h-[500px] overflow-y-auto">
        {segments.map((seg, i) => (
          <div key={i} className={`border-l-4 ${BORDER_COLORS[seg.type] || "border-l-gray-300"} px-4 py-2 text-sm text-gray-700 leading-relaxed`}>
            {highlightScripture(seg.text)}
          </div>
        ))}
      </div>
    </div>
  );
}
