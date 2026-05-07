import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CalendarPlus,
  ClipboardList,
  ExternalLink,
  FileText,
  LockKeyhole,
  Plus,
  Save,
  Trash2
} from "lucide-react";
import { Badge, Button, Field, Section, StatusBanner } from "../components/ui";
import {
  candidateFromSavedService,
  cleanList,
  createLocalSavedService,
  createLocalServiceInteraction,
  createLocalServicePlan,
  findSavedService,
  findPlanForService,
  serviceLocation,
  stableSuffix,
  upsertSavedService,
  upsertServiceInteraction,
  upsertServicePlan,
  type ServiceCandidate
} from "../components/services/SavedServicesPanel";
import {
  load211ArtifactManifest,
  load211Documents,
  load211GeneratedManifest,
  type CorpusDocument
} from "../lib/graphrag";
import type { SavedService, ServiceInteractionEvent, ServicePlan } from "../models/abby";
import {
  addTextDocument,
  createWalletServiceInteraction,
  createWalletServicePlan,
  decryptRecordWithGrant,
  saveWalletService,
  updateWalletServicePlan,
  type WalletApiConfig
} from "../services/walletApi";
import { downloadCalendarAction } from "../services/serviceActionService";

type ServicePlanDocumentState =
  | { status: "loading"; document: null; error: "" }
  | { status: "ready"; document: CorpusDocument; error: "" }
  | { status: "not-found"; document: null; error: "" }
  | { status: "error"; document: null; error: string };

type ChecklistKind = "steps" | "documents_needed" | "questions_to_ask";

interface ServicePlanScreenProps {
  docId: string;
  apiConfig?: WalletApiConfig;
  savedServices: SavedService[];
  servicePlans: ServicePlan[];
  serviceInteractions: ServiceInteractionEvent[];
  setSavedServices: (services: SavedService[]) => void;
  setServicePlans: (plans: ServicePlan[]) => void;
  setServiceInteractions: (interactions: ServiceInteractionEvent[]) => void;
  onBack: () => void;
  onOpenDetail: (docId: string) => void;
  refreshWalletAuditEvents?: () => Promise<void>;
}

const servicePlanPrefix = "#/services/";
const LOCAL_NOTE_STORE_KEY = "abby-service-private-notes-v1";
const LOCAL_CHECKLIST_STORE_KEY = "abby-service-plan-checks-v1";

export function getServicePlanDocIdFromHash(
  hash = typeof window === "undefined" ? "" : window.location.hash
): string | null {
  if (!hash.startsWith(servicePlanPrefix)) return null;
  const parts = hash.slice(servicePlanPrefix.length).split("/");
  if (parts[1] !== "plan") return null;
  try {
    return parts[0] ? decodeURIComponent(parts[0]) : null;
  } catch {
    return parts[0] || null;
  }
}

export function servicePlanRouteHash(docId: string): string {
  return `${servicePlanPrefix}${encodeURIComponent(docId.trim())}/plan`;
}

export function setLocationServicePlanHash(docId: string): void {
  if (typeof window === "undefined") return;
  window.location.hash = servicePlanRouteHash(docId);
}

