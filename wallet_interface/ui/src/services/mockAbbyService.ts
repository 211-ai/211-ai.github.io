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
  servicePartnerHelpRequested: false,
  servicePartnerHelpRequestedAt: "",
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
    shared: false,
    sharingMode: "private",
    allowedRecipientIds: [],
    decentralizedStorageStatus: "not_configured",
    decentralizedStorageProvider: "wallet-api"
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
    title: "Unsheltered residents seeking beds",
    purpose: "Publish verified nightly shelter demand by county and need type without releasing row-level requests.",
    fields: ["county", "need_category", "age_group"],
    minCohortSize: 25,
    epsilonBudget: 1.5,
    spentBudget: 0.45,
    status: "available"
  },
  {
    id: "study-2",
    title: "Provider capacity gap alerts",
    purpose: "Publish where provider networks are full or building waitlists without exposing any program roster.",
    fields: ["county", "service_type"],
    minCohortSize: 20,
    epsilonBudget: 1.2,
    spentBudget: 0.3,
    status: "available"
  },
  {
    id: "study-3",
    title: "Housing placements after referral",
    purpose: "Publish how often verified referrals lead to housing placement at a safe group level.",
    fields: ["county", "housing_outcome"],
    minCohortSize: 30,
    epsilonBudget: 1,
    spentBudget: 0.2,
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
    proofType: "analytics_population_snapshot",
    claim: "Unsheltered residents seeking beds in multnomah county",
    verifier: "Multnomah release verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-population-snapshot-v1",
    verifierDigest: "analytics-pop-2d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-pop-multnomah",
    publicInputs: {
      certificate_type: "population_snapshot",
      study_id: "study-1",
      county: "multnomah",
      need_category: "shelter",
      age_group: "adult_25_54",
      cohort_count: "620",
      shelter_requests: "210",
      waiting_over_7_days: "71"
    },
    witnessLabel: "Derived shelter demand cohort",
    simulated: true,
    createdAt: "Today, 10:41 AM"
  },
  {
    id: "proof-3",
    proofType: "analytics_population_snapshot",
    claim: "Unsheltered residents seeking beds in washington county",
    verifier: "Washington release verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-population-snapshot-v1",
    verifierDigest: "analytics-pop-3d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-pop-washington",
    publicInputs: {
      certificate_type: "population_snapshot",
      study_id: "study-1",
      county: "washington",
      need_category: "shelter",
      age_group: "adult_25_54",
      cohort_count: "480",
      shelter_requests: "158",
      waiting_over_7_days: "43"
    },
    witnessLabel: "Derived shelter demand cohort",
    simulated: true,
    createdAt: "Today, 10:43 AM"
  },
  {
    id: "proof-4",
    proofType: "analytics_population_snapshot",
    claim: "Unsheltered residents seeking beds in clackamas county",
    verifier: "Clackamas release verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-population-snapshot-v1",
    verifierDigest: "analytics-pop-4d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-pop-clackamas",
    publicInputs: {
      certificate_type: "population_snapshot",
      study_id: "study-1",
      county: "clackamas",
      need_category: "shelter",
      age_group: "family_household",
      cohort_count: "390",
      shelter_requests: "95",
      waiting_over_7_days: "29"
    },
    witnessLabel: "Derived shelter demand cohort",
    simulated: true,
    createdAt: "Today, 10:45 AM"
  },
  {
    id: "proof-14",
    proofType: "analytics_population_snapshot",
    claim: "Unsheltered residents seeking beds in multnomah county veteran cohort",
    verifier: "Multnomah release verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-population-snapshot-v1",
    verifierDigest: "analytics-pop-14d64c5b78caa09fd67d24b099c1ca8",
    proofArtifactRef: "zk-cert-analytics-pop-multnomah-veteran",
    publicInputs: {
      certificate_type: "population_snapshot",
      study_id: "study-1",
      county: "multnomah",
      need_category: "shelter",
      age_group: "veteran_household",
      cohort_count: "205",
      shelter_requests: "64",
      waiting_over_7_days: "18"
    },
    witnessLabel: "Derived shelter demand cohort",
    simulated: true,
    createdAt: "Today, 10:46 AM"
  },
  {
    id: "proof-5",
    proofType: "analytics_provider_capacity",
    claim: "Provider capacity gap alerts in multnomah county",
    verifier: "Multnomah provider verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-provider-capacity-v1",
    verifierDigest: "analytics-cap-5d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-cap-multnomah",
    publicInputs: {
      certificate_type: "provider_capacity",
      study_id: "study-2",
      county: "multnomah",
      service_type: "emergency_shelter",
      providers_included: "4",
      occupied_beds: "228",
      licensed_beds: "250",
      same_day_available_programs: "17",
      total_programs: "30"
    },
    witnessLabel: "Provider occupancy release batch",
    simulated: true,
    createdAt: "Today, 10:47 AM"
  },
  {
    id: "proof-6",
    proofType: "analytics_provider_capacity",
    claim: "Provider capacity gap alerts in washington county",
    verifier: "Washington provider verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-provider-capacity-v1",
    verifierDigest: "analytics-cap-6d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-cap-washington",
    publicInputs: {
      certificate_type: "provider_capacity",
      study_id: "study-2",
      county: "washington",
      service_type: "emergency_shelter",
      providers_included: "3",
      occupied_beds: "96",
      licensed_beds: "110",
      same_day_available_programs: "9",
      total_programs: "14"
    },
    witnessLabel: "Provider occupancy release batch",
    simulated: true,
    createdAt: "Today, 10:49 AM"
  },
  {
    id: "proof-7",
    proofType: "analytics_provider_capacity",
    claim: "Provider capacity gap alerts in clackamas county",
    verifier: "Clackamas provider verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-provider-capacity-v1",
    verifierDigest: "analytics-cap-7d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-cap-clackamas",
    publicInputs: {
      certificate_type: "provider_capacity",
      study_id: "study-2",
      county: "clackamas",
      service_type: "emergency_shelter",
      providers_included: "3",
      occupied_beds: "76",
      licensed_beds: "80",
      same_day_available_programs: "5",
      total_programs: "10"
    },
    witnessLabel: "Provider occupancy release batch",
    simulated: true,
    createdAt: "Today, 10:51 AM"
  },
  {
    id: "proof-15",
    proofType: "analytics_provider_capacity",
    claim: "Provider capacity gap alerts in multnomah county transitional housing",
    verifier: "Multnomah provider verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-provider-capacity-v1",
    verifierDigest: "analytics-cap-15d64c5b78caa09fd67d24b099c1ca8",
    proofArtifactRef: "zk-cert-analytics-cap-multnomah-transitional",
    publicInputs: {
      certificate_type: "provider_capacity",
      study_id: "study-2",
      county: "multnomah",
      service_type: "transitional_housing",
      providers_included: "2",
      occupied_beds: "41",
      licensed_beds: "56",
      same_day_available_programs: "4",
      total_programs: "8"
    },
    witnessLabel: "Provider occupancy release batch",
    simulated: true,
    createdAt: "Today, 10:52 AM"
  },
  {
    id: "proof-8",
    proofType: "analytics_housing_outcome",
    claim: "Housing placements after referral in multnomah county",
    verifier: "Multnomah housing verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-housing-outcome-v1",
    verifierDigest: "analytics-house-8d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-house-multnomah",
    publicInputs: {
      certificate_type: "housing_outcome",
      study_id: "study-3",
      county: "multnomah",
      housing_outcome: "placed",
      referrals_completed: "120",
      housed_referrals: "50"
    },
    witnessLabel: "Referral outcome release batch",
    simulated: true,
    createdAt: "Today, 10:53 AM"
  },
  {
    id: "proof-9",
    proofType: "analytics_housing_outcome",
    claim: "Housing placements after referral in washington county",
    verifier: "Washington housing verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-housing-outcome-v1",
    verifierDigest: "analytics-house-9d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-house-washington",
    publicInputs: {
      certificate_type: "housing_outcome",
      study_id: "study-3",
      county: "washington",
      housing_outcome: "placed",
      referrals_completed: "90",
      housed_referrals: "38"
    },
    witnessLabel: "Referral outcome release batch",
    simulated: true,
    createdAt: "Today, 10:55 AM"
  },
  {
    id: "proof-10",
    proofType: "analytics_housing_outcome",
    claim: "Housing placements after referral in clackamas county",
    verifier: "Clackamas housing verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-housing-outcome-v1",
    verifierDigest: "analytics-house-10d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-house-clackamas",
    publicInputs: {
      certificate_type: "housing_outcome",
      study_id: "study-3",
      county: "clackamas",
      housing_outcome: "placed",
      referrals_completed: "60",
      housed_referrals: "25"
    },
    witnessLabel: "Referral outcome release batch",
    simulated: true,
    createdAt: "Today, 10:57 AM"
  },
  {
    id: "proof-16",
    proofType: "analytics_housing_outcome",
    claim: "Housing placements after referral in multnomah county rapid rehousing cohort",
    verifier: "Multnomah housing verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-housing-outcome-v1",
    verifierDigest: "analytics-house-16d64c5b78caa09fd67d24b099c1ca",
    proofArtifactRef: "zk-cert-analytics-house-multnomah-rapid",
    publicInputs: {
      certificate_type: "housing_outcome",
      study_id: "study-3",
      county: "multnomah",
      housing_outcome: "rapid_rehousing",
      referrals_completed: "44",
      housed_referrals: "19"
    },
    witnessLabel: "Referral outcome release batch",
    simulated: true,
    createdAt: "Today, 10:58 AM"
  },
  {
    id: "proof-11",
    proofType: "analytics_outreach_followup",
    claim: "Street outreach follow-up rate in multnomah county",
    verifier: "Multnomah outreach verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-outreach-followup-v1",
    verifierDigest: "analytics-outreach-11d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-outreach-multnomah",
    publicInputs: {
      certificate_type: "outreach_followup",
      study_id: "study-2",
      county: "multnomah",
      service_type: "street_outreach",
      completed_followups: "43",
      assigned_followups: "63"
    },
    witnessLabel: "Outreach follow-up release batch",
    simulated: true,
    createdAt: "Today, 10:59 AM"
  },
  {
    id: "proof-12",
    proofType: "analytics_outreach_followup",
    claim: "Street outreach follow-up rate in washington county",
    verifier: "Washington outreach verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-outreach-followup-v1",
    verifierDigest: "analytics-outreach-12d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-outreach-washington",
    publicInputs: {
      certificate_type: "outreach_followup",
      study_id: "study-2",
      county: "washington",
      service_type: "street_outreach",
      completed_followups: "29",
      assigned_followups: "42"
    },
    witnessLabel: "Outreach follow-up release batch",
    simulated: true,
    createdAt: "Today, 11:01 AM"
  },
  {
    id: "proof-13",
    proofType: "analytics_outreach_followup",
    claim: "Street outreach follow-up rate in clackamas county",
    verifier: "Clackamas outreach verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-outreach-followup-v1",
    verifierDigest: "analytics-outreach-13d64c5b78caa09fd67d24b099c1ca87",
    proofArtifactRef: "zk-cert-analytics-outreach-clackamas",
    publicInputs: {
      certificate_type: "outreach_followup",
      study_id: "study-2",
      county: "clackamas",
      service_type: "street_outreach",
      completed_followups: "26",
      assigned_followups: "39"
    },
    witnessLabel: "Outreach follow-up release batch",
    simulated: true,
    createdAt: "Today, 11:03 AM"
  },
  {
    id: "proof-17",
    proofType: "analytics_outreach_followup",
    claim: "Street outreach follow-up rate in multnomah county hygiene outreach",
    verifier: "Multnomah outreach verifier",
    proofSystem: "simulated_zk_certificate",
    verificationStatus: "verified",
    circuitId: "analytics-outreach-followup-v1",
    verifierDigest: "analytics-outreach-17d64c5b78caa09fd67d24b099c1",
    proofArtifactRef: "zk-cert-analytics-outreach-multnomah-hygiene",
    publicInputs: {
      certificate_type: "outreach_followup",
      study_id: "study-2",
      county: "multnomah",
      service_type: "hygiene_outreach",
      completed_followups: "17",
      assigned_followups: "24"
    },
    witnessLabel: "Outreach follow-up release batch",
    simulated: true,
    createdAt: "Today, 11:04 AM"
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
