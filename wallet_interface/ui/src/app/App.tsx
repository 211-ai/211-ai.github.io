import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bell,
  BarChart3,
  CalendarCheck,
  ClipboardCheck,
  ContactRound,
  FileUp,
  HeartHandshake,
  Home,
  KeyRound,
  Landmark,
  LockKeyhole,
  LogOut,
  Menu,
  MessageSquare,
  ShieldCheck,
  Upload,
  UsersRound
} from "lucide-react";
import { ActionCard, Badge, Button, Field, Section, StatusBanner } from "../components/ui";
import {
  CheckInChannel,
  DisclosureDataScope,
  DisclosureRecipientDraft,
  DisclosureRecipientType,
  RegistrationProfileDraft,
  RouteId,
  UploadItem,
  WalletAccessRequest,
  ProofReceiptView
} from "../models/abby";
import {
  analyticsStudies,
  auditEvents,
  defaultCheckInPolicy,
  emptyRegistrationProfile,
  initialRecipients,
  initialAccessRequests,
  initialUploads,
  proofReceipts,
  serviceMatches
} from "../services/mockAbbyService";

const routes: Array<{ id: RouteId; label: string; icon: typeof Home }> = [
  { id: "home", label: "Home", icon: Home },
  { id: "register", label: "Register", icon: ClipboardCheck },
  { id: "check-in", label: "Check in", icon: CalendarCheck },
  { id: "contacts", label: "Contacts", icon: ContactRound },
  { id: "sharing-rules", label: "Sharing", icon: ShieldCheck },
  { id: "uploads", label: "Uploads", icon: FileUp },
  { id: "social-services", label: "Services", icon: HeartHandshake },
  { id: "shelter", label: "Shelter", icon: UsersRound }
];

const secondaryRoutes: Array<{ id: RouteId; label: string; icon: typeof Home }> = [
  { id: "recipient-access", label: "Recipient access", icon: KeyRound },
  { id: "benefits-protection", label: "Benefits opt-in", icon: Landmark },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "proof-center", label: "Proofs", icon: ShieldCheck },
  { id: "security", label: "Security", icon: LockKeyhole },
  { id: "audit", label: "Audit", icon: ClipboardCheck }
];

const serviceNeeds = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation"];

const disclosureScopes: Array<{ id: DisclosureDataScope; label: string; detail: string }> = [
  { id: "identity_minimum", label: "Minimum identity", detail: "Name, birth date, and contact status" },
  { id: "profile", label: "Profile", detail: "Basic profile details and service needs" },
  { id: "photo", label: "Photo", detail: "The account photo selected during setup" },
  { id: "current_location", label: "Current location", detail: "Most recent safe location or shelter" },
  { id: "uploaded_documents", label: "Uploads", detail: "Documents the user explicitly includes" },
  { id: "medical_notes", label: "Medical notes", detail: "Sensitive health context" },
  { id: "shelter_history", label: "Shelter history", detail: "Shelter stays and staff contact details" },
  { id: "benefits_information", label: "Benefits information", detail: "Benefits identifiers and status" },
  { id: "custom", label: "Custom note", detail: "A user-written emergency note" }
];

function getRouteFromHash(): RouteId {
  const route = window.location.hash.replace("#/", "") || "home";
  return [...routes, ...secondaryRoutes].some((item) => item.id === route) ? (route as RouteId) : "home";
}

