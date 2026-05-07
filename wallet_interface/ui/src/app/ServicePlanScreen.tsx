import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Bookmark,
  CheckSquare,
  ClipboardList,
  ExternalLink,
  LockKeyhole,
  Plus,
  Save,
  Trash2
} from "lucide-react";
import { Badge, Button, Field, Section, StatusBanner } from "../components/ui";
import {
  createLocalServicePlan,
  defaultPlanInput,
  fallbackServiceReference,
  loadPrivateNoteText,
  persistSavedService,
  readLocalPortalState,
  serviceReferenceFromDocument,
  serviceReferenceFromSavedService,
  storePrivateNoteText,
  upsertSavedServiceList,
  upsertServicePlanList,
  writeLocalPortalCollections,
  type ServiceReference
} from "../components/services/SavedServicesPanel";
import { load211Documents, type CorpusDocument } from "../lib/graphrag";
import type { SavedService, ServicePlan } from "../models/abby";
import {
  createWalletServicePlan,
  listWalletSavedServices,
  listWalletServicePlans,
  updateWalletSavedService,
  updateWalletServicePlan,
  type WalletApiConfig
} from "../services/walletApi";

type ChecklistKind = "steps" | "documentsNeeded" | "questionsToAsk";

interface ServicePlanScreenProps {
  apiConfig?: WalletApiConfig;
  docId: string;
  savedServices: SavedService[];
  servicePlans: ServicePlan[];
  setSavedServices: (services: SavedService[]) => void;
  setServicePlans: (plans: ServicePlan[]) => void;
  onBack: () => void;
  onOpenDetail: (docId: string) => void;
}

type DocumentState =
  | { status: "loading"; document: null; error: "" }
  | { status: "ready"; document: CorpusDocument | null; error: "" }
  | { status: "error"; document: null; error: string };

