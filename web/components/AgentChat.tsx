'use client';

/**
 * AgentChat — the template's chat surface, consuming fi-glass.
 *
 * The reusable machinery (visible transcript, optimistic user message, live plan
 * panel, composer) lives in the framework: fi-glass `AgentConversationSurface` +
 * `useAgentConversation`, wired to the template's transport (`useTemplateAgent`).
 * The template supplies only the transport and copy — it does not re-implement the
 * chat. Modelled on apps/og118/web/components/Og118AgentChat.tsx, minus the app-
 * specific pieces (voice queue, conversation library, auth banner).
 */

import { AgentConversationSurface, useAgentConversation } from 'fi-glass/agent';
import 'fi-glass/theme.css';
import 'fi-glass/glass-chat.css';
import { useTemplateAgent } from '@/lib/useTemplateAgent';

export function AgentChat() {
  const agent = useTemplateAgent();
  const conversation = useAgentConversation(agent, {});

  return (
    <div className="agent-shell">
      <AgentConversationSurface
        conversation={conversation}
        composerPlaceholder="Ask the agent — you'll see its plan live…"
        composerBoxClassName="glass-chat-composer"
        composerTextareaClassName="glass-chat-composer-input"
        messageBubbleClassName={(m) =>
          m.role === 'user' ? 'glass-chat-bubble-user' : 'glass-chat-bubble-assistant'
        }
      />
    </div>
  );
}
