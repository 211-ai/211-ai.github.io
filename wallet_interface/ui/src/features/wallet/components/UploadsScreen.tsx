import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
  Camera,
  Download,
  FileUp,
  KeyRound,
  LockKeyhole,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Trash2,
  Upload,
  Wrench
} from "lucide-react";
import QRCode from "qrcode";
import { ActionCard, Badge, Button, Field, Section, StatusBanner } from "../../../components/ui";
import {
  type DisclosureRecipientDraft,
  type ExportBundleView,
  type ProofReceiptView,
  type UploadItem
} from "../../../models/abby";
import { nonGrantedCapabilities } from "../../../services/capabilities";
import {
  getFilecoinStorageConfig,
  normalizeIpfsGatewayUrl,
  pollFilecoinStorageStatus,
  sameOriginIpfsGatewayUrl,
  toFilecoinStoragePatch,
  uploadFileToFilecoinStorage,
  uploadProofBundleToFilecoinStorage,
  uploadRecoveryBundleToFilecoinStorage,
  uploadWalletRecordToFilecoinStorage
} from "../../../services/filecoinStorage";
import {
  buildWalletProofBundlePayload,
  buildWalletProofReviewUrl,
  readQrValue,
  type WalletEncryptedRecordLink,
  type WalletProofQrReview
} from "../../../services/walletProofReview";
import {
  addBinaryDocument,
  addTextDocument,
  createWallet,
  deleteWalletRecord,
  generateWalletRecordMetadata,
  listWalletDocuments,
  loadLatestWalletRecoveryBundle,
  loadWalletDetails,
  loadWalletRecoveryBundleById,
  repairRecordStorage,
  storeWalletRecoveryBundle,
  createDocumentPrivacyProfileProof,
  analyzeRecordFormRedactedWithGrant,
  analyzeRecordRedactedWithGrant,
  createRecordVectorProfileWithGrant,
  createRedactedGraphRAG,
  decryptRecordWithGrant,
  extractRecordTextRedactedWithGrant,
  updateWalletRecordMetadata,
  type WalletApiConfig,
  type WalletMagicUcan
} from "../../../services/walletApi";
import { t, tFormat, type SupportedLocale } from "../../../lib/localization";
import { AccountSafetySection } from "../../../app/components/AccountSafetySection";
import { StatusPanel } from "../../../app/components/StatusPanel";
import { WorldIdSurfaceStatus } from "../../../app/components/WorldIdSurfaceStatus";
import { ExportCenterScreen } from "./ExportCenterScreen";
import {
  buildPassphraseWrappedRecoveryBundle,
  buildClientWrappedRecoveryBundle,
  decryptPassphraseRecoveryBundle,
  parseWalletRecoveryQrPayload,
  randomHex,
  readCachedRecoveryBundle,
  readMagicLoginUcan,
  resolveWalletOwnerDid,
  resolveMagicLoginApiBaseUrl,
  buildWalletRecoveryQrPayload,
  storeWalletDeviceRecoveryRawKey,
  WALLET_DEVICE_RECOVERY_KEY_PREFIX,
  WALLET_RECOVERY_BUNDLE_CACHE_PREFIX
} from "../../../app/utils/authHelpers";
import {
  generateUploadSummary,
  getIdentityDocumentFileDetail,
  ID_DOCUMENT_ACCEPT_ATTR,
  isAcceptedIdentityDocument,
  PROOF_QR_IMAGE_ACCEPT_ATTR,
  summarizeWalletProofClaims,
  toShortSummaryTitle,
  visibleProofCenterProofs
} from "../../../app/utils/formatHelpers";
import {
  base64ToBytes,
  buildWalletFileStats,
  filecoinActionLabel,
  filecoinBadge,
  filecoinBadgeTone,
  getWalletFileFilterOptions,
  ipfsGatewayHref,
  privacyProfileBadge,
  privacyProfileBadgeTone,
  searchWalletFiles,
  sharingBadge,
  shortStorageId,
  shouldShowFilecoinAction,
  uploadTypeLabel,
  type WalletFileFilterMode,
  type WalletFileSortMode
} from "../../../app/utils/walletFiles";
import {
  analysisLines,
  buildDocumentPrivacyProfilePublicInputs,
  buildFallbackDocumentProfileOutput,
  buildOpenRouterOrganizerProfile,
  buildPrivacySearchText,
  buildPrivacyVectorTerms,
  classifyDocumentProfile,
  compactRecord,
  defaultLabelsForMimeType,
  detectDecryptedMimeType,
  displayMimeType,
  normalizePublicMimeType,
  readStringArray,
  summarizeDocumentPrivacyProfile,
  toSafeOrganizerSignal
} from "../../../app/utils/privacyProfile";
import { WALLET_API_CONFIG_KEY, readWalletApiConfig } from "../../../app/services/walletConfig";

