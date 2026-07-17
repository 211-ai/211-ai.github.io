import { Badge } from "../../shared/components/ui";
import type { DisclosureDataScope } from "../../models/abby";
import { abilitiesForDisclosureScopes } from "../../features/wallet/lib/capabilities";
import { t, tFormat, type SupportedLocale } from "../../shared/lib/localization";
import { disclosureScopes } from "../appState";
import {
  disclosureScopeDetailKey,
  disclosureScopeLabelKey,
  formatLocalizedCapabilitySummary,
  formatLocalizedNonGrantedCapabilities,
  getDisclosureScopeLabels
} from "../utils/formatHelpers";

export function SharingScopeChecklist({
  label,
  scopes,
  onToggle,
  help,
  siteLocale
}: {
  label: string;
  scopes: DisclosureDataScope[];
  onToggle: (scope: DisclosureDataScope) => void;
  help?: string;
  siteLocale: SupportedLocale;
}) {
  return (
    <fieldset className="scope-fieldset">
      <legend>{label}</legend>
      {help ? <p className="scope-help">{help}</p> : null}
      <div className="scope-grid">
        {disclosureScopes.map((scope) => (
          <label className="scope-option" key={scope.id}>
            <input checked={scopes.includes(scope.id)} onChange={() => onToggle(scope.id)} type="checkbox" />
            <span>
              <strong>{t(siteLocale, disclosureScopeLabelKey(scope.id))}</strong>
              <small>{t(siteLocale, disclosureScopeDetailKey(scope.id))}</small>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function SharingCapabilityPreview({
  recipientName,
  scopes,
  siteLocale
}: {
  recipientName: string;
  scopes: DisclosureDataScope[];
  siteLocale: SupportedLocale;
}) {
  const abilities = abilitiesForDisclosureScopes(scopes);

  return (
    <div className="capability-preview" role="group" aria-label={tFormat(siteLocale, "contacts.editSharingFor", { name: recipientName })}>
      <div className="scope-header">
        <div>
          <h4>{t(siteLocale, "sharing.whatAllows")}</h4>
          <p>{tFormat(siteLocale, "sharing.selectedItems", { count: String(scopes.length) })}</p>
        </div>
        <Badge tone={scopes.length > 0 ? "success" : "warning"}>{scopes.length > 0 ? t(siteLocale, "sharing.limitedShare") : t(siteLocale, "sharing.noAccess")}</Badge>
      </div>
      <div className="disclosure-package">
        <div className="disclosure-row">
          <strong>{t(siteLocale, "sharing.canDo")}</strong>
          <span>{formatLocalizedCapabilitySummary(abilities, siteLocale) || t(siteLocale, "sharing.noAccessSelected")}</span>
        </div>
        <div className="disclosure-row">
          <strong>{t(siteLocale, "sharing.items")}</strong>
          <span>{getDisclosureScopeLabels(scopes, siteLocale) || t(siteLocale, "sharing.noItemsSelected")}</span>
        </div>
        <div className="disclosure-row">
          <strong>{t(siteLocale, "sharing.notAllowed")}</strong>
          <span>{formatLocalizedNonGrantedCapabilities(abilities, siteLocale)}</span>
        </div>
      </div>
    </div>
  );
}
