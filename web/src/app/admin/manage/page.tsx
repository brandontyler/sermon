"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiUrl, adminFetch } from "@/lib/api";
import { SermonSummary, scoreColor } from "@/lib/types";

export default function AdminManagePage() {
  const [sermons, setSermons] = useState<SermonSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ title: "", pastor: "", date: "", sermonType: "" });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);

  useEffect(() => {
    adminFetch("/api/sermons")
      .then((r) => r.json())
      .then((data) => { setSermons(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  function startEdit(s: SermonSummary) {
    setEditing(s.id);
    setEditForm({ title: s.title || "", pastor: s.pastor || "", date: s.date || "", sermonType: s.sermonType || "" });
    setMessage(null);
  }

  async function saveEdit(id: string) {
    setSaving(true);
    try {
      const r = await adminFetch(`/api/sermons/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editForm),
      });
      const data = await r.json();
      if (!r.ok) { setMessage({ text: data.error, error: true }); return; }
      setSermons((prev) => prev.map((s) => s.id === id ? { ...s, ...data } : s));
      setEditing(null);
      setMessage({ text: "Saved", error: false });
    } catch {
      setMessage({ text: "Failed to save", error: true });
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete(id: string) {
    setDeleting(id);
    try {
      const r = await adminFetch(`/api/sermons/${id}`, {
        method: "DELETE",
      });
      const data = await r.json();
      if (!r.ok) { setMessage({ text: data.error, error: true }); return; }
      setSermons((prev) => prev.filter((s) => s.id !== id));
      setMessage({ text: "Deleted", error: false });
    } catch {
      setMessage({ text: "Failed to delete", error: true });
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="max-w-[960px] mx-auto px-3 sm:px-4 py-6 sm:py-8">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-base sm:text-lg font-semibold text-gray-900">Admin — Manage Sermons</h1>
        <div className="flex gap-3 text-sm">
          <Link href="/admin" className="text-blue-600 hover:underline">Bonus</Link>
          <Link href="/admin/feeds" className="text-blue-600 hover:underline">Feeds</Link>
          <Link href="/sermons" className="text-blue-600 hover:underline">← Sermons</Link>
          <a href="/.auth/logout?post_logout_redirect_uri=/" className="text-gray-400 hover:text-gray-600 hover:underline">Sign out</a>
        </div>
      </div>

      {message && (
        <p className={`text-sm mb-3 ${message.error ? "text-red-500" : "text-green-600"}`}>{message.text}</p>
      )}

      {loading ? (
        <p className="text-gray-400 text-sm">Loading...</p>
      ) : sermons.length === 0 ? (
        <p className="text-gray-400 text-sm">No sermons.</p>
      ) : (
        <div className="space-y-2">
          {sermons.map((s) => (
            <div key={s.id} className="border border-gray-200 rounded-lg p-3">
              {editing === s.id ? (
                <div className="space-y-2">
                  <input value={editForm.title} onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))} placeholder="Title" className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm" />
                  <div className="flex gap-2">
                    <input value={editForm.pastor} onChange={(e) => setEditForm((f) => ({ ...f, pastor: e.target.value }))} placeholder="Pastor" className="flex-1 border border-gray-200 rounded px-2 py-1.5 text-sm" />
                    <input type="date" value={editForm.date} onChange={(e) => setEditForm((f) => ({ ...f, date: e.target.value }))} className="border border-gray-200 rounded px-2 py-1.5 text-sm" />
                    <select value={editForm.sermonType} onChange={(e) => setEditForm((f) => ({ ...f, sermonType: e.target.value }))} className="border border-gray-200 rounded px-2 py-1.5 text-sm">
                      <option value="">Type...</option>
                      <option value="expository">Expository</option>
                      <option value="topical">Topical</option>
                      <option value="survey">Survey</option>
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => saveEdit(s.id)} disabled={saving} className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
                      {saving ? "Saving..." : "Save"}
                    </button>
                    <button onClick={() => setEditing(null)} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200">Cancel</button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <span className={`text-lg font-bold w-12 text-center ${s.compositePsr != null ? scoreColor(s.totalScore ?? s.compositePsr!) : "text-gray-300"}`}>
                    {s.compositePsr != null ? (s.totalScore ?? s.compositePsr).toFixed(1) : "—"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 truncate">{s.title}</div>
                    <div className="text-xs text-gray-500">{s.pastor || "Unknown"} · {s.date} · {s.sermonType || "unclassified"} · {s.status}</div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button onClick={() => startEdit(s)} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200">Edit</button>
                    {deleting === s.id ? (
                      <div className="flex gap-1">
                        <button onClick={() => confirmDelete(s.id)} className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700">Confirm</button>
                        <button onClick={() => setDeleting(null)} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200">Cancel</button>
                      </div>
                    ) : (
                      <button onClick={() => setDeleting(s.id)} className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100">Delete</button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
