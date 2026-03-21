"use client";

import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";
import { CategoryScore, CATEGORY_LABELS, CATEGORY_ORDER } from "@/lib/types";

const SHORT_LABELS: Record<string, string> = {
  "Biblical Accuracy": "Biblical\nAccuracy",
  "Time in the Word": "Time in\nWord",
  "Passage Focus": "Passage\nFocus",
  "Emotional Range": "Emotional\nRange",
  Clarity: "Clarity",
  Engagement: "Engagement",
  Application: "Application",
  Delivery: "Delivery",
};

function WrappedTick({ x, y, payload }: { x: number; y: number; payload: { value: string } }) {
  const lines = (SHORT_LABELS[payload.value] ?? payload.value).split("\n");
  return (
    <text x={x} y={y} textAnchor="middle" dominantBaseline="central" fontSize={11} fill="#94a3b8">
      {lines.map((line, i) => (
        <tspan key={i} x={x} dy={i === 0 ? -(lines.length - 1) * 6 : 14}>
          {line}
        </tspan>
      ))}
    </text>
  );
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { category: string; score: number } }> }) {
  if (!active || !payload?.length) return null;
  const { category, score } = payload[0].payload;
  return (
    <div className="bg-gray-900 text-white text-xs px-3 py-2 rounded-lg shadow-lg">
      <p className="font-medium">{category}</p>
      <p className="text-blue-300 font-bold text-sm">{score}/100</p>
    </div>
  );
}

export default function RadarView({ categories }: { categories: Record<string, CategoryScore> }) {
  const data = CATEGORY_ORDER.map((key) => ({
    category: CATEGORY_LABELS[key],
    score: categories[key]?.score ?? 0,
  }));

  return (
    <div className="w-full max-w-[480px] aspect-square">
      <ResponsiveContainer>
        <RadarChart cx="50%" cy="50%" outerRadius="65%" data={data}>
          <PolarGrid stroke="rgba(255,255,255,0.15)" />
          <PolarAngleAxis dataKey="category" tick={WrappedTick as any} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9, fill: "#64748b" }} tickCount={5} />
          <Tooltip content={<CustomTooltip />} />
          <Radar dataKey="score" stroke="#2563eb" fill="#2563eb" fillOpacity={0.2} strokeWidth={2} dot={{ r: 3, fill: "#2563eb" }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
