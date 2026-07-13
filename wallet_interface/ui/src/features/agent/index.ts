/**
 * agent feature slice
 *
 * Owns the Abby chat/agent flows, LLM worker wrappers, and audio chat.
 * Migrated from:
 *   services/agentChatService.ts
 * Pending migration:
 *   agent/           — agentConversation, agentMemory, agentPlanner, chatController, etc.
 *   lib/graphrag/
 *   workers/ — LLM and audio workers
 */

// Types
export type { AgentMessage, AgentSession, AgentConfig } from "./lib/types";

// Services (canonical location)
export * from "./lib/agentChatService";