export function App() {
  const [activeRoute, setActiveRoute] = useState<RouteId>(getRouteFromHash);
  const [profile, setProfile] = useState<RegistrationProfileDraft>(emptyRegistrationProfile);
  const [policy, setPolicy] = useState(defaultCheckInPolicy);
  const [recipients, setRecipients] = useState<DisclosureRecipientDraft[]>(initialRecipients);
  const [uploads, setUploads] = useState<UploadItem[]>(initialUploads);
  const [accessRequests, setAccessRequests] = useState<WalletAccessRequest[]>(initialAccessRequests);
  const [recipientVerified, setRecipientVerified] = useState(false);
  const [benefitsOptIn, setBenefitsOptIn] = useState(false);
  const [analyticsOptIn, setAnalyticsOptIn] = useState<Record<string, boolean>>({});
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    const syncRouteFromHash = () => setActiveRoute(getRouteFromHash());
    window.addEventListener("hashchange", syncRouteFromHash);
    return () => window.removeEventListener("hashchange", syncRouteFromHash);
  }, []);

  function navigate(route: RouteId) {
    window.location.hash = route === "home" ? "#/" : `#/${route}`;
    setActiveRoute(route);
    setMobileNavOpen(false);
  }

  const nextCheckIn = useMemo(() => {
    const next = new Date(policy.lastCheckInAt);
    next.setDate(next.getDate() + policy.intervalDays);
    return next.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }, [policy.intervalDays, policy.lastCheckInAt]);

  return (
    <div className="app">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark">A</span>
          <div>
            <strong>Abby</strong>
            <small>Safety and services</small>
          </div>
        </div>
        <nav className="nav-list">
          {routes.map((route) => (
            <NavButton
              active={activeRoute === route.id}
              icon={route.icon}
              key={route.id}
              label={route.label}
              onClick={() => navigate(route.id)}
            />
          ))}
        </nav>
        <div className="nav-secondary">
          {secondaryRoutes.map((route) => (
            <NavButton
              active={activeRoute === route.id}
              icon={route.icon}
              key={route.id}
              label={route.label}
              onClick={() => navigate(route.id)}
            />
          ))}
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <Button
            ariaControls="mobile-navigation"
            ariaExpanded={mobileNavOpen}
            ariaLabel={mobileNavOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            variant="quiet"
          >
            <Menu size={20} />
          </Button>
          <div>
            <strong>Abby</strong>
            <small>Next check-in: {nextCheckIn}</small>
          </div>
          <Button ariaLabel="Sign out" variant="quiet">
            <LogOut size={20} />
          </Button>
        </header>

        {mobileNavOpen ? (
          <nav className="mobile-nav-panel" id="mobile-navigation" aria-label="Mobile navigation">
            {[...routes, ...secondaryRoutes].map((route) => (
              <NavButton
                active={activeRoute === route.id}
                icon={route.icon}
                key={route.id}
                label={route.label}
                onClick={() => navigate(route.id)}
              />
            ))}
          </nav>
        ) : null}

        {activeRoute === "home" ? (
          <HomeScreen navigate={navigate} nextCheckIn={nextCheckIn} recipients={recipients} uploads={uploads} />
        ) : null}
        {activeRoute === "register" ? <RegistrationScreen profile={profile} setProfile={setProfile} /> : null}
        {activeRoute === "check-in" ? (
          <CheckInScreen nextCheckIn={nextCheckIn} policy={policy} setPolicy={setPolicy} />
        ) : null}
        {activeRoute === "contacts" ? <ContactsScreen recipients={recipients} setRecipients={setRecipients} /> : null}
        {activeRoute === "sharing-rules" ? (
          <SharingRulesScreen recipients={recipients} setRecipients={setRecipients} />
        ) : null}
        {activeRoute === "uploads" ? <UploadsScreen uploads={uploads} setUploads={setUploads} /> : null}
        {activeRoute === "social-services" ? <SocialServicesScreen /> : null}
        {activeRoute === "shelter" ? <ShelterScreen /> : null}
        {activeRoute === "recipient-access" ? (
          <RecipientAccessScreen
            accessRequests={accessRequests}
            recipients={recipients}
            setAccessRequests={setAccessRequests}
            verified={recipientVerified}
            setVerified={setRecipientVerified}
          />
        ) : null}
        {activeRoute === "benefits-protection" ? (
          <BenefitsProtectionScreen optedIn={benefitsOptIn} setOptedIn={setBenefitsOptIn} />
        ) : null}
        {activeRoute === "analytics" ? (
          <AnalyticsScreen optedIn={analyticsOptIn} setOptedIn={setAnalyticsOptIn} />
        ) : null}
        {activeRoute === "proof-center" ? <ProofCenterScreen proofs={proofReceipts} /> : null}
        {activeRoute === "security" ? <SecurityScreen /> : null}
        {activeRoute === "audit" ? <AuditScreen /> : null}
      </main>
    </div>
  );
}

function NavButton({
  active,
  icon: Icon,
  label,
  onClick
}: {
  active: boolean;
  icon: typeof Home;
  label: string;
  onClick: () => void;
}) {
  return (
    <button aria-current={active ? "page" : undefined} className="nav-button" onClick={onClick} type="button">
      <Icon aria-hidden="true" size={19} />
      <span>{label}</span>
    </button>
  );
}

