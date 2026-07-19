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
 *   app/screens/AnalyticsScreen.tsx
 *   app/screens/ContactsScreen.tsx
 *   app/screens/LoginScreen.tsx
 *   app/screens/RegistrationScreen.tsx
 *   app/screens/SettingsScreen.tsx
 *   services/walletApi.ts
 *   services/walletProofReview.ts
 *   services/filecoinStorage.ts
 *   services/walrusStorage.ts
 *   services/capabilities.ts
 *   services/mockAbbyService.ts
 */

// Types
export type { WalletApiConfig, UploadResult } from "./lib/types";

// Services (canonical locations)
export * from "./lib/walletApi";
export * from "./lib/walletProofReview";
export * from "./lib/filecoinStorage";
export * from "./lib/walrusStorage";
export * from "./lib/capabilities";
export * from "./lib/mockAbbyService";

// Components
export { ProofCenterScreen } from "./components/ProofCenterScreen";
export { ExportCenterScreen } from "./components/ExportCenterScreen";
export { RecipientAccessScreen } from "./components/RecipientAccessScreen";
export { UploadsScreen } from "./components/UploadsScreen";
export { BenefitsProtectionScreen } from "./components/BenefitsProtectionScreen";
export { AnalyticsScreen } from "./components/AnalyticsScreen";
export { ContactsScreen } from "./components/ContactsScreen";
export { LoginScreen } from "./components/LoginScreen";
export { RegistrationScreen } from "./components/RegistrationScreen";
export { SettingsScreen } from "./components/SettingsScreen";