export function UploadsScreen({
  apiBaseUrl,
  apiConfig,
  bundles,
  proofs,
  refreshWalletAuditEvents,
  recipients,
  setApiConfig,
  setBundles,
  siteLocale,
  signedInUser,
  uploads,
  setUploads
}: {
  apiBaseUrl?: string;
  apiConfig?: WalletApiConfig;
  bundles: ExportBundleView[];
  proofs: ProofReceiptView[];
  refreshWalletAuditEvents: () => Promise<void>;
  recipients: DisclosureRecipientDraft[];
  setApiConfig: (config: WalletApiConfig) => void;
  setBundles: (bundles: ExportBundleView[]) => void;
  siteLocale: SupportedLocale;
  signedInUser: string;
  uploads: UploadItem[];
  setUploads: (uploads: UploadItem[]) => void;
}) {
  const [repairingUploadIds, setRepairingUploadIds] = useState<string[]>([]);
  const [filecoinUploadIds, setFilecoinUploadIds] = useState<string[]>([]);
  const [downloadingUploadIds, setDownloadingUploadIds] = useState<string[]>([]);
  const [deletingUploadIds, setDeletingUploadIds] = useState<string[]>([]);
  const [walletFileQuery, setWalletFileQuery] = useState("");
  const [walletFileFilter, setWalletFileFilter] = useState<WalletFileFilterMode>("all");
  const [walletFileSort, setWalletFileSort] = useState<WalletFileSortMode>("newest");
  const [storeNewFilesOnFilecoin, setStoreNewFilesOnFilecoin] = useState(true);
  const uploadsRef = useRef(uploads);
  const filecoinStorageConfig = useMemo(() => getFilecoinStorageConfig(), []);
  const filecoinStorageReady = Boolean(filecoinStorageConfig);
  const verifiedRecipients = recipients.filter((recipient) => recipient.verified);
  const [walletQrCodeUrl, setWalletQrCodeUrl] = useState("");
  const [walletQrStatus, setWalletQrStatus] = useState<"loading" | "ready" | "failed">("loading");
  const [walletProofBundleCid, setWalletProofBundleCid] = useState("");
  const [walletPublishedProofReviewUrl, setWalletPublishedProofReviewUrl] = useState("");
  const [walletCreateStatus, setWalletCreateStatus] = useState<"idle" | "creating" | "created" | "failed">("idle");
  const [walletCreateError, setWalletCreateError] = useState("");
  const [recoveryPassphrase, setRecoveryPassphrase] = useState("");
  const [recoveryStatus, setRecoveryStatus] = useState<"idle" | "saving" | "unlocking" | "ready" | "failed">("idle");
  const [recoveryMessage, setRecoveryMessage] = useState("");
  const [recoveryQrCodeUrl, setRecoveryQrCodeUrl] = useState("");
  const [recoveryQrPayloadLabel, setRecoveryQrPayloadLabel] = useState("");
  const walletQrProofs = useMemo(() => visibleProofCenterProofs(proofs), [proofs]);
  const walletProofBundlePayload = useMemo(
    () => buildWalletProofBundlePayload({ actorDid: apiConfig?.actorDid, proofs: walletQrProofs, walletId: apiConfig?.walletId }),
    [apiConfig?.actorDid, apiConfig?.walletId, walletQrProofs]
  );
  const walletProofBundleReference = walletProofBundleCid ? `ipfs://${walletProofBundleCid}` : walletProofBundlePayload;
  const walletProofReviewUrl = useMemo(
    () => buildWalletProofReviewUrl(walletProofBundleReference),
    [walletProofBundleReference]
  );
  const walletProofReviewHref = walletPublishedProofReviewUrl || walletProofReviewUrl;
  const walletQrPayloadLabel = filecoinStorageReady
    ? walletProofBundleCid || t(siteLocale, "wallet.publishingCid")
    : t(siteLocale, "wallet.connectStorageCid");
  const walletFileFilterOptions = getWalletFileFilterOptions(siteLocale);
  const visibleUploads = useMemo(
    () => searchWalletFiles(uploads, walletFileQuery, walletFileSort, walletFileFilter),
    [uploads, walletFileFilter, walletFileQuery, walletFileSort]
  );
  const walletFileStats = useMemo(() => buildWalletFileStats(uploads), [uploads]);

  useEffect(() => {
    uploadsRef.current = uploads;
  }, [uploads]);

  useEffect(() => {
    if (!apiConfig?.actorDid) return;
    uploads
      .filter((upload) => upload.recordId && (!upload.privacyProfileStatus || upload.privacyProfileNeedsRefresh))
      .forEach((upload) => {
        void profileWalletUpload(upload);
      });
  }, [apiConfig?.actorDid, uploads]);

  useEffect(() => {
    let cancelled = false;
    if (!filecoinStorageConfig) {
      setWalletProofBundleCid("");
      setWalletPublishedProofReviewUrl("");
      if (walletProofReviewUrl.length <= 2500) {
        setWalletQrStatus("loading");
        void QRCode.toDataURL(walletProofReviewUrl, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 220
        })
          .then((qrCodeUrl) => {
            if (!cancelled) {
              setWalletQrCodeUrl(qrCodeUrl);
              setWalletQrStatus("ready");
            }
          })
          .catch(() => {
            if (!cancelled) {
              setWalletQrCodeUrl("");
              setWalletQrStatus("failed");
            }
          });
      } else {
        setWalletQrCodeUrl("");
        setWalletQrStatus("failed");
      }
      return () => {
        cancelled = true;
      };
    }

    setWalletQrStatus("loading");
    const walletRecordLinks: WalletEncryptedRecordLink[] = uploads
      .filter((upload) => upload.recordId && upload.ipfsCid)
      .map((upload) => ({
        cid: upload.ipfsCid!,
        fileName: upload.fileName,
        links: upload.ipldLinks?.length
          ? upload.ipldLinks
          : [{ "/": upload.ipfsCid!, cid: upload.ipfsCid!, name: "encrypted_record" }],
        recordId: upload.recordId,
        root: upload.ipfsRootCid ? { "/": upload.ipfsRootCid } : { "/": upload.ipfsCid! }
      }));
    void Promise.resolve(walletRecordLinks)
      .then((recordLinks) =>
        uploadProofBundleToFilecoinStorage(
          buildWalletProofBundlePayload({
            actorDid: apiConfig?.actorDid,
            encryptedRecordLinks: recordLinks.filter((link): link is WalletEncryptedRecordLink => Boolean(link)),
            proofs: walletQrProofs,
            walletId: apiConfig?.walletId
          }),
          {
            clientConfig: filecoinStorageConfig,
            walletConfig: apiConfig
          }
        )
      )
      .then(async (result) => {
        const cid = result.ipfsCid || result.cid;
        if (!cid) throw new Error("The storage backend did not return a CID. Verify the IPFS/Filecoin storage configuration.");
        const nextReviewUrl = buildWalletProofReviewUrl(`ipfs://${cid}`);
        const nextQrCodeUrl = await QRCode.toDataURL(nextReviewUrl, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 220
        });
        if (!cancelled) {
          setWalletProofBundleCid(cid);
          setWalletPublishedProofReviewUrl(nextReviewUrl);
          setWalletQrCodeUrl(nextQrCodeUrl);
          setWalletQrStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setWalletProofBundleCid("");
          setWalletQrCodeUrl("");
          setWalletPublishedProofReviewUrl("");
          setWalletQrStatus("failed");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [apiConfig, filecoinStorageConfig, uploads, walletProofReviewUrl, walletQrProofs]);

  async function addUpload(file: File | null) {
    if (!file) return;
    const machineSummary = await generateUploadSummary(file);
    if (apiConfig?.actorDid) {
      try {
        const uploaded = normalizeWalletUpload(await addBinaryDocument(apiConfig, { file, title: machineSummary }), file.name);
        prependUpload(uploaded);
        await refreshWalletAuditEvents();
        void persistUploadMetadata(uploaded, {
          fileName: file.name,
          machineSummary,
          privacyProfileMimeType: file.type || "application/octet-stream",
          privacyProfileNeedsRefresh: true,
          privacyProfileStatus: "not_started"
        });
        void profileWalletUpload(uploaded, file);
        if (storeNewFilesOnFilecoin) {
          void storeWalletRecordOnFilecoin(uploaded);
        }
        return;
      } catch {
        try {
          const uploaded = normalizeWalletUpload(await addTextDocument(apiConfig, {
            filename: file.name,
            text: await file.text(),
            title: machineSummary
          }), file.name);
          prependUpload(uploaded);
          await refreshWalletAuditEvents();
          void persistUploadMetadata(uploaded, {
            fileName: file.name,
            machineSummary,
            privacyProfileMimeType: file.type || "application/octet-stream",
            privacyProfileNeedsRefresh: true,
            privacyProfileStatus: "not_started"
          });
          void profileWalletUpload(uploaded, file);
          if (storeNewFilesOnFilecoin) {
            void storeWalletRecordOnFilecoin(uploaded);
          }
          return;
        } catch {
          // Keep local document capture available if the configured API is unavailable.
        }
      }
    }
    const localUpload = normalizeWalletUpload(
      {
        id: `up-${Date.now()}`,
        fileName: file.name,
        machineSummary,
        category: "Uncategorized",
        sensitivity: "high",
        status: "stored",
        shared: false
      },
      file.name
    );
    prependUpload(localUpload);
    if (storeNewFilesOnFilecoin) {
      void storeFileUploadOnFilecoin(localUpload, file);
    }
  }

  async function repairUploadStorage(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    setRepairingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    try {
      const storageOk = await repairRecordStorage(apiConfig, upload.recordId);
      updateUpload(upload.id, {
        status: storageOk ? "stored" : upload.status,
        storageOk
      });
      await refreshWalletAuditEvents();
    } catch {
      updateUpload(upload.id, { storageOk: false });
    } finally {
      setRepairingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function storeFileUploadOnFilecoin(upload: UploadItem, file: File) {
    if (!filecoinStorageConfig) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: t(siteLocale, "wallet.storageConnectBeforeUpload"),
        decentralizedStorageStatus: "not_configured"
      });
      return;
    }
    setFilecoinUploadIds((uploadIds) => [...uploadIds, upload.id]);
    updateUpload(upload.id, {
      filecoinPinRequestId: undefined,
      filecoinPinStatus: undefined,
      filecoinPinStatusUrl: undefined,
      decentralizedStorageMessage: t(siteLocale, "wallet.storageUploading"),
      decentralizedStorageStatus: "uploading"
    });
    try {
      const result = await uploadFileToFilecoinStorage(file, {
        allowedRecipientIds: upload.allowedRecipientIds ?? [],
        clientConfig: filecoinStorageConfig,
        upload,
        walletConfig: apiConfig
      });
      const patch = toFilecoinStoragePatch(result);
      updateUpload(upload.id, patch);
      void persistUploadMetadata(upload, patch);
      void monitorFilecoinPersistence(upload.id, result);
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: error instanceof Error ? error.message : t(siteLocale, "wallet.storageUploadFailed"),
        decentralizedStorageStatus: "failed"
      });
    } finally {
      setFilecoinUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function storeWalletRecordOnFilecoin(upload: UploadItem) {
    if (!filecoinStorageConfig) return;
    setFilecoinUploadIds((uploadIds) => [...uploadIds, upload.id]);
    updateUpload(upload.id, {
      filecoinPinRequestId: undefined,
      filecoinPinStatus: undefined,
      filecoinPinStatusUrl: undefined,
      decentralizedStorageMessage:
        upload.filecoinPinStatus === "failed"
          ? t(siteLocale, "wallet.storageRetryRecord")
          : t(siteLocale, "wallet.storageSendRecord"),
      decentralizedStorageStatus: "uploading"
    });
    try {
      const result = await uploadWalletRecordToFilecoinStorage(upload, {
        clientConfig: filecoinStorageConfig,
        walletConfig: apiConfig
      });
      const patch = toFilecoinStoragePatch(result);
      const nextUpload = { ...upload, ...patch };
      updateUpload(upload.id, patch);
      void persistUploadMetadata(upload, patch);
      if (!nextUpload.privacyProfileStatus || nextUpload.privacyProfileNeedsRefresh) {
        void profileWalletUpload(nextUpload);
      }
      void monitorFilecoinPersistence(upload.id, result);
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: error instanceof Error ? error.message : t(siteLocale, "wallet.storageUploadFailed"),
        decentralizedStorageStatus: "failed"
      });
    } finally {
      setFilecoinUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function profileWalletUpload(upload: UploadItem, file?: File) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    const mimeType = normalizePublicMimeType(
      file?.type || upload.privacyProfileMimeType || "",
      file?.name || upload.fileName || upload.recordId
    );
    updateUpload(upload.id, {
      privacyProfileMessage: t(siteLocale, "wallet.profileCreating"),
      privacyProfileMimeType: mimeType,
      privacyProfileStatus: "profiling"
    });
    void persistUploadMetadata(upload, {
      privacyProfileMessage: t(siteLocale, "wallet.profileCreating"),
      privacyProfileMimeType: mimeType,
      privacyProfileStatus: "profiling"
    });
    try {
      try {
        const serverProfile = await generateWalletRecordMetadata(apiConfig, upload.recordId, {
          fileName: upload.fileName,
          mimeType,
          walletCid: upload.ipfsRootCid || upload.ipfsCid || upload.metadataIpldCid || upload.recordId
        });
        updateUpload(upload.id, {
          ...serverProfile,
          id: upload.id,
          recordId: serverProfile.recordId ?? upload.recordId,
          storageOk: serverProfile.storageOk ?? upload.storageOk
        });
        await refreshWalletAuditEvents().catch(() => {});
        return;
      } catch (serverError) {
        console.warn("Wallet router metadata generation failed; falling back to browser orchestration", serverError);
      }
      const [redacted, vector, graphrag, extracted, form] = await Promise.allSettled([
        analyzeRecordRedactedWithGrant(apiConfig, { recordId: upload.recordId, maxChars: 500 }),
        createRecordVectorProfileWithGrant(apiConfig, { recordId: upload.recordId, chunkSizeWords: 80 }),
        createRedactedGraphRAG(apiConfig, {
          recordIds: [upload.recordId],
          maxBytesPerRecord: 200_000,
          maxCharsPerRecord: 20_000,
          useOcr: true
        }),
        extractRecordTextRedactedWithGrant(apiConfig, {
          recordId: upload.recordId,
          maxBytes: 200_000,
          maxChars: 12_000,
          useOcr: true
        }),
        analyzeRecordFormRedactedWithGrant(apiConfig, {
          recordId: upload.recordId,
          maxFields: 100,
          useOcr: true
        })
      ]);
      const fulfilled = [redacted, vector, graphrag, extracted, form].filter(
        (result): result is PromiseFulfilledResult<Awaited<ReturnType<typeof analyzeRecordRedactedWithGrant>>> =>
          result.status === "fulfilled"
      );
      const outputs = fulfilled.map((result) => result.value.output);
      const organizerProfile = await buildOpenRouterOrganizerProfile({
        fileName: upload.fileName,
        mimeType,
        outputs
      });
      if (organizerProfile) {
        outputs.push({ openrouter_organizer_profile: organizerProfile, output_policy: "redacted_remote_organizer" });
      }
      if (!outputs.length) outputs.push(buildFallbackDocumentProfileOutput(upload, mimeType));
      const artifactIds = fulfilled.map((result) => result.value.artifact.id);
      const publicInputs = buildDocumentPrivacyProfilePublicInputs({
        artifactIds,
        file,
        fileName: upload.fileName,
        mimeType,
        outputs
      });
      const proof = await createDocumentPrivacyProfileProof(apiConfig, {
        publicInputs,
        recordId: upload.recordId
      });
      const patch: Partial<UploadItem> = {
        privacyProfileArtifactIds: artifactIds,
        privacyProfileClassification: classifyDocumentProfile(publicInputs),
        privacyProfileLabels: readStringArray(publicInputs, "organizer_labels") || defaultLabelsForMimeType(mimeType),
        privacyProfileMessage: t(siteLocale, "wallet.profileReady"),
        privacyProfileMimeType: mimeType,
        privacyProfileNeedsRefresh: false,
        privacyProfileProofId: proof.id,
        privacyProfilePublicInputs: proof.publicInputs,
        privacyProfileSearchText: buildPrivacySearchText(outputs, proof.publicInputs),
        privacyProfileStatus: "profiled",
        privacyProfileSummary: summarizeDocumentPrivacyProfile(publicInputs),
        privacyProfileVectorTerms: buildPrivacyVectorTerms(outputs, proof.publicInputs)
      };
      updateUpload(upload.id, patch);
      await persistUploadMetadata(upload, patch);
      await refreshWalletAuditEvents().catch(() => {});
    } catch (error) {
      const patch: Partial<UploadItem> = {
        privacyProfileMessage:
          error instanceof Error ? error.message : t(siteLocale, "wallet.profileError"),
        privacyProfileStatus: "failed"
      };
      updateUpload(upload.id, patch);
      void persistUploadMetadata(upload, patch);
    }
  }

  async function downloadDecryptedUpload(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    setDownloadingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    try {
      const decrypted = await decryptRecordWithGrant(apiConfig, { recordId: upload.recordId });
      const bytes = decrypted.base64 ? base64ToBytes(decrypted.base64) : new TextEncoder().encode(decrypted.text);
      const decryptedMimeType = detectDecryptedMimeType(bytes, upload.fileName, decrypted.text);
      const decryptedClassification = displayMimeType(decryptedMimeType);
      const decryptedLabels = defaultLabelsForMimeType(decryptedMimeType);
      updateUpload(upload.id, {
        decryptedClassification,
        decryptedLabels,
        decryptedMimeType
      });
      void persistUploadMetadata(upload, {
        decryptedClassification,
        decryptedLabels,
        decryptedMimeType
      });
      const payload = new Uint8Array(bytes).buffer as ArrayBuffer;
      const blob = new Blob([payload], { type: decryptedMimeType });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = upload.fileName || `${upload.recordId}.bin`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } finally {
      setDownloadingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function persistUploadMetadata(upload: UploadItem, patch: Partial<UploadItem> = {}) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    try {
      const saved = await updateWalletRecordMetadata(
        apiConfig,
        upload.recordId,
        serializeUploadMetadata({ ...upload, ...patch })
      );
      updateUpload(upload.id, {
        ...saved,
        id: upload.id,
        recordId: saved.recordId ?? upload.recordId,
        storageOk: saved.storageOk ?? upload.storageOk
      });
    } catch (error) {
      console.warn("Wallet file metadata persistence failed", error);
      // Metadata persistence is best-effort so uploads, pins, and proofs can still complete.
    }
  }

  function serializeUploadMetadata(upload: UploadItem): Record<string, unknown> {
    return compactRecord({
      decentralizedStorageMessage: upload.decentralizedStorageMessage,
      decentralizedStorageProvider: upload.decentralizedStorageProvider,
      decentralizedStorageStatus: upload.decentralizedStorageStatus,
      decryptedClassification: upload.decryptedClassification,
      decryptedLabels: upload.decryptedLabels,
      decryptedMimeType: upload.decryptedMimeType,
      encryptedMetadataCid: upload.encryptedMetadataCid,
      encryptedPayloadCid: upload.encryptedPayloadCid,
      fileName: upload.fileName,
      filecoinDealId: upload.filecoinDealId,
      filecoinPieceCid: upload.filecoinPieceCid,
      filecoinPinRequestId: upload.filecoinPinRequestId,
      filecoinPinStatus: upload.filecoinPinStatus,
      filecoinPinStatusUrl: upload.filecoinPinStatusUrl,
      ipfsCid: upload.ipfsCid,
      ipfsGatewayUrl: upload.ipfsGatewayUrl,
      ipfsRootCid: upload.ipfsRootCid,
      ipldLinks: upload.ipldLinks,
      machineSummary: upload.machineSummary,
      metadataCid: upload.metadataCid,
      metadataFilecoinPinRequestId: upload.metadataFilecoinPinRequestId,
      metadataFilecoinPinStatus: upload.metadataFilecoinPinStatus,
      metadataFilecoinPinStatusUrl: upload.metadataFilecoinPinStatusUrl,
      metadataGatewayUrl: upload.metadataGatewayUrl,
      metadataIpldCid: upload.metadataIpldCid,
      metadataIpldLink: upload.metadataIpldLink,
      metadataStorageMessage: upload.metadataStorageMessage,
      privacyProfileArtifactIds: upload.privacyProfileArtifactIds,
      privacyProfileClassification: upload.privacyProfileClassification,
      privacyProfileLabels: upload.privacyProfileLabels,
      privacyProfileMessage: upload.privacyProfileMessage,
      privacyProfileMimeType: upload.privacyProfileMimeType,
      privacyProfileNeedsRefresh: upload.privacyProfileNeedsRefresh,
      privacyProfileProofId: upload.privacyProfileProofId,
      privacyProfilePublicInputs: upload.privacyProfilePublicInputs,
      privacyProfileSearchText: upload.privacyProfileSearchText,
      privacyProfileStatus: upload.privacyProfileStatus,
      privacyProfileSummary: upload.privacyProfileSummary,
      privacyProfileVectorTerms: upload.privacyProfileVectorTerms
    });
  }

  function normalizeWalletUpload(upload: UploadItem, fileName: string): UploadItem {
    return {
      ...upload,
      allowedRecipientIds: upload.allowedRecipientIds ?? [],
      decentralizedStorageProvider: upload.decentralizedStorageProvider ?? (upload.recordId ? "wallet-api" : "local"),
      decentralizedStorageStatus: upload.decentralizedStorageStatus ?? (filecoinStorageReady ? "ready" : "not_configured"),
      fileName,
      shared: upload.shared ?? false,
      sharingMode: upload.sharingMode ?? "private"
    };
  }

  function prependUpload(upload: UploadItem) {
    replaceUploads([upload, ...uploadsRef.current]);
  }

  function replaceUploads(nextUploads: UploadItem[]) {
    uploadsRef.current = nextUploads;
    setUploads(nextUploads);
  }

  function updateUpload(uploadId: string, patch: Partial<UploadItem>) {
    replaceUploads(uploadsRef.current.map((item) => (item.id === uploadId ? { ...item, ...patch } : item)));
  }

  async function deleteWalletUpload(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    const confirmed = window.confirm(
      tFormat(siteLocale, "wallet.deleteConfirm", { name: upload.fileName })
    );
    if (!confirmed) return;
    setDeletingUploadIds((uploadIds) => [...new Set([...uploadIds, upload.id])]);
    try {
      await deleteWalletRecord(apiConfig, upload.recordId, { unpinIpfs: true });
      replaceUploads(uploadsRef.current.filter((item) => item.id !== upload.id));
      await refreshWalletAuditEvents().catch(() => undefined);
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage:
          error instanceof Error
            ? tFormat(siteLocale, "wallet.deleteFailedDetail", { error: error.message })
            : t(siteLocale, "wallet.deleteFailed")
      });
    } finally {
      setDeletingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function monitorFilecoinPersistence(uploadId: string, initialResult: Parameters<typeof toFilecoinStoragePatch>[0]) {
    if (!filecoinStorageConfig) return;
    if (!(initialResult.filecoinPinRequestId || initialResult.requestId)) return;
    try {
      await pollFilecoinStorageStatus(initialResult, {
        clientConfig: filecoinStorageConfig,
        onUpdate: (nextResult) => {
          const patch = toFilecoinStoragePatch(nextResult);
          const upload = uploadsRef.current.find((item) => item.id === uploadId);
          updateUpload(uploadId, patch);
          if (upload) {
            void persistUploadMetadata(upload, patch);
          }
        }
      });
    } catch (error) {
      updateUpload(uploadId, {
        decentralizedStorageMessage:
          error instanceof Error
            ? tFormat(siteLocale, "wallet.pollFailedDetail", { error: error.message })
            : t(siteLocale, "wallet.pollFailed")
      });
    }
  }

  function allowSharing(upload: UploadItem) {
    const selectedRecipients =
      upload.allowedRecipientIds?.length
        ? upload.allowedRecipientIds
        : (verifiedRecipients.length ? verifiedRecipients : recipients).slice(0, 2).map((recipient) => recipient.id);
    updateUpload(upload.id, {
      allowedRecipientIds: selectedRecipients,
      shared: selectedRecipients.length > 0,
      sharingMode: "selected_contacts"
    });
  }

  function makePrivate(upload: UploadItem) {
    updateUpload(upload.id, {
      allowedRecipientIds: [],
      shared: false,
      sharingMode: "private"
    });
  }

  function toggleSharingRecipient(upload: UploadItem, recipientId: string) {
    const currentRecipients = upload.allowedRecipientIds ?? [];
    const allowedRecipientIds = currentRecipients.includes(recipientId)
      ? currentRecipients.filter((id) => id !== recipientId)
      : [...currentRecipients, recipientId];
    updateUpload(upload.id, {
      allowedRecipientIds,
      shared: allowedRecipientIds.length > 0,
      sharingMode: allowedRecipientIds.length > 0 ? "selected_contacts" : "private"
    });
  }

  function walletLoginContact() {
    return signedInUser.includes(":") ? signedInUser.split(":").slice(1).join(":") : signedInUser;
  }

  async function generateWallet() {
    if (!apiBaseUrl) return;
    setWalletCreateStatus("creating");
    setWalletCreateError("");
    const ownerDid = resolveWalletOwnerDid(signedInUser, apiConfig);
    const issuerKeyHex = randomHex(32);

    try {
      const wallet = await createWallet({ apiBaseUrl, ownerDid });
      const nextConfig = {
        apiBaseUrl,
        walletId: wallet.wallet_id,
        actorDid: wallet.owner_did,
        issuerKeyHex,
        audienceKeyHex: undefined
      };
      setApiConfig(nextConfig);
      try {
        const recoveryBundle = await buildClientWrappedRecoveryBundle({
          actorDid: wallet.owner_did,
          contact: walletLoginContact(),
          walletId: wallet.wallet_id
        });
        await storeWalletRecoveryBundle(nextConfig, {
          encryptedBundle: recoveryBundle.encryptedBundle,
          publicMetadata: recoveryBundle.publicMetadata,
          recoveryHint: "This wallet recovery bundle is encrypted to this browser's local recovery key.",
          wrappingMethod: "device-local-key"
        });
      } catch (error) {
        if (import.meta.env.DEV) {
          console.warn("Client-side wallet recovery bundle could not be stored", error);
        }
      }
      setWalletCreateStatus("created");
    } catch (error) {
      setWalletCreateStatus("failed");
      setWalletCreateError(error instanceof Error ? error.message : t(siteLocale, "wallet.generationFailed"));
    }
  }

  async function savePassphraseRecoveryBundle() {
    if (!apiConfig?.actorDid || !recoveryPassphrase.trim()) return;
    setRecoveryStatus("saving");
    setRecoveryMessage("");
    try {
      const bundle = await buildPassphraseWrappedRecoveryBundle({
        actorDid: apiConfig.actorDid,
        contact: walletLoginContact(),
        passphrase: recoveryPassphrase,
        walletId: apiConfig.walletId
      });
      const response = await storeWalletRecoveryBundle(apiConfig, {
        encryptedBundle: bundle.encryptedBundle,
        kdf: bundle.kdf,
        publicMetadata: {
          ...bundle.publicMetadata,
          recoveryMethods: ["passphrase-pbkdf2-aes-gcm"]
        },
        recoveryHint: "Passphrase recovery bundle. The passphrase and wallet key are never sent to 211 AI.",
        wrappingMethod: "passphrase"
      });
      const recoveryQrPayload = buildWalletRecoveryQrPayload(
        apiConfig,
        response.bundle.bundle_id,
        "passphrase",
        recoveryPassphrase
      );
      const recoveryQrText = JSON.stringify(recoveryQrPayload);
      setRecoveryQrPayloadLabel(response.bundle.bundle_id);
      setRecoveryQrCodeUrl(
        await QRCode.toDataURL(recoveryQrText, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 220
        })
      );
      let backupMessage = "";
      if (filecoinStorageConfig) {
        const recoveryBackupPayload = JSON.stringify({
          schema: "211-ai-wallet-recovery-backup-v1",
          bundleId: response.bundle.bundle_id,
          containsPassphrase: false,
          containsPlaintextWalletKey: false,
          encryptedBundle: response.bundle.encrypted_bundle,
          publicMetadata: response.bundle.public_metadata,
          serverCanDecrypt: false,
          walletId: apiConfig.walletId,
          wrappingMethod: response.bundle.wrapping_method
        });
        const backup = await uploadRecoveryBundleToFilecoinStorage(recoveryBackupPayload, {
          clientConfig: filecoinStorageConfig,
          walletConfig: apiConfig
        });
        const backupCid = backup.ipfsCid || backup.cid || backup.root?.["/"];
        backupMessage = backupCid
          ? tFormat(siteLocale, "wallet.recoveryBackupQueuedWithCid", { cid: backupCid })
          : t(siteLocale, "wallet.recoveryBackupQueued");
      }
      setRecoveryStatus("ready");
      setRecoveryMessage(tFormat(siteLocale, "wallet.recoveryReady", { backup: backupMessage }));
    } catch (error) {
      setRecoveryStatus("failed");
      setRecoveryMessage(error instanceof Error ? error.message : t(siteLocale, "wallet.recoverySetupFailed"));
    }
  }

  async function importRecoveryQr(file: File | null) {
    if (!file) return;
    const ucan = readMagicLoginUcan();
    if (!ucan?.token) {
      setRecoveryStatus("failed");
      setRecoveryMessage(t(siteLocale, "wallet.recoveryNeedMagicLink"));
      return;
    }
    setRecoveryStatus("unlocking");
    setRecoveryMessage("");
    try {
      const qrValue = await readQrValue(file);
      const payload = parseWalletRecoveryQrPayload(qrValue);
      const config = {
        ...(apiConfig ?? {
          apiBaseUrl: payload.apiBaseUrl || resolveMagicLoginApiBaseUrl(),
          walletId: payload.walletId
        }),
        apiBaseUrl: payload.apiBaseUrl || apiConfig?.apiBaseUrl || resolveMagicLoginApiBaseUrl(),
        walletId: payload.walletId
      };
      const response = await loadWalletRecoveryBundleById(config, payload.bundleId, ucan.token);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          `${WALLET_RECOVERY_BUNDLE_CACHE_PREFIX}${payload.walletId}`,
          JSON.stringify({
            cachedAt: new Date().toISOString(),
            bundle: response.bundle,
            privacy: response.privacy,
            source: "magic-link-plus-qr",
            ucan: {
              audience: ucan.audience,
              expires_at: ucan.expires_at,
              profile: ucan.profile
            }
          })
        );
      }
      if (!apiConfig) {
        setApiConfig(config);
      }
      setRecoveryQrPayloadLabel(payload.bundleId);
      if (payload.passphrase) {
        const recovered = await decryptPassphraseRecoveryBundle(response.bundle.encrypted_bundle, payload.passphrase);
        if (recovered.walletId && recovered.walletId !== config.walletId) {
          throw new Error(t(siteLocale, "wallet.recoveryWrongWallet"));
        }
        storeWalletDeviceRecoveryRawKey(config.walletId, recovered.walletContentKey);
        if (recovered.actorDid && recovered.actorDid !== config.actorDid) {
          setApiConfig({ ...config, actorDid: recovered.actorDid });
        }
        setRecoveryPassphrase("");
        setRecoveryStatus("ready");
        setRecoveryMessage(t(siteLocale, "wallet.recoveryUnlockedLocal"));
        return;
      }
      setRecoveryStatus("ready");
      setRecoveryMessage(t(siteLocale, "wallet.recoveryImported"));
    } catch (error) {
      setRecoveryStatus("failed");
      setRecoveryMessage(error instanceof Error ? error.message : t(siteLocale, "wallet.recoveryImportFailed"));
    }
  }

  async function unlockCachedPassphraseRecoveryBundle() {
    if (!apiConfig || !recoveryPassphrase.trim()) return;
    setRecoveryStatus("unlocking");
    setRecoveryMessage("");
    try {
      const bundle = readCachedRecoveryBundle(apiConfig.walletId);
      if (!bundle) {
        throw new Error(t(siteLocale, "wallet.recoveryNoCachedBundle"));
      }
      const recovered = await decryptPassphraseRecoveryBundle(bundle, recoveryPassphrase);
      if (recovered.walletId && recovered.walletId !== apiConfig.walletId) {
        throw new Error(t(siteLocale, "wallet.recoveryWrongWallet"));
      }
      storeWalletDeviceRecoveryRawKey(apiConfig.walletId, recovered.walletContentKey);
      if (recovered.actorDid && recovered.actorDid !== apiConfig.actorDid) {
        setApiConfig({ ...apiConfig, actorDid: recovered.actorDid });
      }
      setRecoveryStatus("ready");
      setRecoveryMessage(t(siteLocale, "wallet.recoveryRestored"));
    } catch (error) {
      setRecoveryStatus("failed");
      setRecoveryMessage(error instanceof Error ? error.message : t(siteLocale, "wallet.recoveryFailed"));
    }
  }

  return (
    <div className="screen wallet-screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "wallet.eyebrow")}</p>
        <h1>{t(siteLocale, "wallet.title")}</h1>
      </div>
      {walletCreateStatus === "created" ? <StatusBanner tone="success">{t(siteLocale, "wallet.generatedConnected")}</StatusBanner> : null}
      {walletCreateStatus === "failed" ? <StatusBanner tone="warning">{walletCreateError || t(siteLocale, "wallet.generationFailed")}</StatusBanner> : null}
      <div className="wallet-status-strip" aria-label={t(siteLocale, "wallet.statusAria")}>
        <div>
          <span>{t(siteLocale, "wallet.status.wallet")}</span>
          <strong>
            {apiConfig
              ? t(siteLocale, "wallet.status.connected")
              : apiBaseUrl
                ? t(siteLocale, "wallet.status.ready")
                : t(siteLocale, "wallet.status.needsApi")}
          </strong>
        </div>
        <div>
          <span>{t(siteLocale, "wallet.status.files")}</span>
          <strong>{uploads.length}</strong>
        </div>
        <div>
          <span>{t(siteLocale, "wallet.status.proofs")}</span>
          <strong>{walletFileStats.profiled}</strong>
        </div>
        <div>
          <span>{t(siteLocale, "wallet.status.ipld")}</span>
          <strong>{walletFileStats.ipldLinked}</strong>
        </div>
      </div>
      <WorldIdSurfaceStatus
        apiConfig={apiConfig}
        ariaLabel="Uploads World ID status"
        onAuditRefresh={refreshWalletAuditEvents}
      />
      <Section
        title={t(siteLocale, "wallet.connectionTitle")}
        actions={
          <Badge tone={apiConfig ? "success" : apiBaseUrl ? "warning" : "neutral"}>
            {apiConfig
              ? t(siteLocale, "wallet.connection.connected")
              : apiBaseUrl
                ? t(siteLocale, "wallet.connection.readyToCreate")
                : t(siteLocale, "wallet.connection.apiRequired")}
          </Badge>
        }
      >
        <div className="disclosure-package">
          <div className="disclosure-row">
            <strong>{t(siteLocale, "wallet.connection.wallet")}</strong>
            <span>{apiConfig?.walletId ?? t(siteLocale, "wallet.connection.notConnected")}</span>
          </div>
          <div className="disclosure-row">
            <strong>{t(siteLocale, "wallet.connection.ownerDid")}</strong>
            <span>{apiConfig?.actorDid ?? t(siteLocale, "wallet.connection.ownerDidPending")}</span>
          </div>
          <div className="disclosure-row">
            <strong>{t(siteLocale, "wallet.connection.backend")}</strong>
            <span>{apiBaseUrl ?? t(siteLocale, "wallet.connection.backendHelp")}</span>
          </div>
        </div>
        <div className="row-actions">
          <Button
            ariaLabel={walletCreateStatus === "creating" ? t(siteLocale, "wallet.connection.generating") : t(siteLocale, "wallet.connection.generate")}
            disabled={!apiBaseUrl || walletCreateStatus === "creating"}
            onClick={() => void generateWallet()}
          >
            <Archive size={18} /> {walletCreateStatus === "creating" ? t(siteLocale, "wallet.connection.generating") : t(siteLocale, "wallet.connection.generate")}
          </Button>
        </div>
        <div className="wallet-recovery-panel">
          <div>
            <strong>{t(siteLocale, "wallet.recoveryTitle")}</strong>
            <small>{t(siteLocale, "wallet.recoveryHelp")}</small>
          </div>
          <Field label={t(siteLocale, "wallet.recoveryPassphrase")}>
            <input
              autoComplete="new-password"
              disabled={!apiConfig}
              onChange={(event) => {
                setRecoveryPassphrase(event.target.value);
                setRecoveryMessage("");
                setRecoveryStatus("idle");
              }}
              placeholder={t(siteLocale, "wallet.recoveryPassphrasePlaceholder")}
              type="password"
              value={recoveryPassphrase}
            />
          </Field>
          <div className="row-actions">
            <Button
              disabled={!apiConfig?.actorDid || recoveryPassphrase.trim().length < 8 || recoveryStatus === "saving"}
              loading={recoveryStatus === "saving"}
              loadingLabel={t(siteLocale, "wallet.recoverySaving")}
              onClick={() => void savePassphraseRecoveryBundle()}
              type="button"
              variant="secondary"
            >
              <LockKeyhole size={18} /> {t(siteLocale, "wallet.recoverySave")}
            </Button>
            <Button
              disabled={!apiConfig || recoveryPassphrase.trim().length < 8 || recoveryStatus === "unlocking"}
              loading={recoveryStatus === "unlocking"}
              loadingLabel={t(siteLocale, "wallet.recoveryUnlocking")}
              onClick={() => void unlockCachedPassphraseRecoveryBundle()}
              type="button"
              variant="secondary"
            >
              <KeyRound size={18} /> {t(siteLocale, "wallet.recoveryUnlock")}
            </Button>
          </div>
          <div className="wallet-recovery-qr-grid">
            {recoveryQrCodeUrl ? (
              <img
                alt={t(siteLocale, "wallet.recoveryQrAlt")}
                className="wallet-proof-qr-image"
                height={180}
                src={recoveryQrCodeUrl}
                width={180}
              />
            ) : (
              <div className="wallet-proof-qr-placeholder">{t(siteLocale, "wallet.recoveryQrPlaceholder")}</div>
            )}
            <div className="wallet-recovery-qr-actions">
              <strong>{t(siteLocale, "wallet.recoveryMagicQrTitle")}</strong>
              <small>{t(siteLocale, "wallet.recoveryMagicQrHelp")}</small>
              <div className="disclosure-package">
                <div className="disclosure-row">
                  <strong>{t(siteLocale, "wallet.recoveryBundle")}</strong>
                  <span>{recoveryQrPayloadLabel || t(siteLocale, "wallet.recoveryBundleMissing")}</span>
                </div>
                <div className="disclosure-row">
                  <strong>{t(siteLocale, "wallet.serverAccess")}</strong>
                  <span>{t(siteLocale, "wallet.serverAccessDetail")}</span>
                </div>
                <div className="disclosure-row">
                  <strong>{t(siteLocale, "wallet.qrAccess")}</strong>
                  <span>{t(siteLocale, "wallet.qrAccessDetail")}</span>
                </div>
              </div>
              <label className="button button-secondary">
                <Camera aria-hidden="true" size={18} /> {t(siteLocale, "wallet.importRecoveryQr")}
                <input
                  accept={PROOF_QR_IMAGE_ACCEPT_ATTR}
                  aria-label={t(siteLocale, "wallet.importRecoveryQrPicture")}
                  className="sr-only"
                  onChange={(event) => {
                    void importRecoveryQr(event.target.files?.[0] ?? null);
                    event.currentTarget.value = "";
                  }}
                  type="file"
                />
              </label>
            </div>
          </div>
          {recoveryMessage ? (
            <StatusBanner tone={recoveryStatus === "failed" ? "warning" : "success"}>{recoveryMessage}</StatusBanner>
          ) : null}
        </div>
      </Section>
      <Section
        title={t(siteLocale, "wallet.shareProofQrTitle")}
        actions={
          <Badge tone={walletQrProofs.length > 0 ? "success" : "warning"}>
            {tFormat(siteLocale, "wallet.proofClaims", { count: String(walletQrProofs.length) })}
          </Badge>
        }
      >
        <div className="wallet-proof-qr-panel">
          {walletQrCodeUrl ? (
            <img
              alt={t(siteLocale, "wallet.shareProofQrTitle")}
              className="wallet-proof-qr-image"
              height={220}
              src={walletQrCodeUrl}
              width={220}
            />
          ) : (
            <div aria-live="polite" className="wallet-proof-qr-placeholder">
              {walletQrStatus === "loading"
                ? t(siteLocale, "wallet.proofPublishing")
                : filecoinStorageReady
                  ? t(siteLocale, "wallet.proofUnavailable")
                  : t(siteLocale, "wallet.proofConnectStorage")}
            </div>
          )}
          <div className="wallet-proof-qr-details">
            <strong>{t(siteLocale, "wallet.scanProofTitle")}</strong>
            <small>{t(siteLocale, "wallet.scanProofHelp")}</small>
            <div className="badge-row">
              <Badge tone="info">{t(siteLocale, "wallet.ipfsWalletRootQr")}</Badge>
              <Badge>{apiConfig?.walletId ?? t(siteLocale, "wallet.localWallet")}</Badge>
              {apiConfig?.actorDid ? <Badge>{apiConfig.actorDid}</Badge> : <Badge>{t(siteLocale, "wallet.offlineWalletPreview")}</Badge>}
            </div>
            <div className="disclosure-package">
              <div className="disclosure-row">
                <strong>{t(siteLocale, "wallet.qrPayload")}</strong>
                <span>{walletQrPayloadLabel}</span>
              </div>
              <div className="disclosure-row">
                <strong>{t(siteLocale, "wallet.includes")}</strong>
                <span>
                  {uploads.filter((upload) => upload.recordId).length} encrypted wallet records;{" "}
                  {summarizeWalletProofClaims(walletQrProofs)}
                </span>
              </div>
              <div className="disclosure-row">
                <strong>{t(siteLocale, "wallet.opens")}</strong>
                <span>{t(siteLocale, "wallet.opensDetail")}</span>
              </div>
            </div>
            <a className="button button-secondary" href={walletProofReviewHref}>
              {t(siteLocale, "wallet.openProofReview")}
            </a>
          </div>
        </div>
      </Section>
      <Section
        title={t(siteLocale, "wallet.addFileTitle")}
        actions={
          <Badge tone={filecoinStorageReady ? "success" : "warning"}>
            {filecoinStorageReady ? t(siteLocale, "wallet.storageReady") : t(siteLocale, "wallet.backendRequired")}
          </Badge>
        }
      >
        <div className="wallet-storage-panel">
          <div>
            <strong>{t(siteLocale, "wallet.storageDestination")}</strong>
            <small>
              {filecoinStorageReady
                ? t(siteLocale, "wallet.storageReadyHelp")
                : t(siteLocale, "wallet.storageMissingHelp")}
            </small>
          </div>
          <label className="wallet-filecoin-toggle">
            <input
              checked={storeNewFilesOnFilecoin}
              disabled={!filecoinStorageReady}
              onChange={(event) => setStoreNewFilesOnFilecoin(event.target.checked)}
              type="checkbox"
            />
            <span>{t(siteLocale, "wallet.storeNewFiles")}</span>
          </label>
        </div>
        <label className="upload-dropzone">
          <Upload aria-hidden="true" size={28} />
          <span>{t(siteLocale, "wallet.chooseFile")}</span>
          <small>{t(siteLocale, "wallet.filesPrivateUntilShared")}</small>
          <span className="upload-picker">
            <FileUp aria-hidden="true" size={18} /> {t(siteLocale, "wallet.selectFile")}
          </span>
          <input
            type="file"
            onChange={(event) => addUpload(event.target.files?.[0] ?? null)}
            aria-label={t(siteLocale, "wallet.chooseFileAria")}
          />
        </label>
      </Section>
      <Section
        title={t(siteLocale, "wallet.fileWalletTitle")}
        actions={
          <Badge tone={visibleUploads.length === uploads.length ? "neutral" : "info"}>
            {tFormat(siteLocale, "wallet.fileCount", { total: String(uploads.length), visible: String(visibleUploads.length) })}
          </Badge>
        }
      >
        <div className="wallet-file-workbench">
          <div className="wallet-file-controls" aria-label={t(siteLocale, "wallet.fileControlsAria")}>
            <Field label={t(siteLocale, "wallet.findFiles")}>
              <div className="wallet-file-search-field">
                <Search aria-hidden="true" size={18} />
                <input
                  autoComplete="off"
                  onChange={(event) => setWalletFileQuery(event.target.value)}
                  placeholder={t(siteLocale, "wallet.searchPlaceholder")}
                  type="search"
                  value={walletFileQuery}
                />
              </div>
            </Field>
            <Field label={t(siteLocale, "wallet.sort")}>
              <select
                onChange={(event) => setWalletFileSort(event.target.value as WalletFileSortMode)}
                value={walletFileSort}
              >
                <option value="newest">{t(siteLocale, "wallet.sortNewest")}</option>
                <option value="oldest">{t(siteLocale, "wallet.sortOldest")}</option>
                <option value="name">{t(siteLocale, "wallet.sortName")}</option>
                <option value="type">{t(siteLocale, "wallet.sortType")}</option>
                <option value="profile">{t(siteLocale, "wallet.sortProfile")}</option>
                <option value="storage">{t(siteLocale, "wallet.sortStorage")}</option>
              </select>
            </Field>
          </div>
          <div className="wallet-file-filter-row" aria-label={t(siteLocale, "wallet.filtersAria")}>
            {walletFileFilterOptions.map((option) => (
              <button
                aria-pressed={walletFileFilter === option.value}
                className="choice-chip"
                key={option.value}
                onClick={() => setWalletFileFilter(option.value)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
        <div className="list-stack wallet-file-list">
          {visibleUploads.length === 0 ? (
            <div className="wallet-empty-state">
              <strong>{t(siteLocale, "wallet.emptyTitle")}</strong>
              <small>{t(siteLocale, "wallet.emptyBody")}</small>
            </div>
          ) : null}
        {visibleUploads.map((upload) => (
          <article
            aria-label={tFormat(siteLocale, "wallet.fileAria", { name: upload.fileName })}
            className="list-item upload-list-item wallet-list-item"
            key={upload.id}
          >
            <div className="wallet-file-primary">
              <h3>{upload.fileName}</h3>
              <p>{uploadTypeLabel(upload)}</p>
              <small className="upload-machine-summary">{toShortSummaryTitle(upload.machineSummary)}</small>
              <div className="badge-row">
                <Badge tone="success">{upload.status}</Badge>
                {upload.storageOk !== undefined ? (
                  <Badge tone={upload.storageOk ? "success" : "warning"}>
                    {upload.storageOk ? t(siteLocale, "wallet.saved") : t(siteLocale, "wallet.saveNeedsFix")}
                  </Badge>
                ) : null}
                <Badge tone={upload.shared ? "success" : "neutral"}>{sharingBadge(upload, siteLocale)}</Badge>
                <Badge tone={filecoinBadgeTone(upload)}>{filecoinBadge(upload, siteLocale)}</Badge>
                {upload.decryptedMimeType ? (
                  <Badge tone="success">{displayMimeType(upload.decryptedMimeType)}</Badge>
                ) : null}
                {upload.privacyProfileMimeType ? (
                  <Badge tone="info">{displayMimeType(upload.privacyProfileMimeType)}</Badge>
                ) : null}
                {upload.privacyProfileClassification ? (
                  <Badge tone="info">{upload.privacyProfileClassification}</Badge>
                ) : null}
                {upload.privacyProfileStatus ? (
                  <Badge tone={privacyProfileBadgeTone(upload)}>
                    {privacyProfileBadge(upload, siteLocale)}
                  </Badge>
                ) : null}
              </div>
              {upload.ipfsCid ? (
                <div className="wallet-evidence-row">
                  <span>IPFS</span>
                  <a href={ipfsGatewayHref(upload)} rel="noreferrer" target="_blank">
                    <code>{upload.ipfsCid}</code>
                  </a>
                </div>
              ) : null}
              {upload.ipldLinks?.length ? (
                <div className="wallet-evidence-row">
                  <span>IPLD</span>
                  <strong>
                    {upload.ipldLinks.length} {upload.ipldLinks.length === 1 ? t(siteLocale, "wallet.objectSingular") : t(siteLocale, "wallet.objectPlural")}
                  </strong>
                </div>
              ) : null}
              {upload.metadataCid ? (
                <div className="wallet-evidence-row">
                  <span>{t(siteLocale, "wallet.metadata")}</span>
                  <a href={normalizeIpfsGatewayUrl(upload.metadataGatewayUrl) || ipfsGatewayHref({ ...upload, ipfsCid: upload.metadataCid, ipfsGatewayUrl: undefined })} rel="noreferrer" target="_blank">
                    <code>{upload.metadataCid}</code>
                  </a>
                </div>
              ) : null}
              {upload.metadataStorageMessage ? (
                <small className="wallet-storage-reference">{upload.metadataStorageMessage}</small>
              ) : null}
              {upload.privacyProfileSummary ? (
                <small className="wallet-storage-reference">{tFormat(siteLocale, "wallet.privateProfile", { value: upload.privacyProfileSummary })}</small>
              ) : null}
              {upload.decryptedClassification || upload.decryptedMimeType ? (
                <small className="wallet-storage-reference">
                  {tFormat(siteLocale, "wallet.decryptedDownload", {
                    value: `${upload.decryptedClassification || displayMimeType(upload.decryptedMimeType || "")}${upload.decryptedMimeType ? ` (${upload.decryptedMimeType})` : ""}`
                  })}
                </small>
              ) : null}
              {upload.decryptedLabels?.length ? (
                <small className="wallet-storage-reference">
                  {tFormat(siteLocale, "wallet.decryptedContents", { value: upload.decryptedLabels.slice(0, 6).join(", ") })}
                </small>
              ) : null}
              {upload.privacyProfileClassification || upload.privacyProfileMimeType ? (
                <small className="wallet-storage-reference">
                  {tFormat(siteLocale, "wallet.profiledType", {
                    value: `${upload.privacyProfileClassification || displayMimeType(upload.privacyProfileMimeType || "")}${upload.privacyProfileMimeType ? ` (${upload.privacyProfileMimeType})` : ""}`
                  })}
                </small>
              ) : null}
              {upload.privacyProfileLabels?.length ? (
                <small className="wallet-storage-reference">
                  {tFormat(siteLocale, "wallet.contents", { value: upload.privacyProfileLabels.slice(0, 6).join(", ") })}
                </small>
              ) : null}
              {upload.privacyProfileProofId ? (
                <small className="wallet-storage-reference">{tFormat(siteLocale, "wallet.proof", { value: shortStorageId(upload.privacyProfileProofId) })}</small>
              ) : null}
              {upload.privacyProfileMessage ? (
                <small className="wallet-storage-reference">{upload.privacyProfileMessage}</small>
              ) : null}
              {upload.decentralizedStorageMessage ? (
                <small className="wallet-storage-reference">{upload.decentralizedStorageMessage}</small>
              ) : null}
            </div>
            <div className="wallet-sharing-controls" aria-label={tFormat(siteLocale, "wallet.sharingControlsFor", { name: upload.fileName })}>
              <div className="wallet-sharing-mode">
                <button
                  aria-pressed={(upload.sharingMode ?? "private") === "private"}
                  className="choice-chip"
                  onClick={() => makePrivate(upload)}
                  type="button"
                >
                  {t(siteLocale, "wallet.private")}
                </button>
                <button
                  aria-pressed={(upload.sharingMode ?? "private") === "selected_contacts"}
                  className="choice-chip"
                  onClick={() => allowSharing(upload)}
                  type="button"
                >
                  {t(siteLocale, "wallet.selectedContacts")}
                </button>
              </div>
              {(upload.sharingMode ?? "private") === "selected_contacts" ? (
                <div className="wallet-recipient-grid">
                  {recipients.length ? (
                    recipients.map((recipient) => (
                      <label className="wallet-recipient-option" key={recipient.id}>
                        <input
                          checked={(upload.allowedRecipientIds ?? []).includes(recipient.id)}
                          onChange={() => toggleSharingRecipient(upload, recipient.id)}
                          type="checkbox"
                        />
                        <span>
                          {recipient.displayName}
                          <small>
                            {recipient.verified ? t(siteLocale, "wallet.contactVerified") : t(siteLocale, "wallet.contactNotVerified")} · {recipient.relationship || recipient.agencyName || t(siteLocale, "wallet.contactFallback")}
                          </small>
                        </span>
                      </label>
                    ))
                  ) : (
                    <small className="upload-machine-summary">{t(siteLocale, "wallet.addContactsBeforeSharing")}</small>
                  )}
                </div>
              ) : null}
            </div>
            <div className="wallet-file-footer-actions" aria-label={tFormat(siteLocale, "wallet.actionsFor", { name: upload.fileName })}>
              {upload.storageOk === false && upload.recordId && apiConfig?.actorDid ? (
                <Button
                  disabled={repairingUploadIds.includes(upload.id)}
                  onClick={() => repairUploadStorage(upload)}
                  variant="secondary"
                >
                  <Wrench aria-hidden="true" size={18} />
                  {repairingUploadIds.includes(upload.id) ? t(siteLocale, "wallet.fixing") : t(siteLocale, "wallet.fixSave")}
                </Button>
              ) : null}
              {filecoinStorageReady && upload.recordId && shouldShowFilecoinAction(upload) ? (
                <Button
                  disabled={filecoinUploadIds.includes(upload.id)}
                  onClick={() => void storeWalletRecordOnFilecoin(upload)}
                  variant="secondary"
                >
                  <Upload aria-hidden="true" size={18} />
                  {filecoinActionLabel(upload, filecoinUploadIds.includes(upload.id), siteLocale)}
                </Button>
              ) : null}
              {upload.recordId && apiConfig?.actorDid && upload.privacyProfileStatus !== "profiled" ? (
                <Button
                  disabled={upload.privacyProfileStatus === "profiling"}
                  onClick={() => void profileWalletUpload(upload)}
                  variant="secondary"
                >
                  <ShieldCheck aria-hidden="true" size={18} />
                  {upload.privacyProfileStatus === "profiling" ? t(siteLocale, "wallet.profiling") : t(siteLocale, "wallet.generateProof")}
                </Button>
              ) : null}
              {upload.recordId && apiConfig?.actorDid ? (
                <Button
                  disabled={downloadingUploadIds.includes(upload.id)}
                  onClick={() => void downloadDecryptedUpload(upload)}
                  variant="secondary"
                >
                  <Download aria-hidden="true" size={18} />
                  {downloadingUploadIds.includes(upload.id) ? t(siteLocale, "wallet.decrypting") : t(siteLocale, "wallet.downloadDecrypted")}
                </Button>
              ) : null}
              <Button
                onClick={() => (upload.shared ? makePrivate(upload) : allowSharing(upload))}
                variant="secondary"
              >
                {upload.shared ? t(siteLocale, "wallet.makePrivate") : t(siteLocale, "wallet.allowSharing")}
              </Button>
              {upload.recordId && apiConfig?.actorDid ? (
                <Button
                  disabled={deletingUploadIds.includes(upload.id)}
                  onClick={() => void deleteWalletUpload(upload)}
                  variant="secondary"
                >
                  <Trash2 aria-hidden="true" size={18} />
                  {deletingUploadIds.includes(upload.id) ? t(siteLocale, "wallet.deleting") : t(siteLocale, "wallet.delete")}
                </Button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
      </Section>
      <ExportCenterScreen apiConfig={apiConfig} bundles={bundles} setBundles={setBundles} />
    </div>
  );
}
