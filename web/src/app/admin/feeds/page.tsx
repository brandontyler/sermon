"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiUrl, adminFetch } from "@/lib/api";

interface Feed {
  id: string;
  feedUrl: string;
  title: string;
  active: boolean;
  backfillCount: number;
  lastPolledAt: string | null;
  lastPollResult: { new: number; errors: number; timestamp: string } | null;
  episodeCount?: number;
  processingCount?: number;
  createdAt: string;
}

export default function FeedsPage() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);
  const [adding, setAdding] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newBackfill, setNewBackfill] = useState(0);
  const [saving, setSaving] = useState(false);
  const [polling, setPolling] = useState(false);
  const [preview, setPreview] = useState<{ feeds: { feedId: string; title: string; newCount: number }[]; totalNew: number; estimatedCost: number } | null>(null);

  useEffect(() => {
    adminFetch("/api/feeds")
      .then((r) => r.json())
      .then((data) => { setFeeds(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  // Auto-dismiss success messages after 4s
  useEffect(() => {
    if (message && !message.error) {
      const t = setTimeout(() => setMessage(null), 4000);
      return () => clearTimeout(t);
    }
  }, [message]);

  // Auto-refresh every 30s when any feed has processing sermons
  useEffect(() => {
    const hasProcessing = feeds.some((f) => (f.processingCount ?? 0) > 0);
    if (!hasProcessing) return;
    const t = setInterval(() => {
      adminFetch("/api/feeds").then((r) => r.json()).then(setFeeds).catch(() => {});
    }, 30000);
    return () => clearInterval(t);
  }, [feeds]);

  async function addFeed() {
    if (!newUrl.trim()) return;
    setSaving(true);
    try {
      const r = await adminFetch("/api/feeds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedUrl: newUrl, title: newTitle || undefined, backfillCount: newBackfill }),
      });
      const data = await r.json();
      if (!r.ok) { setMessage({ text: data.error, error: true }); return; }
      setFeeds((prev) => [data, ...prev]);
      setAdding(false);
      setNewUrl("");
      setNewTitle("");
      setNewBackfill(0);
      setMessage({ text: `Subscribed to "${data.title}"`, error: false });
    } catch {
      setMessage({ text: "Failed to add feed", error: true });
    } finally {
      setSaving(false);
    }
  }

  async function toggleFeed(feed: Feed) {
    try {
      const r = await adminFetch(`/api/feeds/${feed.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !feed.active }),
      });
      if (r.ok) setFeeds((prev) => prev.map((f) => f.id === feed.id ? { ...f, active: !f.active } : f));
    } catch {}
  }

  async function deleteFeed(id: string) {
    try {
      const r = await adminFetch(`/api/feeds/${id}`, { method: "DELETE" });
      if (r.ok) setFeeds((prev) => prev.filter((f) => f.id !== id));
    } catch {}
  }

  async function pollNow() {
    if (!preview) {
      // Step 1: fetch preview
      setPolling(true);
      try {
        const r = await adminFetch("/api/feeds/preview");
        const data = await r.json();
        if (data.totalNew === 0) {
          setMessage({ text: "No new episodes found", error: false });
        } else {
          setPreview(data);
        }
      } catch {
        setMessage({ text: "Preview failed", error: true });
      } finally {
        setPolling(false);
      }
    } else {
      // Step 2: confirmed — submit poll
      setPolling(true);
      setPreview(null);
      try {
        const r = await adminFetch("/api/feeds/poll", { method: "POST" });
        const data = await r.json();
        const total = data.results?.reduce((s: number, r: { new?: number }) => s + (r.new || 0), 0) || 0;
        setMessage({ text: `Polled ${data.polled} feeds — ${total} new episodes submitted`, error: false });
      } catch {
        setMessage({ text: "Poll failed", error: true });
      } finally {
        setPolling(false);
      }
    }
  }

  return (
    <div className="max-w-[960px] mx-auto px-3 sm:px-4 py-6 sm:py-8">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-base sm:text-lg font-semibold text-gray-900">Admin — RSS Feeds</h1>
        <div className="flex gap-3 text-sm">
          <Link href="/admin" className="text-blue-600 hover:underline">Bonus</Link>
          <Link href="/admin/manage" className="text-blue-600 hover:underline">Manage</Link>
          <Link href="/sermons" className="text-blue-600 hover:underline">← Sermons</Link>
          <a href="/.auth/logout?post_logout_redirect_uri=/" className="text-gray-400 hover:text-gray-600 hover:underline">Sign out</a>
        </div>
      </div>

      {message && (
        <p className={`text-sm mb-3 ${message.error ? "text-red-500" : "text-green-600"}`}>{message.text}</p>
      )}

      <div className="flex gap-2 mb-4">
        <button onClick={() => setAdding(!adding)} className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
          {adding ? "Cancel" : "+ Add Feed"}
        </button>
        <button onClick={pollNow} disabled={polling} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 disabled:opacity-50">
          {polling ? "Checking..." : preview ? "Confirm Submit" : "Poll Now"}
        </button>
        {preview && (
          <button onClick={() => setPreview(null)} className="px-3 py-1.5 text-gray-500 text-sm hover:text-gray-700">
            Cancel
          </button>
        )}
      </div>

      {preview && (
        <div className="border border-amber-200 bg-amber-50 rounded-lg p-3 mb-4 text-sm">
          <p className="font-medium text-amber-800">
            {preview.totalNew} new episode{preview.totalNew !== 1 ? "s" : ""} found (~${preview.estimatedCost.toFixed(2)})
          </p>
          <ul className="mt-1 text-amber-700">
            {preview.feeds.filter((f) => f.newCount > 0).map((f) => (
              <li key={f.feedId}>{f.title}: {f.newCount} new</li>
            ))}
          </ul>
        </div>
      )}

      {adding && (
        <div className="border border-gray-200 rounded-lg p-4 mb-4 space-y-3">
          <input
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            placeholder="RSS feed URL"
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm"
          />
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Title (optional — auto-detected from feed)"
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm"
          />
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600">Backfill last</label>
            <input
              type="number"
              value={newBackfill}
              onChange={(e) => setNewBackfill(Math.max(0, Math.min(50, parseInt(e.target.value) || 0)))}
              className="w-20 border border-gray-200 rounded px-2 py-1.5 text-sm text-center"
            />
            <span className="text-sm text-gray-500">episodes (0 = from now only)</span>
            {newBackfill > 10 && (
              <span className="text-xs text-amber-600">~${(newBackfill * 0.75).toFixed(2)} estimated cost</span>
            )}
          </div>
          <button onClick={addFeed} disabled={saving || !newUrl.trim()} className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Subscribing..." : "Subscribe"}
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-gray-400 text-sm">Loading...</p>
      ) : feeds.length === 0 ? (
        <p className="text-gray-400 text-sm">No feeds subscribed yet.</p>
      ) : (
        <div className="space-y-2">
          {feeds.map((feed) => (
            <div key={feed.id} className="border border-gray-200 rounded-lg p-3 flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full shrink-0 ${feed.active ? "bg-green-500" : "bg-gray-300"}`} />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 truncate">{feed.title}</div>
                <div className="text-xs text-gray-500 truncate">{feed.feedUrl}</div>
                <div className="text-xs text-gray-400 mt-0.5">
                  {feed.episodeCount ?? 0} scored
                  {(feed.processingCount ?? 0) > 0 && <span className="text-amber-600"> · {feed.processingCount} processing</span>}
                  {feed.lastPolledAt && ` · Last polled ${new Date(feed.lastPolledAt).toLocaleDateString()}`}
                </div>
                {feed.lastPollResult && (
                  <div className="text-xs text-gray-400">
                    Last poll: {feed.lastPollResult.new} new
                    {feed.lastPollResult.errors > 0 && <span className="text-red-500">, {feed.lastPollResult.errors} error{feed.lastPollResult.errors !== 1 ? "s" : ""}</span>}
                  </div>
                )}
              </div>
              <div className="flex gap-1 shrink-0">
                <button
                  onClick={() => toggleFeed(feed)}
                  className={`px-2 py-1 text-xs rounded ${feed.active ? "bg-yellow-50 text-yellow-700 hover:bg-yellow-100" : "bg-green-50 text-green-700 hover:bg-green-100"}`}
                >
                  {feed.active ? "Pause" : "Resume"}
                </button>
                <button
                  onClick={() => { if (confirm(`Delete "${feed.title}"?`)) deleteFeed(feed.id); }}
                  className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
