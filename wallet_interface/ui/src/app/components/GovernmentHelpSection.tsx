import { MessageSquare } from "lucide-react";
import { Badge, Button, Section } from "../../components/ui";
import { t, type SupportedLocale } from "../../shared/lib/localization";
import { formatRequestTimestamp } from "../utils/formatHelpers";

export function GovernmentHelpSection({
  onToggle,
  requested,
  siteLocale,
  requestedAt
}: {
  onToggle: () => void;
  requested: boolean;
  siteLocale: SupportedLocale;
  requestedAt: string;
}) {
  return (
    <Section title={t(siteLocale, "government.title")}>
      <div className={`liaison-panel partner-help-panel${requested ? " partner-help-panel-active" : ""}`}>
        <MessageSquare aria-hidden="true" size={28} />
        <div>
          <h3>{t(siteLocale, "government.heading")}</h3>
          <p>
            {requested
              ? t(siteLocale, "government.requestedText")
              : t(siteLocale, "government.unrequestedText")}
          </p>
          {requested ? (
            <div className="badge-row" aria-label="Government help request status">
              <Badge tone="warning">{t(siteLocale, "government.requestedBadge")}</Badge>
              {requestedAt ? <Badge>{formatRequestTimestamp(requestedAt, siteLocale)}</Badge> : null}
            </div>
          ) : null}
        </div>
        <Button ariaPressed={requested} onClick={onToggle} variant={requested ? "secondary" : "primary"}>
          {requested ? t(siteLocale, "government.clearRequest") : t(siteLocale, "government.startRequest")}
        </Button>
      </div>
    </Section>
  );
}
