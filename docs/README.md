# 211-AI Documentation Index

This directory holds the repository's architecture notes, product plans,
security references, runbooks, and implementation backlogs. Use this file as
the starting point for the current document set.

## Core platform docs

| Document | Focus |
| --- | --- |
| `AGENTIC_SCRAPER_DESIGN.md` | Persistent crawl, ETL, queueing, and optional web-archiving design for the 211 scraper lane. |
| `211_SERVICE_NAVIGATION_PORTAL_PLAN.md` | Product and implementation direction for the service-navigation portal built on the 211 corpus. |
| `211_SERVICE_NAVIGATION_PORTAL_RUNBOOK.md` | Operational notes for the service-navigation portal lane. |
| `211_SERVICE_NAVIGATION_PORTAL_THREAT_MODEL.md` | Threat model for the portal search and user workflow surface. |
| `211_SERVICE_NAVIGATION_PORTAL_TODO.md` | Executable backlog for the portal lane. |
| `AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md` | Plan for Abby's in-app agent/chat controller over the GraphRAG corpus and UI actions. |
| `AI_AGENT_CHAT_RUNBOOK.md` | Operational guidance for the agent-chat implementation lane. |
| `AI_AGENT_CHAT_THREAT_MODEL.md` | Threat model for the agent/chat experience. |
| `AI_AGENT_CHAT_ACCESSIBILITY_REVIEW.md` | Accessibility and mobile review for the agent/chat experience. |
| `AI_AGENT_CHAT_IMPLEMENTATION_TODO.md` | Executable backlog for the agent-chat lane. |
| `PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md` | Port and hardening plan for the browser GraphRAG/runtime stack adapted from Portland Laws. |
| `PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_TODO.md` | Executable backlog for the GraphRAG parity lane. |

## Wallet and security docs

| Document | Focus |
| --- | --- |
| `UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md` | Canonical wallet implementation plan and current production-gate status. |
| `UCAN_ZK_DATA_WALLET_TODO.md` | Executable backlog for the wallet lane. |
| `WALLET_OPERATOR_INTEGRATOR_REFERENCE.md` | Stable operator and integrator reference for the wallet API, CLI, MCP, and deployment surface. |
| `WALLET_OPERATIONS_RUNBOOK.md` | Wallet operations, health checks, and response procedures. |
| `WALLET_PRODUCTION_DECISIONS_ADR.md` | Recorded production decisions for the wallet lane. |
| `WALLET_SECURITY_ARCHITECTURE_ADR.md` | Security architecture decisions for wallet data, grants, and operations. |
| `WALLET_UCAN_PROFILE.md` | Repository UCAN token/profile contract. |
| `WALLET_PROOF_VERIFIER_CONTRACT.md` | HTTP contract for the proof verifier integration. |
| `WALLET_RETENTION_POLICY.md` | Retention mapping and evidence expectations for encrypted wallet storage. |
| `WALLET_TARGET_PRODUCTION_SIGNOFF.md` | Human-facing target signoff checklist for production readiness. |
| `WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json` | Machine-readable template for the target signoff packet. |
| `DOCUMENT_WALLET_IMPLEMENTATION_PLAN.md` | Historical context for the older document-wallet lane; superseded by the wallet plan above. |

## Abby product and UX docs

| Document | Focus |
| --- | --- |
| `Abby Requirements.md` | Product requirements and requirements capture for Abby. |
| `ABBY_PRODUCT_IA_AND_WIREFRAMES.md` | Information architecture and wireframe notes. |
| `ABBY_DESIGN_SYSTEM_FOUNDATION.md` | Abby design-system primitives and shared UX rules. |
| `ABBY_ACCESSIBILITY_SAFETY_REVIEW.md` | Accessibility and safety review guidance for Abby UI work. |
| `ABBY_HANDOFF_CONTRACTS_AND_GOVERNANCE.md` | Product handoff contracts and governance expectations. |
| `ABBY_UI_UX_AGENT_TODO.md` | Abby UI/UX implementation backlog. |
| `abby notes 2.md` | Detailed working notes from Abby iteration. |
| `abby notes 3.md` | Additional working notes from Abby iteration. |
| `abby notes 4.md` | Additional Abby working notes and handoff context. |

## Related docs outside this directory

| Document | Focus |
| --- | --- |
| `../wallet_interface/README.md` | Wallet application-layer overview and API/runtime guidance. |
| `../wallet_interface/deploy/README.md` | Docker/Compose deployment reference for wallet API, UI, and ops worker. |
| `../wallet_interface/deploy/cloudflare/README.md` | Cloudflare edge reference for health and ops-health proxying. |
| `../wallet_interface/deploy/kubernetes/README.md` | Kubernetes deployment reference manifests and required environment. |
| `../wallet_interface/ui/README.md` | Abby UI environment, build, test, and GitHub Pages guidance. |
| `../wallet_interface/ui/docs/multimodal-ui-review.md` | Visual review and refinement loop for the UI lane. |
| `../wallet_interface/ui/docs/magic-login-github-pages.md` | GitHub Pages-safe magic-login guidance. |
| `../wallet_interface/ui/docs/wallet-filecoin-storage.md` | UI/storage notes for IPFS/Filecoin-backed wallet storage. |
| `../wallet_interface/ui/docs/abby3-agent-d-copy-qa.md` | Copy/QA handoff for Abby Notes 3 work. |

## How to navigate this repo's docs

- Start with the plan document for the lane you are changing.
- Use the matching `TODO` file when the lane has an executable backlog.
- Use runbooks and ADRs for deployment, security, and operational decisions.
- Use the wallet operator reference and deployment READMEs when integrating the
  API/UI outside local development.
