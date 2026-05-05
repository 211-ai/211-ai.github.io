import type { AuditEvent } from "../../models/abby";
import { auditEvents } from "../../services/mockAbbyService";
import { listWalletAuditEvents } from "../../services/walletApi";
import type { AppActionResult, AppActionRuntime, AppActionSuccess } from "../../app/appActions";
import type {
  AgentCommandName,
  AuditEventReferenceCommandInput,
  SearchAuditEventsCommandInput,
  SummarizeAuditEventsCommandInput
} from "../commandSchemas";

export async function searchAuditEventsAction(
  runtime: AppActionRuntime,
  input: SearchAuditEventsCommandInput
): Promise<AppActionResult> {
  const events = await loadAuditEvents(runtime);
  const matches = filterAuditEvents(events, input).slice(0, input.limit ?? 10);
  return success(
    "search_audit_events",
    matches.length
      ? `Found ${matches.length} audit event${plural(matches.length)}: ${matches.map(formatAuditEventBrief).join("; ")}.`
      : "No audit events matched that search.",
    {
      recordIds: matches.map((event) => event.id),
      metadata: {
        events: matches.map(sanitizeAuditEvent),
        privateNotesExposed: false
      }
    }
  );
}

export async function summarizeAuditEventsAction(
  runtime: AppActionRuntime,
  input: SummarizeAuditEventsCommandInput
): Promise<AppActionResult> {
  const events = filterAuditEvents(await loadAuditEvents(runtime), input).slice(0, input.limit ?? 25);
  if (!events.length) {
    return success("summarize_audit_events", "No audit events are available for that summary.", {
      metadata: { privateNotesExposed: false }
    });
  }

  const actors = countBy(events.map((event) => safeText(event.actor)));
  const decisions = countBy(events.map((event) => safeText(event.decision)).filter(Boolean));
  const recent = events.slice(0, Math.min(5, events.length)).map(formatAuditEventBrief);
  const decisionSummary = Object.keys(decisions).length ? ` Decisions: ${formatCounts(decisions)}.` : "";
  return success(
    "summarize_audit_events",
    `${events.length} audit event${plural(events.length)} reviewed. Actors: ${formatCounts(actors)}.${decisionSummary} Recent: ${recent.join("; ")}.`,
    {
      recordIds: events.map((event) => event.id),
      metadata: {
        eventCount: events.length,
        actors,
        decisions,
        recentEvents: events.slice(0, 5).map(sanitizeAuditEvent),
        privateNotesExposed: false
      }
    }
  );
}

export async function explainAuditEventAction(
  runtime: AppActionRuntime,
  input: AuditEventReferenceCommandInput
): Promise<AppActionResult> {
  const events = await loadAuditEvents(runtime);
  const event = events.find((candidate) => candidate.id === input.eventId.trim());
  if (!event) {
    return {
      ok: false,
      action: "explain_audit_event",
      errorCode: "audit_event_not_found",
      message: `Audit event ${input.eventId} was not found.`
    };
  }

  return success("explain_audit_event", formatAuditEventExplanation(event), {
    artifactId: event.id,
    metadata: {
      event: sanitizeAuditEvent(event),
      privateNotesExposed: false
    }
  });
}

async function loadAuditEvents(runtime: AppActionRuntime): Promise<AuditEvent[]> {
  if (!runtime.walletApiConfig) return runtime.getState().walletAuditEvents.length ? runtime.getState().walletAuditEvents : auditEvents;
  try {
    const events = await listWalletAuditEvents(runtime.walletApiConfig);
    runtime.setWalletAuditEvents?.(events.length ? events : auditEvents);
    return events.length ? events : auditEvents;
  } catch {
    return runtime.getState().walletAuditEvents.length ? runtime.getState().walletAuditEvents : auditEvents;
  }
}

function filterAuditEvents(
  events: AuditEvent[],
  input: SearchAuditEventsCommandInput | SummarizeAuditEventsCommandInput
): AuditEvent[] {
  const query = input.query?.trim().toLowerCase();
  const actor = input.actor?.trim().toLowerCase();
  const action = input.action?.trim().toLowerCase();
  const resource = input.resource?.trim().toLowerCase();
  const decision = input.decision?.trim().toLowerCase();
  const grantId = input.grantId?.trim().toLowerCase();

  return events.filter((event) => {
    const searchable = [
      event.id,
      event.actor,
      event.action,
      event.timestamp,
      event.resource,
      event.decision,
      event.grantId
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return (
      (!query || searchable.includes(query)) &&
      (!actor || event.actor.toLowerCase().includes(actor)) &&
      (!action || event.action.toLowerCase().includes(action)) &&
      (!resource || event.resource?.toLowerCase().includes(resource)) &&
      (!decision || event.decision?.toLowerCase().includes(decision)) &&
      (!grantId || event.grantId?.toLowerCase().includes(grantId))
    );
  });
}

function sanitizeAuditEvent(event: AuditEvent): AuditEvent {
  return {
    id: event.id,
    actor: safeText(event.actor),
    action: safeText(event.action),
    timestamp: safeText(event.timestamp),
    resource: event.resource ? safeText(event.resource) : undefined,
    decision: event.decision ? safeText(event.decision) : undefined,
    grantId: event.grantId ? safeText(event.grantId) : undefined
  };
}

function formatAuditEventBrief(event: AuditEvent): string {
  const sanitized = sanitizeAuditEvent(event);
  const details = [sanitized.decision, sanitized.resource, sanitized.grantId].filter(Boolean).join(", ");
  return `${sanitized.id} ${sanitized.action} by ${sanitized.actor} at ${sanitized.timestamp}${details ? ` (${details})` : ""}`;
}

function formatAuditEventExplanation(event: AuditEvent): string {
  const sanitized = sanitizeAuditEvent(event);
  const parts = [
    `Audit event ${sanitized.id} records "${sanitized.action}" by ${sanitized.actor} at ${sanitized.timestamp}`,
    sanitized.decision ? `decision ${sanitized.decision}` : "",
    sanitized.resource ? `resource ${sanitized.resource}` : "",
    sanitized.grantId ? `grant ${sanitized.grantId}` : ""
  ].filter(Boolean);
  return `${parts.join(", ")}. Private notes and raw wallet contents are not included in this explanation.`;
}

function safeText(value: string | undefined): string {
  return (value ?? "")
    .replace(/\bprivate\s+notes?\b[^.;,]*/gi, "private notes redacted")
    .replace(/\bnotes?_record_id\b[^.;,]*/gi, "notes record redacted")
    .trim();
}

function countBy(values: string[]): Record<string, number> {
  return values.reduce<Record<string, number>>((counts, value) => {
    if (!value) return counts;
    counts[value] = (counts[value] ?? 0) + 1;
    return counts;
  }, {});
}

function formatCounts(counts: Record<string, number>): string {
  return Object.entries(counts)
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([label, count]) => `${label} ${count}`)
    .join(", ");
}

function success(
  action: AgentCommandName,
  summary: string,
  extra: Omit<AppActionSuccess, "ok" | "action" | "summary"> = {}
): AppActionSuccess {
  return {
    ok: true,
    action,
    summary,
    ...extra
  };
}

function plural(count: number): string {
  return count === 1 ? "" : "s";
}
