"use client";

import { useEffect, useRef } from "react";
import { SITE_NAME } from "../../lib/site";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { useChat } from "./useChat";

export function ChatView() {
  const { messages, streaming, send, abort } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <main className="mx-auto flex h-screen max-w-2xl flex-col px-4">
      <header className="py-4">
        <h1 className="text-lg font-semibold text-zinc-100">{SITE_NAME}</h1>
        <p className="text-sm text-app-muted">FastAPI + fi_runner · streaming chat</p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center text-app-muted">
            <p>Start a conversation — the agent streams its plan, tool calls, and answer live.</p>
          </div>
        ) : (
          messages.map((m) => <MessageBubble key={m.id} message={m} />)
        )}
        <div ref={bottomRef} />
      </div>

      <div className="py-4">
        <ChatInput onSend={send} onAbort={abort} streaming={streaming} />
      </div>
    </main>
  );
}
