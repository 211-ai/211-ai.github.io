# Wallet Kubernetes Deployment

These manifests provide a reference Kubernetes deployment for the 211-AI wallet
stack:

- `namespace.yaml`: dedicated namespace.
- `configmap.yaml`: non-secret wallet runtime configuration.
- `secrets.example.yaml`: secret shape to replace per environment.
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
- Replace the deterministic proof backend with the production verifier.
- Move `WALLET_STORAGE_CONFIG` and any provider credentials into a real Secret
  or external secret manager.
- Change the ingress host and storage class to the target cluster settings.

