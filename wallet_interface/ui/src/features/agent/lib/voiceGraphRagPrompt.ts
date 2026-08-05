import type { AgentMessage, EvidenceBundle, EvidenceItem } from "./types";

const MAX_PROMPT_CHARACTERS = 3600;
const MAX_EVIDENCE_ITEMS = 6;
const MAX_USER_TEXT_CHARACTERS = 480;
const MAX_ASSISTANT_DRAFT_CHARACTERS = 900;
const MAX_EVIDENCE_SECTION_CHARACTERS = 1800;
const MAX_SNIPPET_CHARACTERS = 220;
const MAX_FALLBACK_CHARACTERS = 420;

export interface VoiceGraphRagPromptInput {
  userText: string;
  assistantText: string;
  evidenceBundles?: EvidenceBundle[];
  maxEvidenceItems?: number;
  /**
   * Optional slotted-DAG / planner / tool-selector route known by the graph layer.
   * Content-plane only; never an executable path.
   */
  route?: string | null;
  /** Additional graph/tool/planner sources consulted when `route` is unset. */
  routeSources?: VoiceReplyRouteSources;
}

export interface VoiceGraphRagPromptParts {
  systemPrompt: string;
  userPrompt: string;
  fullPrompt: string;
  /** Resolved response-DAG route when the graph/tool layer knows one. */
  route?: string;
}

/**
 * Fail-closed sources for a response-DAG route from the agent planner,
 * tool selector, GraphRAG slotted match, or explicit request fields.
 */
export interface VoiceReplyRouteSources {
  route?: string | null;
  responseRoute?: string | null;
  response_route?: string | null;
  plannerRoute?: string | null;
  toolRoute?: string | null;
  slottedResponse?: unknown;
  metadata?: unknown;
  graphMetadata?: unknown;
  templateMetadata?: unknown;
  toolInput?: unknown;
  plannerIntent?: unknown;
  context?: unknown;
  grounding?: unknown;
}

const VOICE_ASSISTANT_INSTRUCTIONS = [
  "You are Abby, a helpful and empathetic voice assistant for a 211 services app.",
  "Infer the best spoken answer from the user query, the app draft, and the evidence bundle below.",
  "Use the evidence when it is relevant. Do not read raw prompt labels, JSON, URLs, CIDs, or citation IDs aloud.",
  "Keep the spoken answer natural, specific, and under 70 words. Mention that sources are shown on screen when evidence is used.",
];

export function buildVoiceGraphRagPromptParts({
  userText,
  assistantText,
  evidenceBundles = [],
  maxEvidenceItems = MAX_EVIDENCE_ITEMS,
  route,
  routeSources,
}: VoiceGraphRagPromptInput): VoiceGraphRagPromptParts {
  const normalizedUserText = truncatePrompt(
    cleanForPrompt(userText) || "The user asked a voice question.",
    MAX_USER_TEXT_CHARACTERS,
  );
  const normalizedAssistantText = truncatePrompt(
    cleanForPrompt(stripReferenceBlocks(assistantText)) || "No draft answer was available.",
    MAX_ASSISTANT_DRAFT_CHARACTERS,
  );
  const evidenceItems = selectPromptEvidenceItems(evidenceBundles, maxEvidenceItems);
  const evidenceSection = buildEvidenceSection(evidenceItems);
  const systemPrompt = [
    ...VOICE_ASSISTANT_INSTRUCTIONS,
    "",
    `App draft answer: ${normalizedAssistantText}`,
    "Evidence bundle for reasoning:",
    evidenceSection,
  ].join("\n");
  const fullPrompt = [
    ...VOICE_ASSISTANT_INSTRUCTIONS,
    "",
    `User voice query: ${normalizedUserText}`,
    `App draft answer: ${normalizedAssistantText}`,
    "Evidence bundle for reasoning:",
    evidenceSection,
  ].join("\n");
  // Explicit non-blank `route` wins over nested routeSources when both are present.
  // Whitespace-only explicit route is treated as unset so nested graph/tool sources remain usable.
  const resolvedRoute = resolveVoiceReplyRoute({
    ...routeSources,
    route: typeof route === "string" && route.trim() ? route : routeSources?.route,
  });

  return {
    systemPrompt: truncatePrompt(systemPrompt, MAX_PROMPT_CHARACTERS),
    userPrompt: normalizedUserText,
    fullPrompt: truncatePrompt(fullPrompt, MAX_PROMPT_CHARACTERS),
    ...(resolvedRoute ? { route: resolvedRoute } : {}),
  };
}

