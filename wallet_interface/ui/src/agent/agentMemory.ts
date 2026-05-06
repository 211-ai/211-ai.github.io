import type { RouteId } from "../models/abby";
import type { AgentMessage, AgentPermissionLevel, AgentSession } from "./types";
import { hasPermissionLevel } from "./types";
import { guardPromptText } from "./promptGuards";

export const AGENT_MEMORY_MODES = ["ephemeral", "wallet"] as const;
export type AgentMemoryMode = (typeof AGENT_MEMORY_MODES)[number];

export const AGENT_MEMORY_KINDS = [
  "conversation_summary",
  "user_preference",
  "service_goal",
  "follow_up",
  "safety_note",
  "raw_transcript"
] as const;
export type AgentMemoryKind = (typeof AGENT_MEMORY_KINDS)[number];

export const AGENT_MEMORY_SCOPES = [
  "conversation_summary",
  "user_preference",
  "service_goal",
  "follow_up",
  "safety_note",
  "raw_transcript"
] as const;
export type AgentMemoryScope = (typeof AGENT_MEMORY_SCOPES)[number];

export interface AgentMemoryOptIn {
  granted: boolean;
  grantedAt?: string;
  revokedAt?: string;
  walletId?: string;
  scopes?: readonly AgentMemoryScope[];
  permissionLevel?: AgentPermissionLevel;
  allowRawTranscriptPersistence?: boolean;
}

export interface AgentMemoryRecord {
  id: string;
  sessionId: string;
  kind: AgentMemoryKind;
  summary: string;
  createdAt: string;
  updatedAt: string;
  route?: RouteId;
  sourceMessageIds?: string[];
  evidenceBundleIds?: string[];
  privateContextIncluded: boolean;
  walletBacked: boolean;
  metadata?: Record<string, unknown>;
}

export interface AgentMemoryDraft {
  sessionId: string;
  kind: AgentMemoryKind;
  summary: string;
  route?: RouteId;
  sourceMessageIds?: readonly string[];
  evidenceBundleIds?: readonly string[];
  privateContextIncluded?: boolean;
  metadata?: Record<string, unknown>;
}

export interface AgentMemoryQuery {
  sessionId?: string;
  kinds?: readonly AgentMemoryKind[];
  walletBacked?: boolean;
}

export interface AgentWalletMemoryStore {
  listMemories: (query?: AgentMemoryQuery) => Promise<AgentMemoryRecord[]>;
  saveMemory: (record: AgentMemoryRecord) => Promise<AgentMemoryRecord>;
  deleteMemory: (id: string) => Promise<void>;
  clearSessionMemories?: (sessionId: string) => Promise<void>;
}

export interface AgentMemoryPolicy {
  mode: AgentMemoryMode;
  walletBacked: boolean;
  walletOptInRequired: true;
  walletOptedIn: boolean;
  rawTranscriptPersistenceEnabled: boolean;
  rawTranscriptPersistenceDefault: false;
  reason?: string;
}

export interface AgentMemoryOptions {
  mode?: AgentMemoryMode;
  walletStore?: AgentWalletMemoryStore;
  walletOptIn?: AgentMemoryOptIn;
  permissionLevel?: AgentPermissionLevel;
  allowRawTranscriptPersistence?: boolean;
  maxEphemeralMessagesPerSession?: number;
  maxEphemeralMemoriesPerSession?: number;
  now?: () => string;
  createId?: (prefix: string) => string;
}

export interface RememberSessionSummaryOptions {
  summary?: string;
  route?: RouteId;
  privateContextIncluded?: boolean;
  metadata?: Record<string, unknown>;
}

export interface PersistRawTranscriptOptions {
  confirmRawTranscriptPersistence: boolean;
  route?: RouteId;
  metadata?: Record<string, unknown>;
}

export interface AgentMemoryService {
  getPolicy: () => AgentMemoryPolicy;
  appendEphemeralMessage: (message: AgentMessage) => void;
  appendEphemeralMessages: (messages: readonly AgentMessage[]) => void;
  getEphemeralMessages: (sessionId: string) => AgentMessage[];
  remember: (draft: AgentMemoryDraft) => Promise<AgentMemoryRecord>;
  rememberSessionSummary: (
    session: AgentSession,
    options?: RememberSessionSummaryOptions
  ) => Promise<AgentMemoryRecord>;
  listMemories: (query?: AgentMemoryQuery) => Promise<AgentMemoryRecord[]>;
  forgetMemory: (id: string) => Promise<void>;
  clearSession: (sessionId: string) => Promise<void>;
  persistRawTranscript: (
    session: AgentSession,
    options: PersistRawTranscriptOptions
  ) => Promise<AgentMemoryRecord>;
}

