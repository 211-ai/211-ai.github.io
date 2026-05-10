import type { ProofReceiptView } from "../models/abby";

const qrImageAcceptedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
const defaultIpfsGateways = ["https://w3s.link/ipfs/", "https://ipfs.io/ipfs/"];
const cidPattern = /\b(?:bafy[a-z0-9]{20,}|Qm[1-9A-HJ-NP-Za-km-z]{44})\b/;
const walletProofBundleParam = "walletProofBundle";

type BarcodeDetectorLike = {
  detect(source: ImageBitmapSource): Promise<Array<{ rawValue?: string }>>;
};

type BarcodeDetectorLikeConstructor = new (options?: { formats?: string[] }) => BarcodeDetectorLike;

type ReviewLocator =
  | { kind: "inline"; payload: unknown; sourceLabel: string }
  | { kind: "url"; sourceLabel: string; url: string }
  | { kind: "cid"; cid: string; sourceLabel: string };

export type WalletProofQrReview = {
  bundleTitle?: string;
  proofs: ProofReceiptView[];
  qrValue: string;
  sourceLabel: string;
  sourceUrl?: string;
};

export function buildWalletProofBundlePayload({
  actorDid,
  proofs,
  walletId
}: {
  actorDid?: string;
  proofs: ProofReceiptView[];
  walletId?: string;
}): string {
  const linkedProofs = proofs
    .map((proof) => {
      const locator = parseProofArtifactLocator(proof.proofArtifactRef);
      if (!locator) return undefined;
      return {
        ...locator,
        claim: proof.claim,
        id: proof.id,
        proofType: proof.proofType
      };
    })
    .filter((proof): proof is NonNullable<typeof proof> => Boolean(proof));
  const inlineProofs = proofs
    .filter((proof) => !parseProofArtifactLocator(proof.proofArtifactRef))
    .map((proof) => ({
      claim: proof.claim,
      createdAt: proof.createdAt,
      id: proof.id,
      proofArtifactRef: proof.proofArtifactRef,
      proofSystem: proof.proofSystem,
      proofType: proof.proofType,
      publicInputs: proof.publicInputs,
      simulated: proof.simulated,
      verificationStatus: proof.verificationStatus,
      verifier: proof.verifier,
      verifierDigest: proof.verifierDigest,
      witnessLabel: proof.witnessLabel
    }));
  return JSON.stringify({
    linkedProofs,
    title: "Client wallet proof bundle",
    generatedAt: new Date().toISOString(),
    proofs: inlineProofs,
    wallet: {
      actorDid,
      id: walletId,
      label: walletId ? `Wallet ${walletId}` : "Client wallet"
    }
  });
}

export function buildWalletProofReviewUrl(bundlePayload: string, baseUrl = currentBaseUrl()): string {
  const url = new URL(baseUrl);
  url.searchParams.set(walletProofBundleParam, bundlePayload);
  url.hash = "/proof-center";
  return url.toString();
}

export async function reviewWalletProofBundleReference(
  value: string,
  qrValue = value,
  sourceLabel?: string,
  sourceUrl?: string
): Promise<WalletProofQrReview> {
  const locator = parseReviewLocator(value);
  const resolved = await resolveReviewLocator(locator);
  return reviewWalletProofBundlePayload(
    resolved.payload,
    qrValue,
    sourceLabel || resolved.sourceLabel,
    sourceUrl || resolved.sourceUrl
  );
}

export function reviewWalletProofBundlePayload(
  payload: string | unknown,
  qrValue = "wallet-proof-bundle",
  sourceLabel = "Wallet proof bundle from QR",
  sourceUrl?: string
): WalletProofQrReview {
  const parsedPayload = typeof payload === "string" ? parseJson(payload) : payload;
  if (typeof payload === "string" && parsedPayload === undefined) {
    throw new Error("The wallet proof bundle link is invalid.");
  }
  const bundle = unwrapProofPayload(parsedPayload);
  const proofs = normalizeProofs(bundle);

  if (proofs.length === 0) {
    throw new Error("No proof certificates were found in the QR-linked bundle.");
  }

  return {
    bundleTitle: readBundleTitle(bundle),
    proofs,
    qrValue,
    sourceLabel,
    sourceUrl
  };
}

