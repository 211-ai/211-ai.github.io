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

// Re-export public API when components/hooks are migrated here.
