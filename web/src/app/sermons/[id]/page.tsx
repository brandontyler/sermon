import SermonDetailClient from "@/components/SermonDetail";

// Static export requires at least one param. SWA navigationFallback
// handles routing for actual sermon UUIDs via client-side navigation.
export async function generateStaticParams() {
  return [{ id: "placeholder" }];
}

export default function SermonDetailPage() {
  return <SermonDetailClient />;
}
