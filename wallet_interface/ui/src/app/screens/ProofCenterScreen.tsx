import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { Camera, FileUp, Upload } from "lucide-react";
import { Badge, Button, Field, Section, StatusBanner } from "../../components/ui";
import { nonGrantedCapabilities } from "../../services/capabilities";
import {
  createLocationRegionProof,
  type WalletApiConfig
} from "../../services/walletApi";
import {
  readWalletProofBundlePayloadFromUrl,
  reviewWalletProofBundleReference,
  reviewWalletProofQrScreenshot,
  type WalletEncryptedRecordLink,
  type WalletProofQrReview
} from "../../services/walletProofReview";
import { ProofReceiptView, UploadItem } from "../../models/abby";

const PROOF_QR_IMAGE_ACCEPT_ATTR = "image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp";
const hiddenProofCenterProofTypes = new Set(["location_distance"]);

function visibleProofCenterProofs(proofs: ProofReceiptView[]) {
  return proofs.filter((proof) => !hiddenProofCenterProofTypes.has(proof.proofType));
}

function shortStorageId(value: string): string {
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-6)}` : value;
}

export function ProofCenterScreen({
  apiConfig,
  proofs,
  refreshWalletAuditEvents,
  setProofs,
  uploads
}: {
  apiConfig?: WalletApiConfig;
  proofs: ProofReceiptView[];
  refreshWalletAuditEvents: () => Promise<void>;
  setProofs: (proofs: ProofReceiptView[]) => void;
  uploads: UploadItem[];
}) {
  const [locationRecordId, setLocationRecordId] = useState(
    (import.meta.env.VITE_DEMO_LOCATION_RECORD_ID as string | undefined) ?? "rec-location-current"
  );
  const [regionId, setRegionId] = useState("multnomah_county");
  const [grantId, setGrantId] = useState("");
  const [proofStatus, setProofStatus] = useState<"idle" | "creating" | "created" | "failed">("idle");
  const [reviewStatus, setReviewStatus] = useState<"idle" | "reviewing" | "reviewed" | "failed">("idle");
  const [reviewError, setReviewError] = useState("");
  const [reviewedQrProofs, setReviewedQrProofs] = useState<WalletProofQrReview | null>(null);
  const linkedWalletProofBundle = useMemo(
    () => (typeof window === "undefined" ? undefined : readWalletProofBundlePayloadFromUrl(window.location.href)),
    []
  );

  useEffect(() => {
    if (!linkedWalletProofBundle) return;
    let cancelled = false;
    setReviewStatus("reviewing");
    void reviewWalletProofBundleReference(linkedWalletProofBundle, window.location.href, "Wallet proof bundle link", window.location.href)
      .then((review) => {
        if (cancelled) return;
        setReviewedQrProofs(review);
        setReviewError("");
        setReviewStatus("reviewed");
      })
      .catch((error) => {
        if (cancelled) return;
        setReviewedQrProofs(null);
        setReviewError(error instanceof Error ? error.message : "Unable to review the wallet proof QR.");
        setReviewStatus("failed");
      });
    return () => {
      cancelled = true;
    };
  }, [linkedWalletProofBundle]);

  async function createProof(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig?.actorDid || !locationRecordId.trim() || !regionId.trim()) {
      setProofStatus("failed");
      return;
    }
    setProofStatus("creating");
    try {
      const proof = await createLocationRegionProof(apiConfig, {
        grantId: grantId.trim() || undefined,
        locationRecordId: locationRecordId.trim(),
        regionId: regionId.trim()
      });
      setProofs([proof, ...proofs.filter((item) => item.id !== proof.id)]);
      await refreshWalletAuditEvents().catch(() => undefined);
      setProofStatus("created");
    } catch {
      setProofStatus("failed");
    }
  }

  async function reviewQrScreenshot(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setReviewStatus("reviewing");
    setReviewError("");
    try {
      const review = await reviewWalletProofQrScreenshot(file);
      setReviewedQrProofs(review);
      setReviewStatus("reviewed");
    } catch (error) {
      setReviewedQrProofs(null);
      setReviewError(error instanceof Error ? error.message : "Unable to review the wallet proof QR.");
      setReviewStatus("failed");
    }
  }

  const activeProofs = reviewedQrProofs ? reviewedQrProofs.proofs : proofs;
  const activeVisibleProofs = visibleProofCenterProofs(activeProofs);
  const localEncryptedRecords: WalletEncryptedRecordLink[] = uploads
    .filter((upload) => upload.recordId || upload.ipfsCid)
    .map((upload) => ({
      cid: upload.ipfsCid || upload.recordId || upload.id,
      fileName: upload.fileName,
      links: upload.ipfsCid ? [{ "/": upload.ipfsCid, cid: upload.ipfsCid, name: "encrypted_record" }] : [],
      recordId: upload.recordId,
      root: upload.ipfsCid ? { "/": upload.ipfsCid } : undefined
    }));
  const activeEncryptedRecords = reviewedQrProofs ? reviewedQrProofs.encryptedRecords : localEncryptedRecords;
  const activeWalletId = reviewedQrProofs?.wallet?.id || apiConfig?.walletId;
  const activeActorDid = reviewedQrProofs?.wallet?.actorDid || apiConfig?.actorDid;
  const activeSourceLabel = reviewedQrProofs
    ? reviewedQrProofs.sourceUrl || reviewedQrProofs.sourceLabel
    : apiConfig
      ? "Connected wallet"
      : "No wallet connected";
  const activeWalletTitle = reviewedQrProofs?.bundleTitle || (activeWalletId ? "My connected wallet" : "Wallet proof center");
  const activeModeLabel = reviewedQrProofs ? "imported wallet" : "my wallet";

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Proof center</p>
        <h1>Verified wallet claims</h1>
      </div>
      <p className="page-note">
        Wallet QR imports resolve the IPFS/Filecoin root CID, recover encrypted wallet record links, and review public proof
        certificates without exposing raw documents or precise location.
      </p>
      <article className="proof-card" aria-label="Active wallet proof center">
        <div className="scope-header">
          <div>
            <h3>{activeWalletTitle}</h3>
            <p>
              {reviewedQrProofs
                ? "This view is showing the wallet recovered from the imported QR."
                : "This view defaults to your connected wallet until you import another wallet QR."}
            </p>
          </div>
          <Badge tone={apiConfig || reviewedQrProofs ? "success" : "warning"}>{activeModeLabel}</Badge>
        </div>
        <div
          className="capability-preview"
          role="group"
          aria-label={reviewedQrProofs ? "QR proof bundle summary" : "Active wallet proof bundle summary"}
        >
          <div className="scope-header">
            <div>
              <h4>{reviewedQrProofs?.bundleTitle || activeWalletId || "Wallet not connected"}</h4>
              <p>{activeSourceLabel}</p>
            </div>
            <Badge tone={activeVisibleProofs.length > 0 ? "success" : "warning"}>{activeVisibleProofs.length} claims</Badge>
          </div>
          <div className="disclosure-package">
            <div className="disclosure-row">
              <strong>Owner DID</strong>
              <span>{activeActorDid || "Not available"}</span>
            </div>
            <div className="disclosure-row">
              <strong>Encrypted records</strong>
              <span>{activeEncryptedRecords.length} record link{activeEncryptedRecords.length === 1 ? "" : "s"} available</span>
            </div>
            <div className="disclosure-row">
              <strong>Zero-knowledge proofs</strong>
              <span>
                {activeVisibleProofs.map((proof) => proof.claim).join(", ") ||
                  "No public proof claims are attached to this wallet yet."}
              </span>
            </div>
            <div className="disclosure-row">
              <strong>Privacy</strong>
              <span>Encrypted data remains ciphertext; this view exposes wallet CIDs and proof metadata needed for recovery.</span>
            </div>
          </div>
        </div>
        <div className="upload-controls">
          <label className="upload-dropzone">
            <Upload aria-hidden="true" size={28} />
            <span>Upload wallet QR screenshot</span>
            <small>The same view will switch to the imported wallet after the QR loads.</small>
            <span className="upload-picker">
              <FileUp aria-hidden="true" size={18} /> Upload picture
            </span>
            <input
              accept={PROOF_QR_IMAGE_ACCEPT_ATTR}
              aria-label="Upload proof QR picture"
              onChange={reviewQrScreenshot}
              type="file"
            />
          </label>
          <label className="upload-dropzone">
            <Camera aria-hidden="true" size={28} />
            <span>Take a picture with your camera</span>
            <small>Capture a wallet QR to temporarily inspect that wallet here.</small>
            <span className="upload-picker">
              <Camera aria-hidden="true" size={18} /> Open camera
            </span>
            <input
              accept={PROOF_QR_IMAGE_ACCEPT_ATTR}
              aria-label="Take proof QR photo with camera"
              capture="environment"
              onChange={reviewQrScreenshot}
              type="file"
            />
          </label>
        </div>
        {reviewStatus === "reviewing" ? <StatusBanner tone="info">Reading the QR screenshot and loading wallet recovery links.</StatusBanner> : null}
        {reviewStatus === "failed" ? <StatusBanner tone="warning">{reviewError}</StatusBanner> : null}
      </article>
      {activeEncryptedRecords.length ? (
        <Section title="Recovered encrypted wallet data">
          <div className="list-stack">
            {activeEncryptedRecords.map((record) => (
              <article className="proof-card" key={`${record.recordId ?? "record"}-${record.cid}`}>
                <div className="scope-header">
                  <div>
                    <h3>{record.fileName || record.recordId || "Encrypted wallet record"}</h3>
                    <p>{record.versionId || "Encrypted record graph"}</p>
                  </div>
                  <Badge tone="success">recovered CID</Badge>
                </div>
                <div className="disclosure-package">
                  <div className="disclosure-row">
                    <strong>Root CID</strong>
                    <span>{shortStorageId(record.root?.["/"] || record.cid)}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Record ID</strong>
                    <span>{record.recordId || "Not included"}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>IPLD links</strong>
                    <span>
                      {record.links?.length
                        ? record.links.map((link) => `${link.name}: ${shortStorageId(link["/"] || link.cid || "")}`).join(", ")
                        : "Root record graph contains the encrypted payload link."}
                    </span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </Section>
      ) : null}
      {activeVisibleProofs.length > 0 ? (
        <Section title="Wallet zero-knowledge proofs">
          <div className="list-stack">
            {activeVisibleProofs.map((proof) => (
              <ProofReceiptCard key={`${reviewedQrProofs ? "review" : "wallet"}-${proof.id}`} proof={proof} sourceLabel={reviewedQrProofs ? "From QR bundle" : undefined} />
            ))}
          </div>
        </Section>
      ) : null}
      <article className="proof-card" aria-label="Create location region proof" style={{ display: "none" }}>
        <div className="scope-header">
          <div>
            <h3>Create location-region proof</h3>
            <p>location/prove_region · public inputs only</p>
          </div>
          <Badge tone={apiConfig ? "success" : "warning"}>{apiConfig ? "API connected" : "API required"}</Badge>
        </div>
        <form className="form-grid" onSubmit={createProof}>
          <Field label="Location record ID" required>
            <input
              onChange={(event) => setLocationRecordId(event.target.value)}
              placeholder="rec-location-current"
              value={locationRecordId}
            />
          </Field>
          <Field label="Region ID" required>
            <input
              onChange={(event) => setRegionId(event.target.value)}
              placeholder="multnomah_county"
              value={regionId}
            />
          </Field>
          <Field label="Grant ID">
            <input
              onChange={(event) => setGrantId(event.target.value)}
              placeholder="Owner wallets can leave this blank"
              value={grantId}
            />
          </Field>
          <div className="capability-preview" role="group" aria-label="Create proof capability preview">
            <div className="disclosure-package">
              <div className="disclosure-row">
                <strong>Ability</strong>
                <span>location/prove_region</span>
              </div>
              <div className="disclosure-row">
                <strong>Public output</strong>
                <span>region_id, claim, region_policy_hash</span>
              </div>
              <div className="disclosure-row">
                <strong>Not allowed</strong>
                <span>{nonGrantedCapabilities(["proof/verify", "location/prove_region"]).join(", ")}</span>
              </div>
            </div>
          </div>
          {proofStatus === "created" ? (
            <StatusBanner tone="success">Proof receipt created and added to the wallet timeline.</StatusBanner>
          ) : null}
          {proofStatus === "failed" ? (
            <StatusBanner tone="warning">Proof creation failed. Check the record ID, grant, and API proof mode.</StatusBanner>
          ) : null}
          <Button disabled={!apiConfig?.actorDid || proofStatus === "creating"} type="submit" variant="secondary">
            {proofStatus === "creating" ? "Creating proof..." : "Create proof"}
          </Button>
        </form>
      </article>
    </div>
  );
}

function ProofReceiptCard({
  proof,
  sourceLabel
}: {
  proof: ProofReceiptView;
  sourceLabel?: string;
}) {
  const titleId = `proof-title-${proof.id}`;
  const publicInputKeys = Object.keys(proof.publicInputs);

  return (
    <article aria-labelledby={titleId} className="proof-card">
      <div className="scope-header">
        <div>
          <h3 id={titleId}>{proof.claim}</h3>
          <p>
            {proof.proofType} · {proof.proofSystem} · {proof.verifier}
          </p>
        </div>
        <Badge tone={proof.simulated ? "warning" : "success"}>
          {proof.simulated ? "Simulated" : proof.verificationStatus}
        </Badge>
      </div>
      <div className="badge-row">
        <Badge>{proof.createdAt}</Badge>
        <Badge>{proof.witnessLabel}</Badge>
        {sourceLabel ? <Badge>{sourceLabel}</Badge> : null}
      </div>
      <div
        className="capability-preview"
        role="group"
        aria-label={`${proof.claim} proof capability preview`}
      >
        <div className="scope-header">
          <div>
            <h4>What this allows</h4>
            <p>{proof.proofType} · public inputs only</p>
          </div>
          <Badge tone={proof.simulated ? "warning" : "success"}>
            {proof.simulated ? "development proof" : "verified proof"}
          </Badge>
        </div>
        <div className="disclosure-package">
          <div className="disclosure-row">
            <strong>Ability</strong>
            <span>proof/verify</span>
          </div>
          <div className="disclosure-row">
            <strong>Verification</strong>
            <span>{proof.verificationStatus}</span>
          </div>
          {proof.circuitId ? (
            <div className="disclosure-row">
              <strong>Circuit</strong>
              <span>{proof.circuitId}</span>
            </div>
          ) : null}
          {proof.verifierDigest ? (
            <div className="disclosure-row">
              <strong>Verifier digest</strong>
              <span>{proof.verifierDigest.slice(0, 16)}...</span>
            </div>
          ) : null}
          <div className="disclosure-row">
            <strong>Public inputs</strong>
            <span>{publicInputKeys.length ? publicInputKeys.join(", ") : "No public inputs included"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Not allowed</strong>
            <span>{nonGrantedCapabilities(["proof/verify"]).join(", ")}</span>
          </div>
        </div>
      </div>
      <div className="proof-inputs" aria-label={`${proof.claim} public inputs`}>
        {publicInputKeys.length ? (
          Object.entries(proof.publicInputs).map(([key, value]) => (
            <div className="disclosure-row" key={key}>
              <strong>{key}</strong>
              <span>{value}</span>
            </div>
          ))
        ) : (
          <div className="disclosure-row">
            <strong>Summary</strong>
            <span>No additional public inputs were disclosed.</span>
          </div>
        )}
      </div>
    </article>
  );
}
