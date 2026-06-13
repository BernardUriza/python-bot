"use client";

import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/** Render markdown content with GFM (tables, strikethrough, task lists).
 * Inline Tailwind so it drops in without a globals.css edit. */
const markdownComponents: Components = {
  h1: ({ children }) => <h1 className="mt-3 mb-2 text-xl font-bold text-zinc-100">{children}</h1>,
  h2: ({ children }) => <h2 className="mt-3 mb-2 text-lg font-bold text-zinc-100">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-2 mb-1.5 text-base font-bold text-zinc-100">{children}</h3>,
  p: ({ children }) => <p className="my-2 leading-relaxed text-zinc-100">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5 text-zinc-100">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5 text-zinc-100">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  code: ({ className, children, ...props }) => {
    const isInline = !className?.includes("language-");
    return isInline ? (
      <code className="rounded bg-app-surface px-1.5 py-0.5 font-mono text-[0.9em] text-app-accent" {...props}>
        {children}
      </code>
    ) : (
      <code
        className={`block overflow-x-auto rounded-lg border border-app-border bg-app-surface/60 p-3 font-mono text-xs text-zinc-100 ${className || ""}`}
        {...props}
      >
        {children}
      </code>
    );
  },
  blockquote: ({ children }) => (
    <blockquote className="my-3 border-l-4 border-app-brand/60 bg-app-surface/30 py-1 pl-4 italic text-zinc-300">
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-app-brand underline break-words">
      {children}
    </a>
  ),
  hr: () => <hr className="my-4 border-app-border" />,
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-app-border">
      <table className="min-w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-app-surface/60">{children}</thead>,
  tr: ({ children }) => <tr className="border-t border-app-border">{children}</tr>,
  th: ({ children }) => <th className="px-3 py-2 text-left font-semibold text-zinc-200">{children}</th>,
  td: ({ children }) => <td className="px-3 py-2 text-zinc-100">{children}</td>,
};

export function MarkdownRenderer({ content, caret = false }: { content: string; caret?: boolean }) {
  return (
    <div>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
      {caret && (
        <span
          aria-hidden
          className="ml-0.5 inline-block h-[1em] w-[0.45em] -mb-[0.15em] animate-pulse bg-app-brand align-baseline"
        />
      )}
    </div>
  );
}
