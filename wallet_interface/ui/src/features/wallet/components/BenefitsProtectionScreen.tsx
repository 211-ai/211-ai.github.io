import { Landmark } from "lucide-react";
import { Badge, Button, Section, StatusBanner } from "../../../components/ui";
import { plainCapabilitySummary, plainNonGrantedCapabilities } from "../../../services/capabilities";

export function BenefitsProtectionScreen({
  optedIn,
  setOptedIn
}: {
  optedIn: boolean;
  setOptedIn: (optedIn: boolean) => void;
}) {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Benefits protection</p>
        <h1>Benefits notice</h1>
      </div>
      <StatusBanner tone="warning">
        Abby can ask approved agencies for help. This does not promise benefits.
      </StatusBanner>
      <Section title="Benefits choice">
        <div className="capability-preview" role="group" aria-label="Benefits notification capability preview">
          <div className="scope-header">
            <div>
              <h4>What this allows</h4>
              <p>benefits status and notice details only</p>
            </div>
            <Badge tone={optedIn ? "success" : "neutral"}>{optedIn ? "ready to save" : "off"}</Badge>
          </div>
          <div className="disclosure-package">
            <div className="disclosure-row">
              <strong>Can do</strong>
              <span>{plainCapabilitySummary(["metadata/read", "derived/read"])}</span>
            </div>
            <div className="disclosure-row">
              <strong>Items</strong>
              <span>Benefits information, Notice request</span>
            </div>
            <div className="disclosure-row">
              <strong>Not allowed</strong>
              <span>{plainNonGrantedCapabilities(["metadata/read", "derived/read"]).join(", ")}</span>
            </div>
          </div>
        </div>
        <label className="consent-box">
          <input checked={optedIn} onChange={(event) => setOptedIn(event.target.checked)} type="checkbox" />
          <span>
            <strong>Allow Abby to prepare a benefits notice for agency help.</strong>
            <small>This starts on. You can turn it off. A privacy and legal team must review this before real use.</small>
          </span>
        </label>
        <Button>
          <Landmark size={18} /> Save setting
        </Button>
      </Section>
    </div>
  );
}
