import type {
  AgentCommandName,
  CreateServicePlanCommandInput,
  OpenServiceDetailCommandInput,
  SaveServiceCommandInput,
} from "./commandSchemas";
import type { AgentPermissionLevel } from "./types";
import type { CorpusDocument, GraphRagEvidence, SearchResult } from "../lib/graphrag";

export const EVIDENCE_ACTION_KINDS = [
  "open_detail",
  "save",
  "create_plan",
  "call_script",
  "provider_questions",
  "map",
  "share",
  "reminder",
] as const;

export type EvidenceActionKind = (typeof EVIDENCE_ACTION_KINDS)[number];

export interface EvidenceActionCommand {
  name: Extract<AgentCommandName, "open_service_detail" | "save_service" | "create_service_plan">;
  input: OpenServiceDetailCommandInput | SaveServiceCommandInput | CreateServicePlanCommandInput;
}

export interface EvidenceActionReference {
  serviceDocId: string;
  contentCid?: string;
  pageCid?: string;
  sourceUrl?: string;
  score?: number;
}

export interface EvidenceActionBackingData {
  serviceDocId: string;
  title: string;
  providerName?: string;
  programName?: string;
  category?: string;
  city?: string;
  state?: string;
  sourceUrl?: string;
  sourceContentCid?: string;
  sourcePageCid?: string;
  phones: string[];
  emails: string[];
  websites: string[];
  addresses: string[];
  hours: string[];
  intakeSteps: string[];
  requiredDocuments: string[];
  eligibilityNotes: string[];
  snippet?: string;
}

export interface EvidenceActionPayload {
  url?: string;
  phone?: string;
  email?: string;
  address?: string;
  mapQuery?: string;
  share?: {
    title: string;
    text: string;
    url?: string;
    sourceContentCid?: string;
  };
  callScript?: string[];
  providerQuestions?: string[];
  reminder?: {
    title: string;
    notes: string;
    relatedServiceDocId: string;
  };
}

export interface EvidenceAction {
  id: string;
  kind: EvidenceActionKind;
  label: string;
  description: string;
  serviceDocId: string;
  serviceTitle: string;
  providerName?: string;
  permissionLevel: AgentPermissionLevel;
  requiresConfirmation: boolean;
  requiresWalletUnlock: boolean;
  requiresUserPresence: boolean;
  command?: EvidenceActionCommand;
  payload?: EvidenceActionPayload;
  backingData: string[];
  evidence: EvidenceActionReference;
}

export interface EvidenceActionOptions {
  includeWalletWriteActions?: boolean;
  includeOutboundActions?: boolean;
  maxProviderQuestions?: number;
  maxScriptLines?: number;
}

const DEFAULT_PROVIDER_QUESTION_LIMIT = 7;
const DEFAULT_SCRIPT_LINE_LIMIT = 8;
const MAX_FRAGMENT_LENGTH = 180;

export function evidenceActionsFromGraphEvidence(
  evidence: GraphRagEvidence,
  options: EvidenceActionOptions = {}
): EvidenceAction[] {
  return evidenceActionsFromSearchResults(evidence.results, options);
}

export function evidenceActionsFromSearchResults(
  results: SearchResult[],
  options: EvidenceActionOptions = {}
): EvidenceAction[] {
  return results.flatMap((result) => evidenceActionsFromSearchResult(result, options));
}

export function evidenceActionsFromSearchResult(
  result: SearchResult,
  options: EvidenceActionOptions = {}
): EvidenceAction[] {
  return evidenceActionsFromBackingData(extractEvidenceActionBackingData(result), result.score, options);
}

export function extractEvidenceActionBackingData(result: SearchResult): EvidenceActionBackingData {
  const document = result.document;
  const text = searchableText(document, result.snippet);
  const sourceUrl = cleanOptional(document.source_url);
  const websites = uniqueValues([...extractUrls(text), sourceUrl].filter(isPresent));
  const title = firstPresent(document.title, document.program_name, document.provider_name, result.docId);

  return {
    serviceDocId: result.docId,
    title,
    providerName: cleanOptional(document.provider_name),
    programName: cleanOptional(document.program_name),
    category: cleanOptional(document.categories),
    city: cleanOptional(document.city),
    state: cleanOptional(document.state),
    sourceUrl,
    sourceContentCid: cleanOptional(result.contentCid || document.source_content_cid),
    sourcePageCid: cleanOptional(result.pageCid || document.source_page_cid),
    phones: extractPhones(text),
    emails: extractEmails(text),
    websites,
    addresses: extractAddresses(text),
    hours: extractHours(text),
    intakeSteps: extractSentences(text, /(apply|application|appointment|call|contact|intake|walk[- ]?in|register|schedule)/i),
    requiredDocuments: extractSentences(text, /(bring|document|documents|identification|\bid\b|proof|verification|required)/i),
    eligibilityNotes: extractSentences(text, /(eligible|eligibility|qualify|qualification|income|resident|age|available to|serves)/i),
    snippet: cleanOptional(result.snippet),
  };
}

