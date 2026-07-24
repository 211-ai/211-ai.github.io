/**
 * agent feature slice
 *
 * Owns the Abby chat/agent flows, LLM worker wrappers, and audio chat.
 * Canonical locations:
 *   lib/  — agent core (conversation, memory, planner, tools, etc.),
 *           LLM/audio config, worker services, remote clients
 *   components/ — agent UI (chat drawer, confirmation cards, etc.)
 *   workers/ — LLM and audio web workers
 */

// Types
export type { AgentMessage, AgentSession, AgentConfig, EvidenceBundle, EvidenceCitation, AgentConfirmationRequest, AgentToolCall, AgentToolResult } from "./lib/types";

// Services (canonical location)
export * from "./lib/agentChatService";

// Agent core
export * from "./lib/agentConversation";
export * from "./lib/agentMemory";
export * from "./lib/agentPlanner";
export * from "./lib/chatController";
export * from "./lib/commandSchemas";
export * from "./lib/evidenceActions";
export * from "./lib/localLlmResponder";
export * from "./lib/localLlmToolSelector";
export * from "./lib/permissionPolicy";
export * from "./lib/promptGuards";
export * from "./lib/serviceNavigationAgent";
export * from "./lib/surfaceApi";
export * from "./lib/surfaceRegistry";
export * from "./lib/toolExecutor";

// LLM runtime (canonical location)
export * from "./lib/llmConfig";
export * from "./lib/clientLlmPrompting";
export * from "./lib/clientLLMWorkerService";
export * from "./lib/openRouterClient";
export * from "./lib/huggingFaceWalletRouterClient";

// Audio runtime (canonical location)
export * from "./lib/audioChatConfig";
export * from "./lib/clientAudioReplyService";
export * from "./lib/precomputedAudioReplyService";
export * from "./lib/remoteAudioClient";
export * from "./lib/voiceTurnResult";
export * from "./lib/voiceGraphRagPrompt";
export * from "./lib/voiceProxyPayload";
export * from "./lib/liquidAudioRuntimePatch";

// Components
export { AgentAudioChatSurface, primeVoiceChatActivation } from "./components/AgentAudioChatSurface";
export { AgentChatBottomSheet } from "./components/AgentChatBottomSheet";
export { AgentChatDrawer } from "./components/AgentChatDrawer";
export type { AgentChatMode } from "./components/AgentChatDrawer";
export { AgentCitationLink } from "./components/AgentCitationLink";
export { AgentComposer } from "./components/AgentComposer";
export { AgentConfirmationCard } from "./components/AgentConfirmationCard";
export { AgentEvidencePanel } from "./components/AgentEvidencePanel";
export { AgentMessageList } from "./components/AgentMessageList";
export { AgentRuntimeStatus } from "./components/AgentRuntimeStatus";
export { AgentToolResultCard } from "./components/AgentToolResultCard";
export { PrivateContextConsentCard } from "./components/PrivateContextConsentCard";
