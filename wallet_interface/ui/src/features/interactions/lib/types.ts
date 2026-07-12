/**
 * interactions feature — public type contracts
 *
 * These types will be the stable API surface once services/serviceInteractionService.ts
 * and related screens are migrated into this slice.
 */

/** A recorded interaction between a client and a service provider. */
export interface ServiceInteraction {
  interaction_id: string;
  wallet_id: string;
  service_id: string;
  service_name: string;
  interaction_type: "visit" | "call" | "referral" | "outcome";
  occurred_at: string;
  recorded_at: string;
  notes?: string;
  outcome?: string;
  worker_name?: string;
}

/** A note attached to a service interaction. */
export interface InteractionNote {
  note_id: string;
  interaction_id: string;
  author_did: string;
  content: string;
  created_at: string;
  is_private: boolean;
}