export function ServicePlanScreen({
  docId,
  apiConfig,
  savedServices,
  servicePlans,
  serviceInteractions,
  setSavedServices,
  setServicePlans,
  setServiceInteractions,
  onBack,
  onOpenDetail,
  refreshWalletAuditEvents
}: ServicePlanScreenProps) {
  const [documentState, setDocumentState] = useState<ServicePlanDocumentState>({
    status: "loading",
    document: null,
    error: ""
  });
  const [goal, setGoal] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [documentsNeeded, setDocumentsNeeded] = useState<string[]>([]);
  const [questionsToAsk, setQuestionsToAsk] = useState<string[]>([]);
  const [appointmentAt, setAppointmentAt] = useState("");
  const [reminderAt, setReminderAt] = useState("");
  const [travelTarget, setTravelTarget] = useState("");
  const [status, setStatus] = useState("active");
  const [newStep, setNewStep] = useState("");
  const [newDocument, setNewDocument] = useState("");
  const [newQuestion, setNewQuestion] = useState("");
  const [notesDraft, setNotesDraft] = useState("");
  const [notesDirty, setNotesDirty] = useState(false);
  const [notesRecordId, setNotesRecordId] = useState("");
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});
  const [checkedItemsKey, setCheckedItemsKey] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [notice, setNotice] = useState<{ tone: "success" | "warning" | "info"; text: string } | null>(null);

  const savedService = findSavedService(savedServices, docId);
  const existingPlan = findPlanForService(servicePlans, docId);
  const candidate = useMemo(
    () => resolveServiceCandidate(docId, documentState.document, savedService, existingPlan),
    [docId, documentState.document, existingPlan, savedService]
  );
  const checklistStorageKey = existingPlan?.plan_id || `draft-${candidate.serviceDocId}`;

  useEffect(() => {
    let canceled = false;

    async function loadServiceDocument() {
      setDocumentState({ status: "loading", document: null, error: "" });
      try {
        const [documentsState] = await Promise.all([
          load211Documents(),
          load211ArtifactManifest(),
          load211GeneratedManifest()
        ]);
        if (canceled) return;
        const document =
          documentsState.documentById.get(docId) ??
          documentsState.documentByContentCid.get(docId) ??
          documentsState.documents.find((item) => item.source_page_cid === docId) ??
          null;
        setDocumentState(document ? { status: "ready", document, error: "" } : { status: "not-found", document: null, error: "" });
      } catch (error) {
        if (canceled) return;
        setDocumentState({
          status: "error",
          document: null,
          error: error instanceof Error ? error.message : "Service plan details unavailable"
        });
      }
    }

    void loadServiceDocument();

    return () => {
      canceled = true;
    };
  }, [docId]);

  useEffect(() => {
    if (existingPlan) {
      setGoal(existingPlan.goal);
      setSteps(existingPlan.steps);
      setDocumentsNeeded(existingPlan.documents_needed);
      setQuestionsToAsk(existingPlan.questions_to_ask);
      setAppointmentAt(toDateTimeLocalValue(existingPlan.appointment_at));
      setReminderAt(toDateTimeLocalValue(existingPlan.reminder_at));
      setTravelTarget(existingPlan.travel_target);
      setStatus(existingPlan.status || "active");
      return;
    }

    setGoal(candidate.providerName ? `Contact ${candidate.providerName}` : `Contact ${candidate.title}`);
    setSteps(["Confirm eligibility", "Ask how to apply", "Write down next follow-up"]);
    setDocumentsNeeded([]);
    setQuestionsToAsk(["What should I bring?", "When should I call or visit?"]);
    setAppointmentAt("");
    setReminderAt("");
    setTravelTarget(serviceLocation(candidate) || candidate.sourceUrl || "");
    setStatus("active");
  }, [candidate, existingPlan]);

  useEffect(() => {
    setCheckedItems(readChecklistCompletion(checklistStorageKey));
    setCheckedItemsKey(checklistStorageKey);
  }, [checklistStorageKey]);

  useEffect(() => {
    if (checkedItemsKey !== checklistStorageKey) return;
    writeChecklistCompletion(checklistStorageKey, checkedItems);
  }, [checkedItems, checkedItemsKey, checklistStorageKey]);

  useEffect(() => {
    const recordId = existingPlan?.private_notes_record_id || savedService?.private_notes_record_id || "";
    setNotesRecordId(recordId);
    setNotesDirty(false);

    if (!recordId) {
      setNotesDraft("");
      return;
    }

    let canceled = false;
    async function loadPrivateNotes() {
      const localNote = readLocalProtectedNote(recordId);
      if (localNote !== null) {
        setNotesDraft(localNote);
        setNotice({ tone: "info", text: "Private notes were restored from this browser." });
        return;
      }

      if (!apiConfig?.actorDid) {
        setNotesDraft("");
        return;
      }

      try {
        const decrypted = await decryptRecordWithGrant(apiConfig, { recordId });
        if (canceled) return;
        setNotesDraft(decrypted.text);
        setNotice({ tone: "info", text: "Encrypted notes were restored from the wallet record." });
      } catch {
        if (canceled) return;
        setNotesDraft("");
        setNotice({
          tone: "info",
          text: "Encrypted notes are saved in the wallet. Add a new note here to replace the note record."
        });
      }
    }

    void loadPrivateNotes();

    return () => {
      canceled = true;
    };
  }, [apiConfig, existingPlan?.private_notes_record_id, savedService?.private_notes_record_id]);

  async function saveServiceOnly() {
    setBusyAction("save-service");
    setNotice(null);
    try {
      const privateNotesRecordId = await persistPrivateNotes(candidate);
      const saved = await persistSavedService(candidate, privateNotesRecordId);
      setSavedServices(upsertSavedService(savedServices, saved));
      await refreshWalletAuditEvents?.().catch(() => undefined);
      setNotice({ tone: "success", text: "Service saved. Private notes are stored by encrypted record ID." });
    } catch (error) {
      setNotice({ tone: "warning", text: error instanceof Error ? error.message : "Service could not be saved." });
    } finally {
      setBusyAction("");
    }
  }

  async function savePlan() {
    setBusyAction("save-plan");
    setNotice(null);
    try {
      const privateNotesRecordId = await persistPrivateNotes(candidate);
      const saved = await persistSavedService(candidate, privateNotesRecordId);
      const nextPlan = await persistPlan(candidate, privateNotesRecordId);
      const nextPlans = upsertServicePlan(servicePlans, nextPlan);
      setSavedServices(upsertSavedService(savedServices, saved));
      setServicePlans(nextPlans);

      if (!existingPlan) {
        const interaction = apiConfig?.actorDid
          ? await createWalletServiceInteraction(apiConfig, {
              serviceDocId: candidate.serviceDocId,
              sourceContentCid: candidate.sourceContentCid,
              sourcePageCid: candidate.sourcePageCid,
              providerName: candidate.providerName,
              programName: candidate.programName,
              interactionType: "service_plan_created",
              channel: "web",
              status: "recorded",
              sourceActionUrl: candidate.sourceUrl,
              relatedRecordIds: privateNotesRecordId ? [privateNotesRecordId] : [],
              privacyLevel: "private",
              metadata: { source: "service_plan_screen" }
            }).catch(() => undefined)
          : createLocalServiceInteraction(candidate, "service_plan_created", apiConfig?.walletId);
        if (interaction) {
          setServiceInteractions(upsertServiceInteraction(serviceInteractions, interaction));
        }
      }

      await refreshWalletAuditEvents?.().catch(() => undefined);
      setNotice({ tone: "success", text: existingPlan ? "Service plan updated." : "Service plan created." });
    } catch (error) {
      setNotice({ tone: "warning", text: error instanceof Error ? error.message : "Service plan could not be saved." });
    } finally {
      setBusyAction("");
    }
  }

  async function persistPrivateNotes(candidateForNote: ServiceCandidate): Promise<string> {
    if (!notesDirty) return notesRecordId;
    const text = notesDraft.trim();
    if (!text) return notesRecordId;

    if (apiConfig?.actorDid) {
      const uploaded = await addTextDocument(apiConfig, {
        filename: `${safeFileStem(candidateForNote.serviceDocId)}-private-notes.txt`,
        text,
        title: `Private notes for ${candidateForNote.title}`
      });
      const recordId = uploaded.recordId || uploaded.id;
      setNotesRecordId(recordId);
      setNotesDirty(false);
      return recordId;
    }

    const recordId = notesRecordId || `local-note-${stableSuffix(`${candidateForNote.serviceDocId}-${Date.now()}`)}`;
    writeLocalProtectedNote(recordId, text);
    setNotesRecordId(recordId);
    setNotesDirty(false);
    return recordId;
  }

  async function persistSavedService(candidateToSave: ServiceCandidate, privateNotesRecordId: string): Promise<SavedService> {
    if (apiConfig?.actorDid) {
      return saveWalletService(apiConfig, {
        serviceDocId: candidateToSave.serviceDocId,
        sourceContentCid: candidateToSave.sourceContentCid,
        sourcePageCid: candidateToSave.sourcePageCid,
        title: candidateToSave.title,
        providerName: candidateToSave.providerName,
        programName: candidateToSave.programName,
        sourceUrl: candidateToSave.sourceUrl,
        label: candidateToSave.title,
        reason: savedService?.reason || "Saved from service plan",
        priority: savedService?.priority || "normal",
        status: savedService?.status || "saved",
        privateNotesRecordId
      });
    }

    const localSaved = createLocalSavedService(
      candidateToSave,
      {
        label: savedService?.label || candidateToSave.title,
        reason: savedService?.reason || "Saved from service plan",
        priority: savedService?.priority || "normal",
        status: savedService?.status || "saved",
        privateNotesRecordId
      },
      apiConfig?.walletId
    );
    return savedService
      ? {
          ...localSaved,
          saved_service_id: savedService.saved_service_id,
          created_at: savedService.created_at,
          updated_at: new Date().toISOString()
        }
      : localSaved;
  }

  async function persistPlan(candidateForPlan: ServiceCandidate, privateNotesRecordId: string): Promise<ServicePlan> {
    const planInput = {
      sourceContentCid: candidateForPlan.sourceContentCid,
      sourcePageCid: candidateForPlan.sourcePageCid,
      serviceTitle: candidateForPlan.title,
      providerName: candidateForPlan.providerName,
      goal,
      steps: cleanList(steps),
      documentsNeeded: cleanList(documentsNeeded),
      questionsToAsk: cleanList(questionsToAsk),
      appointmentAt: fromDateTimeLocalValue(appointmentAt),
      reminderAt: fromDateTimeLocalValue(reminderAt),
      travelTarget: travelTarget.trim(),
      status,
      privateNotesRecordId
    };

    if (apiConfig?.actorDid) {
      if (existingPlan) {
        return updateWalletServicePlan(apiConfig, existingPlan.plan_id, planInput);
      }
      return createWalletServicePlan(apiConfig, {
        serviceDocId: candidateForPlan.serviceDocId,
        ...planInput
      });
    }

    if (existingPlan) {
      return {
        ...existingPlan,
        source_content_cid: planInput.sourceContentCid,
        source_page_cid: planInput.sourcePageCid,
        service_title: planInput.serviceTitle,
        provider_name: planInput.providerName,
        goal: planInput.goal,
        steps: planInput.steps,
        documents_needed: planInput.documentsNeeded,
        questions_to_ask: planInput.questionsToAsk,
        appointment_at: planInput.appointmentAt,
        reminder_at: planInput.reminderAt,
        travel_target: planInput.travelTarget,
        status: planInput.status,
        private_notes_record_id: planInput.privateNotesRecordId,
        updated_at: new Date().toISOString()
      };
    }

    return createLocalServicePlan(
      candidateForPlan,
      {
        goal: planInput.goal,
        steps: planInput.steps,
        documentsNeeded: planInput.documentsNeeded,
        questionsToAsk: planInput.questionsToAsk,
        appointmentAt: planInput.appointmentAt,
        reminderAt: planInput.reminderAt,
        travelTarget: planInput.travelTarget,
        status: planInput.status,
        privateNotesRecordId: planInput.privateNotesRecordId
      },
      apiConfig?.walletId
    );
  }

  function addChecklistItem(event: FormEvent<HTMLFormElement>, kind: ChecklistKind) {
    event.preventDefault();
    if (kind === "steps") {
      const item = newStep.trim();
      if (!item) return;
      setSteps(cleanList([...steps, item]));
      setNewStep("");
      return;
    }
    if (kind === "documents_needed") {
      const item = newDocument.trim();
      if (!item) return;
      setDocumentsNeeded(cleanList([...documentsNeeded, item]));
      setNewDocument("");
      return;
    }
    const item = newQuestion.trim();
    if (!item) return;
    setQuestionsToAsk(cleanList([...questionsToAsk, item]));
    setNewQuestion("");
  }

  function removeChecklistItem(kind: ChecklistKind, item: string) {
    if (kind === "steps") setSteps(steps.filter((value) => value !== item));
    if (kind === "documents_needed") setDocumentsNeeded(documentsNeeded.filter((value) => value !== item));
    if (kind === "questions_to_ask") setQuestionsToAsk(questionsToAsk.filter((value) => value !== item));
    setCheckedItems((current) => {
      const next = { ...current };
      delete next[checklistItemKey(kind, item)];
      return next;
    });
  }

  function toggleChecklistItem(kind: ChecklistKind, item: string) {
    const key = checklistItemKey(kind, item);
    setCheckedItems((current) => ({ ...current, [key]: !current[key] }));
  }

  function downloadReminder() {
    const startsAt = appointmentAt || reminderAt;
    if (!startsAt) {
      setNotice({ tone: "warning", text: "Add an appointment or reminder time before downloading a calendar file." });
      return;
    }
    try {
      downloadCalendarAction({
        title: candidate.title,
        notes: goal,
        startsAt: fromDateTimeLocalValue(startsAt),
        durationMinutes: 30,
        location: travelTarget,
        url: candidate.sourceUrl,
        alarms: [{ description: "Service plan reminder", triggerMinutesBefore: 60 }],
        context: {
          serviceDocId: candidate.serviceDocId,
          serviceTitle: candidate.title,
          providerName: candidate.providerName,
          programName: candidate.programName,
          sourceUrl: candidate.sourceUrl,
          sourceContentCid: candidate.sourceContentCid,
          sourcePageCid: candidate.sourcePageCid
        }
      });
      setNotice({ tone: "success", text: "Calendar file prepared." });
    } catch (error) {
      setNotice({ tone: "warning", text: error instanceof Error ? error.message : "Calendar file could not be created." });
    }
  }

  const title = candidate.title || docId;
  const checklistCount = steps.length + documentsNeeded.length + questionsToAsk.length;
  const checkedCount = Object.values(checkedItems).filter(Boolean).length;

  return (
    <div className="screen">
      <div className="page-title">
        <div className="row-actions" style={{ justifyContent: "flex-start" }}>
          <Button onClick={onBack} variant="quiet">
            <ArrowLeft aria-hidden="true" size={18} />
            Services
          </Button>
          <Button onClick={() => onOpenDetail(candidate.serviceDocId)} variant="secondary">
            <ExternalLink aria-hidden="true" size={18} />
            Detail
          </Button>
        </div>
        <p className="eyebrow">Service plan</p>
        <h1>{title}</h1>
      </div>

      {documentState.status === "error" ? (
        <StatusBanner tone="warning">Source detail could not load: {documentState.error}</StatusBanner>
      ) : null}
      {documentState.status === "not-found" ? (
        <StatusBanner tone="info">This plan is using wallet data because the 211 corpus record was not found locally.</StatusBanner>
      ) : null}
      {notice ? <StatusBanner tone={notice.tone}>{notice.text}</StatusBanner> : null}

      <Section
        title="Service"
        actions={
          <div className="badge-row">
            {savedService ? <Badge tone="success">saved</Badge> : <Badge>not saved</Badge>}
            {existingPlan ? <Badge tone="success">plan saved</Badge> : <Badge>draft plan</Badge>}
          </div>
        }
      >
        <div className="list-stack">
          <article className="list-item">
            <div>
              <h3>{candidate.providerName || "Provider not listed"}</h3>
              <p>{candidate.programName || candidate.title}</p>
              <div className="badge-row">
                <Badge>{candidate.docType || "service"}</Badge>
                {serviceLocation(candidate) ? <Badge>{serviceLocation(candidate)}</Badge> : null}
                {notesRecordId ? <Badge tone="success">encrypted notes</Badge> : null}
              </div>
            </div>
            <div className="row-actions">
              {candidate.sourceUrl ? (
                <a className="button button-secondary" href={candidate.sourceUrl} rel="noreferrer" target="_blank">
                  <ExternalLink aria-hidden="true" size={18} />
                  Source
                </a>
              ) : null}
              <Button
                loading={busyAction === "save-service"}
                loadingLabel="Saving"
                onClick={saveServiceOnly}
                variant={savedService ? "secondary" : "primary"}
              >
                <Save aria-hidden="true" size={18} />
                {savedService ? "Update saved" : "Save service"}
              </Button>
            </div>
          </article>
        </div>
      </Section>

      <Section
        title="Plan details"
        actions={
          <Button loading={busyAction === "save-plan"} loadingLabel="Saving" onClick={savePlan}>
            <ClipboardList aria-hidden="true" size={18} />
            {existingPlan ? "Save plan" : "Create plan"}
          </Button>
        }
      >
        <div className="form-grid">
          <Field label="Goal">
            <input value={goal} onChange={(event) => setGoal(event.target.value)} />
          </Field>
          <Field label="Status">
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="active">Active</option>
              <option value="in_progress">In progress</option>
              <option value="waiting">Waiting</option>
              <option value="completed">Completed</option>
              <option value="unavailable">Unavailable</option>
            </select>
          </Field>
          <Field label="Appointment">
            <input type="datetime-local" value={appointmentAt} onChange={(event) => setAppointmentAt(event.target.value)} />
          </Field>
          <Field label="Reminder">
            <input type="datetime-local" value={reminderAt} onChange={(event) => setReminderAt(event.target.value)} />
          </Field>
          <Field label="Travel or contact target">
            <input value={travelTarget} onChange={(event) => setTravelTarget(event.target.value)} />
          </Field>
          <div className="full-span row-actions">
            <Button onClick={downloadReminder} variant="secondary">
              <CalendarPlus aria-hidden="true" size={18} />
              Calendar file
            </Button>
          </div>
        </div>
      </Section>

      <Section
        title="Checklist"
        actions={<Badge tone={checkedCount === checklistCount && checklistCount ? "success" : "neutral"}>{checkedCount}/{checklistCount}</Badge>}
      >
        <ChecklistGroup
          addLabel="Add step"
          checkedItems={checkedItems}
          inputValue={newStep}
          items={steps}
          kind="steps"
          onAdd={(event) => addChecklistItem(event, "steps")}
          onInputChange={setNewStep}
          onRemove={removeChecklistItem}
          onToggle={toggleChecklistItem}
          title="Steps"
        />
        <ChecklistGroup
          addLabel="Add document"
          checkedItems={checkedItems}
          inputValue={newDocument}
          items={documentsNeeded}
          kind="documents_needed"
          onAdd={(event) => addChecklistItem(event, "documents_needed")}
          onInputChange={setNewDocument}
          onRemove={removeChecklistItem}
          onToggle={toggleChecklistItem}
          title="Documents"
        />
        <ChecklistGroup
          addLabel="Add question"
          checkedItems={checkedItems}
          inputValue={newQuestion}
          items={questionsToAsk}
          kind="questions_to_ask"
          onAdd={(event) => addChecklistItem(event, "questions_to_ask")}
          onInputChange={setNewQuestion}
          onRemove={removeChecklistItem}
          onToggle={toggleChecklistItem}
          title="Questions"
        />
      </Section>

      <Section
        title="Private notes"
        actions={notesRecordId ? <Badge tone="success">{notesRecordId}</Badge> : <Badge>no note record</Badge>}
      >
        <div className="review-panel">
          <div className="scope-header">
            <div>
              <h3>Encrypted wallet note</h3>
              <p>Notes are saved as a private wallet text record and linked from the saved service or plan.</p>
            </div>
            <LockKeyhole aria-hidden="true" size={22} />
          </div>
          <Field label="Notes">
            <textarea
              value={notesDraft}
              onChange={(event) => {
                setNotesDraft(event.target.value);
                setNotesDirty(true);
              }}
            />
          </Field>
          {notesRecordId ? (
            <small className="upload-machine-summary">Private notes record: {notesRecordId}</small>
          ) : (
            <small className="upload-machine-summary">Save the service or plan to create a private notes record.</small>
          )}
        </div>
      </Section>
    </div>
  );
}

