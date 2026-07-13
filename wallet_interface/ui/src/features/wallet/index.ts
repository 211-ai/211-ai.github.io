/**
 * wallet feature slice
 *
 * Owns wallet management screens, the wallet API client, and proof/export UI.
 * Migrated from:
 *   app/screens/ProofCenterScreen.tsx
 *   app/screens/ExportCenterScreen.tsx
 *   app/screens/RecipientAccessScreen.tsx
 *   app/screens/UploadsScreen.tsx
 *   app/screens/BenefitsProtectionScreen.tsx
 *   services/walletApi.ts
 *   services/walletProofReview.ts
 *   services/filecoinStorage.ts
 *   services/walrusStorage.ts
 */

// Types
export type { WalletApiConfig, UploadResult } from "./lib/types";

// Services (canonical locations)
export * from "./lib/walletApi";
export * from "./lib/walletProofReview";
export * from "./lib/filecoinStorage";
export * from "./lib/walrusStorage";

// Components
export { ProofCenterScreen } from "./components/ProofCenterScreen";
export { ExportCenterScreen } from "./components/ExportCenterScreen";
export { RecipientAccessScreen } from "./components/RecipientAccessScreen";
export { UploadsScreen } from "./components/UploadsScreen";
export { BenefitsProtectionScreen } from "./components/BenefitsProtectionScreen";
