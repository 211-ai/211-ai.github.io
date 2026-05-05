import { Bot, MessageSquare, X } from "lucide-react";
import type { AgentMessage } from "../../agent/types";
import { Button } from "../ui";
import { AgentComposer } from "./AgentComposer";
import { AgentMessageList } from "./AgentMessageList";

export function AgentChatDrawer({
  activeRouteLabel,
  messages,
  open,
  responding = false,
  onClose,
  onSend,
  onToggle
}: {
  activeRouteLabel: string;
  messages: AgentMessage[];
  open: boolean;
  responding?: boolean;
  onClose: () => void;
  onSend: (message: string) => void;
  onToggle: () => void;
}) {
  return (
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
        <aside
          aria-label="Abby assistant"
          className="agent-chat-drawer"
          id="agent-chat-drawer"
        >
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
            <small>Read-only chat</small>
            <span>Ask questions while continuing to use the app.</span>
          </div>

          <AgentMessageList messages={messages} />

          {responding ? (
            <div className="agent-typing" role="status">
              Abby is checking public app context.
            </div>
          ) : null}

          <AgentComposer disabled={responding} onSend={onSend} />
        </aside>
      ) : null}
    </div>
  );
}