const DEFAULT_MAX_EPHEMERAL_MESSAGES_PER_SESSION = 80;
const DEFAULT_MAX_EPHEMERAL_MEMORIES_PER_SESSION = 40;
const MAX_MEMORY_SUMMARY_LENGTH = 900;

const memoryScopeByKind: Record<AgentMemoryKind, AgentMemoryScope> = {
  conversation_summary: "conversation_summary",
  user_preference: "user_preference",
  service_goal: "service_goal",
  follow_up: "follow_up",
  safety_note: "safety_note",
  raw_transcript: "raw_transcript"
};

export function createAgentMemory(options: AgentMemoryOptions = {}): AgentMemoryService {
  const now = options.now ?? (() => new Date().toISOString());
  const createId =
    options.createId ??
    ((prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  const maxEphemeralMessages = options.maxEphemeralMessagesPerSession ?? DEFAULT_MAX_EPHEMERAL_MESSAGES_PER_SESSION;
  const maxEphemeralMemories = options.maxEphemeralMemoriesPerSession ?? DEFAULT_MAX_EPHEMERAL_MEMORIES_PER_SESSION;
  const ephemeralMessages = new Map<string, AgentMessage[]>();
  const ephemeralMemories = new Map<string, AgentMemoryRecord[]>();

  function getPolicy(): AgentMemoryPolicy {
    const decision = evaluateWalletMemoryPolicy(options);
    return {
      mode: options.mode ?? "ephemeral",
      walletBacked: decision.enabled,
      walletOptInRequired: true,
      walletOptedIn: Boolean(options.walletOptIn?.granted && !options.walletOptIn.revokedAt),
      rawTranscriptPersistenceEnabled: canPersistRawTranscript(options),
      rawTranscriptPersistenceDefault: false,
      reason: decision.reason
    };
  }

  function appendEphemeralMessage(message: AgentMessage): void {
    const messages = ephemeralMessages.get(message.sessionId) ?? [];
    ephemeralMessages.set(message.sessionId, [...messages, message].slice(-maxEphemeralMessages));
  }

  function appendEphemeralMessages(messages: readonly AgentMessage[]): void {
    for (const message of messages) {
      appendEphemeralMessage(message);
    }
  }

  function getEphemeralMessages(sessionId: string): AgentMessage[] {
    return [...(ephemeralMessages.get(sessionId) ?? [])];
  }

  async function remember(draft: AgentMemoryDraft): Promise<AgentMemoryRecord> {
    const createdAt = now();
    const record: AgentMemoryRecord = {
      id: createId("agent-memory"),
      sessionId: draft.sessionId,
      kind: draft.kind,
      summary: sanitizeMemorySummary(draft.summary, draft.privateContextIncluded),
      createdAt,
      updatedAt: createdAt,
      route: draft.route,
      sourceMessageIds: draft.sourceMessageIds ? [...draft.sourceMessageIds] : undefined,
      evidenceBundleIds: draft.evidenceBundleIds ? [...draft.evidenceBundleIds] : undefined,
      privateContextIncluded: Boolean(draft.privateContextIncluded),
      walletBacked: false,
      metadata: draft.metadata
    };

    if (shouldPersistToWallet(record.kind)) {
      const walletRecord = { ...record, walletBacked: true };
      return options.walletStore!.saveMemory(walletRecord);
    }

    rememberEphemerally(record);
    return record;
  }

  async function rememberSessionSummary(
    session: AgentSession,
    summaryOptions: RememberSessionSummaryOptions = {}
  ): Promise<AgentMemoryRecord> {
    const completeMessages = session.messages.filter((message) => message.status === "complete");
    const userCount = completeMessages.filter((message) => message.role === "user").length;
    const assistantCount = completeMessages.filter((message) => message.role === "assistant").length;
    const toolCount = completeMessages.filter((message) => message.role === "tool").length;
    const lastAssistant = [...completeMessages].reverse().find((message) => message.role === "assistant");
    const sourceMessageIds = completeMessages.slice(-12).map((message) => message.id);
    const summary =
      summaryOptions.summary ??
      [
        `Session contained ${userCount} user message(s), ${assistantCount} assistant response(s), and ${toolCount} tool result(s).`,
        lastAssistant ? `Latest assistant summary: ${lastAssistant.content}` : undefined
      ]
        .filter(Boolean)
        .join(" ");

    return remember({
      sessionId: session.id,
      kind: "conversation_summary",
      summary,
      route: summaryOptions.route ?? session.activeRoute,
      sourceMessageIds,
      evidenceBundleIds: session.evidenceBundles.slice(-5).map((bundle) => bundle.id),
      privateContextIncluded: summaryOptions.privateContextIncluded ?? session.privateContextAllowed,
      metadata: {
        messageCount: completeMessages.length,
        userMessageCount: userCount,
        assistantMessageCount: assistantCount,
        toolMessageCount: toolCount,
        rawTranscriptPersisted: false,
        ...summaryOptions.metadata
      }
    });
  }

  async function listMemories(query: AgentMemoryQuery = {}): Promise<AgentMemoryRecord[]> {
    const local = filterMemories(flattenMapValues(ephemeralMemories), query);
    if (!getPolicy().walletBacked) return local;
    const wallet = await options.walletStore!.listMemories(query);
    return [...local, ...wallet];
  }

  async function forgetMemory(id: string): Promise<void> {
    for (const [sessionId, records] of ephemeralMemories.entries()) {
      const next = records.filter((record) => record.id !== id);
      if (next.length === records.length) continue;
      if (next.length) ephemeralMemories.set(sessionId, next);
      else ephemeralMemories.delete(sessionId);
    }

    if (getPolicy().walletBacked) {
      await options.walletStore!.deleteMemory(id);
    }
  }

  async function clearSession(sessionId: string): Promise<void> {
    ephemeralMessages.delete(sessionId);
    ephemeralMemories.delete(sessionId);
    if (getPolicy().walletBacked && options.walletStore!.clearSessionMemories) {
      await options.walletStore!.clearSessionMemories(sessionId);
    }
  }

  async function persistRawTranscript(
    session: AgentSession,
    transcriptOptions: PersistRawTranscriptOptions
  ): Promise<AgentMemoryRecord> {
    if (!transcriptOptions.confirmRawTranscriptPersistence || !canPersistRawTranscript(options)) {
      const createdAt = now();
      const record: AgentMemoryRecord = {
        id: createId("agent-memory"),
        sessionId: session.id,
        kind: "raw_transcript",
        summary: "Raw transcript persistence was not enabled for this session.",
        createdAt,
        updatedAt: createdAt,
        route: transcriptOptions.route ?? session.activeRoute,
        sourceMessageIds: session.messages.map((message) => message.id),
        privateContextIncluded: false,
        walletBacked: false,
        metadata: {
          rawTranscriptPersisted: false,
          reason: "explicit_raw_transcript_opt_in_required",
          ...transcriptOptions.metadata
        }
      };
      rememberEphemerally(record);
      return record;
    }

    const transcript = session.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      createdAt: message.createdAt,
      status: message.status
    }));

    return remember({
      sessionId: session.id,
      kind: "raw_transcript",
      summary: JSON.stringify(transcript),
      route: transcriptOptions.route ?? session.activeRoute,
      sourceMessageIds: session.messages.map((message) => message.id),
      privateContextIncluded: session.privateContextAllowed,
      metadata: {
        rawTranscriptPersisted: true,
        explicitRawTranscriptConfirmation: true,
        ...transcriptOptions.metadata
      }
    });
  }

  function shouldPersistToWallet(kind: AgentMemoryKind): boolean {
    if (kind === "raw_transcript") return canPersistRawTranscript(options);
    const decision = evaluateWalletMemoryPolicy(options);
    if (!decision.enabled) return false;
    return optInAllowsScope(options.walletOptIn, memoryScopeByKind[kind]);
  }

  function rememberEphemerally(record: AgentMemoryRecord): void {
    const memories = ephemeralMemories.get(record.sessionId) ?? [];
    ephemeralMemories.set(record.sessionId, [...memories, record].slice(-maxEphemeralMemories));
  }

  return {
    getPolicy,
    appendEphemeralMessage,
    appendEphemeralMessages,
    getEphemeralMessages,
    remember,
    rememberSessionSummary,
    listMemories,
    forgetMemory,
    clearSession,
    persistRawTranscript
  };
}

