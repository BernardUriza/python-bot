import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-xl font-semibold text-zinc-100">404 — Not found</h1>
      <Link href="/" className="text-sm text-app-brand underline">
        Go home
      </Link>
    </main>
  );
}
