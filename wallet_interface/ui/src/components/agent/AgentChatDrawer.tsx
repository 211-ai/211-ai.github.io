import { Bot, MessageSquare, X } from "lucide-react";
import type { AgentConfirmationRequest, AgentMessage, AgentToolCall, AgentToolResult } from "../../agent/types";
import { Button } from "../ui";
import { AgentComposer } from "./AgentComposer";
import { AgentChatBottomSheet } from "./AgentChatBottomSheet";
import { AgentMessageList } from "./AgentMessageList";

export function AgentChatDrawer({
  activeRouteLabel,
  confirmations = [],
  messages,
  open,
  responding = false,
  toolCalls = [],
  toolResults = [],
  onCancelConfirmation,
  onClose,
  onConfirmConfirmation,
  onSend,
  onToggle
}: {
  activeRouteLabel: string;
  confirmations?: AgentConfirmationRequest[];
  messages: AgentMessage[];
  open: boolean;
  responding?: boolean;
  toolCalls?: AgentToolCall[];
  toolResults?: AgentToolResult[];
  onCancelConfirmation?: (confirmationId: string) => void;
  onClose: () => void;
  onConfirmConfirmation?: (confirmationId: string) => void;
  onSend: (message: string) => void;
  onToggle: () => void;
}) {
  return (
    <>
      <AgentChatBottomSheet
        activeRouteLabel={activeRouteLabel}
        confirmations={confirmations}
        messages={messages}
        onCancelConfirmation={onCancelConfirmation}
        onClose={onClose}
        onConfirmConfirmation={onConfirmConfirmation}
        onSend={onSend}
        onToggle={onToggle}
        open={open}
        responding={responding}
        toolCalls={toolCalls}
        toolResults={toolResults}
      />
      <div className="agent-chat-shell">
        {!open ? (
          <Button
            ariaControls="agent-chat-drawer"
            ariaExpanded={open}
            ariaLabel="Open assistant"
            className="agent-chat-toggle"
            onClick={onToggle}
          >
            <MessageSquare aria-hidden="true" size={20} />
            <span>Assistant</span>
          </Button>
        ) : null}

        {open ? (
          <aside aria-label="Abby assistant" className="agent-chat-drawer" id="agent-chat-drawer">
            <header className="agent-chat-header">
              <div className="agent-chat-title">
                <span className="agent-chat-mark" aria-hidden="true">
                  <Bot size={20} />
                </span>
                <div>
                  <strong>Abby assistant</strong>
                  <small>{activeRouteLabel}</small>
                </div>
              </div>
              <Button ariaLabel="Close assistant" onClick={onClose} variant="quiet">
                <X aria-hidden="true" size={18} />
              </Button>
            </header>

            <div className="agent-current-task" role="status">
              <small>App-aware chat</small>
              <span>Ask questions, move between screens, and review before wallet changes.</span>
            </div>

            <AgentMessageList
              confirmations={confirmations}
              messages={messages}
              onCancel={onCancelConfirmation}
              onConfirm={onConfirmConfirmation}
              responding={responding}
              toolCalls={toolCalls}
              toolResults={toolResults}
            />

            {responding ? (
              <div className="agent-typing" role="status">
                Abby is working through the request.
              </div>
            ) : null}

            <AgentComposer disabled={responding} onSend={onSend} />
          </aside>
        ) : null}
      </div>
    </>
  );
}
