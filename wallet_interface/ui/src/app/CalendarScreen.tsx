import { useMemo } from "react";
import { Bell, CalendarClock, Clock, Download, ExternalLink, MapPin } from "lucide-react";
import { Badge, Button, Section, StatusBanner } from "../components/ui";
import type { CheckInPolicyDraft, ServiceInteractionEvent, ServicePlan } from "../models/abby";
import { downloadCalendarAction } from "../services/serviceActionService";

type CalendarEventKind = "appointment" | "follow-up" | "check-in";

type CalendarEvent = {
  id: string;
  kind: CalendarEventKind;
  title: string;
  provider: string;
  startsAt: Date;
  detail: string;
  reminderAt?: Date;
  location?: string;
  serviceDocId?: string;
  planId?: string;
  status?: string;
  durationMinutes: number;
};

type CalendarStats = {
  appointments: number;
  followUps: number;
  checkIns: number;
};

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric"
});

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit"
});

export function CalendarScreen({
  interactions,
  onOpenPlan,
  onOpenService,
  policy,
  servicePlans
}: {
  interactions: ServiceInteractionEvent[];
  onOpenPlan: (docId: string) => void;
  onOpenService: (docId: string) => void;
  policy: CheckInPolicyDraft;
  servicePlans: ServicePlan[];
}) {
  const events = useMemo(
    () => buildCalendarEvents({ interactions, policy, servicePlans }),
    [
      interactions,
      policy.intervalDays,
      policy.lastCheckInAt,
      policy.reminderChannels,
      servicePlans
    ]
  );
  const now = new Date();
  const upcomingEvents = events.filter((event) => event.startsAt.getTime() >= now.getTime());
  const pastEvents = events.filter((event) => event.startsAt.getTime() < now.getTime()).slice(-5).reverse();
  const nextEvent = upcomingEvents[0];
  const stats = events.reduce<CalendarStats>(
    (current, event) => ({
      appointments: current.appointments + (event.kind === "appointment" ? 1 : 0),
      followUps: current.followUps + (event.kind === "follow-up" ? 1 : 0),
      checkIns: current.checkIns + (event.kind === "check-in" ? 1 : 0)
    }),
    { appointments: 0, followUps: 0, checkIns: 0 }
  );

  return (
    <div className="screen calendar-screen">
      <div className="page-title">
        <p className="eyebrow">Client portal</p>
        <h1>Calendar</h1>
      </div>
      <p className="page-note">
        Upcoming appointments, service follow-ups, and check-ins are collected here so the client can see where they
        need to be and when.
      </p>

      <section className="calendar-summary-grid" aria-label="Calendar summary">
        <div className="calendar-summary-panel">
          <span>Next item</span>
          <strong>{nextEvent ? formatRelativeDay(nextEvent.startsAt, now) : "No upcoming items"}</strong>
          <small>{nextEvent ? `${nextEvent.title} at ${timeFormatter.format(nextEvent.startsAt)}` : "Add an appointment from a service plan."}</small>
        </div>
        <div className="calendar-summary-panel">
          <span>Appointments</span>
          <strong>{stats.appointments}</strong>
          <small>Scheduled from saved service plans.</small>
        </div>
        <div className="calendar-summary-panel">
          <span>Follow-ups</span>
          <strong>{stats.followUps}</strong>
          <small>Next actions from service interactions.</small>
        </div>
      </section>

      {nextEvent ? (
        <StatusBanner tone="info">
          Next up: {nextEvent.title} on {formatDateTime(nextEvent.startsAt)}.
          {nextEvent.location ? ` Travel target: ${nextEvent.location}.` : ""}
        </StatusBanner>
      ) : null}

      <Section title="Upcoming schedule">
        {upcomingEvents.length > 0 ? (
          <div className="calendar-list">
            {upcomingEvents.map((event) => (
              <CalendarEventRow
                event={event}
                key={event.id}
                now={now}
                onOpenPlan={onOpenPlan}
                onOpenService={onOpenService}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <h3>No upcoming appointments</h3>
            <p>Add appointment times from a saved service plan to start building the schedule.</p>
          </div>
        )}
      </Section>

      {pastEvents.length > 0 ? (
        <Section title="Past items">
          <div className="calendar-list">
            {pastEvents.map((event) => (
              <CalendarEventRow
                event={event}
                key={event.id}
                now={now}
                onOpenPlan={onOpenPlan}
                onOpenService={onOpenService}
              />
            ))}
          </div>
        </Section>
      ) : null}
    </div>
  );
}

function CalendarEventRow({
  event,
  now,
  onOpenPlan,
  onOpenService
}: {
  event: CalendarEvent;
  now: Date;
  onOpenPlan: (docId: string) => void;
  onOpenService: (docId: string) => void;
}) {
  const isPast = event.startsAt.getTime() < now.getTime();

  function addToCalendar() {
    downloadCalendarAction({
      title: event.title,
      startsAt: event.startsAt,
      durationMinutes: event.durationMinutes,
      location: event.location,
      notes: buildCalendarNotes(event),
      alarms: event.reminderAt ? [buildAlarm(event)] : undefined,
      context: {
        providerName: event.provider,
        serviceDocId: event.serviceDocId,
        serviceTitle: event.title
      }
    });
  }

  return (
    <article className={`calendar-event-item ${isPast ? "calendar-event-past" : ""}`}>
      <div className="calendar-date-block" aria-label={formatDateTime(event.startsAt)}>
        <strong>{formatRelativeDay(event.startsAt, now)}</strong>
        <span>{timeFormatter.format(event.startsAt)}</span>
      </div>
      <div className="calendar-event-body">
        <div className="badge-row">
          <Badge tone={event.kind === "appointment" ? "success" : event.kind === "follow-up" ? "warning" : "info"}>
            {eventKindLabel(event.kind)}
          </Badge>
          {event.status ? <Badge>{event.status}</Badge> : null}
          {isPast ? <Badge>past</Badge> : null}
        </div>
        <h3>{event.title}</h3>
        <p>{event.detail}</p>
        <dl className="calendar-event-meta">
          <div>
            <Clock aria-hidden="true" size={16} />
            <dt>When</dt>
            <dd>{formatDateTime(event.startsAt)}</dd>
          </div>
          {event.location ? (
            <div>
              <MapPin aria-hidden="true" size={16} />
              <dt>Travel</dt>
              <dd>{event.location}</dd>
            </div>
          ) : null}
          {event.reminderAt ? (
            <div>
              <Bell aria-hidden="true" size={16} />
              <dt>Reminder</dt>
              <dd>{formatDateTime(event.reminderAt)}</dd>
            </div>
          ) : null}
          {event.provider ? (
            <div>
              <CalendarClock aria-hidden="true" size={16} />
              <dt>Provider</dt>
              <dd>{event.provider}</dd>
            </div>
          ) : null}
        </dl>
      </div>
      <div className="row-actions calendar-event-actions">
        <Button onClick={addToCalendar} variant="secondary">
          <Download aria-hidden="true" size={18} />
          Add to calendar
        </Button>
        {event.planId && event.serviceDocId ? (
          <Button onClick={() => onOpenPlan(event.serviceDocId ?? "")} variant="secondary">
            <ExternalLink aria-hidden="true" size={18} />
            Open plan
          </Button>
        ) : event.serviceDocId ? (
          <Button onClick={() => onOpenService(event.serviceDocId ?? "")} variant="secondary">
            <ExternalLink aria-hidden="true" size={18} />
            Open service
          </Button>
        ) : null}
      </div>
    </article>
  );
}

function buildCalendarEvents({
  interactions,
  policy,
  servicePlans
}: {
  interactions: ServiceInteractionEvent[];
  policy: CheckInPolicyDraft;
  servicePlans: ServicePlan[];
}): CalendarEvent[] {
  const planEvents = servicePlans.flatMap((plan): CalendarEvent[] => {
    const appointmentAt = parseDate(plan.appointment_at);
    if (!appointmentAt) return [];

    const title = firstPresent(plan.service_title, plan.provider_name, "Service appointment");
    return [
      {
        id: `plan:${plan.plan_id}`,
        kind: "appointment",
        title,
        provider: plan.provider_name,
        startsAt: appointmentAt,
        detail: firstPresent(plan.goal, "Scheduled service appointment."),
        reminderAt: parseDate(plan.reminder_at) ?? undefined,
        location: trimToUndefined(plan.travel_target),
        serviceDocId: trimToUndefined(plan.service_doc_id),
        planId: plan.plan_id,
        status: trimToUndefined(plan.status),
        durationMinutes: 60
      }
    ];
  });

  const followUpEvents = interactions.flatMap((interaction): CalendarEvent[] => {
    const followUpAt = parseDate(interaction.next_follow_up_at);
    if (!followUpAt) return [];

    const title = firstPresent(interaction.next_action, interaction.program_name, interaction.provider_name, "Service follow-up");
    const provider = firstPresent(interaction.provider_name, interaction.counterparty_name);
    return [
      {
        id: `follow-up:${interaction.interaction_id}`,
        kind: "follow-up",
        title,
        provider,
        startsAt: followUpAt,
        detail: firstPresent(interaction.outcome, interaction.program_name, "Follow up with this service provider."),
        serviceDocId: trimToUndefined(interaction.service_doc_id),
        status: trimToUndefined(interaction.status),
        durationMinutes: 30
      }
    ];
  });

  const checkInEvent = buildCheckInEvent(policy);
  return [...planEvents, ...followUpEvents, ...(checkInEvent ? [checkInEvent] : [])].sort(
    (left, right) => left.startsAt.getTime() - right.startsAt.getTime()
  );
}

function buildCheckInEvent(policy: CheckInPolicyDraft): CalendarEvent | null {
  const lastCheckInAt = parseDate(policy.lastCheckInAt);
  if (!lastCheckInAt || !Number.isFinite(policy.intervalDays) || policy.intervalDays <= 0) return null;

  const startsAt = new Date(lastCheckInAt);
  startsAt.setDate(startsAt.getDate() + policy.intervalDays);
  const channels = policy.reminderChannels.length > 0 ? policy.reminderChannels.join(", ") : "web";

  return {
    id: `check-in:${policy.lastCheckInAt}:${policy.intervalDays}`,
    kind: "check-in",
    title: "Check in with Abby",
    provider: "Abby",
    startsAt,
    detail: `Reminder channels: ${channels}.`,
    durationMinutes: 15
  };
}

function buildAlarm(event: CalendarEvent) {
  if (!event.reminderAt) {
    return { description: event.title, triggerMinutesBefore: 60 };
  }

  const minutes = Math.max(0, Math.round((event.startsAt.getTime() - event.reminderAt.getTime()) / 60000));
  return { description: event.title, triggerMinutesBefore: minutes };
}

function buildCalendarNotes(event: CalendarEvent): string {
  return [
    event.detail,
    event.provider ? `Provider: ${event.provider}` : "",
    event.location ? `Travel target: ${event.location}` : "",
    event.reminderAt ? `Reminder: ${formatDateTime(event.reminderAt)}` : ""
  ]
    .filter(Boolean)
    .join("\n");
}

function parseDate(value: string): Date | null {
  if (!value.trim()) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function firstPresent(...values: string[]): string {
  return values.map((value) => value.trim()).find(Boolean) ?? "";
}

function trimToUndefined(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed || undefined;
}

function eventKindLabel(kind: CalendarEventKind): string {
  if (kind === "appointment") return "appointment";
  if (kind === "follow-up") return "follow-up";
  return "check-in";
}

function formatRelativeDay(date: Date, now: Date): string {
  const today = startOfDay(now);
  const target = startOfDay(date);
  const days = Math.round((target.getTime() - today.getTime()) / 86400000);

  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  if (days === -1) return "Yesterday";
  return dateFormatter.format(date);
}

function formatDateTime(date: Date): string {
  return `${dateFormatter.format(date)} at ${timeFormatter.format(date)}`;
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}
