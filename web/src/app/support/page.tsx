"use client";

import TenantMenu from "@/components/TenantMenu";

export default function SupportPage() {
  return (
    <div className="min-h-screen text-white relative">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-3xl animate-pulse theme-orb-1" />
        <div className="absolute top-1/3 -right-32 w-80 h-80 rounded-full blur-3xl animate-pulse [animation-delay:1s] theme-orb-2" />
      </div>

      <div className="relative z-10 max-w-[700px] mx-auto px-6 py-12">
        <TenantMenu />

        <h2 className="text-xl font-semibold mb-2 text-center">Support</h2>
        <p className="text-center text-sm theme-muted mb-8">Meet Solomon — your AI support assistant</p>

        {/* Solomon AI Chat Placeholder */}
        <div className="rounded-2xl border border-white/20 bg-white/5 backdrop-blur-md overflow-hidden">
          {/* Chat header */}
          <div className="px-4 py-3 border-b border-white/10 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-sm font-bold">S</div>
            <div>
              <p className="text-sm font-medium">Solomon</p>
              <p className="text-xs theme-muted">AI Support Assistant</p>
            </div>
            <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">Coming Soon</span>
          </div>

          {/* Chat body placeholder */}
          <div className="h-80 flex flex-col items-center justify-center px-6 text-center">
            <div className="text-4xl mb-4">🕊️</div>
            <p className="text-sm font-medium mb-2">Solomon is being trained</p>
            <p className="text-xs theme-muted max-w-[320px]">Soon you&apos;ll be able to ask questions about your sermon scores, get help with uploads, and receive guidance — all powered by AI wisdom.</p>
          </div>

          {/* Chat input placeholder */}
          <div className="px-4 py-3 border-t border-white/10">
            <div className="flex gap-2">
              <input disabled type="text" placeholder="Ask Solomon a question..." className="flex-1 px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/30 text-sm cursor-not-allowed opacity-50" />
              <button disabled className="px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-sm opacity-50 cursor-not-allowed">Send</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