export function readWalletProofBundlePayloadFromUrl(urlValue: string): string | undefined {
  try {
    return new URL(urlValue, currentBaseUrl()).searchParams.get(walletProofBundleParam) ?? undefined;
  } catch {
    return undefined;
  }
}

export async function reviewWalletProofQrScreenshot(file: File): Promise<WalletProofQrReview> {
  if (!qrImageAcceptedTypes.has(file.type)) {
    throw new Error("Upload a PNG, JPEG, or WebP screenshot of the wallet QR code.");
  }

  const qrValue = (await readQrValue(file)).trim();
  return reviewWalletProofBundleReference(qrValue);
}

async function readQrValue(file: File): Promise<string> {
  const detectorValue = await readQrValueWithBarcodeDetector(file).catch(() => "");
  if (detectorValue) return detectorValue;

  const ocrValue = await readQrValueWithOcr(file).catch(() => "");
  if (ocrValue) return ocrValue;

  throw new Error("We could not read a QR code or proof bundle link from that screenshot.");
}

async function readQrValueWithBarcodeDetector(file: File): Promise<string> {
  if (typeof window === "undefined") return "";
  const detectorCtor = (window as Window & { BarcodeDetector?: BarcodeDetectorLikeConstructor }).BarcodeDetector;
  if (!detectorCtor) return "";

  const detector = new detectorCtor({ formats: ["qr_code"] });
  const bitmap = await createImageBitmap(file);
  try {
    const matches = await detector.detect(bitmap);
    return matches.find((match) => typeof match.rawValue === "string" && match.rawValue.trim())?.rawValue?.trim() || "";
  } finally {
    bitmap.close();
  }
}

async function readQrValueWithOcr(file: File): Promise<string> {
  const { recognize } = await import("tesseract.js");
  const result = await recognize(file, "eng");
  const text = result.data.text || "";
  return extractLocatorToken(text);
}

