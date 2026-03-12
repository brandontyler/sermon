"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiUrl } from "@/lib/api";
import { scoreColor, normalizeUrl } from "@/lib/types";

interface Pastor { name: string; role?: string; primary?: boolean; sermonCount?: number; avgScore?: number | null; }
interface Church { id: string; name: string; address: string; city: string; state: string; lat: number; lng: number; url?: string; pastors: Pastor[]; }

export default function ChurchAdminPage() {
  const [churches, setChurches] = useState<Church[]>([]);
  const [knownPastors, setKnownPastors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [adminKey, setAdminKey] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<Church | null>(null);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(apiUrl("/api/churches")).then(r => r.json()),
      fetch(apiUrl("/api/sermons")).then(r => r.json()),
    ]).then(([c, s]) => {
      setChurches(c);
      const names = [...new Set(s.map((x: { pastor?: string }) => x.pastor).filter(Boolean))] as string[];
      setKnownPastors(names.sort());
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  function startEdit(c: Church) {
    setEditId(c.id);
    setDraft(JSON.parse(JSON.stringify(c)));
    setShowNew(false);
  }

  function startNew() {
    setEditId(null);
    setShowNew(true);
    setDraft({ id: "", name: "", address: "", city: "", state: "", lat: 0, lng: 0, pastors: [{ name: "", role: "", primary: true }] });
  }

  async function save() {
    if (!draft || !adminKey) return;
    setSaving(true);
    if (!draft.id) draft.id = draft.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "");
    draft.pastors = draft.pastors.filter(p => p.name.trim());
    if (!draft.pastors.some(p => p.primary) && draft.pastors[0]) draft.pastors[0].primary = true;

    const r = await fetch(apiUrl("/api/churches"), {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-admin-key": adminKey },
      body: JSON.stringify(draft),
    });
    if (r.ok) {
      const saved = await r.json();
      setChurches(prev => {
        const idx = prev.findIndex(c => c.id === saved.id);
        if (idx >= 0) { const next = [...prev]; next[idx] = saved; return next; }
        return [...prev, saved];
      });
      setEditId(null); setShowNew(false); setDraft(null);
    }
    setSaving(false);
  }

  function updateDraft(field: string, value: string | number) {
    if (!draft) return;
    setDraft({ ...draft, [field]: value });
  }

  function updatePastor(idx: number, field: string, value: string | boolean) {
    if (!draft) return;
    const pastors = [...draft.pastors];
    if (field === "primary" && value === true) pastors.forEach(p => p.primary = false);
    pastors[idx] = { ...pastors[idx], [field]: value };
    setDraft({ ...draft, pastors });
  }

  function addPastor() {
    if (!draft) return;
    setDraft({ ...draft, pastors: [...draft.pastors, { name: "", role: "", primary: false }] });
  }

  function removePastor(idx: number) {
    if (!draft) return;
    const pastors = draft.pastors.filter((_, i) => i !== idx);
    if (pastors.length && !pastors.some(p => p.primary)) pastors[0].primary = true;
    setDraft({ ...draft, pastors });
  }

  function primaryPastor(c: Church) { return c.pastors.find(p => p.primary) || c.pastors[0]; }

  async function deleteChurch(id: string) {
    if (!adminKey || !confirm("Delete this church?")) return;
    await fetch(apiUrl(`/api/churches/${id}`), { method: "DELETE", headers: { "x-admin-key": adminKey } });
    setChurches(prev => prev.filter(c => c.id !== id));
  }

  return (
    <div className="max-w-[960px] mx-auto p-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-gray-900">Church Admin</h1>
        <div className="flex gap-3 text-sm">
          <Link href="/churches" className="text-blue-600 hover:underline">Church Finder</Link>
          <Link href="/sermons" className="text-blue-600 hover:underline">Sermons</Link>
        </div>
      </div>

      <div className="mb-6 flex items-center gap-3">
        <label className="text-sm text-gray-500">Admin Key:</label>
        <input type="password" value={adminKey} onChange={e => setAdminKey(e.target.value)}
          className="text-sm border border-gray-200 rounded px-3 py-1.5 w-72" placeholder="Enter admin key" />
        <button onClick={startNew} disabled={!adminKey}
          className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-40">
          + New Church
        </button>
      </div>

      {loading ? <p className="text-gray-400 text-sm">Loading...</p> : (
        <div className="space-y-3">
          {showNew && draft && <ChurchForm draft={draft} saving={saving} knownPastors={knownPastors}
            onUpdate={updateDraft} onUpdatePastor={updatePastor} onAddPastor={addPastor}
            onRemovePastor={removePastor} onSave={save} onCancel={() => { setShowNew(false); setDraft(null); }} isNew />}

          {churches.map(c => (
            <div key={c.id} className="bg-white border border-gray-200 rounded-lg p-4">
              {editId === c.id && draft ? (
                <ChurchForm draft={draft} saving={saving} knownPastors={knownPastors}
                  onUpdate={updateDraft} onUpdatePastor={updatePastor} onAddPastor={addPastor}
                  onRemovePastor={removePastor} onSave={save} onCancel={() => { setEditId(null); setDraft(null); }} />
              ) : (
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900 text-sm">
                        {c.url ? <a href={normalizeUrl(c.url)} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{c.name}</a> : c.name}
                      </h3>
                      {primaryPastor(c)?.avgScore != null && (
                        <span className={`text-sm font-bold ${scoreColor(primaryPastor(c)?.avgScore ?? 0)}`}>
                          {primaryPastor(c)?.avgScore?.toFixed(1)}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{c.address}</p>
                    <p className="text-xs text-gray-400">{c.city}, {c.state}{c.lat != null && c.lng != null ? ` · ${c.lat.toFixed(4)}, ${c.lng.toFixed(4)}` : ""}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {c.pastors.map(p => (
                        <span key={p.name} className={`text-xs px-2 py-0.5 rounded-full ${p.primary ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"}`}>
                          {p.primary && "★ "}{p.name}{p.role ? ` · ${p.role}` : ""}
                          {p.sermonCount ? ` (${p.sermonCount})` : ""}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => startEdit(c)} disabled={!adminKey}
                      className="text-xs text-blue-600 hover:underline disabled:opacity-30">Edit</button>
                    <button onClick={() => deleteChurch(c.id)} disabled={!adminKey}
                      className="text-xs text-red-500 hover:underline disabled:opacity-30">Delete</button>
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

function ChurchForm({ draft, saving, knownPastors, onUpdate, onUpdatePastor, onAddPastor, onRemovePastor, onSave, onCancel, isNew }: {
  draft: Church; saving: boolean; knownPastors: string[]; isNew?: boolean;
  onUpdate: (f: string, v: string | number) => void;
  onUpdatePastor: (i: number, f: string, v: string | boolean) => void;
  onAddPastor: () => void; onRemovePastor: (i: number) => void;
  onSave: () => void; onCancel: () => void;
}) {
  // Track which rows are in "new pastor" mode (typing a custom name)
  const [newMode, setNewMode] = useState<Record<number, boolean>>({});

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-500">Church Name</label>
          <input value={draft.name} onChange={e => onUpdate("name", e.target.value)}
            className="w-full text-sm border border-gray-200 rounded px-2 py-1" />
        </div>
        <div>
          <label className="text-xs text-gray-500">Address</label>
          <input value={draft.address} onChange={e => onUpdate("address", e.target.value)}
            className="w-full text-sm border border-gray-200 rounded px-2 py-1" />
        </div>
        <div>
          <label className="text-xs text-gray-500">City</label>
          <input value={draft.city} onChange={e => onUpdate("city", e.target.value)}
            className="w-full text-sm border border-gray-200 rounded px-2 py-1" />
        </div>
        <div>
          <label className="text-xs text-gray-500">State</label>
          <input value={draft.state} onChange={e => onUpdate("state", e.target.value)}
            className="w-full text-sm border border-gray-200 rounded px-2 py-1" />
        </div>
        <div className="col-span-2">
          <label className="text-xs text-gray-500">Website URL</label>
          <input value={draft.url || ""} onChange={e => onUpdate("url", e.target.value)}
            placeholder="https://..." className="w-full text-sm border border-gray-200 rounded px-2 py-1" />
        </div>
        <div>
          <label className="text-xs text-gray-500">Latitude</label>
          <input type="number" step="0.0001" value={draft.lat} onChange={e => onUpdate("lat", parseFloat(e.target.value) || 0)}
            className="w-full text-sm border border-gray-200 rounded px-2 py-1" />
        </div>
        <div>
          <label className="text-xs text-gray-500">Longitude</label>
          <input type="number" step="0.0001" value={draft.lng} onChange={e => onUpdate("lng", parseFloat(e.target.value) || 0)}
            className="w-full text-sm border border-gray-200 rounded px-2 py-1" />
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-500 font-medium mb-2 block">Pastors</label>
        {draft.pastors.map((p, i) => (
          <div key={i} className="flex items-center gap-2 mb-2">
            <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer" title="Primary pastor">
              <input type="radio" name="primary" checked={!!p.primary}
                onChange={() => onUpdatePastor(i, "primary", true)} className="accent-blue-600" />
              ★
            </label>
            {newMode[i] ? (
              <div className="flex items-center gap-1 flex-1">
                <input value={p.name} onChange={e => onUpdatePastor(i, "name", e.target.value)}
                  placeholder="New pastor name" autoFocus
                  className="flex-1 text-sm border border-gray-200 rounded px-2 py-1" />
                <button onClick={() => { setNewMode(m => ({ ...m, [i]: false })); onUpdatePastor(i, "name", ""); }}
                  className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
              </div>
            ) : (
              <select value={p.name}
                onChange={e => {
                  if (e.target.value === "__new__") { setNewMode(m => ({ ...m, [i]: true })); onUpdatePastor(i, "name", ""); }
                  else onUpdatePastor(i, "name", e.target.value);
                }}
                className="flex-1 text-sm border border-gray-200 rounded px-2 py-1 bg-white">
                <option value="">Select pastor...</option>
                {knownPastors.map(n => <option key={n} value={n}>{n}</option>)}
                {p.name && !knownPastors.includes(p.name) && <option value={p.name}>{p.name}</option>}
                <option value="__new__">+ New pastor...</option>
              </select>
            )}
            <input value={p.role || ""} onChange={e => onUpdatePastor(i, "role", e.target.value)}
              placeholder="Role" className="w-40 text-sm border border-gray-200 rounded px-2 py-1" />
            {draft.pastors.length > 1 && (
              <button onClick={() => onRemovePastor(i)} className="text-xs text-red-500 hover:underline">✕</button>
            )}
          </div>
        ))}
        <button onClick={onAddPastor} className="text-xs text-blue-600 hover:underline mt-1">+ Add another pastor</button>
      </div>

      <div className="flex gap-2">
        <button onClick={onSave} disabled={saving || !draft.name}
          className="text-sm bg-blue-600 text-white px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-40">
          {saving ? "Saving..." : isNew ? "Create" : "Save"}
        </button>
        <button onClick={onCancel} className="text-sm text-gray-500 hover:underline">Cancel</button>
      </div>
    </div>
  );
}
