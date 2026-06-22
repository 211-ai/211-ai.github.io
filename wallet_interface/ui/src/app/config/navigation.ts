import {
  BarChart3,
  CalendarCheck,
  CalendarClock,
  ClipboardCheck,
  ContactRound,
  HeartHandshake,
  History,
  Home,
  KeyRound,
  Landmark,
  LockKeyhole,
  LogOut,
  MessageSquare,
  Settings as SettingsIcon,
  Share2,
  ShieldCheck,
  Upload,
  UsersRound,
  Wrench,
} from "lucide-react";
import type { RouteId } from "../../models/abby";
import { primaryRoutes, secondaryRoutes } from "../appState";
import type { WalletApiConfig } from "../../services/walletApi";
import { readWalletApiConfig } from "../services/walletConfig";

export const routeIcons: Record<RouteId, typeof Home> = {
  home: Home,
  register: ClipboardCheck,
  "check-in": CalendarCheck,
  calendar: CalendarClock,
  messages: MessageSquare,
  contacts: ContactRound,
  "provider-cases": ClipboardCheck,
  "provider-messages": MessageSquare,
  "provider-analytics": BarChart3,
  "provider-proofs": ShieldCheck,
  "provider-operations": Wrench,
  "sharing-rules": Share2,
  uploads: Upload,
  settings: SettingsIcon,
  "social-services": HeartHandshake,
  interactions: History,
  shelter: Home,
  "provider-clients": UsersRound,
  "recipient-access": KeyRound,
  "benefits-protection": Landmark,
  analytics: BarChart3,
  "proof-center": ShieldCheck,
  exports: LogOut,
  security: LockKeyhole,
  audit: ClipboardCheck,
};

export const removedStandaloneRoutes = new Set<RouteId>([
  "sharing-rules",
  "recipient-access",
  "benefits-protection",
  "exports",
  "security",
]);

const routes = primaryRoutes
  .filter((route) => !removedStandaloneRoutes.has(route.id))
  .map((route) => ({ ...route, icon: routeIcons[route.id] }));

export const secondaryNavigationRoutes = secondaryRoutes
  .filter((route) => !removedStandaloneRoutes.has(route.id))
  .map((route) => ({ ...route, icon: routeIcons[route.id] }));

export const providerRouteIds = new Set<RouteId>([
  "shelter",
  "provider-clients",
  "provider-cases",
  "provider-messages",
  "provider-analytics",
  "provider-proofs",
  "provider-operations",
]);

export const clientNavigationRoutes = routes.filter((route) => !providerRouteIds.has(route.id) && route.id !== "register");
export const providerNavigationRoutes = routes.filter((route) => providerRouteIds.has(route.id));

export type ProviderPortalView = "overview" | "clients" | "cases" | "messages" | "analytics" | "proofs" | "operations";

export function getProviderPortalView(route: RouteId): ProviderPortalView {
  if (route === "provider-clients") return "clients";
  if (route === "provider-cases") return "cases";
  if (route === "provider-messages") return "messages";
  if (route === "provider-analytics") return "analytics";
  if (route === "provider-proofs") return "proofs";
  if (route === "provider-operations") return "operations";
  return "overview";
}

export function normalizeAppRoute(route: RouteId, walletConfig?: WalletApiConfig): RouteId {
  if (route === "exports") return "uploads";
  if (route === "security") return "settings";
  const resolvedWalletConfig = walletConfig ?? readWalletApiConfig();
  return removedStandaloneRoutes.has(route) && !resolvedWalletConfig ? "home" : route;
}
