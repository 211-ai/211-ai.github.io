import { FormEvent, useState } from "react";
import { MessageSquare, UsersRound } from "lucide-react";
import { Badge, Button, Field, Section } from "../../components/ui";
import type {
  DisclosureDataScope,
  DisclosureRecipientDraft,
  DisclosureRecipientType,
  RegistrationProfileDraft,
  ShelterContactRequest
} from "../../models/abby";
import { defaultDisclosureScopes } from "../../services/mockAbbyService";
import { t, tFormat, type SupportedLocale } from "../../lib/localization";
import { shelterOptions } from "../appState";
import { SharingCapabilityPreview, SharingScopeChecklist } from "../components/SharingScopeComponents";
import {
  LOCAL_PRECINCT_OPTIONS,
  LOCAL_PRECINCT_RELATIONSHIP,
  createEntityId,
  formatContactRequestStatus,
  formatRecipientType,
  isLocalPrecinctRecipient,
  localizedPrecinctName,
  localizedRelationshipName,
  toggleScopeSelection
} from "../utils/formatHelpers";

export function ContactsScreen({
  contactRequests,
  profile,
  recipients,
  siteLocale,
  setContactRequests,
  setRecipients
}: {
  contactRequests: ShelterContactRequest[];
  profile: RegistrationProfileDraft;
  recipients: DisclosureRecipientDraft[];
  siteLocale: SupportedLocale;
  setContactRequests: (requests: ShelterContactRequest[]) => void;
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
}) {
  const [contactCategory, setContactCategory] = useState<"person" | "shelter">("person");
  const [providerType, setProviderType] = useState<"shelter" | "police_precinct">("shelter");
  const [draft, setDraft] = useState({
    firstName: "",
    lastName: "",
    relationship: "",
    email: "",
    phone: "",
    type: "emergency_contact" as DisclosureRecipientType
  });
  const [draftScopes, setDraftScopes] = useState<DisclosureDataScope[]>([...defaultDisclosureScopes]);
  const [editingRecipientId, setEditingRecipientId] = useState<string | null>(null);
  const [editingScopes, setEditingScopes] = useState<DisclosureDataScope[]>([]);
  const [requestedShelter, setRequestedShelter] = useState(shelterOptions[0]);
  const [requestedPrecinct, setRequestedPrecinct] = useState(LOCAL_PRECINCT_OPTIONS[0]);

  const userName = profile.preferredName || profile.legalName || "Abby Example";
  const userContact = [profile.phone, profile.email].map((item) => item.trim()).filter(Boolean).join(" / ");
  const requestBelongsToCurrentUser = (request: ShelterContactRequest) =>
    request.userName.trim().toLowerCase() === userName.trim().toLowerCase() ||
    request.userContact.trim().toLowerCase() === userContact.trim().toLowerCase();
  const userShelterRequests = contactRequests.filter(requestBelongsToCurrentUser);
  const incomingShelterNudges = contactRequests.filter(
    (request) =>
      request.direction === "shelter_to_user" && request.status === "pending" && requestBelongsToCurrentUser(request)
  );
  const hasPendingRequestedShelter = contactRequests.some(
    (request) =>
      request.direction === "user_to_shelter" &&
      request.status === "pending" &&
      request.shelterName === requestedShelter &&
      requestBelongsToCurrentUser(request)
  );
  const hasSavedRequestedPrecinct = recipients.some((recipient) => isLocalPrecinctRecipient(recipient, requestedPrecinct));
  const editingRecipient = recipients.find((recipient) => recipient.id === editingRecipientId) ?? null;

  function addShelterRecipient(shelterName: string) {
    if (recipients.some((recipient) => recipient.type === "shelter_staff" && recipient.agencyName === shelterName)) {
      return;
    }

    setRecipients([
      ...recipients,
      {
        id: createEntityId("rec"),
        type: "shelter_staff",
        displayName: shelterName,
        relationship: "Shelter",
        email: "",
        phone: "",
        agencyName: shelterName,
        precinctName: "",
        verified: true,
        allowedScopes: ["identity_minimum"]
      }
    ]);
  }

  function addRecipient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.firstName) return;
    const displayName = [draft.firstName, draft.lastName].filter(Boolean).join(" ");
    setRecipients([
      ...recipients,
      {
        id: createEntityId("rec"),
        displayName,
        relationship: draft.relationship,
        email: draft.email,
        phone: draft.phone,
        type: draft.type,
        agencyName: "",
        precinctName: "",
        verified: false,
        allowedScopes: [...draftScopes]
      }
    ]);
    setDraft({ firstName: "", lastName: "", relationship: "", email: "", phone: "", type: "emergency_contact" });
    setDraftScopes([...defaultDisclosureScopes]);
  }

  function addPrecinctRecipient(precinctName: string) {
    if (recipients.some((recipient) => isLocalPrecinctRecipient(recipient, precinctName))) {
      return;
    }

    setRecipients([
      ...recipients,
      {
        id: createEntityId("rec"),
        type: "police_precinct",
        displayName: precinctName,
        relationship: LOCAL_PRECINCT_RELATIONSHIP,
        email: "",
        phone: "",
        agencyName: "",
        precinctName,
        verified: true,
        allowedScopes: ["identity_minimum"]
      }
    ]);
  }

  function openRecipientEditor(recipient: DisclosureRecipientDraft) {
    setEditingRecipientId(recipient.id);
    setEditingScopes([...recipient.allowedScopes]);
    window.setTimeout(() => document.getElementById(`recipient-edit-${recipient.id}`)?.focus(), 0);
  }

  function closeRecipientEditor(recipientId: string) {
    setEditingRecipientId(null);
    setEditingScopes([]);
    window.setTimeout(() => document.getElementById(`recipient-open-${recipientId}`)?.focus(), 0);
  }

  function saveRecipientScopes(recipientId: string) {
    setRecipients(
      recipients.map((recipient) =>
        recipient.id === recipientId ? { ...recipient, allowedScopes: [...editingScopes] } : recipient
      )
    );
    closeRecipientEditor(recipientId);
  }

  function removeRecipient(recipientId: string) {
    setRecipients(recipients.filter((item) => item.id !== recipientId));
    if (editingRecipientId === recipientId) {
      setEditingRecipientId(null);
      setEditingScopes([]);
    }
  }

  function requestShelterContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (hasPendingRequestedShelter) return;

    setContactRequests([
      ...contactRequests,
      {
        id: `shelter-request-${Date.now()}`,
        direction: "user_to_shelter",
        status: "pending",
        shelterName: requestedShelter,
        userName,
        userContact,
        createdAt: new Date().toISOString()
      }
    ]);
  }

  function decideShelterNudge(requestId: string, status: "approved" | "denied") {
    const request = contactRequests.find((item) => item.id === requestId);
    if (!request) return;

    if (status === "approved") {
      addShelterRecipient(request.shelterName);
    }

    setContactRequests(
      contactRequests.map((item) =>
        item.id === requestId ? { ...item, status, decidedAt: new Date().toISOString() } : item
      )
    );
  }

  function cancelShelterRequest(requestId: string) {
    setContactRequests(
      contactRequests.map((item) =>
        item.id === requestId && item.direction === "user_to_shelter" && item.status === "pending"
          ? { ...item, status: "canceled", decidedAt: new Date().toISOString() }
          : item
      )
    );
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "contacts.eyebrow")}</p>
        <h1>{t(siteLocale, "contacts.title")}</h1>
      </div>
      <p className="page-note">{t(siteLocale, "contacts.note")}</p>
      <Section title={t(siteLocale, "contacts.addContact")}>
        <div className="contact-type-toggle">
          <label className={`contact-type-option${contactCategory === "person" ? " contact-type-option--active" : ""}`}>
            <input
              checked={contactCategory === "person"}
              name="contactCategory"
              onChange={() => setContactCategory("person")}
              type="radio"
              value="person"
            />
            {t(siteLocale, "contacts.person")}
          </label>
          <label className={`contact-type-option${contactCategory === "shelter" ? " contact-type-option--active" : ""}`}>
            <input
              checked={contactCategory === "shelter"}
              name="contactCategory"
              onChange={() => setContactCategory("shelter")}
              type="radio"
              value="shelter"
            />
            {t(siteLocale, "contacts.shelterGroup")}
          </label>
        </div>
        {contactCategory === "person" ? (
          <form className="form-grid" onSubmit={addRecipient}>
            <Field label={t(siteLocale, "contacts.firstName")} required>
              <input value={draft.firstName} onChange={(event) => setDraft({ ...draft, firstName: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.lastName")}>
              <input value={draft.lastName} onChange={(event) => setDraft({ ...draft, lastName: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.relationshipRole")}>
              <input value={draft.relationship} onChange={(event) => setDraft({ ...draft, relationship: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.phone")}>
              <input value={draft.phone} onChange={(event) => setDraft({ ...draft, phone: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.email")}>
              <input type="email" value={draft.email} onChange={(event) => setDraft({ ...draft, email: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.type")}>
              <select
                value={draft.type}
                onChange={(event) => setDraft({ ...draft, type: event.target.value as DisclosureRecipientType })}
              >
                <option value="emergency_contact">{t(siteLocale, "contacts.recipientType.emergency_contact")}</option>
                <option value="social_worker">{t(siteLocale, "contacts.recipientType.social_worker")}</option>
                <option value="police_precinct">{t(siteLocale, "contacts.recipientType.police_precinct")}</option>
                <option value="government_liaison">{t(siteLocale, "contacts.recipientType.government_liaison")}</option>
                <option value="benefits_agency">{t(siteLocale, "contacts.recipientType.benefits_agency")}</option>
              </select>
            </Field>
            <SharingScopeChecklist
              help={t(siteLocale, "contacts.scopeHelp")}
              label={t(siteLocale, "contacts.scopeForPerson")}
              onToggle={(scope) => setDraftScopes(toggleScopeSelection(draftScopes, scope))}
              scopes={draftScopes}
              siteLocale={siteLocale}
            />
            <div className="full-span centered-action">
              <Button type="submit">
                <UsersRound aria-hidden="true" size={18} /> {t(siteLocale, "contacts.addPerson")}
              </Button>
            </div>
          </form>
        ) : (
          <>
            <p className="section-note">
              {providerType === "shelter"
                ? t(siteLocale, "contacts.providerNoteShelter")
                : t(siteLocale, "contacts.providerNotePrecinct")}
            </p>
            <form
              className="form-grid"
              onSubmit={(event) => {
                if (providerType === "shelter") {
                  requestShelterContact(event);
                  return;
                }
                event.preventDefault();
                addPrecinctRecipient(requestedPrecinct);
              }}
            >
              <Field label={t(siteLocale, "contacts.providerType")}>
                <select
                  value={providerType}
                  onChange={(event) => setProviderType(event.target.value as "shelter" | "police_precinct")}
                >
                  <option value="shelter">{t(siteLocale, "contacts.shelterGroup")}</option>
                  <option value="police_precinct">{t(siteLocale, "contacts.defaultPrecinct")}</option>
                </select>
              </Field>
              <Field label={providerType === "shelter" ? t(siteLocale, "contacts.shelterName") : t(siteLocale, "contacts.localPrecinct")}>
                <select
                  value={providerType === "shelter" ? requestedShelter : requestedPrecinct}
                  onChange={(event) =>
                    providerType === "shelter"
                      ? setRequestedShelter(event.target.value)
                      : setRequestedPrecinct(event.target.value)
                  }
                >
                  {(providerType === "shelter" ? shelterOptions : LOCAL_PRECINCT_OPTIONS).map((providerName) => (
                    <option key={providerName} value={providerName}>
                      {providerType === "shelter" ? providerName : localizedPrecinctName(providerName, siteLocale)}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="full-span centered-action">
                <Button
                  disabled={providerType === "shelter" ? hasPendingRequestedShelter : hasSavedRequestedPrecinct}
                  type="submit"
                  variant="secondary"
                >
                  <MessageSquare aria-hidden="true" size={18} />{" "}
                  {providerType === "shelter" ? t(siteLocale, "contacts.askAddShelter") : t(siteLocale, "contacts.addLocalPrecinct")}
                </Button>
              </div>
              {(providerType === "shelter" ? hasPendingRequestedShelter : hasSavedRequestedPrecinct) ? (
                <small className="full-span pin-request-note">
                  {providerType === "shelter"
                    ? t(siteLocale, "contacts.pendingShelterRequest")
                    : t(siteLocale, "contacts.savedPrecinctExists")}
                </small>
              ) : null}
            </form>
            <div className="list-stack">
              {incomingShelterNudges.map((request) => (
                <article className="list-item access-request-item" key={request.id}>
                  <div>
                    <h3>{request.shelterName}</h3>
                    <p>{tFormat(siteLocale, "contacts.staffAsked", { staff: request.staffName || t(siteLocale, "contacts.defaultStaffName") })}</p>
                    <Badge>{formatContactRequestStatus(request.status, siteLocale)}</Badge>
                  </div>
                  <div className="row-actions">
                    <Button onClick={() => decideShelterNudge(request.id, "approved")} variant="secondary">
                      {t(siteLocale, "contacts.approve")}
                    </Button>
                    <Button onClick={() => decideShelterNudge(request.id, "denied")} variant="danger">
                      {t(siteLocale, "contacts.deny")}
                    </Button>
                  </div>
                </article>
              ))}
              {userShelterRequests.map((request) => (
                <article className="list-item" key={`status-${request.id}`}>
                  <div>
                    <h3>{request.shelterName}</h3>
                    <p>{request.direction === "user_to_shelter" ? t(siteLocale, "contacts.youAskedShelter") : t(siteLocale, "contacts.shelterAskedYou")}</p>
                  </div>
                  <div className="row-actions">
                    <Badge tone={request.status === "approved" ? "success" : request.status === "denied" ? "warning" : "neutral"}>
                      {formatContactRequestStatus(request.status, siteLocale)}
                    </Badge>
                    {request.direction === "user_to_shelter" && request.status === "pending" ? (
                      <Button onClick={() => cancelShelterRequest(request.id)} variant="secondary">
                        {t(siteLocale, "contacts.cancel")}
                      </Button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </Section>
      <Section title={t(siteLocale, "contacts.savedContacts")}>
        {recipients.length === 0 ? (
          <p className="empty-state">{t(siteLocale, "contacts.emptySavedContacts")}</p>
        ) : (
          <>
            <div className="list-stack">
              {recipients.map((recipient) => {
                const isEditing = editingRecipient?.id === recipient.id;

                return (
                  <article className="list-item recipient-list-item" key={recipient.id}>
                    <div className="recipient-row">
                      <button
                        aria-controls={`recipient-edit-${recipient.id}`}
                        aria-expanded={isEditing}
                        aria-label={tFormat(siteLocale, "contacts.editSharingFor", { name: recipient.displayName })}
                        className="recipient-open-button"
                        id={`recipient-open-${recipient.id}`}
                        onClick={() => openRecipientEditor(recipient)}
                        type="button"
                      >
                        <span className="recipient-summary">
                          <span className="recipient-name">{recipient.displayName}</span>
                          <span className="recipient-details">
                            <span>{localizedRelationshipName(recipient.relationship || recipient.agencyName || formatRecipientType(recipient.type, siteLocale), siteLocale)}</span>
                            {recipient.email ? <span>{recipient.email}</span> : null}
                            {recipient.phone ? <span>{recipient.phone}</span> : null}
                          </span>
                          <span className="badge-row" aria-label={`${recipient.displayName} status`}>
                            <Badge tone={recipient.verified ? "success" : "warning"}>
                              {recipient.verified ? t(siteLocale, "contacts.verified") : t(siteLocale, "contacts.needsCheck")}
                            </Badge>
                            <Badge>{recipient.allowedScopes.length} {t(siteLocale, "contacts.items")}</Badge>
                          </span>
                        </span>
                      </button>
                      <div className="row-actions">
                        <Button
                          ariaControls={`recipient-edit-${recipient.id}`}
                          ariaExpanded={isEditing}
                          className="compact-list-action"
                          onClick={() => openRecipientEditor(recipient)}
                          variant="secondary"
                        >
                          {t(siteLocale, "contacts.editSharing")}
                        </Button>
                        <Button
                          ariaLabel={`${t(siteLocale, "contacts.remove")} ${recipient.displayName}`}
                          className="compact-list-action"
                          onClick={() => removeRecipient(recipient.id)}
                          variant="quiet"
                        >
                          {t(siteLocale, "contacts.remove")}
                        </Button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
            {editingRecipient ? (
              <div
                aria-labelledby={`recipient-edit-heading-${editingRecipient.id}`}
                className="recipient-edit-panel"
                id={`recipient-edit-${editingRecipient.id}`}
                role="region"
                tabIndex={-1}
              >
                <div className="scope-header">
                  <div>
                    <h3 id={`recipient-edit-heading-${editingRecipient.id}`}>
                      {tFormat(siteLocale, "contacts.editSharingFor", { name: editingRecipient.displayName })}
                    </h3>
                    <p>{t(siteLocale, "contacts.saveOnlyWhatContactShouldSee")}</p>
                  </div>
                  <Badge>{editingScopes.length} {t(siteLocale, "contacts.selected")}</Badge>
                </div>
                <SharingScopeChecklist
                  label={tFormat(siteLocale, "contacts.scopeForName", { name: editingRecipient.displayName })}
                  onToggle={(scope) => setEditingScopes(toggleScopeSelection(editingScopes, scope))}
                  scopes={editingScopes}
                  siteLocale={siteLocale}
                />
                <SharingCapabilityPreview recipientName={editingRecipient.displayName} scopes={editingScopes} siteLocale={siteLocale} />
                <div className="row-actions">
                  <Button onClick={() => saveRecipientScopes(editingRecipient.id)}>{t(siteLocale, "contacts.saveSharing")}</Button>
                  <Button onClick={() => closeRecipientEditor(editingRecipient.id)} variant="secondary">
                    {t(siteLocale, "contacts.cancel")}
                  </Button>
                </div>
              </div>
            ) : null}
          </>
        )}
      </Section>
    </div>
  );
}
