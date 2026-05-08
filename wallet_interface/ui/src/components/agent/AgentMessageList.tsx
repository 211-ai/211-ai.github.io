import { useEffect, useRef } from "react";
import { Bot, UserRound } from "lucide-react";
import type { AgentConfirmationRequest, AgentMessage, AgentToolCall, AgentToolResult, EvidenceBundle } from "../../agent/types";
import { AgentAudioBubble } from "./AgentAudioBubble";
import { AgentConfirmationCard } from "./AgentConfirmationCard";
import { AgentEvidencePanel } from "./AgentEvidencePanel";
import { AgentToolResultCard } from "./AgentToolResultCard";

export function AgentMessageList({
  messages,
  confirmations = [],
  evidenceBundles = [],
  toolCalls = [],
  toolResults = [],
  responding = false,
  onConfirm,
  onCancel,
  onOpenServiceDetail
}: {
  messages: AgentMessage[];
  confirmations?: AgentConfirmationRequest[];
  evidenceBundles?: EvidenceBundle[];
  toolCalls?: AgentToolCall[];
  toolResults?: AgentToolResult[];
  responding?: boolean;
  onConfirm?: (confirmationId: string) => void;
  onCancel?: (confirmationId: string) => void;
  onOpenServiceDetail?: (docId: string) => void;
}) {
  const endRef = useRef<HTMLDivElement | null>(null);
  const renderedConfirmationIds = new Set<string>();
  const confirmationsById = new Map(confirmations.map((confirmation) => [confirmation.id, confirmation]));
  const toolCallsById = new Map(toolCalls.map((toolCall) => [toolCall.id, toolCall]));
  const toolResultsById = new Map(toolResults.map((result) => [result.id, result]));

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [confirmations, messages, toolResults]);

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
            <div className="agent-text-bubble">
              <p>{message.content}</p>
            </div>
            {shouldRenderAudioBubble(message) ? <AgentAudioBubble messageId={message.id} text={message.content} /> : null}
            <AgentEvidencePanel
              bundleIds={message.evidenceBundleIds}
              bundles={evidenceBundles}
              onOpenServiceDetail={onOpenServiceDetail}
            />
            {getMessageConfirmationIds(message).map((confirmationId) => {
              const confirmation = confirmationsById.get(confirmationId);
              if (!confirmation) return null;
              renderedConfirmationIds.add(confirmation.id);
              return (
                <AgentConfirmationCard
                  confirmation={confirmation}
                  disabled={responding || !onConfirm || !onCancel}
                  key={confirmation.id}
                  onCancel={onCancel ?? noopConfirmationHandler}
                  onConfirm={onConfirm ?? noopConfirmationHandler}
                  toolCall={toolCallsById.get(confirmation.toolCallId)}
                />
              );
            })}
            {(message.toolResultIds ?? []).map((toolResultId) => {
              const result = toolResultsById.get(toolResultId);
              if (!result) return null;
              return (
                <AgentToolResultCard
                  key={result.id}
                  result={result}
                  toolCall={toolCallsById.get(result.toolCallId)}
                />
              );
            })}
          </div>
        </article>
      ))}
      {confirmations
        .filter((confirmation) => confirmation.status === "pending" && !renderedConfirmationIds.has(confirmation.id))
        .map((confirmation) => (
          <AgentConfirmationCard
            confirmation={confirmation}
            disabled={responding || !onConfirm || !onCancel}
            key={confirmation.id}
            onCancel={onCancel ?? noopConfirmationHandler}
            onConfirm={onConfirm ?? noopConfirmationHandler}
            toolCall={toolCallsById.get(confirmation.toolCallId)}
          />
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

function getMessageConfirmationIds(message: AgentMessage): string[] {
  const ids = new Set<string>();
  if (typeof message.metadata?.confirmationId === "string") {
    ids.add(message.metadata.confirmationId);
  }
  for (const toolCallId of message.toolCallIds ?? []) {
    const confirmationId = message.metadata?.[`${toolCallId}:confirmationId`];
    if (typeof confirmationId === "string") ids.add(confirmationId);
  }
  return Array.from(ids);
}

export function shouldRenderAudioBubble(message: AgentMessage): boolean {
  return message.role === "assistant" && message.status === "complete" && message.content.trim().length > 0;
}

function noopConfirmationHandler() {
  return undefined;
}
