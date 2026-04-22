import Link from "next/link";
import TenantMenu from "@/components/TenantMenu";
import ActionButtons from "@/components/ActionButtons";

export default function HomePage() {
  return (
    <div className="min-h-screen text-white overflow-hidden relative">
      {/* Animated background orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-3xl animate-pulse theme-orb-1" />
        <div className="absolute top-1/3 -right-32 w-80 h-80 rounded-full blur-3xl animate-pulse [animation-delay:1s] theme-orb-2" />
        <div className="absolute -bottom-20 left-1/3 w-72 h-72 rounded-full blur-3xl animate-pulse [animation-delay:2s] theme-orb-3" />
      </div>

      <div className="relative z-10 max-w-[900px] mx-auto px-6 py-16 flex flex-col items-center min-h-screen justify-center">
        {/* Tenant menu (subdomain only) */}
        <TenantMenu />

        {/* Logo / Title */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-400 via-orange-500 to-red-500 flex items-center justify-center text-2xl font-bold shadow-lg shadow-orange-500/30">
              P
            </div>
            <div className="text-left">
              <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-white via-blue-100 to-purple-200 bg-clip-text text-transparent">
                PSR
              </h1>
              <p className="text-sm font-medium tracking-widest uppercase theme-accent">Pastor Sermon Rating</p>
            </div>
          </div>
        </div>

        {/* Mission statement */}
        <div className="max-w-[680px] mb-8">
          <p className="text-lg leading-relaxed text-center theme-muted">
            Welcome to a new way of strengthening your voice in ministry. Our platform provides pastors and speakers with thoughtful, data&#8209;driven insights by analyzing uploaded sermon audio and comparing it against a carefully trained communication model. The goal isn&apos;t to critique or diminish—it&apos;s to illuminate strengths, highlight opportunities for growth, and support every pastor in delivering clearer, more impactful messages. With a warm, encouraging approach, we help communicators refine their craft so their words can reach hearts with even greater clarity and purpose.
          </p>
        </div>

        {/* Big action buttons (main site only) */}
        <ActionButtons />

        {/* Design Principles */}
        <div className="mt-8 max-w-[720px] w-full">
          <h2 className="text-center text-sm font-semibold tracking-widest uppercase mb-8 theme-accent">Our Principles</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-xl border border-white/10 bg-white/5 p-5">
              <div className="text-lg mb-2">📖</div>
              <h3 className="font-semibold text-white text-sm mb-1">Denomination-Neutral</h3>
              <p className="text-xs leading-relaxed theme-muted">Biblical Accuracy measures whether a pastor correctly handles the text — not whether their theology is &ldquo;right.&rdquo; A Calvinist and an Arminian can both score 90+.</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-5">
              <div className="text-lg mb-2">🎯</div>
              <h3 className="font-semibold text-white text-sm mb-1">Lighthouse, Not a Dashboard</h3>
              <p className="text-xs leading-relaxed theme-muted">Each sermon gets a detailed audit — big score, category breakdown, and expandable reasoning. The numbers speak for themselves.</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-5">
              <div className="text-lg mb-2">🚦</div>
              <h3 className="font-semibold text-white text-sm mb-1">Three Colors</h3>
              <p className="text-xs leading-relaxed theme-muted">Green (70+), yellow (50–69), red (below 50). Simple, clear, and instantly readable at a glance.</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-5">
              <div className="text-lg mb-2">🤝</div>
              <h3 className="font-semibold text-white text-sm mb-1">Growth, Not Critique</h3>
              <p className="text-xs leading-relaxed theme-muted">We penalize misquoting and proof-texting — not theological convictions. The goal is to illuminate strengths and highlight opportunities.</p>
            </div>
          </div>
        </div>

        {/* Footer accent */}
        <p className="mt-16 text-xs tracking-wide theme-muted opacity-60">
          Strengthening the voice of ministry — one sermon at a time
        </p>
      </div>
    </div>
  );
}
