import {
  AuditEvent,
  AnalyticsStudy,
  CheckInPolicyDraft,
  DisclosureRecipientDraft,
  ProofReceiptView,
  RegistrationProfileDraft,
  ServiceMatch,
  UploadItem,
  WalletAccessRequest
} from "../models/abby";

export const emptyRegistrationProfile: RegistrationProfileDraft = {
  legalName: "",
  preferredName: "",
  pronouns: "",
  dateOfBirth: "",
  photoAssetId: "",
  phone: "",
  email: "",
  currentLocation: "",
  shelterAffiliation: "",
  serviceNeeds: [],
  preferredCheckInChannels: ["web"],
  easyBotCheckStatus: "pending",
  captchaToken: ""
};

export const defaultCheckInPolicy: CheckInPolicyDraft = {
  intervalDays: 7,
  reminderChannels: ["sms", "web"],
  gracePeriodHours: 24,
  escalationEnabled: true,
  lastCheckInAt: new Date().toISOString()
};

export const initialRecipients: DisclosureRecipientDraft[] = [
  {
    id: "rec-1",
    type: "emergency_contact",
    displayName: "Maya Johnson",
    relationship: "Sister",
    email: "maya@example.org",
    phone: "(503) 555-0129",
    agencyName: "",
    precinctName: "",
    verified: true,
    allowedScopes: ["identity_minimum", "photo", "current_location"]
  },
  {
    id: "rec-2",
    type: "social_worker",
    displayName: "Case Worker Desk",
    relationship: "Assigned advocate",
    email: "intake@example.org",
    phone: "(503) 555-0144",
    agencyName: "Downtown Outreach",
    precinctName: "",
    verified: false,
    allowedScopes: ["identity_minimum", "photo", "profile", "uploaded_documents"]
  }
];

export const initialUploads: UploadItem[] = [
  {
    id: "up-1",
    fileName: "State ID photo",
    machineSummary: "State Id Photo",
    category: "Identity",
    sensitivity: "high",
    status: "stored",
    shared: false
  }
];

export const serviceMatches: ServiceMatch[] = [
  {
    id: "svc-1",
    name: "Emergency shelter intake",
    category: "Shelter",
    distance: "2.1 mi",
    availability: "Open tonight"
  },
  {
    id: "svc-2",
    name: "Benefits navigation clinic",
    category: "Benefits",
    distance: "Phone or walk-in",
    availability: "Weekdays"
  },
  {
    id: "svc-3",
    name: "Mobile health outreach",
    category: "Health",
    distance: "3.4 mi",
    availability: "Tomorrow"
  }
];

export const auditEvents: AuditEvent[] = [
  {
    id: "aud-1",
    actor: "You",
    action: "Reviewed emergency disclosure scopes",
    timestamp: "Today, 9:24 AM"
  },
  {
    id: "aud-2",
    actor: "System",
    action: "Check-in reminder scheduled",
    timestamp: "Yesterday, 6:00 PM"
  },
  {
    id: "aud-3",
    actor: "Shelter staff",
    action: "Assisted with contact verification",
    timestamp: "Apr 30, 2:10 PM"
  }
];

export const analyticsStudies: AnalyticsStudy[] = [
  {
    id: "study-1",
    title: "Housing service gaps",
    purpose: "Count county-level housing needs for planning and outreach.",
    fields: ["county", "need_category"],
    minCohortSize: 10,
    epsilonBudget: 1,
    spentBudget: 0.25,
    status: "available"
  },
  {
    id: "study-2",
    title: "Food access demand",
    purpose: "Measure coarse regional food-support demand without raw location.",
    fields: ["county", "need_category"],
    minCohortSize: 15,
    epsilonBudget: 1,
    spentBudget: 0,
    status: "paused"
  }
];

export const initialAccessRequests: WalletAccessRequest[] = [
  {
    id: "access-1",
    requesterName: "Benefits navigation clinic",
    requesterDid: "did:key:benefits-clinic",
    audienceDid: "did:key:benefits-clinic",
    resourceLabel: "Benefits letter",
    abilities: ["record/analyze"],
    purpose: "Screen for SNAP, utility, and housing support",
    status: "pending",
    createdAt: "Today, 10:12 AM"
  },
  {
    id: "access-2",
    requesterName: "Downtown Outreach",
    requesterDid: "did:key:outreach",
    audienceDid: "did:key:outreach",
    resourceLabel: "State ID photo",
    abilities: ["record/decrypt"],
    purpose: "Verify identity for shelter intake",
    status: "pending",
    createdAt: "Yesterday, 4:18 PM",
    approvalRequired: true,
    approvalThreshold: 2,
    approvalCount: 1
  },
  {
    id: "access-3",
    requesterName: "Legal Aid desk",
    requesterDid: "did:key:legal-aid",
    audienceDid: "did:key:legal-aid",
    resourceLabel: "Housing notice",
    abilities: ["record/analyze"],
    purpose: "Prepare appeal options",
    status: "approved",
    createdAt: "Apr 30, 3:05 PM",
    grantStatus: "active"
  }
];

export const proofReceipts: ProofReceiptView[] = [
  {
    id: "proof-1",
    proofType: "location_region",
    claim: "Location is in service region",
    verifier: "211 service matcher",
    publicInputs: {
      region_id: "multnomah_county",
      claim: "location_in_region"
    },
    witnessLabel: "Current location",
    simulated: true,
    createdAt: "Today, 10:38 AM"
  },
  {
    id: "proof-2",
    proofType: "analytics_contribution",
    claim: "Contribution follows study consent",
    verifier: "Analytics template verifier",
    publicInputs: {
      template_id: "housing_service_gap_v1",
      fields: "county, need_category"
    },
    witnessLabel: "Derived service needs",
    simulated: true,
    createdAt: "Today, 10:41 AM"
  }
];
