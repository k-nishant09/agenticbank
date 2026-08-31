# scripts/internal/ — Platform-specific internal scripts

These scripts are **not part of the public setup workflow**. They contain deployment-specific
logic tied to the TADN on-prem CPD instance (direct DB access, pod exec, specific UUIDs).

| Script | Purpose |
|---|---|
| `redeploy_and_test.py` | Full DB-level redeploy + E2E test (run inside archer pod) |
| `execute_agent.py` | Direct agent invocation with hardcoded UUIDs (TADN dev tool) |
| `diagnose_run.py` | Run diagnostics and step-history dump |
| `patch_agents.py` | One-off patch script used during initial deployment |
| `deploy_all_agents.py` | Batch deploy via uvx loop (superseded by `../deploy.sh`) |
| `deploy_qwen_update.py` | One-off Qwen model-gateway migration script |
| `redeploy_with_qwen.py` | Redeploy with Qwen virtual-model config |

These scripts are intentionally kept out of the main `scripts/` folder as they are not
portable and should not be run by external users.
