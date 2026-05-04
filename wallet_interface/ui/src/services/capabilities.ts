import { DisclosureDataScope } from "../models/abby";

const CAPABILITY_LABELS: Record<string, string> = {
  "analytics/contribute": "analytics contribution",
  "analytics/query": "analytics query",
  "derived/read": "derived facts read",
  "export/create": "full wallet export",
  "grant/create": "broader re-sharing",
  "location/read_coarse": "coarse location read",
  "location/read_precise": "precise location read",
  "metadata/read": "metadata read",
  "proof/verify": "proof verification",
  "record/decrypt": "plaintext decrypt"
};

const DEFAULT_SENSITIVE_ABILITIES = [
  "record/decrypt",
  "location/read_precise",
  "grant/create",
  "analytics/query",
  "export/create"
];

const SCOPE_ABILITIES: Partial<Record<DisclosureDataScope, string[]>> = {
  benefits_information: ["derived/read"],
  current_location: ["location/read_coarse"],
  found_permanent_housing: ["derived/read"],
  identity_minimum: ["metadata/read"],
  medical_notes: ["derived/read"],
  missed_check_in: ["metadata/read"],
  photo: ["metadata/read"],
  profile: ["metadata/read"],
  shelter_history: ["derived/read"],
  uploaded_documents: ["record/decrypt"]
};

export function nonGrantedCapabilities(
  grantedAbilities: string[],
  sensitiveAbilities = DEFAULT_SENSITIVE_ABILITIES
): string[] {
  const granted = new Set(grantedAbilities);
  return sensitiveAbilities
    .filter((ability) => !granted.has(ability))
    .map((ability) => CAPABILITY_LABELS[ability] ?? ability);
}

export function abilitiesForDisclosureScopes(scopes: DisclosureDataScope[]): string[] {
  return Array.from(new Set(scopes.flatMap((scope) => SCOPE_ABILITIES[scope] ?? ["metadata/read"])));
}

export function capabilitySummary(abilities: string[]): string {
  return abilities.map((ability) => CAPABILITY_LABELS[ability] ?? ability).join(", ");
}
