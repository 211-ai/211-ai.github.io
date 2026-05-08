import type {
  DisclosureDataScope,
  DisclosureRecipientDraft,
  EasyBotCheckStatus,
  RegistrationProfileDraft,
  RouteId,
  SavedService,
  ServiceInteractionEvent,
  ServicePlan,
  ShelterContactRequest,
  UploadItem
} from "../models/abby";
import {
  defaultCheckInPolicy,
  emptyRegistrationProfile,
  initialRecipients,
  initialShelterContactRequests,
  initialUploads
} from "../services/mockAbbyService";

export const APP_PERSIST_KEY = "abby-ui-state-v1";

export const primaryRoutes: Array<{ id: RouteId; label: string }> = [
  { id: "home", label: "Home" },
  { id: "register", label: "Register" },
  { id: "check-in", label: "Check in" },
  { id: "contacts", label: "Contacts" },
  { id: "sharing-rules", label: "Sharing" },
  { id: "social-services", label: "Services" },
  { id: "interactions", label: "Interactions" },
  { id: "uploads", label: "Uploads" },
  { id: "shelter", label: "Shelter staff" }
];

export const secondaryRoutes: Array<{ id: RouteId; label: string }> = [
  { id: "recipient-access", label: "Who can see info" },
  { id: "benefits-protection", label: "Benefits" },
  { id: "analytics", label: "Analytics" },
  { id: "proof-center", label: "Proofs" },
  { id: "exports", label: "Exports" },
  { id: "security", label: "Security" },
  { id: "audit", label: "Audit" }
];

export const appRoutes = [...primaryRoutes, ...secondaryRoutes];
export const appRouteIds = appRoutes.map((route) => route.id);

export const serviceNeeds = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation"];

export const shelterOptions = [
  "Rose City Shelter",
  "Downtown Outreach Shelter",
  "Harbor Night Shelter",
  "Northside Family Shelter"
];

export type ShelterStaffAccount = {
  id: string;
  shelter: string;
  displayName: string;
  email: string;
  verified: boolean;
  updatedAt: string;
};

export const initialShelterStaffAccounts: ShelterStaffAccount[] = [
  {
    id: "staff-demo-downtown",
    shelter: "Downtown Outreach Shelter",
    displayName: "Jordan Lee",
    email: "jordan@downtown.example",
    verified: true,
    updatedAt: "Today, 8:30 AM"
  },
  {
    id: "staff-demo-rose",
    shelter: "Rose City Shelter",
    displayName: "Avery Patel",
    email: "avery@rose.example",
    verified: true,
    updatedAt: "Today, 8:35 AM"
  },
  {
    id: "staff-demo-harbor",
    shelter: "Harbor Night Shelter",
    displayName: "Riley Chen",
    email: "riley@harbor.example",
    verified: true,
    updatedAt: "Today, 8:40 AM"
  }
];

export type ShelterUserAccount = {
  id: string;
  shelter: string;
  legalName: string;
  preferredName: string;
  pronouns: string;
  dateOfBirth: string;
  photoAssetId: string;
  phone: string;
  email: string;
  currentLocation: string;
  preferredShelter: string;
  serviceNeeds: string[];
  easyBotCheckStatus: EasyBotCheckStatus;
  captchaToken: string;
  localPrecinctNotified: boolean;
  foundPermanentHousing: boolean;
  createdByStaffId: string;
  createdAt: string;
};

export const defaultManagedUserDraft = {
  legalName: "",
  preferredName: "",
  pronouns: "",
  dateOfBirth: "",
  photoAssetId: "",
  phone: "",
  email: "",
  currentLocation: "",
  preferredShelter: "",
  serviceNeeds: [] as string[],
  easyBotCheckStatus: "pending" as EasyBotCheckStatus,
  captchaToken: "",
  localPrecinctNotified: false,
  foundPermanentHousing: false
};

