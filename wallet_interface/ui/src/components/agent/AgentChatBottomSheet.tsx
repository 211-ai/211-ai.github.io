import { useEffect, useState } from "react";
import { Bot, ChevronDown, ChevronUp, MessageSquare, Mic, X } from "lucide-react";
import type {
  AgentConfirmationRequest,
  AgentMessage,
  AgentToolCall,
  AgentToolResult,
  EvidenceBundle
} from "../../agent/types";
import { Button } from "../ui";
import type { AgentChatMode } from "./AgentChatDrawer";
import { AgentAudioChatSurface } from "./AgentAudioChatSurface";
import { AgentComposer } from "./AgentComposer";
import { AgentMessageList } from "./AgentMessageList";
import { AgentRuntimeStatus } from "./AgentRuntimeStatus";

export function AgentChatBottomSheet({
  activeRouteLabel,
  confirmations = [],
  evidenceBundles = [],
  mode = "text",
  messages,
  open,
  responding = false,
  toolCalls = [],
  toolResults = [],
  onCancelConfirmation,
  onClose,
  onConfirmConfirmation,
  onOpenAudio,
  onOpenText,
  onOpenServiceDetail,
  onSend
}: {
  activeRouteLabel: string;
  confirmations?: AgentConfirmationRequest[];
  evidenceBundles?: EvidenceBundle[];
  mode?: AgentChatMode;
  messages: AgentMessage[];
  open: boolean;
  responding?: boolean;
  toolCalls?: AgentToolCall[];
  toolResults?: AgentToolResult[];
  onCancelConfirmation?: (confirmationId: string) => void;
  onClose: () => void;
  onConfirmConfirmation?: (confirmationId: string) => void;
  onOpenAudio: () => void;
  onOpenText: () => void;
  onOpenServiceDetail?: (docId: string) => void;
  onSend: (message: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const sheetTitle = expanded ? "Collapse assistant sheet" : "Expand assistant sheet";

  useEffect(() => {
    if (!open) setExpanded(false);
  }, [open]);

  return (
    <div className="agent-chat-bottom-sheet-shell">
      {!open ? (
        <div className="agent-chat-bottom-launcher" aria-label="Open Abby assistant">
          <Button
            ariaControls="agent-chat-bottom-sheet"
            ariaExpanded={open}
            ariaLabel="Open text chat"
            className="agent-chat-bottom-sheet-toggle agent-chat-toggle-text"
            onClick={onOpenText}
          >
            <MessageSquare aria-hidden="true" size={20} />
            <span>Text</span>
          </Button>
          <Button
            ariaControls="agent-chat-bottom-sheet"
            ariaExpanded={open}
            ariaLabel="Open voice chat"
            className="agent-chat-bottom-sheet-toggle agent-chat-toggle-audio"
            onClick={onOpenAudio}
          >
            <Mic aria-hidden="true" size={20} />
            <span>Audio</span>
          </Button>
        </div>
      ) : null}

      {open ? (
        <aside
          aria-label="Abby assistant"
          className={`agent-chat-bottom-sheet ${expanded ? "agent-chat-bottom-sheet-expanded" : ""}`}
          data-expanded={expanded ? "true" : "false"}
          id="agent-chat-bottom-sheet"
        >
          <button
            aria-controls="agent-chat-bottom-sheet-body"
            aria-expanded={expanded}
            aria-label={sheetTitle}
            className="agent-sheet-grip"
            onClick={() => setExpanded((current) => !current)}
            type="button"
          >
            <span aria-hidden="true" />
          </button>

          <header className="agent-chat-header agent-chat-bottom-sheet-header">
            <div className="agent-chat-title">
              <span className="agent-chat-mark" aria-hidden="true">
                {mode === "audio" ? <Mic size={20} /> : <Bot size={20} />}
              </span>
              <div>
                <strong>{mode === "audio" ? "Abby voice" : "Abby assistant"}</strong>
                <small>{activeRouteLabel}</small>
              </div>
            </div>
            <div className="agent-sheet-actions">
              <Button ariaLabel={sheetTitle} onClick={() => setExpanded((current) => !current)} variant="quiet">
                {expanded ? <ChevronDown aria-hidden="true" size={18} /> : <ChevronUp aria-hidden="true" size={18} />}
              </Button>
              <Button ariaLabel="Close assistant" onClick={onClose} variant="quiet">
                <X aria-hidden="true" size={18} />
              </Button>
            </div>
          </header>

          <div className="agent-chat-bottom-sheet-body" id="agent-chat-bottom-sheet-body">
            {mode === "audio" ? (
              <AgentAudioChatSurface
                activeRouteLabel={activeRouteLabel}
                messages={messages}
                onClose={onClose}
                onSend={onSend}
                open={open && mode === "audio"}
                responding={responding}
                surface="sheet"
              />
            ) : (
              <>
                <div className="agent-current-task" role="status">
                  <small>Read-only chat</small>
                  <span>Ask questions while continuing to use the app.</span>
                </div>
                <AgentRuntimeStatus open={open} showModelSelector={expanded} />
                <AgentMessageList
                  confirmations={confirmations}
                  evidenceBundles={evidenceBundles}
                  messages={messages}
                  onCancel={onCancelConfirmation}
                  onConfirm={onConfirmConfirmation}
                  onOpenServiceDetail={onOpenServiceDetail}
                  responding={responding}
                  toolCalls={toolCalls}
                  toolResults={toolResults}
                />

                {responding ? (
                  <div className="agent-typing" role="status">
                    Abby is checking public app context.
                  </div>
                ) : null}

                <AgentComposer disabled={responding} onSend={onSend} />
              </>
            )}
          </div>
        </aside>
      ) : null}
    </div>
  );
}
