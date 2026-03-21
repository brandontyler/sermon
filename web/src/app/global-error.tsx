"use client";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <html>
      <body>
        <div style={{ maxWidth: 720, margin: "0 auto", padding: "64px 16px", textAlign: "center" }}>
          <p style={{ fontSize: 18, fontWeight: 500, marginBottom: 8 }}>Something went wrong.</p>
          <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: 24 }}>{error.message || "An unexpected error occurred."}</p>
          <button onClick={reset} style={{ fontSize: 14, color: "#2563eb", cursor: "pointer", background: "none", border: "none" }}>Try again</button>
        </div>
      </body>
    </html>
  );
}
