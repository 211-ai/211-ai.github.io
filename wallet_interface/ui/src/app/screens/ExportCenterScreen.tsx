import { FormEvent, useMemo, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Badge, Button, Field, Section, StatusBanner } from "../../components/ui";
import { StatusPanel } from "../components/StatusPanel";
import { nonGrantedCapabilities } from "../../services/capabilities";
import { ExportBundleView } from "../../models/abby";
import { createVerifiedExportBundleView, importExportBundleView, type WalletApiConfig } from "../../services/walletApi";

export function ExportCenterScreen({
  apiConfig,
  bundles,
  setBundles
}: {
  apiConfig?: WalletApiConfig;
  bundles: ExportBundleView[];
  setBundles: (bundles: ExportBundleView[]) => void;
}) {
  const [audienceDid, setAudienceDid] = useState("did:key:legal-aid-desk");
  const [audienceName, setAudienceName] = useState("Legal Aid desk");
  const [recordIds, setRecordIds] = useState("rec-document-benefits\nrec-location-current");
  const [purpose, setPurpose] = useState("user_export");
  const [exportStatus, setExportStatus] = useState<"idle" | "creating" | "created" | "failed">("idle");
  const [importingBundleId, setImportingBundleId] = useState<string | null>(null);
  const [importStatus, setImportStatus] = useState<"idle" | "imported" | "failed">("idle");
  const exportRecordIds = useMemo(() => parseRecordIds(recordIds), [recordIds]);

  async function createBundle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig) return;
    if (!audienceDid.trim() || exportRecordIds.length === 0) {
      setExportStatus("failed");
      return;
    }
    setExportStatus("creating");
    try {
      const bundleView = await createVerifiedExportBundleView(apiConfig, {
        audienceDid: audienceDid.trim(),
        audienceName: audienceName.trim() || undefined,
        purpose: purpose.trim() || "user_export",
        recordIds: exportRecordIds
      });
      setBundles([bundleView, ...bundles.filter((bundle) => bundle.bundleId !== bundleView.bundleId)]);
      setExportStatus("created");
    } catch {
      setExportStatus("failed");
    }
  }

  async function importBundle(bundleView: ExportBundleView) {
    if (!apiConfig || !bundleView.bundle || bundleView.imported) return;
    setImportingBundleId(bundleView.bundleId);
    setImportStatus("idle");
    try {
      const importedBundle = await importExportBundleView({
        apiBaseUrl: apiConfig.apiBaseUrl,
        bundleView
      });
      setBundles(bundles.map((bundle) => (bundle.bundleId === importedBundle.bundleId ? importedBundle : bundle)));
      setImportStatus("imported");
    } catch {
      setImportStatus("failed");
    } finally {
      setImportingBundleId(null);
    }
  }

  return (
    <>
      {!apiConfig ? (
        <StatusBanner tone="warning">Connect Abby before you make live export bundles.</StatusBanner>
      ) : null}
      {exportStatus === "created" ? <StatusBanner tone="success">Export bundle verified.</StatusBanner> : null}
      {exportStatus === "failed" ? <StatusBanner tone="warning">Export bundle creation failed.</StatusBanner> : null}
      {importStatus === "imported" ? <StatusBanner tone="success">Export descriptors imported.</StatusBanner> : null}
      {importStatus === "failed" ? <StatusBanner tone="warning">Export import failed.</StatusBanner> : null}
      <Section title="Export or import wallet bundles">
        <p className="page-note">
          Export bundles carry encrypted records, receipt hashes, and storage reports. Importing descriptors adds the
          bundle's encrypted record index and proof metadata for review without revealing plaintext.
        </p>
        <form className="form-grid export-builder" onSubmit={createBundle}>
          <Field label="Recipient DID" required>
            <input
              onChange={(event) => setAudienceDid(event.target.value)}
              placeholder="did:key:recipient"
              value={audienceDid}
            />
          </Field>
          <Field label="Recipient label">
            <input
              onChange={(event) => setAudienceName(event.target.value)}
              placeholder="Legal Aid desk"
              value={audienceName}
            />
          </Field>
          <Field label="Purpose">
            <input onChange={(event) => setPurpose(event.target.value)} value={purpose} />
          </Field>
          <Field label="Record IDs" required>
            <textarea
              onChange={(event) => setRecordIds(event.target.value)}
              placeholder="rec-document-benefits"
              rows={3}
              value={recordIds}
            />
          </Field>
          <div className="row-actions full-span">
            <Button disabled={!apiConfig || exportStatus === "creating"} type="submit" variant="secondary">
              <ShieldCheck size={18} /> {exportStatus === "creating" ? "Creating" : "Create bundle"}
            </Button>
          </div>
          <div className="capability-preview full-span" role="group" aria-label="Export capability preview">
            <div className="scope-header">
              <div>
                <h3>What this allows</h3>
                <p>{audienceName.trim() || audienceDid.trim() || "Recipient"} · {purpose.trim() || "user_export"}</p>
              </div>
              <Badge tone={exportRecordIds.length > 0 ? "success" : "warning"}>
                {exportRecordIds.length} records
              </Badge>
            </div>
            <div className="disclosure-package">
              <div className="disclosure-row">
                <strong>Ability</strong>
                <span>export/create</span>
              </div>
              <div className="disclosure-row">
                <strong>Records</strong>
                <span>{exportRecordIds.length > 0 ? exportRecordIds.join(", ") : "No records selected"}</span>
              </div>
              <div className="disclosure-row">
                <strong>Outputs</strong>
                <span>Encrypted descriptors, proof receipts, derived artifacts, storage report</span>
              </div>
              <div className="disclosure-row">
                <strong>Not allowed</strong>
                <span>{nonGrantedCapabilities(["export/create"]).join(", ")}</span>
              </div>
            </div>
          </div>
        </form>
      </Section>
      <Section title="Recent export bundles">
        <div className="list-stack">
          {bundles.map((bundle) => {
            const titleId = `export-title-${bundle.id}`;

            return (
              <article aria-labelledby={titleId} className="export-card" key={bundle.id}>
                <div className="scope-header">
                  <div>
                    <h3 id={titleId}>{bundle.audienceName}</h3>
                    <p>{bundle.bundleId}</p>
                  </div>
                  <Badge tone={bundle.verificationOk && bundle.storageOk ? "success" : "warning"}>
                    {!bundle.verificationOk ? "receipt invalid" : bundle.storageOk ? "storage verified" : "storage missing"}
                  </Badge>
                </div>
                <div className="privacy-metrics">
                  <StatusPanel label="Records" value={String(bundle.recordCount)} tone="teal" />
                  <StatusPanel label="Proofs" value={String(bundle.proofCount)} tone="gold" />
                </div>
                <div className="receipt-hash-row">
                  <span>Bundle hash</span>
                  <code>{bundle.bundleHash}</code>
                </div>
                <div className="badge-row">
                  <Badge tone={bundle.hashOk ? "success" : "warning"}>
                    {bundle.hashOk ? "hash verified" : "hash mismatch"}
                  </Badge>
                  <Badge tone={bundle.schemaOk ? "success" : "warning"}>
                    {bundle.schemaOk ? "schema verified" : "schema failed"}
                  </Badge>
                  <Badge>{bundle.createdAt}</Badge>
                  <Badge tone={bundle.imported ? "success" : "neutral"}>
                    {bundle.imported ? "import verified" : "not imported"}
                  </Badge>
                </div>
                {bundle.schemaError ? <p className="receipt-error">{bundle.schemaError}</p> : null}
                {bundle.imported ? (
                  <p className="wallet-storage-reference">
                    Descriptors are already imported for this bundle.
                  </p>
                ) : bundle.bundle ? (
                  <div className="row-actions">
                    <Button
                      disabled={!apiConfig || importingBundleId === bundle.bundleId}
                      onClick={() => importBundle(bundle)}
                      variant="secondary"
                    >
                      <ShieldCheck size={18} /> {importingBundleId === bundle.bundleId ? "Importing" : "Import descriptors"}
                    </Button>
                  </div>
                ) : (
                  <p className="wallet-storage-reference">
                    Bundle contents are not available to import from this view.
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </Section>
    </>
  );
}

function parseRecordIds(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(/[\n,]/)
        .map((recordId) => recordId.trim())
        .filter(Boolean)
    )
  );
}
