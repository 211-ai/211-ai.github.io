import type { CheckInPolicyDraft, SavedService, ServiceInteractionEvent, ServicePlan } from "../../models/abby";
import type { SearchResult, ServiceLocationRecord } from "../../lib/graphrag";
import { formatShelterDate } from "./providerHelpers";

// ─── Service persistence helpers ──────────────────────────────────────────────

export function appStableSuffix(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
}

export function toSaveWalletServiceInput(result: SearchResult) {
  const document = result.document;
  const title = document.program_name || document.provider_name || document.title || result.docId;
  return {
    serviceDocId: result.docId,
    sourceContentCid: result.contentCid || document.source_content_cid || `ui-unresolved-${appStableSuffix(result.docId)}`,
    sourcePageCid: result.pageCid || document.source_page_cid || "",
    title,
    providerName: document.provider_name || "",
    programName: document.program_name || document.title || "",
    sourceUrl: document.source_url || "",
    label: title,
    priority: "normal",
    reason: "",
    status: "saved",
    metadata: {
      saved_from: "services_search"
    }
  };
}

export function toLocalSavedService(result: SearchResult, walletId = "local-wallet"): SavedService {
  const now = new Date().toISOString();
  const input = toSaveWalletServiceInput(result);
  return {
    created_at: now,
    label: input.label,
    metadata: input.metadata,
    priority: input.priority,
    private_notes_record_id: "",
    program_name: input.programName,
    provider_name: input.providerName,
    reason: input.reason,
    saved_service_id: `saved-local-${appStableSuffix(input.serviceDocId)}`,
    service_doc_id: input.serviceDocId,
    source_content_cid: input.sourceContentCid,
    source_page_cid: input.sourcePageCid,
    source_url: input.sourceUrl,
    status: input.status,
    title: input.title,
    updated_at: now,
    wallet_id: walletId
  };
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(Math.max(0, Math.trunc(value || 0)));
}

// ─── Home calendar helpers ────────────────────────────────────────────────────

export type HomeServiceSuggestion = {
  need: string;
  result: SearchResult;
  locationLabel: string;
};

export type HomeCalendarItem = {
  id: string;
  title: string;
  detail: string;
  kindLabel: string;
  urgencyLabel: string;
  urgencyTone: "neutral" | "warning" | "info";
  startsAt: Date;
  location?: string;
  serviceDocId?: string;
};