export function ServicePlanScreen({
  apiConfig,
  docId,
  savedServices,
  servicePlans,
  setSavedServices,
  setServicePlans,
  onBack,
  onOpenDetail
}: ServicePlanScreenProps) {
  const [documentState, setDocumentState] = useState<DocumentState>({ status: "loading", document: null, error: "" });
  const [portalLoadError, setPortalLoadError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const [savingService, setSavingService] = useState(false);
  const [savingPlan, setSavingPlan] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [noteLoading, setNoteLoading] = useState(false);
  const [noteLoadError, setNoteLoadError] = useState("");

  const serviceKeys = useMemo(() => {
    const keys = [
      docId,
      documentState.document?.doc_id,
      documentState.document?.source_content_cid,
      documentState.document?.source_page_cid
    ].filter(Boolean) as string[];
    return new Set(keys);
  }, [docId, documentState.document]);

  const savedService = useMemo(
    () =>
      savedServices.find(
        (service) =>
          serviceKeys.has(service.service_doc_id) ||
          serviceKeys.has(service.source_content_cid) ||
          serviceKeys.has(service.source_page_cid)
      ),
    [savedServices, serviceKeys]
  );

  const currentPlan = useMemo(
    () =>
      servicePlans.find(
        (plan) =>
          plan.status !== "revoked" &&
          (serviceKeys.has(plan.service_doc_id) ||
            serviceKeys.has(plan.source_content_cid) ||
            serviceKeys.has(plan.source_page_cid))
      ),
    [servicePlans, serviceKeys]
  );

  const reference = useMemo<ServiceReference>(() => {
    if (documentState.document) return serviceReferenceFromDocument(documentState.document);
    if (savedService) return serviceReferenceFromSavedService(savedService);
    return fallbackServiceReference(docId);
  }, [docId, documentState.document, savedService]);

  const [goal, setGoal] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [documentsNeeded, setDocumentsNeeded] = useState<string[]>([]);
  const [questionsToAsk, setQuestionsToAsk] = useState<string[]>([]);
  const [appointmentAt, setAppointmentAt] = useState("");
  const [reminderAt, setReminderAt] = useState("");
  const [travelTarget, setTravelTarget] = useState("");
  const [status, setStatus] = useState("active");
  const [newChecklistKind, setNewChecklistKind] = useState<ChecklistKind>("steps");
  const [newChecklistItem, setNewChecklistItem] = useState("");
  const [noteText, setNoteText] = useState("");

  useEffect(() => {
    let canceled = false;

    async function loadDocument() {
      setDocumentState({ status: "loading", document: null, error: "" });
      try {
        const documentsState = await load211Documents();
        if (canceled) return;
        const document =
          documentsState.documentById.get(docId) ??
          documentsState.documentByContentCid.get(docId) ??
          documentsState.documents.find((item) => item.source_page_cid === docId) ??
          null;
        setDocumentState({ status: "ready", document, error: "" });
      } catch (error) {
        if (!canceled) {
          setDocumentState({
            status: "error",
            document: null,
            error: error instanceof Error ? error.message : "Service record unavailable"
          });
        }
      }
    }

    void loadDocument();

    return () => {
      canceled = true;
    };
  }, [docId]);

  useEffect(() => {
    let canceled = false;

    async function loadPortalState() {
      setPortalLoadError("");
      try {
        if (apiConfig?.actorDid) {
          const [walletSavedServices, walletPlans] = await Promise.all([
            listWalletSavedServices(apiConfig),
            listWalletServicePlans(apiConfig)
          ]);
          if (canceled) return;
          setSavedServices(walletSavedServices);
          setServicePlans(walletPlans);
        } else {
          const localState = readLocalPortalState();
          if (canceled) return;
          setSavedServices(localState.savedServices);
          setServicePlans(localState.servicePlans);
        }
      } catch (error) {
        if (!canceled) {
          setPortalLoadError(error instanceof Error ? error.message : "Wallet service state could not load");
        }
      }
    }

    void loadPortalState();

    return () => {
      canceled = true;
    };
  }, [apiConfig?.actorDid, apiConfig?.apiBaseUrl, apiConfig?.walletId, setSavedServices, setServicePlans]);

  useEffect(() => {
    const defaults = defaultPlanInput(reference);
    setGoal(currentPlan?.goal || defaults.goal);
    setSteps(currentPlan?.steps.length ? currentPlan.steps : defaults.steps);
    setDocumentsNeeded(currentPlan?.documents_needed || []);
    setQuestionsToAsk(currentPlan?.questions_to_ask.length ? currentPlan.questions_to_ask : defaults.questionsToAsk);
    setAppointmentAt(toDateTimeInputValue(currentPlan?.appointment_at || ""));
    setReminderAt(toDateTimeInputValue(currentPlan?.reminder_at || ""));
    setTravelTarget(currentPlan?.travel_target || defaults.travelTarget || "");
    setStatus(currentPlan?.status || "active");
  }, [currentPlan?.plan_id, reference.serviceDocId]);

  const noteRecordId = currentPlan?.private_notes_record_id || savedService?.private_notes_record_id || "";

  useEffect(() => {
    let canceled = false;

    async function loadNote() {
      setNoteLoadError("");
      if (!noteRecordId) {
        setNoteText("");
        return;
      }

      setNoteLoading(true);
      try {
        const text = await loadPrivateNoteText(apiConfig, noteRecordId);
        if (!canceled) setNoteText(text);
      } catch (error) {
        if (!canceled) {
          setNoteLoadError(error instanceof Error ? error.message : "Private note could not be decrypted");
        }
      } finally {
        if (!canceled) setNoteLoading(false);
      }
    }

    void loadNote();

    return () => {
      canceled = true;
    };
  }, [apiConfig?.actorDid, apiConfig?.apiBaseUrl, apiConfig?.walletId, noteRecordId]);

  async function saveService() {
    if (savedService) return;
    setSavingService(true);
    setSaveError("");
    setSaveMessage("");
    try {
      const saved = await persistSavedService(apiConfig, reference);
      const nextSavedServices = upsertSavedServiceList(savedServices, saved);
      setSavedServices(nextSavedServices);
      if (!apiConfig?.actorDid) {
        writeLocalPortalCollections(nextSavedServices, servicePlans);
      }
      setSaveMessage("Service saved.");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Service could not be saved");
    } finally {
      setSavingService(false);
    }
  }

  async function savePlan(event?: FormEvent<HTMLFormElement>): Promise<ServicePlan | undefined> {
    event?.preventDefault();
    setSavingPlan(true);
    setSaveError("");
    setSaveMessage("");
    try {
      const planInput = currentPlanInput(reference, {
        goal,
        steps,
        documentsNeeded,
        questionsToAsk,
        appointmentAt,
        reminderAt,
        travelTarget,
        status
      });
      const plan =
        apiConfig?.actorDid && currentPlan
          ? await updateWalletServicePlan(apiConfig, currentPlan.plan_id, planInput)
          : apiConfig?.actorDid
            ? await createWalletServicePlan(apiConfig, planInput)
            : createLocalServicePlan(reference, planInput, currentPlan);
      const nextPlans = upsertServicePlanList(servicePlans, plan);
      setServicePlans(nextPlans);
      if (!apiConfig?.actorDid) {
        writeLocalPortalCollections(savedServices, nextPlans);
      }
      setSaveMessage(currentPlan ? "Plan saved." : "Plan created.");
      return plan;
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Service plan could not be saved");
      return undefined;
    } finally {
      setSavingPlan(false);
    }
  }

  async function savePrivateNote() {
    setSavingNote(true);
    setSaveError("");
    setSaveMessage("");
    try {
      const recordId = await storePrivateNoteText({
        apiConfig,
        existingRecordId: noteRecordId,
        noteText,
        title: reference.title
      });
      const planInput = currentPlanInput(reference, {
        goal,
        steps,
        documentsNeeded,
        questionsToAsk,
        appointmentAt,
        reminderAt,
        travelTarget,
        status,
        privateNotesRecordId: recordId
      });
      const plan =
        apiConfig?.actorDid && currentPlan
          ? await updateWalletServicePlan(apiConfig, currentPlan.plan_id, { ...planInput, privateNotesRecordId: recordId })
          : apiConfig?.actorDid
            ? await createWalletServicePlan(apiConfig, planInput)
            : createLocalServicePlan(reference, planInput, currentPlan);
      const nextPlans = upsertServicePlanList(servicePlans, plan);
      setServicePlans(nextPlans);

      let nextSavedServices = savedServices;
      if (savedService?.private_notes_record_id && !currentPlan) {
        const updatedSavedService = apiConfig?.actorDid
          ? await updateWalletSavedService(apiConfig, savedService.saved_service_id, { privateNotesRecordId: recordId })
          : { ...savedService, private_notes_record_id: recordId, updated_at: new Date().toISOString() };
        nextSavedServices = upsertSavedServiceList(savedServices, updatedSavedService);
        setSavedServices(nextSavedServices);
      }

      if (!apiConfig?.actorDid) {
        writeLocalPortalCollections(nextSavedServices, nextPlans);
      }
      setSaveMessage("Private note saved.");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Private note could not be saved");
    } finally {
      setSavingNote(false);
    }
  }

  function addChecklistItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = newChecklistItem.trim();
    if (!text) return;
    updateChecklist(newChecklistKind, (items) => [...items, serializeChecklistItem({ text, done: false })]);
    setNewChecklistItem("");
  }

  function toggleChecklistItem(kind: ChecklistKind, index: number) {
    updateChecklist(kind, (items) =>
      items.map((item, itemIndex) => {
        if (itemIndex !== index) return item;
        const parsed = parseChecklistItem(item);
        return serializeChecklistItem({ ...parsed, done: !parsed.done });
      })
    );
  }

  function removeChecklistItem(kind: ChecklistKind, index: number) {
    updateChecklist(kind, (items) => items.filter((_, itemIndex) => itemIndex !== index));
  }

  function updateChecklist(kind: ChecklistKind, updater: (items: string[]) => string[]) {
    if (kind === "steps") setSteps((items) => updater(items));
    if (kind === "documentsNeeded") setDocumentsNeeded((items) => updater(items));
    if (kind === "questionsToAsk") setQuestionsToAsk((items) => updater(items));
  }

  const title = reference.title;
  const provider = reference.providerName || "Provider not listed";
  const location = [documentState.document?.city, documentState.document?.state].filter(Boolean).join(", ");

  return (
    <div className="screen service-plan-screen">
      <div className="page-title">
        <Button onClick={onBack} variant="quiet">
          <ArrowLeft aria-hidden="true" size={18} />
          Services
        </Button>
        <p className="eyebrow">Service plan</p>
        <h1>{title}</h1>
      </div>

      {documentState.status === "error" ? (
        <StatusBanner tone="warning">The 211 detail could not load: {documentState.error}</StatusBanner>
      ) : null}
      {portalLoadError ? <StatusBanner tone="warning">Wallet state could not refresh: {portalLoadError}</StatusBanner> : null}
      {saveMessage ? <StatusBanner tone="success">{saveMessage}</StatusBanner> : null}
      {saveError ? <StatusBanner tone="warning">{saveError}</StatusBanner> : null}

      <Section title="Service">
        <div className="list-item service-plan-summary">
          <div className="service-list-meta">
            <h3>{title}</h3>
            <p>{provider}</p>
            <div className="badge-row">
              {location ? <Badge tone="success">{location}</Badge> : null}
              {savedService ? <Badge tone="success">saved</Badge> : <Badge>not saved</Badge>}
              {currentPlan ? <Badge tone="success">plan ready</Badge> : <Badge>no plan yet</Badge>}
              {reference.sourceContentCid ? <Badge>source CID</Badge> : null}
            </div>
          </div>
          <div className="row-actions list-item-action">
            {reference.sourceUrl ? (
              <a className="button button-secondary" href={reference.sourceUrl} rel="noreferrer" target="_blank">
                <ExternalLink aria-hidden="true" size={18} />
                Source
              </a>
            ) : null}
            <Button onClick={() => onOpenDetail(reference.serviceDocId)} variant="secondary">
              <ClipboardList aria-hidden="true" size={18} />
              Detail
            </Button>
            <Button disabled={Boolean(savedService)} loading={savingService} loadingLabel="Saving" onClick={() => void saveService()}>
              <Bookmark aria-hidden="true" size={18} />
              {savedService ? "Saved" : "Save"}
            </Button>
          </div>
        </div>
      </Section>

      <Section title={currentPlan ? "Plan details" : "Create plan"}>
        <form className="form-grid" onSubmit={(event) => void savePlan(event)}>
          <Field label="Goal" required>
            <input value={goal} onChange={(event) => setGoal(event.target.value)} />
          </Field>
          <Field label="Status">
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="active">Active</option>
              <option value="in_progress">In progress</option>
              <option value="waiting">Waiting</option>
              <option value="completed">Completed</option>
              <option value="paused">Paused</option>
            </select>
          </Field>
          <Field label="Reminder">
            <input type="datetime-local" value={reminderAt} onChange={(event) => setReminderAt(event.target.value)} />
          </Field>
          <Field label="Appointment">
            <input type="datetime-local" value={appointmentAt} onChange={(event) => setAppointmentAt(event.target.value)} />
          </Field>
          <Field label="Travel target">
            <input value={travelTarget} onChange={(event) => setTravelTarget(event.target.value)} />
          </Field>
          <div className="full-span row-actions">
            <Button disabled={!goal.trim()} loading={savingPlan} loadingLabel="Saving" type="submit">
              <Save aria-hidden="true" size={18} />
              {currentPlan ? "Save plan" : "Create plan"}
            </Button>
          </div>
        </form>
      </Section>

      <Section title="Checklist">
        <div className="service-plan-checklists">
          <ChecklistGroup
            items={steps}
            kind="steps"
            onRemove={removeChecklistItem}
            onToggle={toggleChecklistItem}
            title="Steps"
          />
          <ChecklistGroup
            items={documentsNeeded}
            kind="documentsNeeded"
            onRemove={removeChecklistItem}
            onToggle={toggleChecklistItem}
            title="Documents"
          />
          <ChecklistGroup
            items={questionsToAsk}
            kind="questionsToAsk"
            onRemove={removeChecklistItem}
            onToggle={toggleChecklistItem}
            title="Questions"
          />
        </div>
        <form className="inline-form" onSubmit={addChecklistItem}>
          <Field label="Checklist type">
            <select value={newChecklistKind} onChange={(event) => setNewChecklistKind(event.target.value as ChecklistKind)}>
              <option value="steps">Steps</option>
              <option value="documentsNeeded">Documents</option>
              <option value="questionsToAsk">Questions</option>
            </select>
          </Field>
          <Field label="Checklist item">
            <input value={newChecklistItem} onChange={(event) => setNewChecklistItem(event.target.value)} />
          </Field>
          <Button disabled={!newChecklistItem.trim()} type="submit">
            <Plus aria-hidden="true" size={18} />
            Add
          </Button>
        </form>
        <div className="row-actions">
          <Button disabled={!goal.trim()} loading={savingPlan} loadingLabel="Saving" onClick={() => void savePlan()}>
            <CheckSquare aria-hidden="true" size={18} />
            Save checklist
          </Button>
        </div>
      </Section>

      <Section title="Private notes">
        <div className="review-panel service-notes-panel">
          <div className="badge-row">
            <Badge tone="warning">
              <LockKeyhole aria-hidden="true" size={14} />
              encrypted note record
            </Badge>
            {noteRecordId ? <Badge>{noteRecordId}</Badge> : <Badge>not saved yet</Badge>}
          </div>
          {noteLoading ? <StatusBanner tone="info">Decrypting private note.</StatusBanner> : null}
          {noteLoadError ? <StatusBanner tone="warning">Private note could not load: {noteLoadError}</StatusBanner> : null}
          <Field label="Notes">
            <textarea value={noteText} onChange={(event) => setNoteText(event.target.value)} />
          </Field>
          <div className="row-actions">
            <Button loading={savingNote} loadingLabel="Saving note" onClick={() => void savePrivateNote()}>
              <LockKeyhole aria-hidden="true" size={18} />
              Save private note
            </Button>
          </div>
        </div>
      </Section>
    </div>
  );
}