export function createInMemoryAgentWalletMemoryStore(initialRecords: readonly AgentMemoryRecord[] = []): AgentWalletMemoryStore {
  const records = new Map(initialRecords.map((record) => [record.id, record]));

  return {
    listMemories: async (query = {}) => filterMemories([...records.values()], query),
    saveMemory: async (record) => {
      records.set(record.id, record);
      return record;
    },
    deleteMemory: async (id) => {
      records.delete(id);
    },
    clearSessionMemories: async (sessionId) => {
      for (const record of records.values()) {
        if (record.sessionId === sessionId) records.delete(record.id);
      }
    }
  };
}

export function evaluateWalletMemoryPolicy(options: AgentMemoryOptions = {}): { enabled: boolean; reason?: string } {
  if (options.mode !== "wallet") {
    return { enabled: false, reason: "Agent chat memory is ephemeral by default." };
  }
  if (!options.walletStore) {
    return { enabled: false, reason: "Wallet-backed memory requires a wallet memory store." };
  }
  if (!options.walletOptIn?.granted || options.walletOptIn.revokedAt) {
    return { enabled: false, reason: "Wallet-backed memory requires explicit user opt-in." };
  }
  const permissionLevel = options.walletOptIn.permissionLevel ?? options.permissionLevel;
  if (permissionLevel && !hasPermissionLevel(permissionLevel, "wallet_private")) {
    return { enabled: false, reason: "Wallet-backed memory requires wallet_private permission." };
  }
  return { enabled: true };
}

