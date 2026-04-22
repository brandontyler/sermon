"use client";

import { useEffect, useState } from "react";
import TenantMenu from "@/components/TenantMenu";
import { apiUrl } from "@/lib/api";

interface UserAccount {
  id: string;
  name: string;
  email: string;
  phone: string;
  joinedAt: string;
  uploadsUsed: number;
  uploadsLimit: number;
  trialDays: number;
}

function generateId() {
  return "user-" + Math.random().toString(36).slice(2, 10);
}

export default function AccountPage() {
  const [account, setAccount] = useState<UserAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // Check localStorage for any saved account
    const keys = Object.keys(localStorage).filter(k => k.startsWith("psr_account_"));
    if (keys.length > 0) {
      try {
        const stored = JSON.parse(localStorage.getItem(keys[0]) || "{}");
        if (stored?.id) { setAccount({ ...stored, phone: stored.phone || "" }); setLoading(false); return; }
      } catch { /* ignore */ }
    }

    // Try SWA auth (works on default domain, may fail on custom domains)
    fetch("/.auth/me")
      .then(r => r.json())
      .then(d => {
        if (d?.clientPrincipal) {
          const p = d.clientPrincipal;
          const claims: Record<string, string> = {};
          (p.claims || []).forEach((c: { typ: string; val: string }) => { claims[c.typ] = c.val; });
          const email = claims["http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"] || claims["preferred_username"] || p.userDetails || "";
          const acct: UserAccount = { id: p.userId, name: "", email, phone: "", joinedAt: new Date().toISOString(), uploadsUsed: 0, uploadsLimit: 3, trialDays: 30 };
          localStorage.setItem(`psr_account_${p.userId}`, JSON.stringify(acct));
          setAccount(acct);
        } else {
          // No auth available — create a local account so user can still use the page
          const id = generateId();
          const acct: UserAccount = { id, name: "", email: "", phone: "", joinedAt: new Date().toISOString(), uploadsUsed: 0, uploadsLimit: 3, trialDays: 30 };
          setAccount(acct);
        }
        setLoading(false);
      })
      .catch(() => {
        const id = generateId();
        setAccount({ id, name: "", email: "", phone: "", joinedAt: new Date().toISOString(), uploadsUsed: 0, uploadsLimit: 3, trialDays: 30 });
        setLoading(false);
      });
  }, []);

  async function saveProfile() {
    if (!account) return;
    setSaving(true); setSaved(false);
    localStorage.setItem(`psr_account_${account.id}`, JSON.stringify(account));
    try {
      await fetch(apiUrl("/api/account"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: account.id, name: account.name, phone: account.phone, email: account.email }),
      });
    } catch {}
    setSaving(false); setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  const daysRemaining = account ? Math.max(0, account.trialDays - Math.floor((Date.now() - new Date(account.joinedAt).getTime()) / 86400000)) : 0;
  const uploadsRemaining = account ? Math.max(0, account.uploadsLimit - account.uploadsUsed) : 0;

  return (
    <div className="min-h-screen">
      <div className="max-w-[600px] mx-auto px-4 py-8">
        <TenantMenu />
        <h1 className="text-xl font-bold text-gray-900 mb-6">My Account</h1>

        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : account ? (
          <div className="space-y-6">
            <div className="bg-white border border-gray-200 rounded-lg p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Profile</h2>
              <div className="space-y-3 text-sm">
                <div>
                  <label className="text-gray-500 block mb-1">Name</label>
                  <input type="text" value={account.name} onChange={(e) => setAccount({ ...account, name: e.target.value })} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" placeholder="Enter your name" />
                </div>
                <div>
                  <label className="text-gray-500 block mb-1">Email</label>
                  <input type="email" value={account.email} onChange={(e) => setAccount({ ...account, email: e.target.value })} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" placeholder="Enter your email" />
                </div>
                <div>
                  <label className="text-gray-500 block mb-1">Phone</label>
                  <input type="tel" value={account.phone} onChange={(e) => setAccount({ ...account, phone: e.target.value })} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" placeholder="Enter phone number" />
                </div>
                <div className="flex justify-between items-center"><span className="text-gray-500">Joined</span><span className="font-medium">{new Date(account.joinedAt).toLocaleDateString()}</span></div>
                <button onClick={saveProfile} disabled={saving} className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
                  {saving ? "Saving..." : saved ? "✓ Saved!" : "Save Profile"}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
                <p className={`text-2xl font-bold ${daysRemaining > 7 ? "text-green-600" : daysRemaining > 0 ? "text-amber-500" : "text-red-500"}`}>{daysRemaining}</p>
                <p className="text-xs text-gray-500">Days Remaining</p>
              </div>
              <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
                <p className={`text-2xl font-bold ${uploadsRemaining > 1 ? "text-green-600" : uploadsRemaining > 0 ? "text-amber-500" : "text-red-500"}`}>{uploadsRemaining}</p>
                <p className="text-xs text-gray-500">Uploads Remaining</p>
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-1">Billing</h2>
              <p className="text-xs text-gray-400 mb-4">
                {account.uploadsLimit <= 3 ? "Free trial — upgrade for more uploads" : `Current plan: ${account.uploadsLimit === 4 ? "Basic" : "Pro"}`}
              </p>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className={`border rounded-lg p-4 text-center ${account.uploadsLimit === 4 ? "border-blue-500 bg-blue-50" : "border-gray-200"}`}>
                  <p className="text-lg font-bold text-gray-900">$9<span className="text-xs font-normal text-gray-500">/mo</span></p>
                  <p className="text-xs font-semibold text-gray-700 mt-1">Basic</p>
                  <p className="text-xs text-gray-500 mt-1">4 sermons/month</p>
                  {account.uploadsLimit === 4 ? (
                    <span className="inline-block mt-3 text-xs text-blue-600 font-medium">Current Plan</span>
                  ) : (
                    <button onClick={() => window.open("https://buy.stripe.com/test_basic_placeholder", "_blank")} className="mt-3 w-full py-1.5 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors">
                      {account.uploadsLimit <= 3 ? "Upgrade" : "Downgrade"}
                    </button>
                  )}
                </div>
                <div className={`border rounded-lg p-4 text-center ${account.uploadsLimit === 10 ? "border-blue-500 bg-blue-50" : "border-gray-200"}`}>
                  <p className="text-lg font-bold text-gray-900">$15<span className="text-xs font-normal text-gray-500">/mo</span></p>
                  <p className="text-xs font-semibold text-gray-700 mt-1">Pro</p>
                  <p className="text-xs text-gray-500 mt-1">10 sermons/month</p>
                  {account.uploadsLimit === 10 ? (
                    <span className="inline-block mt-3 text-xs text-blue-600 font-medium">Current Plan</span>
                  ) : (
                    <button onClick={() => window.open("https://buy.stripe.com/test_pro_placeholder", "_blank")} className="mt-3 w-full py-1.5 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors">Upgrade</button>
                  )}
                </div>
              </div>
              <p className="text-[10px] text-gray-400 text-center">Payments processed securely via Stripe. Cancel anytime.</p>
            </div>

            <a href="/.auth/logout?post_logout_redirect_uri=/" className="block w-full text-center py-3 rounded-lg bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 transition-colors text-sm font-medium">Sign Out</a>
          </div>
        ) : null}
      </div>
    </div>
  );
}