export function evidenceActionsFromBackingData(
  backingData: EvidenceActionBackingData,
  score?: number,
  options: EvidenceActionOptions = {}
): EvidenceAction[] {
  const actions: EvidenceAction[] = [];
  const includeWalletWriteActions = options.includeWalletWriteActions ?? true;
  const includeOutboundActions = options.includeOutboundActions ?? true;
  const evidence = evidenceReference(backingData, score);
  const base = actionBase(backingData, evidence);

  actions.push({
    ...base,
    id: actionId(backingData.serviceDocId, "open_detail"),
    kind: "open_detail",
    label: "Open detail",
    description: `Open the 211 service record for ${backingData.title}.`,
    permissionLevel: "public",
    requiresConfirmation: false,
    requiresWalletUnlock: false,
    requiresUserPresence: false,
    command: {
      name: "open_service_detail",
      input: { docId: backingData.serviceDocId },
    },
    backingData: ["service_doc_id"],
  });

  if (includeWalletWriteActions) {
    actions.push({
      ...base,
      id: actionId(backingData.serviceDocId, "save"),
      kind: "save",
      label: "Save service",
      description: `Save ${backingData.title} to the wallet-backed service list.`,
      permissionLevel: "wallet_write",
      requiresConfirmation: true,
      requiresWalletUnlock: true,
      requiresUserPresence: true,
      command: {
        name: "save_service",
        input: {
          serviceId: backingData.serviceDocId,
          note: buildSaveNote(backingData),
        },
      },
      backingData: ["service_doc_id", ...availableSourceKeys(backingData)],
    });

    actions.push({
      ...base,
      id: actionId(backingData.serviceDocId, "create_plan"),
      kind: "create_plan",
      label: "Create plan",
      description: `Create a private follow-up plan for ${backingData.title}.`,
      permissionLevel: "wallet_write",
      requiresConfirmation: true,
      requiresWalletUnlock: true,
      requiresUserPresence: true,
      command: {
        name: "create_service_plan",
        input: {
          serviceId: backingData.serviceDocId,
          goal: `Contact ${serviceLabel(backingData)} and confirm fit.`,
          steps: buildPlanSteps(backingData),
        },
      },
      backingData: ["service_doc_id", "service_summary"],
    });
  }

  const callScript = buildCallScript(backingData, options.maxScriptLines ?? DEFAULT_SCRIPT_LINE_LIMIT);
  if (callScript.length > 0) {
    actions.push({
      ...base,
      id: actionId(backingData.serviceDocId, "call_script"),
      kind: "call_script",
      label: "Prepare call script",
      description: `Draft a short call script for ${serviceLabel(backingData)}.`,
      permissionLevel: "public",
      requiresConfirmation: false,
      requiresWalletUnlock: false,
      requiresUserPresence: false,
      payload: {
        phone: backingData.phones[0],
        callScript,
      },
      backingData: ["service_label", ...conditionalKeys(backingData.phones.length > 0, "phone")],
    });
  }

  const providerQuestions = buildProviderQuestions(
    backingData,
    options.maxProviderQuestions ?? DEFAULT_PROVIDER_QUESTION_LIMIT
  );
  if (providerQuestions.length > 0) {
    actions.push({
      ...base,
      id: actionId(backingData.serviceDocId, "provider_questions"),
      kind: "provider_questions",
      label: "Provider questions",
      description: `Prepare questions to ask ${serviceLabel(backingData)}.`,
      permissionLevel: "public",
      requiresConfirmation: false,
      requiresWalletUnlock: false,
      requiresUserPresence: false,
      payload: { providerQuestions },
      backingData: providerQuestionBackingKeys(backingData),
    });
  }

  if (includeOutboundActions) {
    const mapQuery = buildMapQuery(backingData);
    if (mapQuery) {
      actions.push({
        ...base,
        id: actionId(backingData.serviceDocId, "map"),
        kind: "map",
        label: "Map",
        description: `Open a map search for ${mapQuery}.`,
        permissionLevel: "public",
        requiresConfirmation: true,
        requiresWalletUnlock: false,
        requiresUserPresence: true,
        payload: {
          address: backingData.addresses[0],
          mapQuery,
          url: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}`,
        },
        backingData: backingData.addresses.length > 0 ? ["address"] : ["provider_or_title", "city_or_state"],
      });
    }

    const sharePayload = buildSharePayload(backingData);
    if (sharePayload) {
      actions.push({
        ...base,
        id: actionId(backingData.serviceDocId, "share"),
        kind: "share",
        label: "Share",
        description: `Share public service details for ${backingData.title}.`,
        permissionLevel: "share_or_disclose",
        requiresConfirmation: true,
        requiresWalletUnlock: false,
        requiresUserPresence: true,
        payload: { share: sharePayload },
        backingData: ["title", ...availableSourceKeys(backingData)],
      });
    }

    const reminder = buildReminderPayload(backingData);
    if (reminder) {
      actions.push({
        ...base,
        id: actionId(backingData.serviceDocId, "reminder"),
        kind: "reminder",
        label: "Reminder",
        description: `Create a follow-up reminder for ${backingData.title}.`,
        permissionLevel: "wallet_write",
        requiresConfirmation: true,
        requiresWalletUnlock: true,
        requiresUserPresence: true,
        payload: { reminder },
        backingData: reminderBackingKeys(backingData),
      });
    }
  }

  return actions;
}

export function buildCallScript(backingData: EvidenceActionBackingData, limit = DEFAULT_SCRIPT_LINE_LIMIT): string[] {
  if (!backingData.title && !backingData.providerName && backingData.phones.length === 0) return [];

  return [
    `Hi, I am calling about ${serviceLabel(backingData)}.`,
    backingData.programName ? `I saw the program listed as ${backingData.programName}.` : undefined,
    "Can you confirm whether this service is currently available?",
    backingData.eligibilityNotes.length > 0
      ? "Can you confirm the eligibility rules and whether they apply to me?"
      : "Who is eligible for this service?",
    backingData.requiredDocuments.length > 0
      ? `Should I bring documents such as ${summarizeList(backingData.requiredDocuments)}?`
      : "What documents or information should I have ready?",
    backingData.hours.length > 0
      ? `Are these hours still correct: ${summarizeList(backingData.hours)}?`
      : "What are the best hours or days to contact or visit?",
    backingData.addresses.length > 0 ? `Is this the right location: ${backingData.addresses[0]}?` : undefined,
    "What is the next step if I want to apply or schedule an appointment?",
  ]
    .filter(isPresent)
    .slice(0, limit);
}

export function buildProviderQuestions(
  backingData: EvidenceActionBackingData,
  limit = DEFAULT_PROVIDER_QUESTION_LIMIT
): string[] {
  if (!backingData.title && !backingData.providerName) return [];

  return uniqueValues([
    "Is this service currently available?",
    backingData.eligibilityNotes.length > 0
      ? "Can you confirm the eligibility requirements listed for this service?"
      : "Who is eligible for this service?",
    backingData.requiredDocuments.length > 0
      ? "Which documents should I bring or upload?"
      : "Are any documents required before intake?",
    backingData.intakeSteps.length > 0
      ? "What is the first intake or application step?"
      : "How do I apply or get screened?",
    backingData.hours.length > 0 ? "Are the listed hours current?" : "When should I contact or visit?",
    backingData.addresses.length > 0 ? "Is the listed address the correct place to go?" : undefined,
    backingData.phones.length > 0 ? "Is this the best phone number for this program?" : undefined,
    backingData.emails.length > 0 ? "Is email an accepted way to start?" : undefined,
  ])
    .filter(isPresent)
    .slice(0, limit);
}

function actionBase(
  backingData: EvidenceActionBackingData,
  evidence: EvidenceActionReference
): Pick<EvidenceAction, "serviceDocId" | "serviceTitle" | "providerName" | "evidence"> {
  return {
    serviceDocId: backingData.serviceDocId,
    serviceTitle: backingData.title,
    providerName: backingData.providerName,
    evidence,
  };
}

function evidenceReference(backingData: EvidenceActionBackingData, score?: number): EvidenceActionReference {
  return {
    serviceDocId: backingData.serviceDocId,
    contentCid: backingData.sourceContentCid,
    pageCid: backingData.sourcePageCid,
    sourceUrl: backingData.sourceUrl,
    score,
  };
}

function searchableText(document: CorpusDocument, snippet?: string): string {
  return [
    document.title,
    document.provider_name,
    document.program_name,
    document.categories,
    document.city,
    document.state,
    document.source_url,
    snippet,
    document.text,
  ]
    .filter(isPresent)
    .join("\n");
}

function buildSaveNote(backingData: EvidenceActionBackingData): string {
  const parts = [
    backingData.providerName ? `Provider: ${backingData.providerName}` : undefined,
    backingData.programName ? `Program: ${backingData.programName}` : undefined,
    backingData.category ? `Category: ${backingData.category}` : undefined,
    backingData.sourceUrl ? `Source: ${backingData.sourceUrl}` : undefined,
  ].filter(isPresent);
  return parts.length > 0 ? parts.join("; ") : `Saved from 211 evidence record ${backingData.serviceDocId}.`;
}

function buildPlanSteps(backingData: EvidenceActionBackingData): string[] {
  return uniqueValues([
    backingData.sourceUrl ? "Review the public source page for current details." : "Review the service detail record.",
    backingData.phones.length > 0 ? `Call ${backingData.phones[0]} to confirm availability.` : undefined,
    backingData.emails.length > 0 ? `Email ${backingData.emails[0]} if phone contact is not possible.` : undefined,
    backingData.requiredDocuments.length > 0
      ? `Prepare documents: ${summarizeList(backingData.requiredDocuments)}.`
      : "Ask what documents or information are needed.",
    backingData.addresses.length > 0 ? `Confirm travel to ${backingData.addresses[0]}.` : undefined,
    "Write down eligibility, intake, and appointment details after contacting the provider.",
  ]).filter(isPresent);
}

function buildMapQuery(backingData: EvidenceActionBackingData): string | undefined {
  if (backingData.addresses.length > 0) return backingData.addresses[0];
  const placeParts = [backingData.providerName, backingData.programName || backingData.title, backingData.city, backingData.state]
    .filter(isPresent)
    .filter((value, index, values) => values.indexOf(value) === index);
  return placeParts.length >= 2 && (backingData.city || backingData.state) ? placeParts.join(" ") : undefined;
}

function buildSharePayload(backingData: EvidenceActionBackingData): EvidenceActionPayload["share"] | undefined {
  if (!backingData.sourceUrl && !backingData.sourceContentCid && !backingData.title) return undefined;
  return {
    title: backingData.title,
    text: [
      backingData.title,
      backingData.providerName ? `Provider: ${backingData.providerName}` : undefined,
      backingData.programName ? `Program: ${backingData.programName}` : undefined,
      backingData.sourceUrl ? `Source: ${backingData.sourceUrl}` : undefined,
      !backingData.sourceUrl && backingData.sourceContentCid ? `Source CID: ${backingData.sourceContentCid}` : undefined,
    ]
      .filter(isPresent)
      .join("\n"),
    url: backingData.sourceUrl,
    sourceContentCid: backingData.sourceContentCid,
  };
}

function buildReminderPayload(backingData: EvidenceActionBackingData): EvidenceActionPayload["reminder"] | undefined {
  const backing = [
    ...backingData.hours,
    ...backingData.intakeSteps,
    ...backingData.phones,
    ...backingData.addresses,
    backingData.sourceUrl,
  ].filter(isPresent);
  if (backing.length === 0) return undefined;
  return {
    title: `Follow up with ${serviceLabel(backingData)}`,
    notes: `Confirm availability, eligibility, and next steps for ${backingData.title}. ${summarizeList(backing)}`,
    relatedServiceDocId: backingData.serviceDocId,
  };
}

function providerQuestionBackingKeys(backingData: EvidenceActionBackingData): string[] {
  return uniqueValues([
    "service_label",
    ...conditionalKeys(backingData.eligibilityNotes.length > 0, "eligibility"),
    ...conditionalKeys(backingData.requiredDocuments.length > 0, "required_documents"),
    ...conditionalKeys(backingData.intakeSteps.length > 0, "intake_steps"),
    ...conditionalKeys(backingData.hours.length > 0, "hours"),
    ...conditionalKeys(backingData.addresses.length > 0, "address"),
    ...conditionalKeys(backingData.phones.length > 0, "phone"),
    ...conditionalKeys(backingData.emails.length > 0, "email"),
  ]);
}

function reminderBackingKeys(backingData: EvidenceActionBackingData): string[] {
  return uniqueValues([
    ...conditionalKeys(backingData.hours.length > 0, "hours"),
    ...conditionalKeys(backingData.intakeSteps.length > 0, "intake_steps"),
    ...conditionalKeys(backingData.phones.length > 0, "phone"),
    ...conditionalKeys(backingData.addresses.length > 0, "address"),
    ...conditionalKeys(Boolean(backingData.sourceUrl), "source_url"),
  ]);
}

function availableSourceKeys(backingData: EvidenceActionBackingData): string[] {
  return uniqueValues([
    ...conditionalKeys(Boolean(backingData.sourceUrl), "source_url"),
    ...conditionalKeys(Boolean(backingData.sourceContentCid), "source_content_cid"),
    ...conditionalKeys(Boolean(backingData.sourcePageCid), "source_page_cid"),
  ]);
}

function conditionalKeys(condition: boolean, key: string): string[] {
  return condition ? [key] : [];
}

function extractPhones(text: string): string[] {
  const matches =
    text.match(/(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\b\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?:\s*(?:x|ext\.?|extension)\s*\d{1,6})?/gi) ?? [];
  return uniqueValues(matches.map((value) => value.replace(/\s+/g, " ").trim()));
}

function extractEmails(text: string): string[] {
  return uniqueValues(
    text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi)?.map((value) => trimTrailingPunctuation(value)) ?? []
  );
}

function extractUrls(text: string): string[] {
  return uniqueValues(
    text.match(/https?:\/\/[^\s<>"')]+/gi)?.map((value) => trimTrailingPunctuation(value)) ?? []
  );
}

function extractAddresses(text: string): string[] {
  const matches =
    text.match(
      /\b\d{1,6}\s+[A-Z0-9][A-Z0-9 .'-]{2,80}\s+(?:Avenue|Ave\.?|Boulevard|Blvd\.?|Court|Ct\.?|Drive|Dr\.?|Highway|Hwy\.?|Lane|Ln\.?|Parkway|Pkwy\.?|Place|Pl\.?|Road|Rd\.?|Street|St\.?|Way)\b(?:[, ]+[A-Z][A-Z .'-]{2,50})?(?:[, ]+[A-Z]{2}\b)?(?:[, ]+\d{5}(?:-\d{4})?)?/gi
    ) ?? [];
  return uniqueValues(matches.map((value) => trimTrailingPunctuation(value.replace(/\s+/g, " ").trim())));
}

function extractHours(text: string): string[] {
  return extractSentences(
    text,
    /\b(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday|hours?|open|closed|a\.?m\.?|p\.?m\.?)\b/i
  );
}

function extractSentences(text: string, pattern: RegExp): string[] {
  const sentences = text
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?])\s+|\n+/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence.length > 0 && pattern.test(sentence))
    .map((sentence) => truncateFragment(sentence));
  return uniqueValues(sentences).slice(0, 4);
}

function truncateFragment(value: string): string {
  if (value.length <= MAX_FRAGMENT_LENGTH) return value;
  return `${value.slice(0, MAX_FRAGMENT_LENGTH - 1).trim()}...`;
}

function serviceLabel(backingData: EvidenceActionBackingData): string {
  return firstPresent(backingData.providerName, backingData.programName, backingData.title);
}

function summarizeList(values: string[]): string {
  return values.slice(0, 3).join("; ");
}

function firstPresent(...values: Array<string | undefined>): string {
  return values.find((value) => Boolean(value?.trim()))?.trim() ?? "";
}

function cleanOptional(value: string | undefined): string | undefined {
  const cleaned = value?.replace(/\s+/g, " ").trim();
  return cleaned ? cleaned : undefined;
}

function trimTrailingPunctuation(value: string): string {
  return value.replace(/[),.;:]+$/g, "");
}

function uniqueValues<T extends string | undefined>(values: T[]): Exclude<T, undefined>[] {
  const seen = new Set<string>();
  const result: Exclude<T, undefined>[] = [];
  for (const value of values) {
    if (!value) continue;
    const trimmed = value.trim();
    const key = trimmed.toLowerCase();
    if (!trimmed || seen.has(key)) continue;
    seen.add(key);
    result.push(trimmed as Exclude<T, undefined>);
  }
  return result;
}

function actionId(serviceDocId: string, kind: EvidenceActionKind): string {
  return `${serviceDocId}:${kind}`;
}

function isPresent(value: string | undefined): value is string {
  return typeof value === "string" && value.trim().length > 0;
}
