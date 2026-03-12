"use client";

import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix default marker icons in Next.js
const icon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

interface Pastor { name: string; role?: string; sermonCount?: number; avgScore?: number | null; }
interface Church { id: string; name: string; address: string; city: string; state: string; lat: number; lng: number; url?: string; pastors: Pastor[]; }

export default function MapView({ churches }: { churches: Church[] }) {
  const center: [number, number] = churches.length === 1
    ? [churches[0].lat, churches[0].lng]
    : churches.length > 1
    ? [churches[0].lat, churches[0].lng]
    : [37.5, -96];
  const zoom = churches.length === 1 ? 12 : 4;

  return (
    <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom={true}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {churches.map((c) => (
        <Marker key={c.id} position={[c.lat, c.lng]} icon={icon}>
          <Popup>
            {c.url ? <a href={c.url.replace(/^(?!https?:\/\/)/i, 'https://')} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600 }}>{c.name}</a> : <strong>{c.name}</strong>}<br />
            <span style={{ fontSize: 12, color: "#666" }}>{c.city}, {c.state}</span><br />
            {c.pastors.map((p) => (
              <div key={p.name} style={{ fontSize: 12 }}>
                {p.name}{p.avgScore ? ` — ${p.avgScore.toFixed(1)} PSR` : ""}
              </div>
            ))}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