function ChecklistGroup({
  title,
  kind,
  items,
  checkedItems,
  inputValue,
  addLabel,
  onInputChange,
  onAdd,
  onToggle,
  onRemove
}: {
  title: string;
  kind: ChecklistKind;
  items: string[];
  checkedItems: Record<string, boolean>;
  inputValue: string;
  addLabel: string;
  onInputChange: (value: string) => void;
  onAdd: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (kind: ChecklistKind, item: string) => void;
  onRemove: (kind: ChecklistKind, item: string) => void;
}) {
  return (
    <div className="review-panel">
      <div className="scope-header">
        <div>
          <h3>{title}</h3>
          <p>{items.length} item{items.length === 1 ? "" : "s"}</p>
        </div>
        <FileText aria-hidden="true" size={22} />
      </div>
      {items.length ? (
        <div className="list-stack">
          {items.map((item) => {
            const checked = Boolean(checkedItems[checklistItemKey(kind, item)]);
            return (
              <article className="list-item" key={`${kind}-${item}`}>
                <label className="consent-box" style={{ border: 0, padding: 0 }}>
                  <input checked={checked} onChange={() => onToggle(kind, item)} type="checkbox" />
                  <span>
                    <strong>{item}</strong>
                    <small>{checked ? "Done" : "Still needed"}</small>
                  </span>
                </label>
                <Button ariaLabel={`Remove ${item}`} onClick={() => onRemove(kind, item)} variant="quiet">
                  <Trash2 aria-hidden="true" size={18} />
                </Button>
              </article>
            );
          })}
        </div>
      ) : (
        <p className="empty-state">No {title.toLowerCase()} yet.</p>
      )}
      <form className="form-grid" onSubmit={onAdd}>
        <Field label={addLabel}>
          <input value={inputValue} onChange={(event) => onInputChange(event.target.value)} />
        </Field>
        <div className="row-actions">
          <Button disabled={!inputValue.trim()} type="submit" variant="secondary">
            <Plus aria-hidden="true" size={18} />
            Add
          </Button>
        </div>
      </form>
    </div>
  );
}

