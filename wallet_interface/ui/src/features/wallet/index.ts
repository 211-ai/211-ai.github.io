/**
 * wallet feature slice
 *
 * Owns wallet management screens, the wallet API client, and proof/export UI.
 * Migrate from:
 *   app/screens/ProofCenterScreen.tsx
 *   app/screens/ExportCenterScreen.tsx
 *   app/screens/RecipientAccessScreen.tsx
 *   services/walletApi.ts
 *   services/walletProofReview.ts (future)
 */

// Re-export public API when components/hooks are migrated here.
// Example:
//   export { ProofCenterScreen } from './components/ProofCenterScreen';
//   export { useWalletSync } from './hooks/useWalletSync';
