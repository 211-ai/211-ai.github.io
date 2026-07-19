/**
 * calendar feature — public type contracts
 *
 * These types will be the stable API surface once app/CalendarScreen.tsx
 * and lib/calendar/ are migrated into this slice.
 */

/** A calendar event (appointment, service visit, check-in). */
export interface CalendarEvent {
  event_id: string;
  wallet_id: string;
  title: string;
  description?: string;
  start_time: string;
  end_time?: string;
  event_type: "appointment" | "check_in" | "service_visit" | "reminder";
  service_id?: string;
  service_name?: string;
  location?: string;
  is_recurring: boolean;
}

/** A completed or scheduled check-in entry. */
export interface CheckInEntry {
  check_in_id: string;
  wallet_id: string;
  channel: "email" | "sms" | "web";
  status: "ok" | "missed" | "pending";
  checked_in_at?: string;
  expected_at: string;
  notes?: string;
}

/** Filter parameters for calendar event queries. */
export interface CalendarFilters {
  wallet_id?: string;
  event_type?: CalendarEvent["event_type"];
  from_date?: string;
  to_date?: string;
  include_recurring?: boolean;
}
