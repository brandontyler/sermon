/** Shared types matching the API contract from frontend-spec.md */

export interface SermonSummary {
  id: string;
  title: string;
  pastor: string | null;
  date: string;
  duration: number | null;
  status: "processing" | "complete" | "failed";
  sermonType: string | null;
  compositePsr: number | null;
  inputType?: "audio" | "text" | "youtube";
  bonus?: number;
  totalScore?: number;
}

export interface CategoryScore {
  score: number;
  weight: number;
  reasoning: string;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  type: "scripture" | "teaching" | "application" | "anecdote" | "illustration" | "prayer" | "transition";
}

export interface AudioMetrics {
  pitchMeanHz: number;
  pitchStdHz: number;
  pitchRangeHz: number;
  intensityMeanDb: number;
  intensityRangeDb: number;
  noiseFloorDb: number;
  pauseCount: number;
  meanPauseDuration: number;
}

export interface SermonDetail extends SermonSummary {
  summary: string | null;
  bonus?: number;
  totalScore?: number;
  categories: Record<string, CategoryScore> | null;
  strengths: string[] | null;
  improvements: string[] | null;
  transcript: {
    fullText?: string;
    segments?: TranscriptSegment[];
    wordCount?: number;
  } | null;
  error: string | null;
  failedAt: string | null;
  blobUrl: string | null;
  filename: string | null;
  youtubeUrl?: string | null;
  wpmFlag: boolean;
  audioMetrics: AudioMetrics | null;
  classificationConfidence: number | null;
  normalizationApplied: "full" | "half" | "none" | null;
  aiScore?: 1 | 2 | 3 | null;
  aiReasoning?: string | null;
  sermonSummary?: { overview: string; keyPoints: string[] } | null;
}

export const CATEGORY_WEIGHTS: Record<string, number> = {
  biblicalAccuracy: 25,
  timeInTheWord: 20,
  passageFocus: 10,
  clarity: 10,
  engagement: 10,
  application: 10,
  delivery: 10,
  emotionalRange: 5,
};

export const CATEGORY_LABELS: Record<string, string> = {
  biblicalAccuracy: "Biblical Accuracy",
  timeInTheWord: "Time in the Word",
  passageFocus: "Passage Focus",
  clarity: "Clarity",
  engagement: "Engagement",
  application: "Application",
  delivery: "Delivery",
  emotionalRange: "Emotional Range",
};

/** Display order (by weight descending) */
export const CATEGORY_ORDER = [
  "biblicalAccuracy",
  "timeInTheWord",
  "passageFocus",
  "clarity",
  "engagement",
  "application",
  "delivery",
  "emotionalRange",
];

export function scoreColor(score: number): string {
  if (score >= 74) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  return "text-red-500";
}

export function scoreBgColor(score: number): string {
  if (score >= 74) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  return "bg-red-500";
}

export function normalizeUrl(url: string): string {
  if (!url) return url;
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}
