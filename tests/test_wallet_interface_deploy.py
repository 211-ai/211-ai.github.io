from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


DEPLOY_ROOT = Path(__file__).parent.parent / "wallet_interface" / "deploy"
K8S_ROOT = DEPLOY_ROOT / "kubernetes"
CLOUDFLARE_ROOT = DEPLOY_ROOT / "cloudflare"


def test_wallet_deploy_reference_files_exist() -> None:
    required_files = [
        DEPLOY_ROOT / "Dockerfile.api",
        DEPLOY_ROOT / "Dockerfile.ui",
        DEPLOY_ROOT / "docker-compose.wallet.yml",
        DEPLOY_ROOT / "README.md",
        CLOUDFLARE_ROOT / "README.md",
        CLOUDFLARE_ROOT / "wrangler.toml",
        CLOUDFLARE_ROOT / "src" / "index.ts",
        K8S_ROOT / "README.md",
        K8S_ROOT / "namespace.yaml",
        K8S_ROOT / "configmap.yaml",
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


def test_wallet_kubernetes_manifests_reference_ops_and_persistence() -> None:
    api_manifest = (K8S_ROOT / "api-deployment.yaml").read_text(encoding="utf-8")
    ops_manifest = (K8S_ROOT / "ops-deployment.yaml").read_text(encoding="utf-8")
    pvc_manifest = (K8S_ROOT / "pvc.yaml").read_text(encoding="utf-8")
    config_map = (K8S_ROOT / "configmap.yaml").read_text(encoding="utf-8")
    secrets = (K8S_ROOT / "secrets.example.yaml").read_text(encoding="utf-8")

    assert "wallet-state-pvc" in api_manifest
    assert "wallet-state-pvc" in ops_manifest
    assert "wallet_interface.ops" in ops_manifest
    assert "PersistentVolumeClaim" in pvc_manifest
    assert "secretRef" in api_manifest
    assert "secretRef" in ops_manifest
    assert "WALLET_OPS_ALERT_ON" in config_map
    assert "WALLET_OPS_HEALTH_SHARED_SECRET" in secrets
    assert "WALLET_OPS_ALERT_WEBHOOK_URL" in secrets
    assert "WALLET_OPS_ALERT_BEARER_TOKEN" in secrets
    assert "WALLET_OPS_ALERT_HEADER_NAME" in secrets
    assert "WALLET_OPS_ALERT_HEADER_VALUE" in secrets
    assert "WALLET_PROOF_SERVICE_URL" in secrets
    assert "WALLET_PROOF_VERIFIER_ID" in secrets
    assert "WALLET_PROOF_BEARER_TOKEN" in secrets


def test_wallet_cloudflare_assets_reference_ops_health_and_origin() -> None:
    wrangler = (CLOUDFLARE_ROOT / "wrangler.toml").read_text(encoding="utf-8")
    worker = (CLOUDFLARE_ROOT / "src" / "index.ts").read_text(encoding="utf-8")
    readme = (CLOUDFLARE_ROOT / "README.md").read_text(encoding="utf-8")

    assert 'crons = ["*/5 * * * *"]' in wrangler
    assert "ORIGIN_API_BASE_URL" in worker
    assert "OPS_HEALTH_SHARED_SECRET" in worker
    assert '"/ops/health"' in worker
    assert '"/health"' in worker
    assert "x-wallet-ops-scheduled" in worker
    assert "wrangler deploy" in readme
    assert "Cloudflare Access" in readme


def test_wallet_kubernetes_manifests_validate_when_kubectl_available() -> None:
    if shutil.which("kubectl") is None:
        pytest.skip("kubectl not available; skipping wallet Kubernetes manifest validation")

    for yaml_file in sorted(K8S_ROOT.glob("*.yaml")):
        result = subprocess.run(
            ["kubectl", "apply", "--dry-run=client", "--validate=false", "-f", str(yaml_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if "connect: connection refused" in result.stderr or "couldn't get current server API group list" in result.stderr:
                pytest.skip("kubectl available but no cluster reachable; skipping wallet Kubernetes manifest validation")
            assert False, f"Kubernetes validation failed for {yaml_file.name}: {result.stderr}"