function HomeScreen({
  navigate,
  nextCheckIn,
  recipients,
  uploads
}: {
  navigate: (route: RouteId) => void;
  nextCheckIn: string;
  recipients: DisclosureRecipientDraft[];
  uploads: UploadItem[];
}) {
  return (
    <div className="screen home-screen">
      <div className="page-title">
        <p className="eyebrow">Today</p>
        <h1>Your safety plan</h1>
      </div>
      <div className="home-actions" aria-label="Primary actions">
        <ActionCard
          detail={`${recipients.length} recipients configured`}
          icon={<ContactRound aria-hidden="true" size={28} />}
          onClick={() => navigate("contacts")}
          title="Emergency contacts"
        />
        <ActionCard
          detail="Find shelter, food, benefits, health, and legal help"
          icon={<HeartHandshake aria-hidden="true" size={28} />}
          onClick={() => navigate("social-services")}
          title="Social services"
        />
      </div>
      <div className="dashboard-grid">
        <StatusPanel label="Next check-in" value={nextCheckIn} tone="teal" />
        <StatusPanel label="Stored uploads" value={String(uploads.length)} tone="gold" />
        <StatusPanel label="Sharing rules" value="Review due" tone="red" />
      </div>
      <Section title="Quick actions">
        <div className="quick-actions">
          <Button onClick={() => navigate("check-in")}>
            <CalendarCheck size={18} /> Check in now
          </Button>
          <Button onClick={() => navigate("sharing-rules")} variant="secondary">
            <ShieldCheck size={18} /> Review sharing
          </Button>
        </div>
      </Section>
    </div>
  );
}

