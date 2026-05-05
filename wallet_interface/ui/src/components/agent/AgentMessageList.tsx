import { useEffect, useRef } from "react";
import { Bot, UserRound } from "lucide-react";
import type { AgentMessage } from "../../agent/types";

export function AgentMessageList({ messages }: { messages: AgentMessage[] }) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  return (
    <div aria-label="Assistant conversation" className="agent-message-list" role="log">
      {messages.map((message) => (
        <article className={`agent-message agent-message-${message.role}`} key={message.id}>
          <div className="agent-message-icon" aria-hidden="true">
            {message.role === "user" ? <UserRound size={16} /> : <Bot size={16} />}
          </div>
          <div className="agent-message-body">
            <div className="agent-message-meta">
              <strong>{message.role === "user" ? "You" : "Abby assistant"}</strong>
              <span>{formatMessageTime(message.createdAt)}</span>
            </div>
            <p>{message.content}</p>
          </div>
        </article>
      ))}
      <div ref={endRef} />
    </div>
  );
}

function formatMessageTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}
