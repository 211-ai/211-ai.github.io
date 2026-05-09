import { Bot, MessageSquare, Mic, X } from "lucide-react";
import type {
  AgentConfirmationRequest,
  AgentMessage,
  AgentToolCall,
  AgentToolResult,
  EvidenceBundle
} from "../../agent/types";
import { Button } from "../ui";
import { AgentComposer } from "./AgentComposer";
import { AgentAudioChatSurface } from "./AgentAudioChatSurface";
import { AgentChatBottomSheet } from "./AgentChatBottomSheet";
import { AgentMessageList } from "./AgentMessageList";
import { AgentRuntimeStatus } from "./AgentRuntimeStatus";

export type AgentChatMode = "text" | "audio";

export function AgentChatDrawer({
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
  return (
    <>
      <AgentChatBottomSheet
        activeRouteLabel={activeRouteLabel}
        confirmations={confirmations}
        evidenceBundles={evidenceBundles}
        mode={mode}
        messages={messages}
        onCancelConfirmation={onCancelConfirmation}
        onClose={onClose}
        onConfirmConfirmation={onConfirmConfirmation}
        onOpenAudio={onOpenAudio}
        onOpenText={onOpenText}
        onOpenServiceDetail={onOpenServiceDetail}
        onSend={onSend}
        open={open}
        responding={responding}
        toolCalls={toolCalls}
        toolResults={toolResults}
      />
      <div className="agent-chat-shell">
        {!open ? (
          <div className="agent-chat-launcher" aria-label="Open Abby assistant">
            <Button
              ariaControls="agent-chat-drawer"
              ariaExpanded={open}
              ariaLabel="Open text chat"
              className="agent-chat-toggle agent-chat-toggle-text"
              onClick={onOpenText}
            >
              <MessageSquare aria-hidden="true" size={20} />
              <span>Text</span>
            </Button>
            <Button
              ariaControls="agent-chat-drawer"
              ariaExpanded={open}
              ariaLabel="Open voice chat"
              className="agent-chat-toggle agent-chat-toggle-audio"
              onClick={onOpenAudio}
            >
              <Mic aria-hidden="true" size={20} />
              <span>Audio</span>
            </Button>
          </div>
        ) : null}

        {open && mode === "text" ? (
          <aside aria-label="Abby text assistant" className="agent-chat-drawer" id="agent-chat-drawer">
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
            <AgentRuntimeStatus open={open} />

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
                Abby is working through the request.
              </div>
            ) : null}

            <AgentComposer disabled={responding} onSend={onSend} />
          </aside>
        ) : null}

        {open && mode === "audio" ? (
          <aside aria-label="Abby voice assistant" className="agent-chat-drawer agent-audio-chat-drawer" id="agent-chat-drawer">
            <header className="agent-chat-header">
              <div className="agent-chat-title">
                <span className="agent-chat-mark" aria-hidden="true">
                  <Mic size={20} />
                </span>
                <div>
                  <strong>Abby voice</strong>
                  <small>{activeRouteLabel}</small>
                </div>
              </div>
              <Button ariaLabel="Close voice assistant" onClick={onClose} variant="quiet">
                <X aria-hidden="true" size={18} />
              </Button>
            </header>

            <AgentAudioChatSurface
              activeRouteLabel={activeRouteLabel}
              messages={messages}
              onClose={onClose}
              onSend={onSend}
              open={open && mode === "audio"}
              responding={responding}
              surface="drawer"
            />
          </aside>
        ) : null}
      </div>
    </>
  );
}
