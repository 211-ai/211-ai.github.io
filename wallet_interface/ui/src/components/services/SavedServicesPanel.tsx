import { useEffect, useMemo, useState } from "react";
import { Bookmark, ClipboardList, ExternalLink, RefreshCw } from "lucide-react";
import { Badge, Button, Section, StatusBanner } from "../ui";
import type { CorpusDocument } from "../../lib/graphrag";
import type { SavedService, ServicePlan } from "../../models/abby";
import {
  addTextDocument,
  createWalletServicePlan,
  decryptRecordWithGrant,
  listWalletSavedServices,
  listWalletServicePlans,
  saveWalletService,
  type WalletApiConfig
} from "../../services/walletApi";

const APP_SESSION_KEY = "abby-ui-session-v1";
const LOCAL_PORTAL_STATE_KEY = "abby-service-portal-state-v1";
const LOCAL_NOTE_PREFIX = "local-note-";

export interface ServiceReference {
  serviceDocId: string;
  sourceContentCid: string;
  sourcePageCid: string;
  title: string;
  providerName: string;
  programName: string;
  sourceUrl: string;
}

interface LocalNoteEnvelope {
  algorithm: "AES-GCM" | "base64";
  ciphertext: string;
  iv: string;
  updatedAt: string;
}

export interface LocalPortalState {
  savedServices: SavedService[];
  servicePlans: ServicePlan[];
  noteVault: Record<string, LocalNoteEnvelope>;
}

interface SavedServicesPanelProps {
  apiConfig?: WalletApiConfig;
  savedServices: SavedService[];
  servicePlans: ServicePlan[];
  setSavedServices: (services: SavedService[]) => void;
  setServicePlans: (plans: ServicePlan[]) => void;
  onOpenDetail: (docId: string) => void;
  onOpenPlan: (docId: string) => void;
}