function extractLocatorToken(text: string): string {
  const jsonStart = text.indexOf("{");
  const jsonEnd = text.lastIndexOf("}");
  if (jsonStart >= 0 && jsonEnd > jsonStart) {
    const jsonCandidate = text.slice(jsonStart, jsonEnd + 1).trim();
    try {
      JSON.parse(jsonCandidate);
      return jsonCandidate;
    } catch {
      // Ignore and continue with URL/CID detection.
    }
  }

  const urlMatch = text.match(/https?:\/\/[^\s<>"']+|ipfs:\/\/[^\s<>"']+/i);
  if (urlMatch) return urlMatch[0];

  const cidMatch = text.match(cidPattern);
  return cidMatch?.[0] ?? "";
}

function parseReviewLocator(qrValue: string): ReviewLocator {
  const jsonPayload = parseJson(qrValue);
  if (jsonPayload && hasInlineProofs(jsonPayload)) {
    return { kind: "inline", payload: jsonPayload, sourceLabel: "Wallet proof bundle from QR" };
  }

  const locatorFromPayload = jsonPayload ? locatorFromObject(jsonPayload) : undefined;
  if (locatorFromPayload) return locatorFromPayload;

  if (qrValue.startsWith("ipfs://")) {
    return { kind: "cid", cid: qrValue.slice("ipfs://".length).replace(/^ipfs\//, ""), sourceLabel: "IPFS/Filecoin proof bundle" };
  }

  if (/^https?:\/\//i.test(qrValue)) {
    const inlinePayload = readWalletProofBundlePayloadFromUrl(qrValue);
    if (inlinePayload) {
      return {
        kind: "inline",
        payload: inlinePayload,
        sourceLabel: "Wallet proof bundle link"
      };
    }
    return { kind: "url", url: qrValue, sourceLabel: labelForUrl(qrValue) };
  }

  const cidMatch = qrValue.match(cidPattern);
  if (cidMatch) {
    return { kind: "cid", cid: cidMatch[0], sourceLabel: "IPFS/Filecoin proof bundle" };
  }

  throw new Error("The QR code does not point to a supported proof bundle.");
}

function locatorFromObject(payload: unknown): ReviewLocator | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const record = payload as Record<string, unknown>;
  const urlValue = firstString(
    record.proofsUrl,
    record.proofBundleUrl,
    record.proof_manifest_url,
    record.gatewayUrl,
    record.url
  );
  if (urlValue) {
    return /^https?:\/\//i.test(urlValue)
      ? { kind: "url", url: urlValue, sourceLabel: labelForUrl(urlValue) }
      : { kind: "cid", cid: normalizeCid(urlValue), sourceLabel: "IPFS/Filecoin proof bundle" };
  }

  const cidValue = firstString(record.proofsCid, record.proofBundleCid, record.ipfsCid, record.cid);
  if (cidValue) {
    return { kind: "cid", cid: normalizeCid(cidValue), sourceLabel: "IPFS/Filecoin proof bundle" };
  }

  return undefined;
}

async function resolveReviewLocator(locator: ReviewLocator): Promise<{
  payload: unknown;
  sourceLabel: string;
  sourceUrl?: string;
}> {
  if (locator.kind === "inline") {
    return {
      payload: await hydrateProofBundle(locator.payload),
      sourceLabel: locator.sourceLabel
    };
  }

  if (locator.kind === "url") {
    return {
      payload: await hydrateProofBundle(await fetchJson(locator.url)),
      sourceLabel: locator.sourceLabel,
      sourceUrl: locator.url
    };
  }

  let lastError: Error | undefined;
  for (const gateway of defaultIpfsGateways) {
    const url = `${gateway}${locator.cid}`;
    try {
      return {
        payload: await hydrateProofBundle(await fetchJson(url)),
        sourceLabel: locator.sourceLabel,
        sourceUrl: url
      };
    } catch (error) {
      lastError = error instanceof Error ? error : new Error("Unable to load the proof bundle from IPFS/Filecoin.");
    }
  }
  throw lastError ?? new Error("Unable to load the proof bundle from IPFS/Filecoin.");
}

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Unable to load the proof bundle (${response.status}).`);
  }
  return response.json();
}

function unwrapProofPayload(payload: unknown): unknown {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return payload;
  const record = payload as Record<string, unknown>;
  return record.proofBundle ?? record.walletProofBundle ?? record;
}

async function hydrateProofBundle(payload: unknown): Promise<unknown> {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return payload;
  const record = unwrapProofPayload(payload) as Record<string, unknown>;
  const linkedProofs = readLinkedProofs(record);
  if (!linkedProofs.length) return record;

  const resolvedProofEntries = (
    await Promise.all(
      linkedProofs.map(async (entry) => {
        const locator = locatorFromObject(entry);
        if (!locator) return [];
        const resolved = await resolveReviewLocator(locator);
        return readProofArray(resolved.payload) ?? [unwrapProofPayload(resolved.payload)];
      })
    )
  ).flat();

  return {
    ...record,
    proofs: [...(readProofArray(record) ?? []), ...resolvedProofEntries]
  };
}

function hasInlineProofs(payload: unknown): boolean {
  return Array.isArray(readProofArray(payload));
}

function readProofArray(payload: unknown): unknown[] | undefined {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return undefined;
  const record = payload as Record<string, unknown>;
  const proofArrays = [record.proofs, record.proofCertificates, record.certificates, record.claims, record.p];
  return proofArrays.find(Array.isArray);
}

function readLinkedProofs(payload: Record<string, unknown>): Array<Record<string, unknown>> {
  const linkedProofArrays = [payload.linkedProofs, payload.proofLinks];
  const firstArray = linkedProofArrays.find(Array.isArray);
  if (!firstArray) return [];
  return firstArray.filter((entry): entry is Record<string, unknown> => Boolean(entry) && typeof entry === "object");
}

function readBundleTitle(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const record = payload as Record<string, unknown>;
  const wallet =
    record.wallet && typeof record.wallet === "object" ? (record.wallet as Record<string, unknown>) : undefined;
  const compactWallet = record.w && typeof record.w === "object" ? (record.w as Record<string, unknown>) : undefined;
  return firstString(record.title, record.name, record.t, wallet?.title, wallet?.name, wallet?.label, compactWallet?.l);
}

function normalizeProofs(payload: unknown): ProofReceiptView[] {
  const proofArray = readProofArray(payload);
  if (!proofArray) return [];
  return proofArray.map(normalizeProof).filter((proof): proof is ProofReceiptView => Boolean(proof));
}

function normalizeProof(proof: unknown): ProofReceiptView | undefined {
  if (!proof || typeof proof !== "object") return undefined;
  const record = proof as Record<string, unknown>;
  const publicInputs = normalizePublicInputs(
    record.publicInputs,
    record.public_inputs,
    record.disclosedClaims,
    record.disclosed_claims,
    record.statement,
    record.u
  );
  const claim =
    firstString(record.claim, record.c, publicInputs.claim, objectString(record.statement, "claim"), record.title, record.name) ||
    firstString(record.proofType, record.proof_type, record.certificateType, record.type, record.pt) ||
    "Verified claim";
  const proofType = firstString(record.proofType, record.proof_type, record.certificateType, record.type, record.pt) || "wallet_proof";
  const witnessRecordIds = Array.isArray(record.witness_record_ids)
    ? record.witness_record_ids.filter((value): value is string => typeof value === "string")
    : [];

  return {
    id: firstString(record.id, record.proofId, record.proof_id, record.certificateId, record.certificate_id, record.i) || claim,
    proofType,
    claim,
    verifier:
      firstString(record.verifier, record.verifierId, record.verifier_id, record.issuer, record.issuedBy, record.issuerDid, record.v) ||
      "Wallet verifier",
    proofSystem: firstString(record.proofSystem, record.proof_system, record.system, record.ps) || "linked bundle",
    verificationStatus: firstString(record.verificationStatus, record.verification_status, record.status, record.vs) || "verified",
    circuitId: firstString(record.circuitId, record.circuit_id),
    verifierDigest: firstString(record.verifierDigest, record.verifier_digest),
    proofArtifactRef: firstString(record.proofArtifactRef, record.proof_artifact_ref, record.artifactRef, record.ipfsCid, record.cid),
    publicInputs,
    witnessLabel:
      firstString(record.witnessLabel, record.witness_label, record.sourceLabel, record.source_label, record.w) ||
      witnessRecordIds.join(", ") ||
      "Wallet witness",
    simulated: Boolean(record.simulated ?? record.is_simulated),
    createdAt: firstString(record.createdAt, record.created_at, record.issuedAt, record.issued_at) || "Reviewed from QR"
  };
}

function normalizePublicInputs(...values: Array<unknown>): Record<string, string> {
  for (const value of values) {
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    const record = value as Record<string, unknown>;
    return Object.fromEntries(
      Object.entries(record)
        .map(([key, entry]) => [key, stringifyValue(entry)] as const)
        .filter(([, entry]) => entry.length > 0)
    );
  }
  return {};
}

function stringifyValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(stringifyValue).filter(Boolean).join(", ");
  if (value && typeof value === "object") {
    const nestedClaim = objectString(value, "claim");
    if (nestedClaim) return nestedClaim;
    try {
      return JSON.stringify(value);
    } catch {
      return "";
    }
  }
  return "";
}

function parseJson(value: string): unknown | undefined {
  try {
    return JSON.parse(value);
  } catch {
    return undefined;
  }
}

function normalizeCid(value: string): string {
  return value.replace(/^ipfs:\/\//, "").replace(/^\/?ipfs\//, "");
}

function parseProofArtifactLocator(value: string | undefined): Record<string, string> | undefined {
  if (!value) return undefined;
  if (/^https?:\/\//i.test(value)) return { url: value };
  if (/^ipfs:\/\//i.test(value) || /^\/?ipfs\//i.test(value) || cidPattern.test(value)) {
    return { cid: normalizeCid(value) };
  }
  return undefined;
}

function labelForUrl(url: string): string {
  return /\/ipfs\//i.test(url) || /^ipfs:\/\//i.test(url) ? "IPFS/Filecoin proof bundle" : "Wallet proof bundle link";
}

function objectString(value: unknown, key: string): string | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  return firstString((value as Record<string, unknown>)[key]);
}

function firstString(...values: Array<unknown>): string | undefined {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return undefined;
}

function currentBaseUrl(): string {
  if (typeof window === "undefined") {
    return "http://localhost/";
  }
  return `${window.location.origin}${window.location.pathname}`;
}
