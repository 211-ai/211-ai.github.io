/**
 * wallet feature slice
 *
 * Owns wallet management screens, the wallet API client, and proof/export UI.
 * Migrate from:
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

// Types — re-exported from lib once migration is complete
export type { WalletApiConfig, UploadResult } from "./lib/types";

// Components — uncomment as screens are migrated
// export { ProofCenterScreen } from './components/ProofCenterScreen';
// export { ExportCenterScreen } from './components/ExportCenterScreen';
// export { RecipientAccessScreen } from './components/RecipientAccessScreen';
// export { UploadsScreen } from './components/UploadsScreen';

// Hooks — uncomment as hooks are migrated
// export { useWalletSync } from './hooks/useWalletSync';
// export { useWalletRecords } from './hooks/useWalletRecords';