function resolveServiceCandidate(
  docId: string,
  document: CorpusDocument | null,
  savedService: SavedService | undefined,
  plan: ServicePlan | undefined
): ServiceCandidate {
  if (document) {
    return {
      serviceDocId: document.doc_id || docId,
      sourceContentCid: document.source_content_cid || `ui-unresolved-${stableSuffix(docId)}`,
      sourcePageCid: document.source_page_cid || "",
      title: document.program_name || document.provider_name || document.title || docId,
      providerName: document.provider_name || "",
      programName: document.program_name || document.title || "",
      sourceUrl: document.source_url || "",
      city: document.city || "",
      state: document.state || "",
      docType: document.doc_type || "service"
    };
  }

  if (savedService) return candidateFromSavedService(savedService);

  if (plan) {
    return {
      serviceDocId: plan.service_doc_id,
      sourceContentCid: plan.source_content_cid || `ui-unresolved-${stableSuffix(plan.service_doc_id)}`,
      sourcePageCid: plan.source_page_cid || "",
      title: plan.service_title || plan.service_doc_id,
      providerName: plan.provider_name || "",
      programName: plan.service_title || "",
      sourceUrl: "",
      city: "",
      state: "",
      docType: "service"
    };
  }

  return {
    serviceDocId: docId,
    sourceContentCid: `ui-unresolved-${stableSuffix(docId)}`,
    sourcePageCid: "",
    title: docId,
    providerName: "",
    programName: "",
    sourceUrl: "",
    city: "",
    state: "",
    docType: "service"
  };
}

