"use client";

import { useState } from "react";
import TenantMenu from "@/components/TenantMenu";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitted(true);
  }

  return (
    <div>

      <TenantMenu />

      <div className="max-w-xl mx-auto px-6 py-16">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[#111827] mb-3">Contact Us</h1>
          <p className="text-sm text-[#6b7280] italic">&ldquo;Speak, for your servant is listening.&rdquo; — 1 Samuel 3:10</p>
        </div>

        <p className="text-sm text-[#4b5563] leading-relaxed mb-3">
          When you reach out to us, we want you to feel heard. That&apos;s why our support team takes its inspiration from Samuel — the prophet who didn&apos;t ignore the call, didn&apos;t hit &ldquo;Do Not Disturb,&rdquo; and didn&apos;t pretend he was asleep. He listened, responded, and helped bring clarity when things felt confusing.
        </p>
        <p className="text-sm text-[#4b5563] leading-relaxed mb-8">
          If your sermon upload is acting like it wandered into the wilderness, or your score looks more mysterious than a parable, we&apos;re here to help.
        </p>

        {submitted ? (
          <div style={{ border: "1px solid #d1fae5", background: "#f0fdf4" }} className="text-center p-8 rounded-lg">
            <p className="text-base font-semibold text-[#065f46]">Thank you!</p>
            <p className="text-sm text-[#6b7280] mt-2">We&apos;ll get back to you soon.</p>
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
                id="message" name="message" required rows={6}
                placeholder="How can we help?"
                style={{ border: "1px solid #d1d5db" }}
                className="w-full px-3 py-2 rounded-lg text-sm text-[#111827] bg-white focus:outline-none focus:border-[#2563eb] resize-y"
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