export const disclosureScopes: Array<{ id: DisclosureDataScope; label: string; detail: string }> = [
  { id: "identity_minimum", label: "Minimum identity", detail: "name, birthdate and contact status" },
  { id: "profile", label: "Profile", detail: "Basic profile details and help needs" },
  { id: "photo", label: "Photo or ID file", detail: "The setup file you chose, like an image or PDF" },
  { id: "current_location", label: "Current location", detail: "Most recent safe place or shelter" },
  { id: "uploaded_documents", label: "Uploads", detail: "Files the person chooses to include" },
  { id: "missed_check_in", label: "Missed check-in", detail: "Whether a check-in was missed" },
  { id: "found_permanent_housing", label: "Found permanent housing", detail: "Whether stable housing was reported" },
  { id: "medical_notes", label: "Medical notes", detail: "Sensitive health notes" },
  { id: "shelter_history", label: "Shelter history", detail: "Shelter stays and staff contact details" },
  { id: "benefits_information", label: "Benefits information", detail: "Benefits status and IDs" },
  { id: "custom", label: "Custom note", detail: "A user-written emergency note" }
];

export const defaultShelterChecklist = {
  userPresent: false,
  clearBrowserData: false,
  auditLogConfirmed: false
};

export type PersistedAppState = {
  profile?: RegistrationProfileDraft;
  policy?: typeof defaultCheckInPolicy;
  recipients?: DisclosureRecipientDraft[];
  uploads?: UploadItem[];
  shelterContactRequests?: ShelterContactRequest[];
  shelterStaffAccounts?: ShelterStaffAccount[];
  shelterUserAccounts?: ShelterUserAccount[];
  savedServices?: SavedService[];
  servicePlans?: ServicePlan[];
  serviceInteractions?: ServiceInteractionEvent[];
  benefitsOptIn?: boolean;
  analyticsOptIn?: Record<string, boolean>;
  shelterChecklist?: typeof defaultShelterChecklist;
};

export function readPersistedAppState(): PersistedAppState {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(APP_PERSIST_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? (parsed as PersistedAppState) : {};
  } catch {
    return {};
  }
}

export function writePersistedAppState(state: PersistedAppState): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(APP_PERSIST_KEY, JSON.stringify(state));
}

export function isAppRouteId(value: unknown): value is RouteId {
  return typeof value === "string" && appRouteIds.includes(value as RouteId);
}

export function routeToHash(route: RouteId): string {
  return route === "home" ? "#/" : `#/${route}`;
}

export function getRouteFromHash(hash = typeof window === "undefined" ? "" : window.location.hash): RouteId {
  const route = hash.replace("#/", "") || "home";
  return isAppRouteId(route) ? route : "home";
}

export function setLocationRouteHash(route: RouteId): void {
  if (typeof window === "undefined") return;
  window.location.hash = routeToHash(route);
}

export function createDefaultAppState(persistedState: PersistedAppState = {}): Required<PersistedAppState> {
  return {
    profile: {
      ...emptyRegistrationProfile,
      ...persistedState.profile
    },
    policy: {
      ...defaultCheckInPolicy,
      ...persistedState.policy
    },
    recipients: Array.isArray(persistedState.recipients) ? persistedState.recipients : initialRecipients,
    uploads: Array.isArray(persistedState.uploads) ? persistedState.uploads : initialUploads,
    shelterContactRequests: Array.isArray(persistedState.shelterContactRequests)
      ? persistedState.shelterContactRequests
      : initialShelterContactRequests,
    shelterStaffAccounts: Array.isArray(persistedState.shelterStaffAccounts)
      ? persistedState.shelterStaffAccounts
      : initialShelterStaffAccounts,
    shelterUserAccounts: Array.isArray(persistedState.shelterUserAccounts) ? persistedState.shelterUserAccounts : [],
    savedServices: Array.isArray(persistedState.savedServices) ? persistedState.savedServices : [],
    servicePlans: Array.isArray(persistedState.servicePlans) ? persistedState.servicePlans : [],
    serviceInteractions: Array.isArray(persistedState.serviceInteractions) ? persistedState.serviceInteractions : [],
    benefitsOptIn: persistedState.benefitsOptIn ?? true,
    analyticsOptIn:
      persistedState.analyticsOptIn && typeof persistedState.analyticsOptIn === "object"
        ? persistedState.analyticsOptIn
        : {},
    shelterChecklist: {
      ...defaultShelterChecklist,
      ...persistedState.shelterChecklist
    }
  };
}
