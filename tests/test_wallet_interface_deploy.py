from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


DEPLOY_ROOT = Path(__file__).parent.parent / "wallet_interface" / "deploy"
K8S_ROOT = DEPLOY_ROOT / "kubernetes"
CLOUDFLARE_ROOT = DEPLOY_ROOT / "cloudflare"
DOCS_ROOT = Path(__file__).parent.parent / "docs"


def test_wallet_deploy_reference_files_exist() -> None:
    required_files = [
        DEPLOY_ROOT / "Dockerfile.api",
        DEPLOY_ROOT / "Dockerfile.ui",
        DEPLOY_ROOT / "docker-compose.wallet.yml",
        DEPLOY_ROOT / "40-runtime-config.sh",
        DEPLOY_ROOT / "nginx.211-ai.com.conf",
        DEPLOY_ROOT / "install_211_ai_nginx.sh",
        DEPLOY_ROOT / "env.production.example",
        DEPLOY_ROOT / "runtime-config.template.json",
        DEPLOY_ROOT / "storage-retention.example.json",
        DOCS_ROOT / "WALLET_OPERATOR_INTEGRATOR_REFERENCE.md",
        DOCS_ROOT / "WALLET_PROOF_VERIFIER_CONTRACT.md",
        DEPLOY_ROOT / "README.md",
        CLOUDFLARE_ROOT / "README.md",
        CLOUDFLARE_ROOT / "wrangler.toml",
        CLOUDFLARE_ROOT / "src" / "index.ts",
        K8S_ROOT / "README.md",
        K8S_ROOT / "namespace.yaml",
        K8S_ROOT / "configmap.yaml",
        K8S_ROOT / "externalsecret.example.yaml",
        K8S_ROOT / "pvc.yaml",
        K8S_ROOT / "api-deployment.yaml",
        K8S_ROOT / "ops-deployment.yaml",
        K8S_ROOT / "ui-deployment.yaml",
        K8S_ROOT / "services.yaml",
        K8S_ROOT / "ingress.yaml",
    ]

    for path in required_files:
        assert path.exists(), f"Missing deployment asset: {path}"