function checklistItemKey(kind: ChecklistKind, item: string): string {
  return `${kind}:${item}`;
}

function readChecklistCompletion(key: string): Record<string, boolean> {
  if (typeof window === "undefined") return {};
  try {
    const parsed = JSON.parse(window.localStorage.getItem(LOCAL_CHECKLIST_STORE_KEY) ?? "{}") as Record<
      string,
      Record<string, boolean>
    >;
    return parsed[key] ?? {};
  } catch {
    return {};
  }
}

function writeChecklistCompletion(key: string, value: Record<string, boolean>): void {
  if (typeof window === "undefined") return;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(LOCAL_CHECKLIST_STORE_KEY) ?? "{}") as Record<
      string,
      Record<string, boolean>
    >;
    parsed[key] = value;
    window.localStorage.setItem(LOCAL_CHECKLIST_STORE_KEY, JSON.stringify(parsed));
  } catch {
    // Checklist completion is UI-only state; leave wallet data untouched if local storage is unavailable.
  }
}

function readLocalProtectedNote(recordId: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(LOCAL_NOTE_STORE_KEY) ?? "{}") as Record<string, string>;
    const encoded = parsed[recordId];
    if (!encoded) return null;
    const decoded = decodeURIComponent(window.atob(encoded));
    const payload = JSON.parse(decoded) as { text?: string };
    return typeof payload.text === "string" ? payload.text : null;
  } catch {
    return null;
  }
}

function writeLocalProtectedNote(recordId: string, text: string): void {
  if (typeof window === "undefined") return;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(LOCAL_NOTE_STORE_KEY) ?? "{}") as Record<string, string>;
    parsed[recordId] = window.btoa(encodeURIComponent(JSON.stringify({ text, updatedAt: new Date().toISOString() })));
    window.localStorage.setItem(LOCAL_NOTE_STORE_KEY, JSON.stringify(parsed));
  } catch {
    // Local note fallback should never block saving the non-private service plan fields.
  }
}

function toDateTimeLocalValue(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 16);
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function fromDateTimeLocalValue(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}

function safeFileStem(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64) || "service";
}
