from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

DEPLOY_ROOT = Path(__file__).parent.parent / "wallet_interface" / "deploy"
K8S_ROOT = DEPLOY_ROOT / "kubernetes"
CLOUDFLARE_ROOT = DEPLOY_ROOT / "cloudflare"
DOCS_ROOT = Path(__file__).parent.parent / "docs"
REPO_ROOT = Path(__file__).parent.parent
UI_ROOT = REPO_ROOT / "wallet_interface" / "ui"
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "abby-ui-pages.yml"


def test_wallet_deploy_reference_files_exist() -> None:
    required_files = [
        DEPLOY_ROOT / "Dockerfile.api",
        DEPLOY_ROOT / "Dockerfile.ui",
        DEPLOY_ROOT / "docker-compose.wallet.yml",
        DEPLOY_ROOT / "env.production.example",
        DEPLOY_ROOT / "storage-retention.example.json",
        DOCS_ROOT / "specs" / "WALLET_OPERATOR_INTEGRATOR_REFERENCE.md",
        DOCS_ROOT / "specs" / "WALLET_PROOF_VERIFIER_CONTRACT.md",
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
    readme = (DEPLOY_ROOT / "README.md").read_text(encoding="utf-8")
    assert "--validate-proof-contract" in readme
    assert "--validate-target-signoff-packet" in readme
    assert "storage-retention.example.json" in readme


def test_wallet_voice_deploy_defaults_use_publicus_batch_primary() -> None:
    compose = (DEPLOY_ROOT / "docker-compose.wallet.yml").read_text(encoding="utf-8")
    production_env = (DEPLOY_ROOT / "env.production.example").read_text(encoding="utf-8")

    for rendered in (compose, production_env):
        assert "https://publicus-indextts-2-demo.hf.space" in rendered
        assert "https://indexteam-indextts-2-demo.hf.space" in rendered
        assert "Publicus/IndexTTS-2-Demo" in rendered
        assert "IndexTeam/IndexTTS-2-Demo" in rendered
        assert "WALLET_INDEXTTS_BATCH_API_NAME" in rendered
        assert "gen_batch" in rendered
        assert "WALLET_INDEXTTS_BATCH_ENABLED" in rendered
        assert "WALLET_INDEXTTS_ENDPOINT_TIMEOUT_SECONDS" in rendered
        assert "IPFS_ACCELERATE_PY_ABBY_INDEXTTS_URLS" in rendered
        assert "IPFS_ACCELERATE_PY_ABBY_INDEXTTS_REFERENCE_AUDIO" in rendered

    assert (
        "WALLET_INDEXTTS_SPACE_URL=https://publicus-indextts-2-demo.hf.space"
        in production_env
    )
    assert "WALLET_INDEXTTS_BATCH_FN_INDEX=" in production_env
    assert "WALLET_INDEXTTS_ENDPOINT_TIMEOUT_SECONDS=95" in production_env
    assert (
        "WALLET_INDEXTTS_ENDPOINT_TIMEOUT_SECONDS: "
        "${WALLET_INDEXTTS_ENDPOINT_TIMEOUT_SECONDS:-95}"
    ) in compose
    assert (
        "WALLET_INDEXTTS_BATCH_FN_INDEX: ${WALLET_INDEXTTS_BATCH_FN_INDEX:-}"
        in compose
    )
    assert "IPFS_ACCELERATE_PY_ABBY_INDEXTTS_TIMEOUT_SECONDS=900" in production_env
    assert "IPFS_DATASETS_VOICE_REPLY_PROVIDER_KIND=remote-proxy" in production_env
    assert (
        "IPFS_DATASETS_VOICE_PROXY_INFER_URL="
        "http://wallet-api:8000/voice/indextts/infer"
    ) in production_env
    assert (
        "IPFS_ACCELERATE_PY_ABBY_INDEXTTS_TIMEOUT_SECONDS: "
        "${IPFS_ACCELERATE_PY_ABBY_INDEXTTS_TIMEOUT_SECONDS:-900}"
    ) in compose
    assert (
        "IPFS_DATASETS_VOICE_REPLY_PROVIDER_KIND: "
        "${IPFS_DATASETS_VOICE_REPLY_PROVIDER_KIND:-remote-proxy}"
    ) in compose


def test_precomputed_audio_runtime_config_is_effective_and_explicit() -> None:
    template = json.loads(
        (DEPLOY_ROOT / "runtime-config.template.json").read_text(encoding="utf-8")
    )
    startup_script = (DEPLOY_ROOT / "40-runtime-config.sh").read_text(
        encoding="utf-8"
    )
    dockerfile = (DEPLOY_ROOT / "Dockerfile.ui").read_text(encoding="utf-8")
    compose = (DEPLOY_ROOT / "docker-compose.wallet.yml").read_text(
        encoding="utf-8"
    )
    config_map = (K8S_ROOT / "configmap.yaml").read_text(encoding="utf-8")
    ui_deployment = (K8S_ROOT / "ui-deployment.yaml").read_text(encoding="utf-8")
    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")
    ui_package = json.loads((UI_ROOT / "package.json").read_text(encoding="utf-8"))

    assert template["precomputedAudio"]["manifestUrl"] == (
        "${ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL}"
    )
    assert 'export ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL="' in startup_script
    assert "/resolve/[0-9a-fA-F]{40,64}/" in startup_script
    assert "${ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL}" in startup_script
    assert "runtime-config.template.json /opt/abby/runtime-config.template.json" in dockerfile
    assert "40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "@rollup/rollup-linux-x64-musl" not in ui_package["devDependencies"]
    assert "ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL:" in compose
    assert "WALLET_ABBY_VOICE_RUNTIME_MANIFEST_URL:" in compose
    assert "WALLET_ABBY_VOICE_RUNTIME_MANIFEST_TIMEOUT_SECONDS:-15" in compose
    assert "WALLET_ABBY_VOICE_RUNTIME_MANIFEST_RETRY_SECONDS:-60" in compose
    assert 'ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL: ""' in config_map
    assert 'WALLET_ABBY_VOICE_RUNTIME_MANIFEST_URL: ""' in config_map
    assert 'WALLET_ABBY_VOICE_RUNTIME_MANIFEST_TIMEOUT_SECONDS: "15"' in config_map
    assert 'WALLET_ABBY_VOICE_RUNTIME_MANIFEST_RETRY_SECONDS: "60"' in config_map
    assert "key: ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL" in ui_deployment
    assert "vars.ABBY_PAGES_PRECOMPUTED_AUDIO_MANIFEST_URL" in workflow
    assert "configure_precomputed_audio_runtime.mjs" in workflow
    assert "resolve/main" not in template["precomputedAudio"]["manifestUrl"]


def test_precomputed_audio_runtime_shell_rejects_mutable_hf_refs(
    tmp_path: Path,
) -> None:
    if shutil.which("envsubst") is None:
        pytest.skip("envsubst is unavailable")

    script = DEPLOY_ROOT / "40-runtime-config.sh"
    syntax = subprocess.run(
        ["sh", "-n", str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert syntax.returncode == 0, syntax.stderr

    pinned_revision = "a" * 40
    pinned_url = (
        "https://huggingface.co/datasets/Publicus/211-abby-tts/resolve/"
        f"{pinned_revision}/data/abby_voice_v2/release-1/metadata/"
        "runtime-precomputed-audio-manifest.json"
    )
    pinned_output = tmp_path / "runtime-config.pinned.json"
    base_env = os.environ.copy()
    base_env.update(
        {
            "ABBY_RUNTIME_CONFIG_TEMPLATE_PATH": str(
                DEPLOY_ROOT / "runtime-config.template.json"
            ),
            "ABBY_RUNTIME_CONFIG_OUTPUT_PATH": str(pinned_output),
            "ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL": pinned_url,
        }
    )
    accepted = subprocess.run(
        ["sh", str(script)],
        env=base_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stderr
    assert json.loads(pinned_output.read_text(encoding="utf-8"))[
        "precomputedAudio"
    ]["manifestUrl"] == pinned_url

    mutable_output = tmp_path / "runtime-config.mutable.json"
    mutable_env = {
        **base_env,
        "ABBY_RUNTIME_CONFIG_OUTPUT_PATH": str(mutable_output),
        "ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL": (
            "https://huggingface.co/datasets/Publicus/211-abby-tts/"
            "resolve/main/manifest.json"
        ),
    }
    rejected = subprocess.run(
        ["sh", str(script)],
        env=mutable_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode != 0
    assert "must pin a 40-64 character Hugging Face commit SHA" in rejected.stderr
    assert not mutable_output.exists()

    query_bypass_env = {
        **mutable_env,
        "ABBY_RUNTIME_PRECOMPUTED_AUDIO_MANIFEST_URL": (
            "https://huggingface.co/datasets/Publicus/211-abby-tts/"
            f"resolve/main/manifest.json?decoy=/resolve/{pinned_revision}/"
        ),
    }
    query_bypass = subprocess.run(
        ["sh", str(script)],
        env=query_bypass_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert query_bypass.returncode != 0


def test_pages_precomputed_audio_configurator() -> None:
    if shutil.which("node") is None:
        pytest.skip("node is unavailable")

    result = subprocess.run(
        [
            "node",
            "--test",
            "scripts/configure_precomputed_audio_runtime.test.mjs",
        ],
        cwd=UI_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


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