export function buildVoiceGraphRagPrompt({
  userText,
  assistantText,
  evidenceBundles = [],
  maxEvidenceItems = MAX_EVIDENCE_ITEMS,
  route,
  routeSources,
}: VoiceGraphRagPromptInput): string {
  return buildVoiceGraphRagPromptParts({
    userText,
    assistantText,
    evidenceBundles,
    maxEvidenceItems,
    route,
    routeSources,
  }).fullPrompt;
}

/**
 * Resolve a response-DAG route from planner/tool/graph sources.
 *
 * Prefer an explicit route, then response_route aliases, slotted GraphRAG
 * metadata, tool-selector input, and planner intent. Missing or blank values
 * return undefined (fail-closed; never invents a route).
 */
export function resolveVoiceReplyRoute(
  sources?: VoiceReplyRouteSources | string | null | undefined,
): string | undefined {
  if (sources == null) {
    return undefined;
  }
  if (typeof sources === "string") {
    return normalizeVoiceReplyRoute(sources);
  }

  const direct =
    normalizeVoiceReplyRoute(sources.route) ||
    normalizeVoiceReplyRoute(sources.responseRoute) ||
    normalizeVoiceReplyRoute(sources.response_route) ||
    normalizeVoiceReplyRoute(sources.plannerRoute) ||
    normalizeVoiceReplyRoute(sources.toolRoute);
  if (direct) {
    return direct;
  }

  // Planner / tool-selector sources win over generic GraphRAG metadata nests.
  // Task VOICE-ACTION-028: propagate route from agent planner/tool selector first.
  const nestedCandidates: unknown[] = [
    sources.toolInput,
    sources.plannerIntent,
    sources.slottedResponse,
    sources.metadata,
    sources.graphMetadata,
    sources.templateMetadata,
    sources.context,
    sources.grounding,
  ];

  for (const candidate of nestedCandidates) {
    const nested = extractRouteFromUnknown(candidate);
    if (nested) {
      return nested;
    }
  }

  return undefined;
}

