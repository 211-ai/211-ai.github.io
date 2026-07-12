/**
 * agent feature — public type contracts
 *
 * These types will be the stable API surface once agent/, services/agentChatService.ts,
 * and related workers are migrated into this slice.
 */

/** A single turn in an agent conversation. */
export interface AgentMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  audio_url?: string;
  tool_calls?: AgentToolCall[];
}

/** A tool call made by the agent during a turn. */
export interface AgentToolCall {
  tool: string;
  input: Record<string, unknown>;
  output?: unknown;
  status: "pending" | "success" | "error";
}

/** An active agent session (conversation context). */
export interface AgentSession {
  session_id: string;
  wallet_id: string;
  messages: AgentMessage[];
  created_at: string;
  updated_at: string;
  is_audio_mode: boolean;
}

/** Configuration for the local/remote LLM backend. */
export interface AgentConfig {
  model: string;
  backend: "local" | "hf_space" | "openai_compat";
  endpoint?: string;
  temperature?: number;
  max_tokens?: number;
}
