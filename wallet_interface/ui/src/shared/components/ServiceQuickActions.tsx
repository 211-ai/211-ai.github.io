import { ExternalLink, MapPinned, Phone } from "lucide-react";
import type { CorpusDocument } from "../../features/service-navigation/lib/graphrag";
import { t, type SupportedLocale } from "../lib/localization";
import {
  getPrimaryAddress,
  getPrimaryIntakeText,
  getPrimaryMapQuery,
  getPrimaryPhone,
  getPrimaryWebsite,
} from "../../features/service-navigation/lib/graphrag";
import { buildCallAction, buildMapAction } from "../../services/serviceActionService";
import {
  buildManualServiceInteractionIntent,
  buildServiceInteractionIntent,
  emitWalletServiceInteractionIntent,
} from "../../services/serviceInteractionService";
import type { WalletApiConfig } from "../../features/wallet/lib/walletApi";
import type { ServiceInteractionEvent } from "../../models/abby";
import type { ServiceActionDescriptor, ServiceActionKind } from "../../services/serviceActionService";

function makeLocalInteractionId(): string {
  return `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function intentToLocalEvent(
  action: { kind: ServiceActionKind },
  intent: ReturnType<typeof buildServiceInteractionIntent>,
): ServiceInteractionEvent | null {
  if (!intent.ok || !intent.intent) return null;
  const i = intent.intent;
  const now = new Date().toISOString();
  return {
    interaction_id: makeLocalInteractionId(),
    wallet_id: "",
    service_doc_id: i.serviceDocId,
    source_content_cid: i.sourceContentCid ?? "",
    source_page_cid: i.sourcePageCid ?? "",
    provider_name: i.providerName ?? "",
    program_name: i.programName ?? "",
    interaction_type: i.interactionType,
    channel: i.channel ?? action.kind,
    actor_did: "",
    counterparty_name: i.counterpartyName ?? "",
    counterparty_contact: i.counterpartyContact ?? "",
    timestamp: i.timestamp,
    status: i.status,
    outcome: i.outcome,
    notes_record_id: i.notesRecordId ?? "",
    next_action: i.nextAction ?? "",
    next_follow_up_at: i.nextFollowUpAt ?? "",
    source_action_url: i.sourceActionUrl ?? "",
    related_grant_ids: i.relatedGrantIds ?? [],
    related_record_ids: i.relatedRecordIds ?? [],
    privacy_level: i.privacyLevel,
    created_at: now,
    updated_at: now,
    metadata: i.metadata,
  };
}

export function ServiceQuickActions({
  apiConfig,
  document,
  className = "row-actions",
  includeApply = true,
  onInteract,
  siteLocale,
}: {
  apiConfig?: WalletApiConfig;
  document: CorpusDocument;
  className?: string;
  includeApply?: boolean;
  onInteract?: (event: ServiceInteractionEvent) => void;
  siteLocale: SupportedLocale;
}) {
  const primaryPhone = getPrimaryPhone(document);
  const primaryAddress = getPrimaryAddress(document);
  const primaryWebsite = getPrimaryWebsite(document);
  const intakeText = getPrimaryIntakeText(document);
  const actionContext = {
    serviceDocId: document.doc_id,
    providerName: document.provider_name,
    programName: document.program_name || document.title,
    sourceUrl: document.source_url,
    sourceContentCid: document.source_content_cid,
    sourcePageCid: document.source_page_cid,
  };
  const callAction = buildCallAction({ phone: primaryPhone?.value, context: actionContext });
  const mapAction = buildMapAction({
    query: getPrimaryMapQuery(document),
    address: primaryAddress?.address,
    context: actionContext,
  });

  function handleActionClick(action: ServiceActionDescriptor) {
    if (!onInteract) return;
    const updatedAction = { ...action, observedStatus: "handoff_requested" as const };
    const intentResult = buildServiceInteractionIntent(updatedAction, { userInitiated: true });
    if (apiConfig) {
      void emitWalletServiceInteractionIntent(apiConfig, updatedAction, { userInitiated: true }).then((result) => {
        if (result.ok && result.event) {
          onInteract(result.event);
        }
      });
    } else {
      const localEvent = intentToLocalEvent(updatedAction, intentResult);
      if (localEvent) {
        onInteract(localEvent);
      }
    }
  }

  function handleWebsiteClick() {
    if (!onInteract) return;
    const intentResult = buildManualServiceInteractionIntent({
      userInitiated: true,
      interactionType: "viewed_service",
      channel: "web",
      context: actionContext,
      sourceActionUrl: primaryWebsite,
      outcome: "User opened the provider website. The browser cannot verify whether any application was submitted.",
    });
    const localEvent = intentToLocalEvent({ kind: "share" }, intentResult);
    if (localEvent) {
      onInteract(localEvent);
    }
  }

  return (
    <div className={className}>
      {callAction.href ? (
        <a
          className="button button-secondary"
          href={callAction.href}
          onClick={() => handleActionClick(callAction)}
        >
          <Phone aria-hidden="true" size={18} />
          {t(siteLocale, "action.call")}
        </a>
      ) : null}
      {mapAction.href ? (
        <a
          className="button button-secondary"
          href={mapAction.href}
          onClick={() => handleActionClick(mapAction)}
          rel={mapAction.rel}
          target={mapAction.target}
        >
          <MapPinned aria-hidden="true" size={18} />
          {t(siteLocale, "action.directions")}
        </a>
      ) : null}
      {includeApply && primaryWebsite ? (
        <a
          className="button button-secondary"
          href={primaryWebsite}
          onClick={handleWebsiteClick}
          rel="noreferrer"
          target="_blank"
        >
          <ExternalLink aria-hidden="true" size={18} />
          {intakeText ? t(siteLocale, "action.applyInfo") : t(siteLocale, "action.website")}
        </a>
      ) : null}
    </div>
  );
}