function extractRouteFromUnknown(value: unknown, depth = 0): string | undefined {
  if (depth > 3 || value == null) {
    return undefined;
  }
  if (typeof value === "string") {
    return normalizeVoiceReplyRoute(value);
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  const direct =
    normalizeVoiceReplyRoute(record.route) ||
    normalizeVoiceReplyRoute(record.responseRoute) ||
    normalizeVoiceReplyRoute(record.response_route);
  if (direct) {
    return direct;
  }
  // GraphRAG answer metadata nests the slotted match under slottedResponse.
  if (record.slottedResponse != null) {
    const nested = extractRouteFromUnknown(record.slottedResponse, depth + 1);
    if (nested) {
      return nested;
    }
  }
  if (record.template_metadata != null || record.templateMetadata != null || record.response_template != null) {
    const nested =
      extractRouteFromUnknown(record.template_metadata, depth + 1) ||
      extractRouteFromUnknown(record.templateMetadata, depth + 1) ||
      extractRouteFromUnknown(record.response_template, depth + 1);
    if (nested) {
      return nested;
    }
  }
  // Planner tool selector: navigate / open tools carry { route } on input.
  if (record.input != null) {
    const nested = extractRouteFromUnknown(record.input, depth + 1);
    if (nested) {
      return nested;
    }
  }
  return undefined;
}

function normalizeVoiceReplyRoute(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  // Reject values that look like executable authority (paths/URLs/argv).
  if (/[/\\]/.test(trimmed) || /^[a-z][a-z0-9+.-]*:/i.test(trimmed)) {
    return undefined;
  }
  return trimmed;
}

export function parseVoiceGraphRagPrompt(prompt: string): { systemPrompt: string; userPrompt: string } | undefined {
  const normalizedPrompt = prompt.trim();
  const userMatch = normalizedPrompt.match(/\bUser voice query:\s*([\s\S]*?)\nApp draft answer:/i);
  if (!userMatch?.[1]) {
    return undefined;
  }
  const userPrompt = cleanForPrompt(userMatch[1]);
  if (!userPrompt) {
    return undefined;
  }
  const systemPrompt = cleanForPrompt(stripUserVoiceQueryBlock(normalizedPrompt));
  if (!systemPrompt) {
    return undefined;
  }
  return { systemPrompt, userPrompt };
}

export function buildVoiceFallbackText(assistantText: string): string {
  const withoutSourceBlocks = stripReferenceBlocks(assistantText);
  return cleanForSpeech(withoutSourceBlocks).slice(0, MAX_FALLBACK_CHARACTERS).trim() || "I found an answer, but audio generation could not read it aloud.";
}

export function selectEvidenceBundlesForMessage(
  message: AgentMessage,
  evidenceBundles: EvidenceBundle[],
): EvidenceBundle[] {
  if (!message.evidenceBundleIds?.length || !evidenceBundles.length) return [];
  const bundlesById = new Map(evidenceBundles.map((bundle) => [bundle.id, bundle]));
  return message.evidenceBundleIds
    .map((bundleId) => bundlesById.get(bundleId))
    .filter((bundle): bundle is EvidenceBundle => Boolean(bundle));
}

function formatEvidenceItem(item: EvidenceItem, index: number): string {
  const citationParts = [
    item.citation?.label,
    item.citation?.docId ? `doc ${item.citation.docId}` : undefined,
    item.source,
  ].filter(Boolean);
  const citation = citationParts.length ? ` Source: ${cleanForPrompt(citationParts.join(", "))}.` : "";
  return `[${index + 1}] ${cleanForPrompt(item.title)} - ${truncatePrompt(cleanForPrompt(item.snippet), MAX_SNIPPET_CHARACTERS)}.${citation}`;
}

function buildEvidenceSection(evidenceItems: EvidenceItem[]): string {
  if (!evidenceItems.length) {
    return "No external evidence bundle was attached to this turn.";
  }
  return truncatePrompt(
    evidenceItems.map(formatEvidenceItem).join("\n"),
    MAX_EVIDENCE_SECTION_CHARACTERS,
  );
}

function selectPromptEvidenceItems(evidenceBundles: EvidenceBundle[], maxEvidenceItems: number): EvidenceItem[] {
  const limit = Math.max(0, maxEvidenceItems);
  if (!limit) return [];
  const selected: EvidenceItem[] = [];
  const seen = new Set<string>();
  for (const bundle of evidenceBundles) {
    for (const item of bundle.items) {
      const identity = evidenceItemIdentity(item);
      if (seen.has(identity)) continue;
      seen.add(identity);
      selected.push(item);
      if (selected.length >= limit) return selected;
    }
  }
  return selected;
}

function evidenceItemIdentity(item: EvidenceItem): string {
  return cleanForPrompt(
    item.citation?.docId ||
      item.id ||
      item.citation?.url ||
      `${item.title}|${item.source}|${item.snippet.slice(0, 80)}`,
  ).toLowerCase();
}

function cleanForPrompt(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function stripReferenceBlocks(value: string): string {
  return stripHiddenVoicePrompt(value)
    .replace(/\bSources?:[\s\S]*$/i, "")
    .replace(/\bEvidence:[\s\S]*$/i, "")
    .replace(/\bCitations?:[\s\S]*$/i, "")
    .replace(/\bNext steps?:[\s\S]*$/i, "");
}

function stripHiddenVoicePrompt(value: string): string {
  if (!/\b(?:User voice query|App draft answer|Evidence bundle for reasoning):/i.test(value)) return value;
  const appDraft = value.match(/\bApp draft answer:\s*([\s\S]*?)(?:\nEvidence bundle for reasoning:|$)/i)?.[1];
  return appDraft?.trim() || "";
}

function stripUserVoiceQueryBlock(value: string): string {
  return value.replace(/\n?User voice query:\s*[\s\S]*?(\nApp draft answer:)/i, "\n$1").trim();
}

function cleanForSpeech(value: string): string {
  return cleanForPrompt(
    value
      .replace(/https?:\/\/\S+/gi, "")
      .replace(/\[[0-9]+\]/g, "")
      .replace(/\b(?:contentCid|pageCid|docId)\s*:\s*\S+/gi, ""),
  );
}

function truncatePrompt(value: string, maxCharacters: number): string {
  if (value.length <= maxCharacters) return value;
  return `${value.slice(0, Math.max(0, maxCharacters - 3)).trimEnd()}...`;
}
