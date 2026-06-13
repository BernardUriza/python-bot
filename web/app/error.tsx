"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-xl font-semibold text-zinc-100">Something went wrong</h1>
      <p className="text-sm text-app-muted">The page hit an unexpected error.</p>
      <button
        onClick={reset}
        className="rounded-lg bg-app-brand px-4 py-2 text-sm font-medium text-white"
      >
        Try again
      </button>
    </main>
  );
}
