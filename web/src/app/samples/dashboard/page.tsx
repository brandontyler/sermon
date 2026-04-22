"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SampleDashboardPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dashboard?pastor=Tom+Nelson");
  }, [router]);
  return <p className="text-center text-gray-500 mt-12">Loading dashboard...</p>;
}
