"use client";

import { useState } from "react";
import TenantMenu from "@/components/TenantMenu";

export default function SupportPage() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitted(true);
  }

  return (
    <div>

      <TenantMenu />

      <div className="max-w-xl mx-auto px-6 py-16">

        {/* Solomon AI chat card */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[#111827] mb-2">Support</h1>
          <p className="text-sm text-[#6b7280]">Meet Solomon — your AI support assistant</p>
        </div>

        <div style={{ border: "1px solid #e5e7eb", background: "#ffffff" }} className="rounded-lg overflow-hidden shadow-sm mb-16">

          {/* Chat header */}
          <div style={{ borderBottom: "1px solid #e5e7eb", background: "#f9fafb" }} className="px-4 py-3 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-sm font-bold text-white">
              S
            </div>
            <div>
              <p className="text-sm font-semibold text-[#111827]">Solomon</p>
              <p className="text-xs text-[#6b7280]">AI Support Assistant</p>
            </div>
            <span
              style={{ border: "1px solid #fcd34d", background: "#fefce8" }}
              className="ml-auto text-xs px-2 py-0.5 rounded-full text-[#92400e]"
            >
              Coming Soon
            </span>
          </div>

          {/* Chat body */}
          <div className="h-72 flex flex-col items-center justify-center px-6 text-center">
            <div className="text-4xl mb-4">🕊️</div>
            <p className="text-sm font-semibold text-[#111827] mb-2">Solomon is being trained</p>
            <p className="text-sm text-[#6b7280] max-w-xs leading-relaxed">
              Soon you&apos;ll be able to ask questions about your sermon scores, get help with uploads, and receive guidance — all powered by AI wisdom.
            </p>
          </div>

          {/* Chat input */}
          <div style={{ borderTop: "1px solid #e5e7eb" }} className="px-4 py-3">
            <div className="flex gap-2">
              <input
                disabled
                type="text"
                placeholder="Ask Solomon a question..."
                style={{ border: "1px solid #e5e7eb", background: "#f9fafb" }}
                className="flex-1 px-3 py-2 rounded text-sm text-[#9ca3af] cursor-not-allowed opacity-60"
              />
              <button
                disabled
                style={{ border: "1px solid #e5e7eb", background: "#f9fafb" }}
                className="px-4 py-2 rounded text-sm text-[#9ca3af] cursor-not-allowed opacity-60"
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Contact Us */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-[#111827] mb-4">Contact Us</h2>
          <p className="text-sm text-[#4b5563] italic mb-4">&ldquo;Speak, for your servant is listening.&rdquo; — 1 Samuel 3:10</p>
          <p className="text-sm text-[#4b5563] leading-relaxed mb-3">
            When you reach out to us, we want you to feel heard. That&apos;s why our support team takes its inspiration from Samuel — the prophet who didn&apos;t ignore the call, didn&apos;t hit &ldquo;Do Not Disturb,&rdquo; and didn&apos;t pretend he was asleep. He listened, responded, and helped bring clarity when things felt confusing.
          </p>
          <p className="text-sm text-[#4b5563] leading-relaxed">
            If your sermon upload is acting like it wandered into the wilderness, or your score looks more mysterious than a parable, we&apos;re here to help.
          </p>
        </div>

        {submitted ? (
          <div style={{ border: "1px solid #d1fae5", background: "#f0fdf4" }} className="text-center p-8 rounded-lg">
            <p className="text-base font-semibold text-[#065f46]">Thank you!</p>
            <p className="text-sm text-[#6b7280] mt-2">We&apos;ll be in touch soon.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-[#374151] mb-1">Name</label>
              <input
                id="name" name="name" type="text" required
                placeholder="Your name"
                style={{ border: "1px solid #d1d5db" }}
                className="w-full px-3 py-2 rounded-lg text-sm text-[#111827] bg-white focus:outline-none focus:border-[#2563eb]"
              />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[#374151] mb-1">Email</label>
              <input
                id="email" name="email" type="email" required
                placeholder="you@example.com"
                style={{ border: "1px solid #d1d5db" }}
                className="w-full px-3 py-2 rounded-lg text-sm text-[#111827] bg-white focus:outline-none focus:border-[#2563eb]"
              />
            </div>
            <div>
              <label htmlFor="message" className="block text-sm font-medium text-[#374151] mb-1">Message</label>
              <textarea
                id="message" name="message" required rows={5}
                placeholder="How can we help?"
                style={{ border: "1px solid #d1d5db" }}
                className="w-full px-3 py-2 rounded-lg text-sm text-[#111827] bg-white focus:outline-none focus:border-[#2563eb] resize-none"
              />
            </div>
            <button
              type="submit"
              className="w-full py-3 rounded-lg bg-[#2563eb] text-white font-medium text-sm hover:bg-[#1d4ed8] transition-colors"
            >
              Send Message
            </button>
          </form>
        )}

      </div>
    </div>
  );
}
