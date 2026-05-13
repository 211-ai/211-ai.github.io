# Wallet Kubernetes Deployment

These manifests provide a reference Kubernetes deployment for the 211-AI wallet
stack:

- `namespace.yaml`: dedicated namespace.
- `configmap.yaml`: non-secret wallet runtime configuration.
- `secrets.example.yaml`: secret shape to replace per environment.
- `externalsecret.example.yaml`: optional External Secrets Operator mapping for
  environment-specific secret managers.
- `../storage-retention.example.json`: target IPFS/Filecoin/S3 retention and
  repair-evidence mapping template.
- `pvc.yaml`: persistent storage for wallet snapshots and encrypted blob state.
- `api-deployment.yaml`: FastAPI wallet API deployment.
- `ops-deployment.yaml`: long-running ops-health worker.
- `ui-deployment.yaml`: static UI deployment.
- `services.yaml`: cluster services for API and UI.
- `ingress.yaml`: example ingress routing.

Apply in order:

```bash
kubectl apply -f wallet_interface/deploy/kubernetes/namespace.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/configmap.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/pvc.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/api-deployment.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/ops-deployment.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/ui-deployment.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/services.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/ingress.yaml
```

Before production use:

- Replace `wallet-interface-api:latest` and `wallet-interface-ui:latest` with
  registry-published image references.
- Configure the production verifier by setting
  `WALLET_PROOF_BACKEND=http-location-region` plus
  `WALLET_PROOF_SERVICE_URL`, `WALLET_PROOF_VERIFIER_ID`,
  `WALLET_PROOF_SYSTEM`, `WALLET_PROOF_PROVE_PATH`,
  `WALLET_PROOF_DISTANCE_PROVE_PATH`, and verifier auth secrets.
- Move `WALLET_STORAGE_CONFIG` and any provider credentials into a real Secret
  or external secret manager. `externalsecret.example.yaml` provides the
  expected key mapping when using External Secrets Operator.
- When `WALLET_STORAGE_CONFIG` includes an `ipfs` mirror, also set
  `IPFS_DATASETS_PY_ENABLE_IPFS_HTTPAPI=1` and `IPFS_HOST` so the API and ops
  pods can reach a trusted Kubo HTTP API. The checked-in examples use a local
  primary replica plus a pinned IPFS mirror because raw `filecoin` mirrors
  still require a runtime backend injection path outside these manifests.
- Map `WALLET_STORAGE_RETENTION_POLICY_REF`,
  `WALLET_STORAGE_IPFS_PINNING_POLICY_REF`,
  `WALLET_STORAGE_FILECOIN_DEAL_POLICY_REF`,
  `WALLET_STORAGE_S3_LIFECYCLE_POLICY_REF`,
  `WALLET_BACKUP_PURGE_POLICY_REF`, and
  `WALLET_ALERT_RETENTION_POLICY_REF` to target evidence IDs before launch.
  The completed mapping should prove that encrypted replicas, IPFS pins,
  Filecoin deals, S3 lifecycle rules, backups, and alert-router payloads all
  expire or purge under the approved retention policy.
- Set the non-secret reference keys `WALLET_OPS_HEALTH_SECRET_REF`,
  `WALLET_OPS_ALERT_SECRET_REF`, `WALLET_PROOF_CREDENTIAL_SECRET_REF`, and
  `WALLET_STORAGE_CREDENTIAL_SECRET_REF` to the target secret-manager paths so
  readiness reports and signoff packets can identify credential sources without
  printing secret values.
- Set `WALLET_OPS_HEALTH_SHARED_SECRET` for the API and any edge caller, and
  set `WALLET_OPS_ALERT_WEBHOOK_URL` if ops-health alerts should route to an
  incident system.
- Set `WALLET_OPS_ALERT_BEARER_TOKEN` or a custom
  `WALLET_OPS_ALERT_HEADER_NAME` / `WALLET_OPS_ALERT_HEADER_VALUE` pair if the
  alert receiver requires webhook authentication.
- Set `WALLET_API_CORS_ORIGINS` to the deployed UI origin when API and UI are
  served from different browser origins. Leave it empty when ingress routes both
  behind the same origin.
- Change the ingress host and storage class to the target cluster settings.
- Run `python -m wallet_interface.ops --validate-production-readiness` and
  `python -m wallet_interface.ops --validate-target-signoff-packet` from the
  deployed ops environment before live wallet data. The readiness report must
  show `storage_retention_controls=ok` and `storage_repair_safety=ok`.
- Run `/ops/health?verify_storage=true` and the wallet or record storage repair
  endpoint after any replica outage. Archive only ciphertext hashes, storage
  types, failure counts, and repair counts; never archive wallet plaintext,
  proof witnesses, precise coordinates, tokens, or credential values.
