import type { AppActionResult, AppActionRuntime } from "../../app/appActions";
import type { RouteId } from "../../models/abby";
import type { OpenServiceDetailCommandInput } from "../commandSchemas";

interface ServiceDetailRouteRuntime {
  setActiveRoute?: (route: RouteId) => void;
  setServiceDetailDocId?: (docId: string | null) => void;
  setMobileNavOpen?: (open: boolean) => void;
}

const serviceDetailPrefix = "#/services/";

export function getServiceDetailDocIdFromHash(
  hash = typeof window === "undefined" ? "" : window.location.hash
): string | null {
  if (!hash.startsWith(serviceDetailPrefix)) return null;
  const encodedDocId = hash.slice(serviceDetailPrefix.length).split("/")[0];
  if (!encodedDocId) return null;
  try {
    return decodeURIComponent(encodedDocId);
  } catch {
    return encodedDocId;
  }
}

export function serviceDetailRouteHash(docId: string): string {
  return `${serviceDetailPrefix}${encodeURIComponent(normalizeServiceDetailDocId(docId))}`;
}

export function setLocationServiceDetailHash(docId: string): void {
  if (typeof window === "undefined") return;
  window.location.hash = serviceDetailRouteHash(docId);
}

export function openCanonicalServiceDetailRoute(
  docId: string,
  runtime: ServiceDetailRouteRuntime = {}
): string | undefined {
  const normalizedDocId = normalizeServiceDetailDocId(docId);
  if (!normalizedDocId) return undefined;

  setLocationServiceDetailHash(normalizedDocId);
  runtime.setServiceDetailDocId?.(normalizedDocId);
  runtime.setActiveRoute?.("social-services");
  runtime.setMobileNavOpen?.(false);
  return serviceDetailRouteHash(normalizedDocId);
}

export async function openServiceDetailAction(
  runtime: AppActionRuntime,
  input: OpenServiceDetailCommandInput
): Promise<AppActionResult> {
  const normalizedDocId = normalizeServiceDetailDocId(input.docId);
  if (!normalizedDocId) {
    return {
      ok: false,
      action: "open_service_detail",
      errorCode: "missing_service_doc_id",
      message: "A service document ID is required to open service detail."
    };
  }

  const canonicalRoute = openCanonicalServiceDetailRoute(normalizedDocId, runtime);
  return {
    ok: true,
    action: "open_service_detail",
    summary: `Opened service ${normalizedDocId}.`,
    route: "social-services",
    artifactId: normalizedDocId,
    metadata: canonicalRoute ? { canonicalRoute } : undefined
  };
}

function normalizeServiceDetailDocId(docId: string): string {
  return docId.trim();
}
