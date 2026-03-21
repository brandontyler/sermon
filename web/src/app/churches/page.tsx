"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { apiUrl } from "@/lib/api";
import { scoreColor, normalizeUrl } from "@/lib/types";

const MapView = dynamic(() => import("./MapView"), { ssr: false });

interface Pastor {
  name: string;
  role?: string;
  primary?: boolean;
  sermonCount?: number;
  avgScore?: number | null;
}

interface Church {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  lat: number;
  lng: number;
  url?: string;
  pastors: Pastor[];
}

export default function ChurchesPage() {
  const [churches, setChurches] = useState<Church[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedState, setSelectedState] = useState("all");
  const [selectedCity, setSelectedCity] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch(apiUrl("/api/churches"))
      .then((r) => r.json())
      .then((d) => { setChurches(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const states = useMemo(() => [...new Set(churches.map((c) => c.state))].sort(), [churches]);
  const cities = useMemo(() => {
    const filtered = selectedState === "all" ? churches : churches.filter((c) => c.state === selectedState);
    return [...new Set(filtered.map((c) => c.city))].sort();
  }, [churches, selectedState]);

  const filtered = useMemo(() => {
    let result = churches;
    if (selectedState !== "all") result = result.filter((c) => c.state === selectedState);
    if (selectedCity !== "all") result = result.filter((c) => c.city === selectedCity);
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.city.toLowerCase().includes(q) ||
          c.pastors.some((p) => p.name.toLowerCase().includes(q))
      );
    }
    return result;
  }, [churches, selectedState, selectedCity, search]);

  return (
    <div className="max-w-[1200px] mx-auto p-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-gray-900">Find a Church</h1>
        <div className="flex gap-3 text-sm">
          <Link href="/" className="text-blue-600 hover:underline">Home</Link>
          <Link href="/church-admin" className="text-blue-600 hover:underline">Admin</Link>
          <Link href="/sermons" className="text-blue-600 hover:underline">Sermons</Link>
          <Link href="/upload" className="text-blue-600 hover:underline">Upload</Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="text"
          placeholder="Search church, city, or pastor..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="text-sm border border-gray-200 rounded px-3 py-1.5 bg-white w-64"
        />
        <select
          value={selectedState}
          onChange={(e) => { setSelectedState(e.target.value); setSelectedCity("all"); }}
          className="text-sm border border-gray-200 rounded px-2 py-1.5 bg-white"
        >
          <option value="all">All States</option>
          {states.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          value={selectedCity}
          onChange={(e) => setSelectedCity(e.target.value)}
          className="text-sm border border-gray-200 rounded px-2 py-1.5 bg-white"
        >
          <option value="all">All Cities</option>
          {cities.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading churches...</p>
      ) : (
        <>
          {/* Map */}
          <div className="rounded-lg overflow-hidden border border-gray-200 mb-6" style={{ height: 400 }}>
            <MapView churches={filtered.filter((c) => c.lat != null && c.lng != null)} />
          </div>

          {/* Stats */}
          <div className="flex gap-4 mb-6 text-sm text-gray-500">
            <span>{filtered.length} church{filtered.length !== 1 ? "es" : ""}</span>
            <span>{filtered.reduce((n, c) => n + c.pastors.length, 0)} pastors</span>
          </div>

          {/* Church cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filtered.map((church) => (
              <div key={church.id} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 text-sm">
                    {church.url ? <a href={normalizeUrl(church.url)} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{church.name}</a> : church.name}
                  </h3>
                  {(() => {
                    const primary = church.pastors.find((p: Pastor) => p.primary) || church.pastors[0];
                    return primary?.avgScore != null ? (
                      <span className={`text-lg font-bold ${scoreColor(primary.avgScore)}`}>{primary.avgScore.toFixed(1)}</span>
                    ) : null;
                  })()}
                </div>
                <p className="text-xs text-gray-500 mt-1">{church.address}</p>
                <p className="text-xs text-gray-400">{church.city}, {church.state}</p>
                <div className="mt-3 border-t border-gray-100 pt-3">
                  {church.pastors.map((p) => (
                    <div key={p.name} className="flex items-center justify-between py-1">
                      <div>
                        <Link
                          href={`/dashboard?pastor=${encodeURIComponent(p.name)}`}
                          className="text-sm text-blue-600 hover:underline"
                        >
                          {p.name}
                        </Link>
                        {p.role && <span className="text-xs text-gray-400 ml-1">· {p.role}</span>}
                      </div>
                      <div className="text-right text-xs">
                        {p.sermonCount ? (
                          <>
                            <span className={`font-bold ${scoreColor(p.avgScore ?? 0)}`}>
                              {p.avgScore?.toFixed(1)}
                            </span>
                            <span className="text-gray-400 ml-1">({p.sermonCount})</span>
                          </>
                        ) : (
                          <span className="text-gray-300">No sermons</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {filtered.length === 0 && (
            <p className="text-gray-400 text-sm text-center py-8">No churches found matching your search.</p>
          )}
        </>
      )}
    </div>
  );
}
