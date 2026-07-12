/**
 * wallet feature — public type contracts
 *
 * These types will be the stable API surface once services/walletApi.ts
 * and related files are migrated into this slice.
 */

/** Base configuration for the wallet REST API client. */
export interface WalletApiConfig {
  /** Base URL of the wallet backend (e.g. "https://wallet.211-ai.com"). */
  baseUrl: string;
  /** ****** obtained after magic-login. */
  bearerToken?: string;
}

/** Result of a record or file upload to IPFS/Filecoin. */
export interface UploadResult {
  cid: string;
  gatewayUrl: string;
  filecoinPinRequestId?: string;
  statusUrl?: string;
  provider: string;
  status: "stored" | "queued" | "failed";
}

/** A wallet record summary returned by the list endpoint. */
export interface WalletRecordSummary {
  record_id: string;
  wallet_id: string;
  data_type: string;
  created_at: string;
  updated_at: string;
  cid?: string;
  labels?: string[];
}

/** Access-request entry visible to wallet owner. */
export interface WalletAccessRequest {
  request_id: string;
  requester_did: string;
  audience_did: string;
  resources: string[];
  abilities: string[];
  purpose: string;
  status: "pending" | "approved" | "rejected" | "revoked";
  created_at: string;
}