export function parseHomeDate(value: string): Date | null {
  if (!value.trim()) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function describeHomeUrgency(
  startsAt: Date,
  now: Date
): { label: string; tone: "neutral" | "warning" | "info" } | null {
  const deltaMs = startsAt.getTime() - now.getTime();
  const dayMs = 24 * 60 * 60 * 1000;
  if (deltaMs < 0) {
    return { label: "Overdue", tone: "warning" };
  }
  if (deltaMs <= dayMs) {
    return { label: "Today", tone: "warning" };
  }
  if (deltaMs <= 2 * dayMs) {
    return { label: "Tomorrow", tone: "warning" };
  }
  if (deltaMs <= 7 * dayMs) {
    return { label: `In ${Math.round(deltaMs / dayMs)} days`, tone: "info" };
  }
  return { label: formatShelterDate(startsAt.toISOString()), tone: "neutral" };
}

export function formatHomeDateTime(value: Date): string {
  return value.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

export function buildHomeCalendarItems({
  policy,
  serviceInteractions,
  servicePlans
}: {
  policy: CheckInPolicyDraft;
  serviceInteractions: ServiceInteractionEvent[];
  servicePlans: ServicePlan[];
}): HomeCalendarItem[] {
  const now = new Date();
  const twoWeeksAhead = now.getTime() + 14 * 24 * 60 * 60 * 1000;
  const items: HomeCalendarItem[] = [];

  for (const plan of servicePlans) {
    const startsAt = parseHomeDate(plan.appointment_at);
    if (!startsAt) continue;
    const urgency = describeHomeUrgency(startsAt, now);
    if (!urgency || startsAt.getTime() > twoWeeksAhead) continue;
    items.push({
      id: `plan:${plan.plan_id}`,
      title: plan.service_title || plan.provider_name || "Service appointment",
      detail: plan.goal || "Scheduled service appointment.",
      kindLabel: "Appointment",
      urgencyLabel: urgency.label,
      urgencyTone: urgency.tone,
      startsAt,
      location: plan.travel_target.trim() || undefined,
      serviceDocId: plan.service_doc_id || undefined
    });
  }

  for (const interaction of serviceInteractions) {
    const startsAt = parseHomeDate(interaction.next_follow_up_at);
    if (!startsAt) continue;
    const urgency = describeHomeUrgency(startsAt, now);
    if (!urgency || startsAt.getTime() > twoWeeksAhead) continue;
    items.push({
      id: `follow-up:${interaction.interaction_id}`,
      title: interaction.next_action || interaction.program_name || interaction.provider_name || "Service follow-up",
      detail: interaction.outcome || interaction.program_name || "Follow up with this provider.",
      kindLabel: "Follow-up",
      urgencyLabel: urgency.label,
      urgencyTone: urgency.tone,
      startsAt,
      serviceDocId: interaction.service_doc_id || undefined
    });
  }

  const nextCheckInAt = parseHomeDate(policy.lastCheckInAt);
  if (nextCheckInAt && policy.intervalDays > 0) {
    nextCheckInAt.setDate(nextCheckInAt.getDate() + policy.intervalDays);
    const urgency = describeHomeUrgency(nextCheckInAt, now);
    if (urgency) {
      items.push({
        id: `check-in:${policy.lastCheckInAt}:${policy.intervalDays}`,
        title: "Check in with Abby",
        detail: `Reminder channels: ${policy.reminderChannels.join(", ") || "web"}.`,
        kindLabel: "Check-in",
        urgencyLabel: urgency.label,
        urgencyTone: urgency.tone,
        startsAt: nextCheckInAt
      });
    }
  }

  return items.sort((left, right) => left.startsAt.getTime() - right.startsAt.getTime());
}

// ─── Location label helpers ───────────────────────────────────────────────────

export function formatServiceLocationLabel(location: ServiceLocationRecord | null | undefined): string {
  if (!location) return "";
  return (
    location.address ||
    location.maps_query ||
    [location.street, location.city, location.state, location.postal_code].filter(Boolean).join(", ")
  );
}

export function choosePreferredServiceLocation(
  rows: ServiceLocationRecord[],
  preferredClusterIds: Set<number>
): ServiceLocationRecord | null {
  if (!rows.length) return null;
  const rankedRows = [...rows].sort((left, right) => {
    const leftPreferred = left.geo_cluster_id != null && preferredClusterIds.has(left.geo_cluster_id) ? 1 : 0;
    const rightPreferred = right.geo_cluster_id != null && preferredClusterIds.has(right.geo_cluster_id) ? 1 : 0;
    if (leftPreferred !== rightPreferred) return rightPreferred - leftPreferred;
    const leftHasAddress = formatServiceLocationLabel(left) ? 1 : 0;
    const rightHasAddress = formatServiceLocationLabel(right) ? 1 : 0;
    if (leftHasAddress !== rightHasAddress) return rightHasAddress - leftHasAddress;
    return String(left.location_id).localeCompare(String(right.location_id));
  });
  return rankedRows[0] || null;
}

export function buildSearchResultLocationLabels(
  results: SearchResult[],
  locationRows: ServiceLocationRecord[],
  preferredClusterIds: number[]
): Record<string, string> {
  const preferredClusterSet = new Set(preferredClusterIds);
  const rowsByDocId = new Map<string, ServiceLocationRecord[]>();
  for (const row of locationRows) {
    if (!row.service_doc_id) continue;
    const existing = rowsByDocId.get(row.service_doc_id) || [];
    existing.push(row);
    rowsByDocId.set(row.service_doc_id, existing);
  }

  const labels: Record<string, string> = {};
  for (const result of results) {
    const row = choosePreferredServiceLocation(rowsByDocId.get(result.docId) || [], preferredClusterSet);
    const label = formatServiceLocationLabel(row);
    if (label) {
      labels[result.docId] = label;
    }
  }
  return labels;
}
