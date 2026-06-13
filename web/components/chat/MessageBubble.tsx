"use client";

import type { ChatMessage } from "./types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { ThinkingPanel } from "./ThinkingPanel";

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-app-brand/20 px-4 py-2.5 text-zinc-100 whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  const isThinking = message.status === "thinking";
  const isStreaming = message.status === "streaming";

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-app-border bg-app-surface px-4 py-3">
        <ThinkingPanel plan={message.plan} steps={message.steps} />

        {isThinking && message.content === "" ? (
          <p className="text-sm text-app-muted">thinking…</p>
        ) : (
          <MarkdownRenderer content={message.content} caret={isStreaming} />
        )}

        {message.status === "error" && (
          <p className="mt-2 text-sm text-amber-400">⚠ {message.errorMessage ?? "request failed"}</p>
        )}

        {message.meta && message.status === "done" && (
          <p className="mt-2 text-xs text-app-muted">
            {formatMeta(message.meta)}
          </p>
        )}
      </div>
    </div>
  );
}

function formatMeta(meta: NonNullable<Extract<ChatMessage, { role: "assistant" }>["meta"]>): string {
  const parts: string[] = [];
  if (meta.latency_ms != null) parts.push(`${(meta.latency_ms / 1000).toFixed(1)}s`);
  if (meta.tool_count != null) parts.push(`${meta.tool_count} tools`);
  if (meta.model) parts.push(meta.model);
  return parts.length ? `✓ ${parts.join(" · ")}` : "";
}
