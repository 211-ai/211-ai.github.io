/**
 * service-navigation feature — public type contracts
 *
 * These types will be the stable API surface once services/serviceActionService.ts,
 * services/serviceInteractionService.ts, and related screens are migrated.
 */

/** A 211-directory service entry returned by GraphRAG or live search. */
export interface ServiceDirectoryEntry {
  id: string;
  name: string;
  description?: string;
  categories: string[];
  phone?: string;
  address?: string;
  url?: string;
  hours?: string;
  eligibility?: string;
  score?: number;
}

/** Parameters for searching the 211 service directory. */
export interface ServiceSearchParams {
  query: string;
  location?: string;
  categories?: string[];
  limit?: number;
  offset?: number;
}

/** A service plan containing an ordered list of services for a client. */
export interface ServicePlan {
  plan_id: string;
  wallet_id: string;
  title: string;
  services: ServicePlanItem[];
  created_at: string;
  updated_at: string;
}

/** A single item in a service plan. */
export interface ServicePlanItem {
  service_id: string;
  service_name: string;
  status: "pending" | "in_progress" | "completed" | "skipped";
  notes?: string;
}