def test_wallet_compose_references_api_ui_and_ops() -> None:
    compose = (DEPLOY_ROOT / "docker-compose.wallet.yml").read_text(encoding="utf-8")
    nginx = (DEPLOY_ROOT / "nginx.conf").read_text(encoding="utf-8")
    host_nginx = (DEPLOY_ROOT / "nginx.211-ai.com.conf").read_text(encoding="utf-8")
    install_script = (DEPLOY_ROOT / "install_211_ai_nginx.sh").read_text(encoding="utf-8")
    dockerfile_api = (DEPLOY_ROOT / "Dockerfile.api").read_text(encoding="utf-8")
    dockerfile_ui = (DEPLOY_ROOT / "Dockerfile.ui").read_text(encoding="utf-8")
    runtime_template = (DEPLOY_ROOT / "runtime-config.template.json").read_text(encoding="utf-8")
    runtime_entrypoint = (DEPLOY_ROOT / "40-runtime-config.sh").read_text(encoding="utf-8")
    env_example = (DEPLOY_ROOT / "env.production.example").read_text(encoding="utf-8")

    assert "wallet-api:" in compose
    assert "wallet-ops:" in compose
    assert "wallet-ui:" in compose
    assert "wallet_interface.ops" in compose
    assert "wallet_interface/deploy/Dockerfile.api" in compose
    assert "wallet_interface/deploy/Dockerfile.ui" in compose
    assert "WALLET_OPS_HEALTH_SHARED_SECRET" in compose
    assert "WALLET_OPS_ALERT_WEBHOOK_URL" in compose
    assert "WALLET_OPS_ALERT_ON" in compose
    assert "WALLET_OPS_ALERT_BEARER_TOKEN" in compose
    assert "WALLET_OPS_ALERT_HEADER_NAME" in compose
    assert "WALLET_OPS_ALERT_HEADER_VALUE" in compose
    assert "WALLET_PROOF_SERVICE_URL" in compose
    assert "WALLET_PROOF_VERIFIER_ID" in compose
    assert "WALLET_PROOF_BEARER_TOKEN" in compose
    assert "WALLET_OPS_HEALTH_SECRET_REF" in compose
    assert "WALLET_OPS_ALERT_SECRET_REF" in compose
    assert "WALLET_PROOF_CREDENTIAL_SECRET_REF" in compose
    assert "WALLET_STORAGE_CREDENTIAL_SECRET_REF" in compose
    assert "WALLET_STORAGE_IPFS_PINNING_POLICY_REF" in compose
    assert "WALLET_STORAGE_FILECOIN_DEAL_POLICY_REF" in compose
    assert "WALLET_STORAGE_S3_LIFECYCLE_POLICY_REF" in compose
    assert "WALLET_BACKUP_PURGE_POLICY_REF" in compose
    assert "WALLET_ALERT_RETENTION_POLICY_REF" in compose
    assert "VITE_WALLET_API_BASE_URL" in compose
    assert "ABBY_RUNTIME_WALLET_API_BASE_URL" in compose
    assert "ABBY_RUNTIME_WALLET_ID" in compose
    assert "ABBY_RUNTIME_FILECOIN_UPLOAD_URL" in compose
    assert '"127.0.0.1:8080:8080"' in compose
    readme = (DEPLOY_ROOT / "README.md").read_text(encoding="utf-8")
    assert "--validate-proof-contract" in readme
    assert "--validate-target-signoff-packet" in readme
    assert "storage-retention.example.json" in readme
    assert "211-ai.com" in readme
    assert "abby.network" in readme
    assert "abetterbridgetoyou.com" in readme
    assert "ABBY_RUNTIME_*" in readme
    assert '"python-multipart>=0.0.9"' in dockerfile_api
    assert "ARG VITE_WALLET_API_BASE_URL=same-origin" in dockerfile_ui
    assert "runtime-config.template.json" in dockerfile_ui
    assert "40-runtime-config.sh" in dockerfile_ui
    assert "server_name 211-ai.com www.211-ai.com abby.network www.abby.network abetterbridgetoyou.com www.abetterbridgetoyou.com;" in nginx
    assert "proxy_pass http://wallet-api:8000/wallets;" in nginx
    assert "proxy_pass http://wallet-api:8000/ops/;" in nginx
    assert "proxy_pass http://wallet-api:8000/analytics/;" in nginx
    assert "listen 443 ssl http2;" in host_nginx
    assert "ssl_certificate /etc/letsencrypt/live/211-ai.com/fullchain.pem;" in host_nginx
    assert "ssl_certificate /etc/letsencrypt/live/abby.network/fullchain.pem;" in host_nginx
    assert "ssl_certificate /etc/letsencrypt/live/abetterbridgetoyou.com/fullchain.pem;" in host_nginx
    assert "proxy_pass http://127.0.0.1:8080;" in host_nginx
    assert 'TARGET_AVAILABLE="/etc/nginx/sites-available/211-ai.com.conf"' in install_script
    assert "nginx -t" in install_script
    assert "systemctl reload nginx" in install_script
    assert '"walletApi": {' in runtime_template
    assert '${ABBY_RUNTIME_WALLET_API_BASE_URL}' in runtime_template
    assert '${ABBY_RUNTIME_FILECOIN_UPLOAD_URL}' in runtime_template
    assert "envsubst" in runtime_entrypoint
    assert "/usr/share/nginx/html/runtime-config.json" in runtime_entrypoint
    assert "ABBY_RUNTIME_WALLET_API_BASE_URL=same-origin" in env_example
    assert "ABBY_RUNTIME_WALLET_ID=" in env_example
    assert "ABBY_RUNTIME_FILECOIN_UPLOAD_URL=" in env_example