function StatusPanel({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className={`status-panel panel-${tone}`}>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function RegistrationScreen({
  profile,
  setProfile
}: {
  profile: RegistrationProfileDraft;
  setProfile: (profile: RegistrationProfileDraft) => void;
}) {
  const requiredMissing = !profile.legalName || !profile.dateOfBirth || !profile.photoAssetId || !profile.captchaToken;
  const update = (patch: Partial<RegistrationProfileDraft>) => setProfile({ ...profile, ...patch });

  function toggleNeed(need: string) {
    update({
      serviceNeeds: profile.serviceNeeds.includes(need)
        ? profile.serviceNeeds.filter((item) => item !== need)
        : [...profile.serviceNeeds, need]
    });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Registration</p>
        <h1>Create your Abby profile</h1>
      </div>
      <StatusBanner tone="info">Only name, birth date, photo, and bot check are required to start.</StatusBanner>
      <form className="form-grid" onSubmit={(event) => event.preventDefault()}>
        <Field help="Used for emergency identity matching." label="Legal or full name" required>
          <input value={profile.legalName} onChange={(event) => update({ legalName: event.target.value })} />
        </Field>
        <Field help="Shown in the app when provided." label="Preferred name">
          <input value={profile.preferredName} onChange={(event) => update({ preferredName: event.target.value })} />
        </Field>
        <Field help="Required to distinguish people with similar names." label="Birth date" required>
          <input
            type="date"
            value={profile.dateOfBirth}
            onChange={(event) => update({ dateOfBirth: event.target.value })}
          />
        </Field>
        <Field help="Use camera on mobile or upload a file on desktop." label="Account photo" required>
          <input
            accept="image/*"
            capture="user"
            type="file"
            onChange={(event) => update({ photoAssetId: event.target.files?.[0]?.name ?? "" })}
          />
        </Field>
        <Field help="Used for text reminders if enabled." label="Phone">
          <input value={profile.phone} onChange={(event) => update({ phone: event.target.value })} />
        </Field>
        <Field help="Used for email reminders if enabled." label="Email">
          <input type="email" value={profile.email} onChange={(event) => update({ email: event.target.value })} />
        </Field>
        <Field help="Can be a neighborhood, shelter, or general area." label="Current safe location">
          <input value={profile.currentLocation} onChange={(event) => update({ currentLocation: event.target.value })} />
        </Field>
        <Field help="Optional; useful for assisted setup." label="Shelter affiliation">
          <input
            value={profile.shelterAffiliation}
            onChange={(event) => update({ shelterAffiliation: event.target.value })}
          />
        </Field>
        <div className="full-span">
          <span className="field-label">Service needs</span>
          <div className="chip-grid">
            {serviceNeeds.map((need) => (
              <button
                aria-pressed={profile.serviceNeeds.includes(need)}
                className="choice-chip"
                key={need}
                onClick={() => toggleNeed(need)}
                type="button"
              >
                {need}
              </button>
            ))}
          </div>
        </div>
        <label className="captcha-box full-span">
          <input
            checked={Boolean(profile.captchaToken)}
            onChange={(event) => update({ captchaToken: event.target.checked ? "mock-captcha-token" : "" })}
            type="checkbox"
          />
          <span>Bot check complete</span>
        </label>
      </form>
      <Section title="Profile review">
        <div className="review-list">
          <ReviewRow label="Name" value={profile.legalName || "Required"} />
          <ReviewRow label="Birth date" value={profile.dateOfBirth || "Required"} />
          <ReviewRow label="Photo" value={profile.photoAssetId || "Required"} />
          <ReviewRow label="Needs" value={profile.serviceNeeds.join(", ") || "None selected"} />
        </div>
        <Button disabled={requiredMissing}>
          <ShieldCheck size={18} /> Create profile draft
        </Button>
      </Section>
    </div>
  );
}

function CheckInScreen({
  policy,
  setPolicy,
  nextCheckIn
}: {
  policy: typeof defaultCheckInPolicy;
  setPolicy: (policy: typeof defaultCheckInPolicy) => void;
  nextCheckIn: string;
}) {
  const update = (patch: Partial<typeof defaultCheckInPolicy>) => setPolicy({ ...policy, ...patch });
  const toggleChannel = (channel: CheckInChannel) => {
    update({
      reminderChannels: policy.reminderChannels.includes(channel)
        ? policy.reminderChannels.filter((item) => item !== channel)
        : [...policy.reminderChannels, channel]
    });
  };

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Check-in</p>
        <h1>Set your schedule</h1>
      </div>
      <StatusBanner tone="warning">The maximum interval is 30 days before escalation.</StatusBanner>
      <Section title="Reminder schedule">
        <div className="form-grid">
          <Field help="Choose 1 to 30 days." label="Interval days" required>
            <input
              max={30}
              min={1}
              type="number"
              value={policy.intervalDays}
              onChange={(event) =>
                update({ intervalDays: Math.max(1, Math.min(30, Number(event.target.value || 1))) })
              }
            />
          </Field>
          <Field help="Time after a missed check-in before escalation starts." label="Grace period hours">
            <input
              min={0}
              type="number"
              value={policy.gracePeriodHours}
              onChange={(event) => update({ gracePeriodHours: Number(event.target.value || 0) })}
            />
          </Field>
        </div>
        <div className="chip-grid">
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => (
            <button
              aria-pressed={policy.reminderChannels.includes(channel)}
              className="choice-chip"
              key={channel}
              onClick={() => toggleChannel(channel)}
              type="button"
            >
              {channel.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="schedule-preview">
          <CalendarCheck aria-hidden="true" size={28} />
          <div>
            <small>Next check-in</small>
            <strong>{nextCheckIn}</strong>
          </div>
        </div>
        <Button onClick={() => update({ lastCheckInAt: new Date().toISOString() })}>
          <Bell size={18} /> Check in now
        </Button>
      </Section>
    </div>
  );
}

function ContactsScreen({
  recipients,
  setRecipients
}: {
  recipients: DisclosureRecipientDraft[];
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
}) {
  const [draft, setDraft] = useState({
    displayName: "",
    relationship: "",
    email: "",
    phone: "",
    type: "emergency_contact" as DisclosureRecipientType
  });

  function addRecipient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.displayName) return;
    setRecipients([
      ...recipients,
      {
        id: `rec-${Date.now()}`,
        ...draft,
        agencyName: "",
        precinctName: "",
        verified: false,
        allowedScopes: []
      }
    ]);
    setDraft({ displayName: "", relationship: "", email: "", phone: "", type: "emergency_contact" });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Emergency contacts</p>
        <h1>People and agencies</h1>
      </div>
      <div className="list-stack">
        {recipients.map((recipient) => (
          <article className="list-item recipient-list-item" key={recipient.id}>
            <div>
              <h3>{recipient.displayName}</h3>
              <p>{recipient.relationship || recipient.agencyName || recipient.type.replace("_", " ")}</p>
              <div className="badge-row">
                <Badge tone={recipient.verified ? "success" : "warning"}>
                  {recipient.verified ? "Verified" : "Needs verification"}
                </Badge>
                <Badge>{recipient.allowedScopes.length} scopes</Badge>
              </div>
            </div>
            <Button
              ariaLabel={`Remove ${recipient.displayName}`}
              className="compact-list-action"
              onClick={() => setRecipients(recipients.filter((item) => item.id !== recipient.id))}
              variant="quiet"
            >
              Remove
            </Button>
          </article>
        ))}
      </div>
      <Section title="Add recipient">
        <form className="form-grid" onSubmit={addRecipient}>
          <Field label="Name or agency" required>
            <input value={draft.displayName} onChange={(event) => setDraft({ ...draft, displayName: event.target.value })} />
          </Field>
          <Field label="Relationship or role">
            <input value={draft.relationship} onChange={(event) => setDraft({ ...draft, relationship: event.target.value })} />
          </Field>
          <Field label="Phone">
            <input value={draft.phone} onChange={(event) => setDraft({ ...draft, phone: event.target.value })} />
          </Field>
          <Field label="Email">
            <input type="email" value={draft.email} onChange={(event) => setDraft({ ...draft, email: event.target.value })} />
          </Field>
          <Field label="Type">
            <select
              value={draft.type}
              onChange={(event) => setDraft({ ...draft, type: event.target.value as DisclosureRecipientType })}
            >
              <option value="emergency_contact">Emergency contact</option>
              <option value="social_worker">Social worker</option>
              <option value="police_precinct">Police precinct</option>
              <option value="shelter_staff">Shelter staff</option>
              <option value="government_liaison">Government liaison</option>
            </select>
          </Field>
          <div className="full-span">
            <Button type="submit">
              <UsersRound size={18} /> Add recipient
            </Button>
          </div>
        </form>
      </Section>
    </div>
  );
}

function SharingRulesScreen({
  recipients,
  setRecipients
}: {
  recipients: DisclosureRecipientDraft[];
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
}) {
  function toggleScope(recipientId: string, scope: DisclosureDataScope) {
    setRecipients(
      recipients.map((recipient) =>
        recipient.id === recipientId
          ? {
              ...recipient,
              allowedScopes: recipient.allowedScopes.includes(scope)
                ? recipient.allowedScopes.filter((item) => item !== scope)
                : [...recipient.allowedScopes, scope]
            }
          : recipient
      )
    );
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Sharing rules</p>
        <h1>Choose what each person can see</h1>
      </div>
      <StatusBanner tone="info">No recipient receives new information unless a scope is selected here.</StatusBanner>
      <div className="list-stack">
        {recipients.map((recipient) => (
          <article className="scope-editor" key={recipient.id}>
            <div className="scope-header">
              <div>
                <h3>{recipient.displayName}</h3>
                <p>{recipient.type.replace("_", " ")}</p>
              </div>
              <Badge>{recipient.allowedScopes.length} selected</Badge>
            </div>
            <div className="scope-grid">
              {disclosureScopes.map((scope) => (
                <label className="scope-option" key={scope.id}>
                  <input
                    checked={recipient.allowedScopes.includes(scope.id)}
                    onChange={() => toggleScope(recipient.id, scope.id)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{scope.label}</strong>
                    <small>{scope.detail}</small>
                  </span>
                </label>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function UploadsScreen({
  uploads,
  setUploads
}: {
  uploads: UploadItem[];
  setUploads: (uploads: UploadItem[]) => void;
}) {
  function addUpload(fileName: string) {
    if (!fileName) return;
    setUploads([
      ...uploads,
      {
        id: `up-${Date.now()}`,
        fileName,
        category: "Uncategorized",
        sensitivity: "high",
        status: "stored",
        shared: false
      }
    ]);
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Uploads</p>
        <h1>Document and information vault</h1>
      </div>
      <Section title="Add information">
        <label className="upload-dropzone">
          <Upload aria-hidden="true" size={28} />
          <span>Choose a file or photo</span>
          <small>Stored items stay private until added to a sharing rule.</small>
          <span className="upload-picker">
            <FileUp aria-hidden="true" size={18} /> Select file
          </span>
          <input
            type="file"
            onChange={(event) => addUpload(event.target.files?.[0]?.name ?? "")}
            aria-label="Choose file to upload"
          />
        </label>
      </Section>
      <div className="list-stack">
        {uploads.map((upload) => (
          <article className="list-item upload-list-item" key={upload.id}>
            <div>
              <h3>{upload.fileName}</h3>
              <p>{upload.category}</p>
              <div className="badge-row">
                <Badge tone="success">{upload.status}</Badge>
                <Badge tone="warning">{upload.sensitivity}</Badge>
                <Badge>{upload.shared ? "Shared" : "Private"}</Badge>
              </div>
            </div>
            <Button
              className="list-item-action"
              onClick={() =>
                setUploads(uploads.map((item) => (item.id === upload.id ? { ...item, shared: !item.shared } : item)))
              }
              variant="secondary"
            >
              {upload.shared ? "Mark private" : "Mark eligible"}
            </Button>
          </article>
        ))}
      </div>
    </div>
  );
}

function SocialServicesScreen() {
  const categories = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation", "Employment", "Crisis"];
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Social services</p>
        <h1>Find support</h1>
      </div>
      <div className="category-grid">
        {categories.map((category) => (
          <button className="category-tile" key={category} type="button">
            <HeartHandshake aria-hidden="true" size={22} />
            <span>{category}</span>
          </button>
        ))}
      </div>
      <Section title="Government services liaison">
        <div className="liaison-panel">
          <MessageSquare aria-hidden="true" size={28} />
          <div>
            <h3>Request help navigating benefits, IDs, housing, or agency paperwork.</h3>
            <p>Only the details you choose to share will be included in the request.</p>
          </div>
          <Button>Start request</Button>
        </div>
      </Section>
      <Section title="Matched services">
        <div className="list-stack">
          {serviceMatches.map((service) => (
            <article className="list-item" key={service.id}>
              <div>
                <h3>{service.name}</h3>
                <p>
                  {service.category} · {service.distance}
                </p>
              </div>
              <Badge tone="success">{service.availability}</Badge>
            </article>
          ))}
        </div>
      </Section>
    </div>
  );
}

function ShelterScreen() {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Shelter portal</p>
        <h1>Assisted access</h1>
      </div>
      <StatusBanner tone="info">Shelter workflows are free and keep user sharing choices separate from staff access.</StatusBanner>
      <Section title="Staff tools">
        <div className="tool-grid">
          <button className="tool-tile" type="button">
            <ClipboardCheck size={24} /> Assist registration
          </button>
          <button className="tool-tile" type="button">
            <UsersRound size={24} /> Verify contact
          </button>
          <button className="tool-tile" type="button">
            <ShieldCheck size={24} /> Review staff audit
          </button>
        </div>
      </Section>
      <Section title="Shared-device safety">
        <div className="checklist">
          <label>
            <input type="checkbox" /> Confirm user is present for assisted setup
          </label>
          <label>
            <input type="checkbox" /> Clear browser data after shared-device session
          </label>
          <label>
            <input type="checkbox" /> Staff action will be added to the audit log
          </label>
        </div>
      </Section>
    </div>
  );
}

function RecipientAccessScreen({
  accessRequests,
  recipients,
  setAccessRequests,
  verified,
  setVerified
}: {
  accessRequests: WalletAccessRequest[];
  recipients: DisclosureRecipientDraft[];
  setAccessRequests: (requests: WalletAccessRequest[]) => void;
  verified: boolean;
  setVerified: (verified: boolean) => void;
}) {
  const recipient = recipients[0];
  function hasThresholdApproval(request: WalletAccessRequest) {
    if (!request.approvalRequired) return true;
    return (request.approvalCount ?? 0) >= (request.approvalThreshold ?? 1);
  }

  function recordControllerApproval(requestId: string) {
    setAccessRequests(
      accessRequests.map((request) =>
        request.id === requestId
          ? {
              ...request,
              approvalCount: Math.min(
                (request.approvalCount ?? 0) + 1,
                request.approvalThreshold ?? (request.approvalCount ?? 0) + 1
              )
            }
          : request
      )
    );
  }

  function decideRequest(requestId: string, status: "approved" | "rejected") {
    setAccessRequests(
      accessRequests.map((request) =>
        request.id === requestId
          ? { ...request, status, grantStatus: status === "approved" ? "active" : request.grantStatus }
          : request
      )
    );
  }

  function revokeRequest(requestId: string) {
    setAccessRequests(
      accessRequests.map((request) =>
        request.id === requestId ? { ...request, grantStatus: "revoked" } : request
      )
    );
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Secure access</p>
        <h1>Access requests</h1>
      </div>
      <Section title="Review requested access">
        <div className="list-stack">
          {accessRequests.map((request) => (
            <article className="list-item access-request-item" key={request.id}>
              <div>
                <div className="scope-header">
                  <div>
                    <h3>{request.requesterName}</h3>
                    <p>{request.resourceLabel} · {request.purpose}</p>
                  </div>
                  <Badge tone={request.status === "approved" ? "success" : request.status === "rejected" ? "warning" : "neutral"}>
                    {request.status}
                  </Badge>
                </div>
                <div className="badge-row">
                  {request.abilities.map((ability) => (
                    <Badge key={ability}>{ability}</Badge>
                  ))}
                  <Badge>{request.createdAt}</Badge>
                  {request.approvalRequired ? (
                    <Badge tone={hasThresholdApproval(request) ? "success" : "warning"}>
                      {request.approvalCount ?? 0}/{request.approvalThreshold ?? 1} approvals
                    </Badge>
                  ) : null}
                  {request.status === "approved" ? (
                    <Badge tone={request.grantStatus === "revoked" ? "warning" : "success"}>
                      {request.grantStatus === "revoked" ? "revoked" : "active grant"}
                    </Badge>
                  ) : null}
                </div>
                {request.approvalRequired && !hasThresholdApproval(request) ? (
                  <p className="approval-note">Multi-sig approval is required before this access can be granted.</p>
                ) : null}
                <small>{request.requesterDid}</small>
              </div>
              {request.status === "pending" ? (
                <div className="row-actions">
                  {request.approvalRequired && !hasThresholdApproval(request) ? (
                    <Button onClick={() => recordControllerApproval(request.id)} variant="secondary">
                      <ShieldCheck size={18} /> Record approval
                    </Button>
                  ) : null}
                  <Button
                    disabled={!hasThresholdApproval(request)}
                    onClick={() => decideRequest(request.id, "approved")}
                    variant="secondary"
                  >
                    <ShieldCheck size={18} /> Approve
                  </Button>
                  <Button onClick={() => decideRequest(request.id, "rejected")} variant="danger">
                    Reject
                  </Button>
                </div>
              ) : request.status === "approved" && request.grantStatus !== "revoked" ? (
                <div className="row-actions">
                  <Button onClick={() => revokeRequest(request.id)} variant="danger">
                    Revoke
                  </Button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </Section>
      {!verified ? (
        <Section title="Verify recipient">
          <StatusBanner tone="warning">Sensitive information is hidden until recipient verification is complete.</StatusBanner>
          <div className="form-grid">
            <Field label="Access code">
              <input placeholder="Enter code" />
            </Field>
            <Field label="Recipient phone or email">
              <input placeholder="Confirm contact method" />
            </Field>
          </div>
          <Button onClick={() => setVerified(true)}>
            <KeyRound size={18} /> Verify and view
          </Button>
        </Section>
      ) : (
        <Section title={`Authorized for ${recipient.displayName}`}>
          <div className="disclosure-package">
            {recipient.allowedScopes.map((scope) => (
              <div className="disclosure-row" key={scope}>
                <strong>{disclosureScopes.find((item) => item.id === scope)?.label ?? scope}</strong>
                <span>Available in this emergency package</span>
              </div>
            ))}
          </div>
          <Button variant="secondary">Contact liaison</Button>
        </Section>
      )}
    </div>
  );
}

function BenefitsProtectionScreen({
  optedIn,
  setOptedIn
}: {
  optedIn: boolean;
  setOptedIn: (optedIn: boolean) => void;
}) {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Benefits protection</p>
        <h1>Optional agency notification</h1>
      </div>
      <StatusBanner tone="warning">
        This can only request or notify through approved agency workflows. It does not guarantee agency action.
      </StatusBanner>
      <Section title="Explicit opt-in">
        <label className="consent-box">
          <input checked={optedIn} onChange={(event) => setOptedIn(event.target.checked)} type="checkbox" />
          <span>
            <strong>Allow Abby to prepare a benefits-protection notification after missed check-ins.</strong>
            <small>Legal and policy review must be completed before this can be sent in production.</small>
          </span>
        </label>
        <Button disabled={!optedIn}>
          <Landmark size={18} /> Save opt-in
        </Button>
      </Section>
    </div>
  );
}

function AnalyticsScreen({
  optedIn,
  setOptedIn
}: {
  optedIn: Record<string, boolean>;
  setOptedIn: (value: Record<string, boolean>) => void;
}) {
  function toggleStudy(studyId: string) {
    setOptedIn({ ...optedIn, [studyId]: !optedIn[studyId] });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Analytics consent</p>
        <h1>Share patterns, not personal records</h1>
      </div>
      <StatusBanner tone="info">
        Only derived fields are used. Exact counts stay hidden until privacy thresholds and budget checks pass.
      </StatusBanner>
      <div className="analytics-grid">
        {analyticsStudies.map((study) => {
          const selected = Boolean(optedIn[study.id]);
          const budgetRemaining = Math.max(0, study.epsilonBudget - study.spentBudget);
          const titleId = `analytics-title-${study.id}`;
          return (
            <article aria-labelledby={titleId} className="analytics-card" key={study.id}>
              <div className="scope-header">
                <div>
                  <h3 id={titleId}>{study.title}</h3>
                  <p>{study.purpose}</p>
                </div>
                <Badge tone={study.status === "paused" ? "warning" : selected ? "success" : "neutral"}>
                  {selected ? "Consented" : study.status}
                </Badge>
              </div>
              <div className="privacy-metrics">
                <StatusPanel label="Minimum cohort" value={String(study.minCohortSize)} tone="teal" />
                <StatusPanel label="Budget left" value={budgetRemaining.toFixed(2)} tone="gold" />
              </div>
              <div className="badge-row">
                {study.fields.map((field) => (
                  <Badge key={field}>{field}</Badge>
                ))}
              </div>
              <label className="consent-box">
                <input
                  checked={selected}
                  disabled={study.status === "paused"}
                  onChange={() => toggleStudy(study.id)}
                  type="checkbox"
                />
                <span>
                  <strong>Allow this study to use the listed derived fields.</strong>
                  <small>Precise location, raw documents, names, and contact details are excluded.</small>
                </span>
              </label>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function ProofCenterScreen({ proofs }: { proofs: ProofReceiptView[] }) {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Proof center</p>
        <h1>Verified wallet claims</h1>
      </div>
      <StatusBanner tone="info">
        Proof receipts expose public claims and verifier details without showing raw documents or precise location.
      </StatusBanner>
      <div className="list-stack">
        {proofs.map((proof) => {
          const titleId = `proof-title-${proof.id}`;

          return (
            <article aria-labelledby={titleId} className="proof-card" key={proof.id}>
              <div className="scope-header">
                <div>
                  <h3 id={titleId}>{proof.claim}</h3>
                  <p>
                    {proof.proofType} · {proof.verifier}
                  </p>
                </div>
                <Badge tone={proof.simulated ? "warning" : "success"}>
                  {proof.simulated ? "Simulated" : "Verified"}
                </Badge>
              </div>
              <div className="badge-row">
                <Badge>{proof.createdAt}</Badge>
                <Badge>{proof.witnessLabel}</Badge>
              </div>
              <div className="proof-inputs" aria-label={`${proof.claim} public inputs`}>
                {Object.entries(proof.publicInputs).map(([key, value]) => (
                  <div className="disclosure-row" key={key}>
                    <strong>{key}</strong>
                    <span>{value}</span>
                  </div>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function SecurityScreen() {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Security</p>
        <h1>Account safety</h1>
      </div>
      <div className="tool-grid">
        <button className="tool-tile" type="button">
          <LockKeyhole size={24} /> Session timeout
        </button>
        <button className="tool-tile" type="button">
          <KeyRound size={24} /> Recovery settings
        </button>
        <button className="tool-tile" type="button">
          <ShieldCheck size={24} /> CAPTCHA settings
        </button>
      </div>
    </div>
  );
}

function AuditScreen() {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Audit</p>
        <h1>Consent and access history</h1>
      </div>
      <div className="timeline">
        {auditEvents.map((event) => (
          <article className="timeline-event" key={event.id}>
            <span aria-hidden="true" />
            <div>
              <h3>{event.action}</h3>
              <p>
                {event.actor} · {event.timestamp}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="review-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
