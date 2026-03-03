"use client";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="max-w-[720px] mx-auto p-4 py-16 text-center">
      <p className="text-lg font-medium text-gray-900 mb-2">Something went wrong.</p>
      <p className="text-sm text-gray-500 mb-6">{error.message || "An unexpected error occurred."}</p>
      <button onClick={reset} className="text-sm text-blue-600 hover:underline">Try again</button>
    </div>
  );
}