def test_wallet_kubernetes_manifests_reference_ops_and_persistence() -> None:
    api_manifest = (K8S_ROOT / "api-deployment.yaml").read_text(encoding="utf-8")
    ops_manifest = (K8S_ROOT / "ops-deployment.yaml").read_text(encoding="utf-8")
    pvc_manifest = (K8S_ROOT / "pvc.yaml").read_text(encoding="utf-8")
    config_map = (K8S_ROOT / "configmap.yaml").read_text(encoding="utf-8")
    secrets = (K8S_ROOT / "secrets.example.yaml").read_text(encoding="utf-8")
    external_secret = (K8S_ROOT / "externalsecret.example.yaml").read_text(encoding="utf-8")

    assert "wallet-state-pvc" in api_manifest
    assert "wallet-state-pvc" in ops_manifest
    assert "wallet_interface.ops" in ops_manifest
    assert "PersistentVolumeClaim" in pvc_manifest
    assert "secretRef" in api_manifest
    assert "secretRef" in ops_manifest
    assert "WALLET_OPS_ALERT_ON" in config_map
    assert "WALLET_STORAGE_IPFS_PINNING_POLICY_REF" in config_map
    assert "WALLET_STORAGE_FILECOIN_DEAL_POLICY_REF" in config_map
    assert "WALLET_STORAGE_S3_LIFECYCLE_POLICY_REF" in config_map
    assert "WALLET_BACKUP_PURGE_POLICY_REF" in config_map
    assert "WALLET_ALERT_RETENTION_POLICY_REF" in config_map
    assert "WALLET_OPS_HEALTH_SHARED_SECRET" in secrets
    assert "WALLET_OPS_ALERT_WEBHOOK_URL" in secrets
    assert "WALLET_OPS_ALERT_BEARER_TOKEN" in secrets
    assert "WALLET_OPS_ALERT_HEADER_NAME" in secrets
    assert "WALLET_OPS_ALERT_HEADER_VALUE" in secrets
    assert "WALLET_PROOF_SERVICE_URL" in secrets
    assert "WALLET_PROOF_VERIFIER_ID" in secrets
    assert "WALLET_PROOF_BEARER_TOKEN" in secrets
    assert "WALLET_OPS_HEALTH_SECRET_REF" in secrets
    assert "WALLET_OPS_ALERT_SECRET_REF" in secrets
    assert "WALLET_PROOF_CREDENTIAL_SECRET_REF" in secrets
    assert "WALLET_STORAGE_CREDENTIAL_SECRET_REF" in secrets
    assert "kind: ExternalSecret" in external_secret
    assert "wallet-production-secrets" in external_secret
    assert "WALLET_OPS_ALERT_WEBHOOK_URL" in external_secret
    assert "WALLET_STORAGE_CONFIG" in external_secret
    assert "WALLET_PROOF_CREDENTIAL_SECRET_REF" in external_secret


def test_wallet_cloudflare_assets_reference_ops_health_and_origin() -> None:
    wrangler = (CLOUDFLARE_ROOT / "wrangler.toml").read_text(encoding="utf-8")
    worker = (CLOUDFLARE_ROOT / "src" / "index.ts").read_text(encoding="utf-8")
    readme = (CLOUDFLARE_ROOT / "README.md").read_text(encoding="utf-8")

    assert 'crons = ["*/5 * * * *"]' in wrangler
    assert "ORIGIN_API_BASE_URL" in worker
    assert "OPS_HEALTH_SHARED_SECRET" in worker
    assert "CF_ACCESS_CLIENT_ID" in worker
    assert "ORIGIN_AUTH_HEADER_NAME" in worker
    assert "methodAllowed" in worker
    assert "Method not allowed" in worker
    assert '"/ops/health"' in worker
    assert '"/health"' in worker
    assert "x-wallet-ops-scheduled" in worker
    assert "wrangler deploy" in readme
    assert "Cloudflare Access" in readme


def test_wallet_storage_retention_template_maps_target_provider_controls() -> None:
    payload = json.loads((DEPLOY_ROOT / "storage-retention.example.json").read_text(encoding="utf-8"))
    mapping = payload["retention_mapping"]
    storage_config = payload["wallet_storage_config_example"]

    assert payload["schema"] == "wallet-storage-retention-target-v1"
    assert "storage_credentials" in payload["secret_manager_refs"]
    assert {mirror["type"] for mirror in storage_config["mirrors"]} == {"ipfs", "s3", "filecoin"}
    assert "ipfs_pinning" in mapping
    assert "filecoin_deal_expiration" in mapping
    assert "s3_lifecycle" in mapping
    assert "backup_purge" in mapping
    assert "alert_retention" in mapping
    assert "repair_validation" in payload
    rendered = json.dumps(payload)
    assert "plaintext" in rendered
    assert "secret-manager://" in rendered


def test_wallet_kubernetes_manifests_validate_when_kubectl_available() -> None:
    if shutil.which("kubectl") is None:
        pytest.skip("kubectl not available; skipping wallet Kubernetes manifest validation")

    for yaml_file in sorted(K8S_ROOT.glob("*.yaml")):
        if yaml_file.name == "externalsecret.example.yaml":
            continue
        result = subprocess.run(
            ["kubectl", "apply", "--dry-run=client", "--validate=false", "-f", str(yaml_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if "connect: connection refused" in result.stderr or "couldn't get current server API group list" in result.stderr:
                pytest.skip("kubectl available but no cluster reachable; skipping wallet Kubernetes manifest validation")
            assert False, f"Kubernetes validation failed for {yaml_file.name}: {result.stderr}"
