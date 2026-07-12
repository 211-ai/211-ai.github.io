/**
 * agent feature slice
 *
 * Owns the Abby chat/agent flows, LLM worker wrappers, and audio chat.
 * Migrate from:
 *   agent/           — agentConversation, agentMemory, agentPlanner, chatController, etc.
 *   services/agentChatService.ts
 *   lib/graphrag/
 *   workers/ — LLM and audio workers
 */

// Types — re-exported from lib once migration is complete
export type { AgentMessage, AgentSession, AgentConfig } from "./lib/types";

// Components — uncomment as screens are migrated
// export { AgentChatScreen } from './components/AgentChatScreen';
// export { AudioChatButton } from './components/AudioChatButton';

// Hooks — uncomment as hooks are migrated
// export { useAgentChat } from './hooks/useAgentChat';
// export { useAgentSession } from './hooks/useAgentSession';