function ChecklistGroup({
  items,
  kind,
  onRemove,
  onToggle,
  title
}: {
  items: string[];
  kind: ChecklistKind;
  onRemove: (kind: ChecklistKind, index: number) => void;
  onToggle: (kind: ChecklistKind, index: number) => void;
  title: string;
}) {
  return (
    <div className="review-panel checklist-group">
      <div className="scope-header">
        <h3>{title}</h3>
        <Badge>{items.length}</Badge>
      </div>
      {items.length === 0 ? (
        <p className="supporting-copy">No items yet.</p>
      ) : (
        <div className="plan-checklist-list">
          {items.map((item, index) => {
            const parsed = parseChecklistItem(item);
            return (
              <label className="plan-checklist-row" key={`${kind}-${parsed.text}-${index}`}>
                <input checked={parsed.done} onChange={() => onToggle(kind, index)} type="checkbox" />
                <span>{parsed.text}</span>
                <Button ariaLabel={`Remove ${parsed.text}`} onClick={() => onRemove(kind, index)} variant="quiet">
                  <Trash2 aria-hidden="true" size={18} />
                </Button>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}

function currentPlanInput(
  reference: ServiceReference,
  input: {
    goal: string;
    steps: string[];
    documentsNeeded: string[];
    questionsToAsk: string[];
    appointmentAt: string;
    reminderAt: string;
    travelTarget: string;
    status: string;
    privateNotesRecordId?: string;
  }
) {
  return {
    serviceDocId: reference.serviceDocId,
    sourceContentCid: reference.sourceContentCid,
    sourcePageCid: reference.sourcePageCid,
    serviceTitle: reference.title,
    providerName: reference.providerName,
    goal: input.goal.trim(),
    steps: cleanChecklistValues(input.steps),
    documentsNeeded: cleanChecklistValues(input.documentsNeeded),
    questionsToAsk: cleanChecklistValues(input.questionsToAsk),
    appointmentAt: input.appointmentAt,
    reminderAt: input.reminderAt,
    travelTarget: input.travelTarget.trim(),
    status: input.status,
    privateNotesRecordId: input.privateNotesRecordId
  };
}

function parseChecklistItem(value: string): { text: string; done: boolean } {
  const trimmed = value.trim();
  const doneMatch = trimmed.match(/^\[x\]\s*(.+)$/i);
  if (doneMatch) return { text: doneMatch[1].trim(), done: true };
  const pendingMatch = trimmed.match(/^\[\s\]\s*(.+)$/i);
  if (pendingMatch) return { text: pendingMatch[1].trim(), done: false };
  return { text: trimmed, done: false };
}

function serializeChecklistItem(item: { text: string; done: boolean }): string {
  return `${item.done ? "[x]" : "[ ]"} ${item.text.trim()}`;
}

function cleanChecklistValues(values: string[]): string[] {
  const seen = new Set<string>();
  const cleaned: string[] = [];
  for (const value of values) {
    const parsed = parseChecklistItem(value);
    if (!parsed.text || seen.has(parsed.text.toLowerCase())) continue;
    seen.add(parsed.text.toLowerCase());
    cleaned.push(serializeChecklistItem(parsed));
  }
  return cleaned;
}

function toDateTimeInputValue(value: string): string {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) return value.slice(0, 16);
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}