export function canPersistRawTranscript(options: AgentMemoryOptions = {}): boolean {
  const decision = evaluateWalletMemoryPolicy(options);
  return Boolean(
    decision.enabled &&
      options.allowRawTranscriptPersistence &&
      options.walletOptIn?.allowRawTranscriptPersistence &&
      optInAllowsScope(options.walletOptIn, "raw_transcript")
  );
}

export function isAgentMemoryRecord(value: unknown): value is AgentMemoryRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const record = value as Partial<AgentMemoryRecord>;
  return (
    typeof record.id === "string" &&
    typeof record.sessionId === "string" &&
    isAgentMemoryKind(record.kind) &&
    typeof record.summary === "string" &&
    typeof record.createdAt === "string" &&
    typeof record.updatedAt === "string" &&
    typeof record.privateContextIncluded === "boolean" &&
    typeof record.walletBacked === "boolean"
  );
}

export function isAgentMemoryKind(value: unknown): value is AgentMemoryKind {
  return typeof value === "string" && AGENT_MEMORY_KINDS.includes(value as AgentMemoryKind);
}

function sanitizeMemorySummary(summary: string, privateContextIncluded = false): string {
  return guardPromptText(summary, "agentMemory.summary", {
    includePrivateWalletContext: privateContextIncluded,
    includePreciseLocation: privateContextIncluded,
    includePrivateNotes: privateContextIncluded,
    includeProviderConversations: privateContextIncluded,
    maxTextLength: MAX_MEMORY_SUMMARY_LENGTH
  });
}

function optInAllowsScope(optIn: AgentMemoryOptIn | undefined, scope: AgentMemoryScope): boolean {
  if (!optIn?.granted || optIn.revokedAt) return false;
  if (!optIn.scopes?.length) return scope !== "raw_transcript";
  return optIn.scopes.includes(scope);
}

function filterMemories(records: AgentMemoryRecord[], query: AgentMemoryQuery): AgentMemoryRecord[] {
  return records.filter((record) => {
    if (query.sessionId && record.sessionId !== query.sessionId) return false;
    if (query.walletBacked !== undefined && record.walletBacked !== query.walletBacked) return false;
    if (query.kinds?.length && !query.kinds.includes(record.kind)) return false;
    return true;
  });
}

function flattenMapValues<T>(map: Map<string, T[]>): T[] {
  return [...map.values()].flat();
}
