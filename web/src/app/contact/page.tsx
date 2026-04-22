"use client";

import { useState } from "react";
import TenantMenu from "@/components/TenantMenu";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    // TODO: wire to backend or email service
    setSubmitted(true);
  }

  return (
    <div className="min-h-screen text-white relative">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-3xl animate-pulse theme-orb-1" />
        <div className="absolute top-1/3 -right-32 w-80 h-80 rounded-full blur-3xl animate-pulse [animation-delay:1s] theme-orb-2" />
      </div>

      <div className="relative z-10 max-w-[600px] mx-auto px-6 py-12">
        <TenantMenu />

        <h2 className="text-xl font-semibold mb-6 text-center">Contact Us</h2>

        <div className="mb-8 text-sm leading-relaxed theme-muted">
          <p className="italic text-center mb-4">&ldquo;Speak, for your servant is listening.&rdquo; — 1 Samuel 3:10</p>
          <p className="mb-3">When you reach out to us, we want you to feel heard. That&apos;s why our support team takes its inspiration from Samuel — the prophet who didn&apos;t ignore the call, didn&apos;t hit &ldquo;Do Not Disturb,&rdquo; and didn&apos;t pretend he was asleep. He listened, responded, and helped bring clarity when things felt confusing.</p>
          <p>If your sermon upload is acting like it wandered into the wilderness, or your score looks more mysterious than a parable, we&apos;re here to help.</p>
        </div>

        {submitted ? (
          <div className="text-center p-8 rounded-xl bg-white/10 border border-white/20">
            <p className="text-lg font-medium">Thank you!</p>
            <p className="text-sm theme-muted mt-2">We&apos;ll get back to you soon.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium mb-1">Name</label>
              <input id="name" name="name" type="text" required className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:border-white/50" placeholder="Your name" />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-1">Email</label>
              <input id="email" name="email" type="email" required className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:border-white/50" placeholder="you@example.com" />
            </div>
            <div>
              <label htmlFor="message" className="block text-sm font-medium mb-1">Message</label>
              <textarea id="message" name="message" required rows={6} className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:border-white/50 resize-y" placeholder="How can we help?" />
            </div>
            <button type="submit" className="w-full py-3 rounded-lg bg-white/20 border border-white/30 font-medium hover:bg-white/30 transition-colors">
              Send Message
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