export function SavedServicesPanel({
  apiConfig,
  savedServices,
  servicePlans,
  setSavedServices,
  setServicePlans,
  onOpenDetail,
  onOpenPlan
}: SavedServicesPanelProps) {
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [creatingPlanIds, setCreatingPlanIds] = useState<string[]>([]);

  const sortedSavedServices = useMemo(
    () =>
      [...savedServices].sort(
        (first, second) => timestampValue(second.updated_at || second.created_at) - timestampValue(first.updated_at || first.created_at)
      ),
    [savedServices]
  );

  const activePlanByServiceDocId = useMemo(() => {
    const byService = new Map<string, ServicePlan>();
    for (const plan of servicePlans) {
      if (plan.status === "revoked") continue;
      if (!byService.has(plan.service_doc_id)) {
        byService.set(plan.service_doc_id, plan);
      }
    }
    return byService;
  }, [servicePlans]);

  async function refreshPortalState(isCanceled: () => boolean = () => false) {
    setLoading(true);
    setLoadError("");
    try {
      if (apiConfig?.actorDid) {
        const [walletSavedServices, walletServicePlans] = await Promise.all([
          listWalletSavedServices(apiConfig),
          listWalletServicePlans(apiConfig)
        ]);
        if (isCanceled()) return;
        setSavedServices(walletSavedServices);
        setServicePlans(walletServicePlans);
      } else {
        const localState = readLocalPortalState();
        if (isCanceled()) return;
        setSavedServices(localState.savedServices);
        setServicePlans(localState.servicePlans);
      }
    } catch (error) {
      if (!isCanceled()) {
        setLoadError(error instanceof Error ? error.message : "Saved services could not load");
      }
    } finally {
      if (!isCanceled()) setLoading(false);
    }
  }

  useEffect(() => {
    let canceled = false;

    void refreshPortalState(() => canceled);

    return () => {
      canceled = true;
    };
  }, [apiConfig?.actorDid, apiConfig?.apiBaseUrl, apiConfig?.walletId, setSavedServices, setServicePlans]);

  async function createPlan(savedService: SavedService) {
    const existingPlan = activePlanByServiceDocId.get(savedService.service_doc_id);
    if (existingPlan) {
      onOpenPlan(savedService.service_doc_id);
      return;
    }

    setCreatingPlanIds((ids) => [...ids, savedService.saved_service_id]);
    setLoadError("");
    try {
      const reference = serviceReferenceFromSavedService(savedService);
      const plan = apiConfig?.actorDid
        ? await createWalletServicePlan(apiConfig, defaultPlanInput(reference))
        : createLocalServicePlan(reference, defaultPlanInput(reference));
      const nextPlans = upsertServicePlanList(servicePlans, plan);
      setServicePlans(nextPlans);
      if (!apiConfig?.actorDid) {
        writeLocalPortalCollections(savedServices, nextPlans);
      }
      onOpenPlan(savedService.service_doc_id);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Service plan could not be created");
    } finally {
      setCreatingPlanIds((ids) => ids.filter((id) => id !== savedService.saved_service_id));
    }
  }

  return (
    <Section
      actions={
        <Button
          ariaLabel="Refresh saved services"
          disabled={loading}
          onClick={() => void refreshPortalState()}
          variant="quiet"
        >
          <RefreshCw aria-hidden="true" size={18} />
        </Button>
      }
      title="Saved services"
    >
      {loadError ? <StatusBanner tone="warning">Saved services are using the current screen state: {loadError}</StatusBanner> : null}
      {loading && !sortedSavedServices.length ? (
        <StatusBanner tone="info">Loading saved services.</StatusBanner>
      ) : null}
      {!loading && sortedSavedServices.length === 0 ? (
        <div className="empty-state">
          <h3>No saved services yet</h3>
          <p>Search results can be saved here with private wallet-backed plans.</p>
        </div>
      ) : (
        <div className="list-stack saved-services-list">
          {sortedSavedServices.map((savedService) => {
            const title = savedService.label || savedService.title || savedService.program_name || savedService.service_doc_id;
            const provider = savedService.provider_name || "Provider not listed";
            const plan = activePlanByServiceDocId.get(savedService.service_doc_id);
            const creatingPlan = creatingPlanIds.includes(savedService.saved_service_id);
            return (
              <article className="list-item saved-service-item" key={savedService.saved_service_id}>
                <div className="service-list-meta">
                  <h3>{title}</h3>
                  <p>{provider}</p>
                  <div className="badge-row">
                    <Badge tone={savedService.status === "saved" ? "success" : "neutral"}>{savedService.status || "saved"}</Badge>
                    <Badge>{savedService.priority || "normal"}</Badge>
                    {savedService.private_notes_record_id ? <Badge tone="warning">private note</Badge> : null}
                    {plan ? <Badge tone="success">plan ready</Badge> : null}
                  </div>
                </div>
                <div className="row-actions list-item-action">
                  {savedService.source_url ? (
                    <a className="button button-secondary" href={savedService.source_url} rel="noreferrer" target="_blank">
                      <ExternalLink aria-hidden="true" size={18} />
                      Source
                    </a>
                  ) : null}
                  <Button onClick={() => onOpenDetail(savedService.service_doc_id)} variant="secondary">
                    <Bookmark aria-hidden="true" size={18} />
                    Detail
                  </Button>
                  <Button loading={creatingPlan} loadingLabel="Creating" onClick={() => void createPlan(savedService)}>
                    <ClipboardList aria-hidden="true" size={18} />
                    {plan ? "Open plan" : "Create plan"}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </Section>
  );
}

export function serviceReferenceFromDocument(document: CorpusDocument): ServiceReference {
  const title = document.program_name || document.provider_name || document.title || document.doc_id;
  return {
    serviceDocId: document.doc_id,
    sourceContentCid: document.source_content_cid || fallbackCid(document.doc_id),
    sourcePageCid: document.source_page_cid || "",
    title,
    providerName: document.provider_name || "",
    programName: document.program_name || document.title || "",
    sourceUrl: document.source_url || ""
  };
}

export function serviceReferenceFromSavedService(savedService: SavedService): ServiceReference {
  return {
    serviceDocId: savedService.service_doc_id,
    sourceContentCid: savedService.source_content_cid || fallbackCid(savedService.service_doc_id),
    sourcePageCid: savedService.source_page_cid || "",
    title: savedService.title || savedService.label || savedService.program_name || savedService.service_doc_id,
    providerName: savedService.provider_name || "",
    programName: savedService.program_name || savedService.title || "",
    sourceUrl: savedService.source_url || ""
  };
}

export function fallbackServiceReference(docId: string): ServiceReference {
  return {
    serviceDocId: docId,
    sourceContentCid: fallbackCid(docId),
    sourcePageCid: "",
    title: docId,
    providerName: "",
    programName: "",
    sourceUrl: ""
  };
}

export async function persistSavedService(
  apiConfig: WalletApiConfig | undefined,
  reference: ServiceReference,
  input: {
    label?: string;
    reason?: string;
    priority?: string;
    privateNotesRecordId?: string;
  } = {}
): Promise<SavedService> {
  if (apiConfig?.actorDid) {
    return saveWalletService(apiConfig, {
      serviceDocId: reference.serviceDocId,
      sourceContentCid: reference.sourceContentCid,
      sourcePageCid: reference.sourcePageCid,
      title: reference.title,
      providerName: reference.providerName,
      programName: reference.programName,
      sourceUrl: reference.sourceUrl,
      label: input.label || reference.title,
      reason: input.reason || "",
      priority: input.priority || "normal",
      privateNotesRecordId: input.privateNotesRecordId,
      metadata: { saved_from: "services_ui" }
    });
  }

  const localState = readLocalPortalState();
  const existing = localState.savedServices.find((item) => item.service_doc_id === reference.serviceDocId);
  return createLocalSavedService(reference, input, existing);
}

export function createLocalSavedService(
  reference: ServiceReference,
  input: {
    label?: string;
    reason?: string;
    priority?: string;
    privateNotesRecordId?: string;
  } = {},
  existing?: SavedService
): SavedService {
  const now = new Date().toISOString();
  return {
    saved_service_id: existing?.saved_service_id || `saved-${stableSuffix(reference.serviceDocId)}`,
    wallet_id: existing?.wallet_id || "local-wallet",
    service_doc_id: reference.serviceDocId,
    source_content_cid: reference.sourceContentCid,
    source_page_cid: reference.sourcePageCid,
    title: reference.title,
    provider_name: reference.providerName,
    program_name: reference.programName,
    source_url: reference.sourceUrl,
    label: input.label ?? existing?.label ?? reference.title,
    reason: input.reason ?? existing?.reason ?? "",
    priority: input.priority ?? existing?.priority ?? "normal",
    status: existing?.status || "saved",
    created_at: existing?.created_at || now,
    updated_at: now,
    private_notes_record_id: input.privateNotesRecordId ?? existing?.private_notes_record_id ?? "",
    metadata: { ...(existing?.metadata || {}), persistence: "local" }
  };
}

export function createLocalServicePlan(
  reference: ServiceReference,
  input: Partial<{
    goal: string;
    steps: string[];
    documentsNeeded: string[];
    questionsToAsk: string[];
    appointmentAt: string;
    reminderAt: string;
    travelTarget: string;
    assignedWorkerRecipientId: string;
    status: string;
    relatedInteractionIds: string[];
    privateNotesRecordId: string;
  }> = {},
  existing?: ServicePlan
): ServicePlan {
  const now = new Date().toISOString();
  const defaults = defaultPlanInput(reference);
  return {
    plan_id: existing?.plan_id || `plan-${stableSuffix(`${reference.serviceDocId}-${now}`)}`,
    wallet_id: existing?.wallet_id || "local-wallet",
    service_doc_id: reference.serviceDocId,
    source_content_cid: reference.sourceContentCid,
    source_page_cid: reference.sourcePageCid,
    service_title: reference.title,
    provider_name: reference.providerName,
    goal: input.goal ?? existing?.goal ?? defaults.goal ?? "",
    steps: cleanList(input.steps ?? existing?.steps ?? defaults.steps),
    documents_needed: cleanList(input.documentsNeeded ?? existing?.documents_needed ?? defaults.documentsNeeded),
    questions_to_ask: cleanList(input.questionsToAsk ?? existing?.questions_to_ask ?? defaults.questionsToAsk),
    appointment_at: input.appointmentAt ?? existing?.appointment_at ?? "",
    reminder_at: input.reminderAt ?? existing?.reminder_at ?? "",
    travel_target: input.travelTarget ?? existing?.travel_target ?? "",
    assigned_worker_recipient_id: input.assignedWorkerRecipientId ?? existing?.assigned_worker_recipient_id ?? "",
    status: input.status ?? existing?.status ?? "active",
    related_interaction_ids: cleanList(input.relatedInteractionIds ?? existing?.related_interaction_ids ?? []),
    private_notes_record_id: input.privateNotesRecordId ?? existing?.private_notes_record_id ?? "",
    created_at: existing?.created_at || now,
    updated_at: now
  };
}

export function defaultPlanInput(reference: ServiceReference) {
  return {
    serviceDocId: reference.serviceDocId,
    sourceContentCid: reference.sourceContentCid,
    sourcePageCid: reference.sourcePageCid,
    serviceTitle: reference.title,
    providerName: reference.providerName,
    goal: `Contact ${reference.title}`,
    steps: ["Confirm hours and eligibility", "Ask how to apply", "Record the outcome"],
    documentsNeeded: [],
    questionsToAsk: ["What documents should I bring?", "Is this service available right now?"],
    travelTarget: reference.providerName || reference.title,
    status: "active"
  };
}

export function upsertSavedServiceList(current: SavedService[], savedService: SavedService): SavedService[] {
  return [
    savedService,
    ...current.filter(
      (item) =>
        item.saved_service_id !== savedService.saved_service_id &&
        item.service_doc_id !== savedService.service_doc_id &&
        item.source_content_cid !== savedService.source_content_cid
    )
  ];
}

export function upsertServicePlanList(current: ServicePlan[], plan: ServicePlan): ServicePlan[] {
  return [
    plan,
    ...current.filter((item) => item.plan_id !== plan.plan_id)
  ];
}

export function writeLocalPortalCollections(savedServices: SavedService[], servicePlans: ServicePlan[]): void {
  const current = readLocalPortalState();
  writeLocalPortalState({ ...current, savedServices, servicePlans });
}

export function readLocalPortalState(): LocalPortalState {
  if (typeof window === "undefined") return emptyLocalPortalState();
  try {
    const parsed = JSON.parse(window.localStorage.getItem(LOCAL_PORTAL_STATE_KEY) ?? "null") as Partial<LocalPortalState> | null;
    if (!parsed || typeof parsed !== "object") return emptyLocalPortalState();
    return {
      savedServices: Array.isArray(parsed.savedServices) ? parsed.savedServices : [],
      servicePlans: Array.isArray(parsed.servicePlans) ? parsed.servicePlans : [],
      noteVault: parsed.noteVault && typeof parsed.noteVault === "object" ? parsed.noteVault : {}
    };
  } catch {
    return emptyLocalPortalState();
  }
}

export function writeLocalPortalState(state: LocalPortalState): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LOCAL_PORTAL_STATE_KEY, JSON.stringify(state));
}

export async function loadPrivateNoteText(
  apiConfig: WalletApiConfig | undefined,
  recordId: string
): Promise<string> {
  if (!recordId) return "";
  if (recordId.startsWith(LOCAL_NOTE_PREFIX)) {
    return decryptLocalPrivateNote(recordId);
  }
  if (!apiConfig?.actorDid) return "";
  const decrypted = await decryptRecordWithGrant(apiConfig, { recordId });
  return decrypted.text;
}

export async function storePrivateNoteText({
  apiConfig,
  existingRecordId,
  noteText,
  title
}: {
  apiConfig?: WalletApiConfig;
  existingRecordId?: string;
  noteText: string;
  title: string;
}): Promise<string> {
  if (apiConfig?.actorDid) {
    const uploaded = await addTextDocument(apiConfig, {
      filename: `${safeFilename(title)}-private-notes.txt`,
      text: noteText,
      title: `Private service note: ${title}`
    });
    return uploaded.recordId || uploaded.id;
  }

  const recordId = existingRecordId?.startsWith(LOCAL_NOTE_PREFIX)
    ? existingRecordId
    : `${LOCAL_NOTE_PREFIX}${stableSuffix(`${title}-${Date.now()}`)}`;
  await encryptLocalPrivateNote(recordId, noteText);
  return recordId;
}

export function stableSuffix(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
}

function emptyLocalPortalState(): LocalPortalState {
  return { savedServices: [], servicePlans: [], noteVault: {} };
}

async function encryptLocalPrivateNote(recordId: string, noteText: string): Promise<void> {
  const current = readLocalPortalState();
  current.noteVault[recordId] = await encryptText(noteText);
  writeLocalPortalState(current);
}

async function decryptLocalPrivateNote(recordId: string): Promise<string> {
  const envelope = readLocalPortalState().noteVault[recordId];
  if (!envelope) return "";
  return decryptText(envelope);
}

async function encryptText(text: string): Promise<LocalNoteEnvelope> {
  const updatedAt = new Date().toISOString();
  if (!globalThis.crypto?.subtle) {
    return {
      algorithm: "base64",
      ciphertext: base64FromBytes(new TextEncoder().encode(text)),
      iv: "",
      updatedAt
    };
  }

  const iv = new Uint8Array(12);
  globalThis.crypto.getRandomValues(iv);
  const key = await localNoteKey();
  const ciphertext = await globalThis.crypto.subtle.encrypt(
    { name: "AES-GCM", iv: arrayBufferFromBytes(iv) },
    key,
    new TextEncoder().encode(text)
  );
  return {
    algorithm: "AES-GCM",
    ciphertext: base64FromBytes(new Uint8Array(ciphertext)),
    iv: base64FromBytes(iv),
    updatedAt
  };
}

async function decryptText(envelope: LocalNoteEnvelope): Promise<string> {
  if (envelope.algorithm === "base64" || !globalThis.crypto?.subtle) {
    return new TextDecoder().decode(bytesFromBase64(envelope.ciphertext));
  }

  const key = await localNoteKey();
  const plaintext = await globalThis.crypto.subtle.decrypt(
    { name: "AES-GCM", iv: arrayBufferFromBytes(bytesFromBase64(envelope.iv)) },
    key,
    arrayBufferFromBytes(bytesFromBase64(envelope.ciphertext))
  );
  return new TextDecoder().decode(plaintext);
}

async function localNoteKey(): Promise<CryptoKey> {
  const username = readSignedInUsername() || "local-wallet";
  const material = await globalThis.crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(`abby-service-notes:${username}`),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  return globalThis.crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      iterations: 120000,
      salt: new TextEncoder().encode("abby-service-portal-local-notes-v1")
    },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

function readSignedInUsername(): string {
  if (typeof window === "undefined") return "";
  try {
    const parsed = JSON.parse(window.localStorage.getItem(APP_SESSION_KEY) ?? "null");
    return typeof parsed?.username === "string" ? parsed.username : "";
  } catch {
    return "";
  }
}

function base64FromBytes(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

function bytesFromBase64(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function arrayBufferFromBytes(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

function fallbackCid(serviceDocId: string): string {
  return `local-service-${stableSuffix(serviceDocId)}`;
}

function cleanList(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function safeFilename(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48) || "service";
}

function timestampValue(value: string): number {
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : 0;
}
