import Link from "next/link";
import TenantMenu from "@/components/TenantMenu";

export default function HomePage() {
  return (
    <div>

      {/* Tenant menu (subdomain only) */}
      <TenantMenu />

      {/* Hero */}
      <section className="py-20 px-6 text-center">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-4xl font-bold text-[#111827] mb-6 leading-tight whitespace-nowrap">
            Strengthen your voice in ministry
          </h1>
          <p className="text-xl text-[#4b5563] mb-10 leading-relaxed max-w-2xl mx-auto">
            Upload a sermon and receive a data-driven score across 8 categories —
            from Biblical Accuracy to Delivery. Clear insights to help every pastor
            communicate with greater clarity and impact.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/upload"
              className="px-8 py-3 text-base font-medium bg-[#2563eb] text-white rounded hover:bg-[#1d4ed8] transition-colors"
            >
              Upload a Sermon
            </Link>
            <Link
              href="/sermons"
              style={{ border: "1px solid #2563eb" }}
              className="px-8 py-3 text-base font-medium text-[#2563eb] rounded hover:bg-[#eff6ff] transition-colors"
            >
              Browse Sermons
            </Link>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section style={{ background: "#f9fafb", borderTop: "1px solid #e5e7eb", borderBottom: "1px solid #e5e7eb" }} className="py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <p className="text-center text-sm font-semibold tracking-widest uppercase text-[#2563eb] mb-3">Pricing</p>
          <h2 className="text-center text-3xl font-bold text-[#111827] mb-2">Simple, transparent pricing</h2>
          <p className="text-center text-sm text-[#6b7280] mb-10">No hidden fees. Cancel anytime.</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">

            {/* Basic */}
            <div style={{ border: "1px solid #e5e7eb", background: "#ffffff" }} className="rounded-lg p-8 flex flex-col">
              <h3 className="text-base font-semibold text-[#111827] mb-1">Basic</h3>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-4xl font-bold text-[#111827]">$7</span>
                <span className="text-sm text-[#6b7280]">/ month</span>
              </div>
              <p className="text-xs text-[#6b7280] mb-6">Billed monthly</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> 4 sermon uploads per month
                </li>
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> Text file &amp; YouTube uploads
                </li>
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> Full 8-category scoring
                </li>
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> Transcript &amp; breakdown
                </li>
              </ul>
              <Link
                href="/upload"
                style={{ border: "1px solid #2563eb" }}
                className="block text-center py-2.5 rounded text-sm font-medium text-[#2563eb] hover:bg-[#eff6ff] transition-colors"
              >
                Get started
              </Link>
            </div>

            {/* Pro */}
            <div style={{ border: "2px solid #2563eb", background: "#ffffff" }} className="rounded-lg p-8 flex flex-col relative">
              <span
                style={{ background: "#2563eb" }}
                className="absolute -top-3 left-1/2 -translate-x-1/2 text-white text-xs font-semibold px-3 py-1 rounded-full"
              >
                Most Popular
              </span>
              <h3 className="text-base font-semibold text-[#111827] mb-1">Pro</h3>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-4xl font-bold text-[#111827]">$14</span>
                <span className="text-sm text-[#6b7280]">/ month</span>
              </div>
              <p className="text-xs text-[#6b7280] mb-6">Billed monthly</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> 10 sermon uploads per month
                </li>
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> Audio file processing
                </li>
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> Text file &amp; YouTube uploads
                </li>
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> Full 8-category scoring
                </li>
                <li className="flex items-center gap-2 text-sm text-[#374151]">
                  <span className="text-[#2563eb] font-bold">✓</span> Transcript &amp; breakdown
                </li>
              </ul>
              <Link
                href="/upload"
                className="block text-center py-2.5 rounded text-sm font-medium bg-[#2563eb] text-white hover:bg-[#1d4ed8] transition-colors"
              >
                Get started
              </Link>
            </div>

          </div>

          <p className="text-center text-xs text-[#9ca3af] mt-6">
            Payments processed securely via Stripe. Cancel anytime. No contracts.
          </p>
        </div>
      </section>

      {/* Principles */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-sm font-semibold tracking-widest uppercase text-[#2563eb] mb-3">
            Our Principles
          </p>
          <h2 className="text-center text-3xl font-bold text-[#111827] mb-10">
            Built for pastors. Grounded in the Word.
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div style={{ border: "1px solid #e5e7eb", background: "#ffffff" }} className="rounded-lg p-6 hover:shadow-md transition-shadow">
              <div className="text-2xl mb-3">📖</div>
              <h3 className="text-base font-semibold text-[#111827] mb-2">Denomination-Neutral</h3>
              <p className="text-sm text-[#6b7280] leading-relaxed">
                Biblical Accuracy measures whether a pastor correctly handles the text — not whether their theology is &ldquo;right.&rdquo; A Calvinist and an Arminian can both score 90+.
              </p>
            </div>
            <div style={{ border: "1px solid #e5e7eb", background: "#ffffff" }} className="rounded-lg p-6 hover:shadow-md transition-shadow">
              <div className="text-2xl mb-3">🎯</div>
              <h3 className="text-base font-semibold text-[#111827] mb-2">Lighthouse, Not a Dashboard</h3>
              <p className="text-sm text-[#6b7280] leading-relaxed">
                Each sermon gets a detailed audit — big score, category breakdown, and expandable reasoning. The numbers speak for themselves.
              </p>
            </div>
            <div style={{ border: "1px solid #e5e7eb", background: "#ffffff" }} className="rounded-lg p-6 hover:shadow-md transition-shadow">
              <div className="text-2xl mb-3">🚦</div>
              <h3 className="text-base font-semibold text-[#111827] mb-2">Three Colors</h3>
              <p className="text-sm text-[#6b7280] leading-relaxed">
                Green (70+), yellow (50–69), red (below 50). Simple, clear, and instantly readable at a glance.
              </p>
            </div>
            <div style={{ border: "1px solid #e5e7eb", background: "#ffffff" }} className="rounded-lg p-6 hover:shadow-md transition-shadow">
              <div className="text-2xl mb-3">🤝</div>
              <h3 className="text-base font-semibold text-[#111827] mb-2">Growth, Not Critique</h3>
              <p className="text-sm text-[#6b7280] leading-relaxed">
                We penalize misquoting and proof-texting — not theological convictions. The goal is to illuminate strengths and highlight opportunities.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid #e5e7eb" }} className="py-8 px-6 text-center">
        <p className="text-sm text-[#6b7280]">
          Strengthening the voice of ministry — one sermon at a time
        </p>
      </footer>

    </div>
  );
}
