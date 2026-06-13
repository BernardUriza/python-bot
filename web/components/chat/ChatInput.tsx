"use client";

import { type KeyboardEvent, useState } from "react";
import { Send, Square } from "lucide-react";
import { MAX_CHAT_MESSAGE_CHARS } from "../../lib/api";

/** Composer: textarea + send button. Enter sends, Shift+Enter newlines. While
 * streaming, the send becomes "Stop" so the user can cancel mid-turn. */
export function ChatInput({
  onSend,
  onAbort,
  streaming,
  placeholder = "Ask anything…",
}: {
  onSend: (text: string) => void;
  onAbort: () => void;
  streaming: boolean;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");

  const submit = () => {
    const t = draft.trim();
    if (!t || streaming) return;
    onSend(t);
    setDraft("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2">
      <textarea
        className="min-h-[3rem] flex-1 resize-none rounded-xl border border-app-border bg-app-surface px-3 py-2.5 text-zinc-100 placeholder:text-app-muted focus:border-app-brand focus:outline-none"
        rows={2}
        value={draft}
        placeholder={placeholder}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={streaming}
        maxLength={MAX_CHAT_MESSAGE_CHARS}
        aria-label="message to the agent"
      />
      {streaming ? (
        <button
          type="button"
          onClick={onAbort}
          className="flex h-12 items-center gap-2 rounded-xl border border-app-border px-4 text-sm text-zinc-200 hover:bg-app-surface"
          aria-label="stop the current turn"
        >
          <Square className="h-4 w-4" aria-hidden />
          Stop
        </button>
      ) : (
        <button
          type="button"
          onClick={submit}
          disabled={!draft.trim()}
          className="flex h-12 items-center gap-2 rounded-xl bg-app-brand px-4 text-sm font-medium text-white disabled:opacity-40"
          aria-label="send message"
        >
          Send
          <Send className="h-4 w-4" aria-hidden />
        </button>
      )}
    </div>
  );
}
