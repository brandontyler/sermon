"use client";

import { useEffect, useState } from "react";
import TenantMenu from "@/components/TenantMenu";
import SampleNav from "@/components/SampleNav";
import SermonDetailClient from "@/components/SermonDetail";
import { SermonDetail } from "@/lib/types";

const SAMPLE_ID = "cb2845b3-396e-408f-81da-5fa1f5e17a0e";

export default function SamplesPage() {
  const [data, setData] = useState<SermonDetail | null>(null);

  useEffect(() => {
    fetch("/sample-sermon.json")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen">
      <div className="max-w-[960px] mx-auto px-4 py-8">
        <TenantMenu />
        <SampleNav />
        {data ? (
          <SermonDetailClient sermonId={SAMPLE_ID} sample preloadedData={data} />
        ) : (
          <p className="text-gray-400 text-sm text-center">Loading sample...</p>
        )}
      </div>
    </div>
  );
}
