"use client";

import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";
import { CategoryScore, CATEGORY_LABELS, CATEGORY_ORDER } from "@/lib/types";

export default function RadarView({ categories }: { categories: Record<string, CategoryScore> }) {
  const data = CATEGORY_ORDER.map((key) => ({
    category: CATEGORY_LABELS[key]?.replace("Biblical Accuracy", "Biblical Acc.").replace("Emotional Range", "Emot. Range").replace("Time in the Word", "Time in Word"),
    score: categories[key]?.score ?? 0,
  }));

  return (
    <div className="w-full max-w-[400px] aspect-square">
      <ResponsiveContainer>
        <RadarChart data={data}>
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis dataKey="category" tick={{ fontSize: 11, fill: "#6b7280" }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
          <Tooltip />
          <Radar dataKey="score" stroke="#2563eb" fill="#2563eb" fillOpacity={0.2} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
