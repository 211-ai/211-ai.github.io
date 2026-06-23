import { useEffect, type Dispatch, type MutableRefObject, type SetStateAction } from "react";
import { getServiceDetailDocIdFromHash } from "../../agent/tools/serviceDetailTools";
import { getRouteFromHash } from "../appState";
import { normalizeAppRoute } from "../config/navigation";
import { getServicePlanDocIdFromHash } from "../ServicePlanScreen";
import type { RouteId } from "../../models/abby";

interface HashRouteSyncDeps {
  activeRouteRef: MutableRefObject<RouteId>;
  setActiveRoute: Dispatch<SetStateAction<RouteId>>;
  setMobileNavOpen: Dispatch<SetStateAction<boolean>>;
  setServiceDetailDocId: Dispatch<SetStateAction<string | null>>;
  setServicePlanDocId: Dispatch<SetStateAction<string | null>>;
}

export function useHashRouteSync({
  activeRouteRef,
  setActiveRoute,
  setMobileNavOpen,
  setServiceDetailDocId,
  setServicePlanDocId,
}: HashRouteSyncDeps) {
  useEffect(() => {
    const syncRouteFromHash = () => {
      const planDocId = getServicePlanDocIdFromHash();
      const detailDocId = planDocId ? null : getServiceDetailDocIdFromHash();
      const nextRoute = planDocId || detailDocId ? "social-services" : normalizeAppRoute(getRouteFromHash());
      setServicePlanDocId(planDocId);
      setServiceDetailDocId(detailDocId);
      activeRouteRef.current = nextRoute;
      setActiveRoute(nextRoute);
      setMobileNavOpen(false);
    };
    window.addEventListener("hashchange", syncRouteFromHash);
    return () => window.removeEventListener("hashchange", syncRouteFromHash);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
