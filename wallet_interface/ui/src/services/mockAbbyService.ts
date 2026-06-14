import {
  AuditEvent,
  AnalyticsStudy,
  CheckInPolicyDraft,
  DisclosureDataScope,
  DisclosureRecipientDraft,
  ExportBundleView,
  ProofReceiptView,
  RegistrationProfileDraft,
  ServiceMatch,
  ShelterContactRequest,
  UploadItem,
  WalletAccessRequest,
  WalletGrantReceipt
} from "../models/abby";

export const defaultDisclosureScopes: DisclosureDataScope[] = [
  "identity_minimum",
  "profile",
  "photo",
  "current_location",
  "uploaded_documents",
  "missed_check_in",
  "found_permanent_housing",
  "medical_notes",
  "shelter_history",
  "benefits_information",
  "custom"
];

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
    allowedScopes: [...defaultDisclosureScopes]
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
    allowedScopes: [...defaultDisclosureScopes]
  }
];

export const initialShelterContactRequests: ShelterContactRequest[] = [
  {
    id: "shelter-request-1",
    direction: "shelter_to_user",
    status: "pending",
    shelterName: "Downtown Outreach Shelter",
    userName: "Abby Example",
    userContact: "abby@example.org",
    staffId: "staff-demo-downtown",
    staffName: "Jordan Lee",
    createdAt: "Today, 8:45 AM"
  },
  {
    id: "shelter-request-2",
    direction: "user_to_shelter",
    status: "pending",
    shelterName: "Rose City Shelter",
    userName: "Abby Example",
    userContact: "abby@example.org",
    createdAt: "Today, 9:05 AM"
  }
];

export const initialUploads: UploadItem[] = [
  {
    id: "up-1",
    fileName: "State ID file",
    machineSummary: "State Id File",
    category: "Identity",
    sensitivity: "high",
    status: "stored",
    shared: false
  }
];

export const serviceMatches: ServiceMatch[] = [
  {
    id: "svc-1",
    name: "Emergency shelter sign-up",
    category: "Shelter",
    distance: "2.1 mi",
    availability: "Open tonight"
  },
  {
    id: "svc-2",
    name: "Benefits help clinic",
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
    purpose: "Count where housing help is missing.",
    fields: ["county", "need_category"],
    minCohortSize: 10,
    epsilonBudget: 1,
    spentBudget: 0.25,
    status: "available"
  },
  {
    id: "study-2",
    title: "Food access demand",
    purpose: "Count where food help is needed without exact locations.",
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
    requesterName: "Benefits help clinic",
    requesterDid: "did:key:benefits-clinic",
    audienceDid: "did:key:benefits-clinic",
    resourceLabel: "Benefits letter",
    abilities: ["record/analyze"],
    purpose: "Check if you can get food, bill, or housing help",
    status: "pending",
    createdAt: "Today, 10:12 AM"
  },
  {
    id: "access-2",
    requesterName: "Downtown Outreach",
    requesterDid: "did:key:outreach",
    audienceDid: "did:key:outreach",
    resourceLabel: "State ID file",
    abilities: ["record/decrypt"],
    purpose: "Check your ID for shelter sign-up",
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
    purpose: "Help plan an appeal",
    status: "approved",
    createdAt: "Apr 30, 3:05 PM",
    grantStatus: "active"
  }
];

export const initialGrantReceipts: WalletGrantReceipt[] = [
  {
    id: "receipt-1",
    grantId: "grant-legal-aid",
    audienceName: "Legal Aid desk",
    audienceDid: "did:key:legal-aid",
    resources: ["wallet://demo-wallet/records/rec-housing-notice"],
    recordId: "rec-housing-notice",
    resourceLabel: "Housing notice",
    abilities: ["record/analyze"],
    purpose: "Help plan an appeal",
    receiptHash: "8d2e31b4f7a9c6eab2d4f0c98a3e7b1f",
    status: "active",
    createdAt: "Apr 30, 3:05 PM",
    expiresAt: "May 30, 2026"
  }
];

export const proofReceipts: ProofReceiptView[] = [
  {
    id: "proof-1",
    proofType: "location_region",
    claim: "Location is in service region",
    verifier: "211 service matcher",
    proofSystem: "simulated",
    verificationStatus: "verified",
    circuitId: "simulated-location-region",
    verifierDigest: "425551d64c5b78caa09fd67d24b099c1ca8749bc9747daa0ae84a69cf3507e3e",
    publicInputs: {
      region_id: "multnomah_county",
      claim: "location_in_region",
      region_policy_hash: "425551d64c5b78caa09fd67d24b099c1ca8749bc9747daa0ae84a69cf3507e3e"
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
    proofSystem: "simulated",
    verificationStatus: "verified",
    circuitId: "simulated-analytics-contribution",
    publicInputs: {
      template_id: "housing_service_gap_v1",
      fields: "county, need_category"
    },
    witnessLabel: "Derived service needs",
    simulated: true,
    createdAt: "Today, 10:41 AM"
  }
];

export const exportBundles: ExportBundleView[] = [
  {
    id: "export-1",
    bundleId: "export-6d8f4e92b1a7c340d57a92ce",
    bundleHash: "6d8f4e92b1a7c340d57a92ce90ef335aa64b85d62ef4d8e2b66a2010b16f5718",
    audienceName: "Legal Aid desk",
    recordCount: 2,
    proofCount: 1,
    verificationOk: true,
    hashOk: true,
    schemaOk: true,
    storageOk: true,
    imported: true,
    createdAt: "Today, 11:18 AM"
  },
  {
    id: "export-2",
    bundleId: "export-3a41c9fe8420d718ce1490b4",
    bundleHash: "3a41c9fe8420d718ce1490b45820ad275b01365f1d51287b27b835e192fc0062",
    audienceName: "Benefits help clinic",
    recordCount: 1,
    proofCount: 0,
    verificationOk: true,
    hashOk: true,
    schemaOk: true,
    storageOk: false,
    imported: false,
    createdAt: "Yesterday, 2:35 PM"
  }
];
