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

// All 66 books + common abbreviations and variants
const BOOKS = [
  "Genesis","Gen","Exodus","Ex","Exod","Leviticus","Lev","Numbers","Num",
  "Deuteronomy","Deut","Joshua","Josh","Judges","Judg","Ruth",
  "1 Samuel","2 Samuel","1 Sam","2 Sam","1 Kings","2 Kings",
  "1 Chronicles","2 Chronicles","1 Chron","2 Chron",
  "Ezra","Nehemiah","Neh","Esther","Est","Job",
  "Psalms?","Ps","Psa","Proverbs","Prov","Ecclesiastes","Eccl",
  "Song of Solomon","Song of Songs","Song","SoS",
  "Isaiah","Isa","Jeremiah","Jer","Lamentations","Lam",
  "Ezekiel","Ezek","Daniel","Dan","Hosea","Hos","Joel",
  "Amos","Obadiah","Obad","Jonah","Micah","Mic","Nahum","Nah",
  "Habakkuk","Hab","Zephaniah","Zeph","Haggai","Hag",
  "Zechariah","Zech","Malachi","Mal",
  "Matthew","Matt","Mark","Luke","John","Acts",
  "Romans","Rom","1 Corinthians","2 Corinthians","1 Cor","2 Cor",
  "I Corinthians","II Corinthians",
  "Galatians","Gal","Ephesians","Eph","Philippians","Phil",
  "Colossians","Col","1 Thessalonians","2 Thessalonians","1 Thess","2 Thess",
  "1 Timothy","2 Timothy","1 Tim","2 Tim",
  "I Timothy","II Timothy","I John","II John","III John",
  "Titus","Philemon","Phlm","Hebrews","Heb",
  "James","Jas","1 Peter","2 Peter","1 Pet","2 Pet",
  "1 John","2 John","3 John","Jude","Revelation","Rev",
];

// Sort longest first so "Song of Solomon" matches before "Song"
const bookPattern = BOOKS.sort((a, b) => b.length - a.length).join("|");
// Match: book name + chapter:verse (with optional ranges, commas, cross-chapter)
const SCRIPTURE_RE = new RegExp(
  `(?:${bookPattern})\\.?\\s+\\d{1,3}(?::\\d{1,3}(?:\\s*[-–]\\s*\\d{1,3}(?::\\d{1,3})?)?(?:,\\s*\\d{1,3})*)?`,
  "gi"
);

function highlightScripture(text: string) {
  const result: React.ReactNode[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(SCRIPTURE_RE)) {
    const idx = match.index!;
    if (idx > lastIndex) result.push(text.slice(lastIndex, idx));
    result.push(
      <strong key={idx} className="text-gray-900">{match[0]}</strong>
    );
    lastIndex = idx + match[0].length;
  }
  if (lastIndex === 0) return text;
  if (lastIndex < text.length) result.push(text.slice(lastIndex));
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
