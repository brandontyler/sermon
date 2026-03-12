# Rescore Operations

Detailed reference for the PSR rescore system. For quick API usage, see memory.md.

## Key Vault & API Details

- Key Vault name: `psr-kv-dev-001` (NOT `psr-vault-dev`)
- Admin key app setting: `ADMIN_KEY` (retrieve via `az functionapp config appsettings list`)
- Header: `x-admin-key: <value>`

## API Formats

```bash
# Pass 4 only (enrichment) — ~60s per sermon
{"sermonIds": ["<id>"], "passes": [4]}

# Scoring passes only (1-3) — ~2-3 min per sermon
{"sermonIds": ["<id>"], "passes": [1,2,3]}

# Auto-detect stale passes — only re-runs passes whose prompt/model changed
{"sermonIds": ["<id>"], "staleOnly": true}
{"all": true, "staleOnly": true}

# Full rescore (backward compatible)
{"all": true}

# Other selective options
{"passes": ["segments"], "all": true}   # re-classify segments only
{"passes": ["summary"], "all": true}    # re-generate summary only
```

## Pass-to-Category Mapping

| Pass | Model | Categories/Fields |
|------|-------|-------------------|
| pass1 | o4-mini | biblicalAccuracy, timeInTheWord, passageFocus |
| pass2 | gpt-5-mini | clarity, application, engagement |
| pass3 | gpt-5-nano | delivery, emotionalRange |
| pass4 | gpt-5-nano | enrichment (biblicalLanguages, churchHistory, illustrations) |
| classify | gpt-5-nano | sermonType, confidence |
| segments | gpt-5-nano | transcript segment types |
| summary | gpt-5-nano | strengths, improvements, summary |

## Staleness Detection

- Each pass has a fingerprint string in `_PASS_FINGERPRINTS` (activities.py ~line 175)
- Fingerprint = model name + pass name + version + description
- Hash stored per-sermon in `passVersions` field in Cosmos
- `staleOnly` compares stored hashes vs current — only re-runs mismatches
- If nothing is stale, returns instantly with zero LLM calls

## When You Change a Prompt

1. Edit the prompt in activities.py
2. Bump the fingerprint string for that pass in `_PASS_FINGERPRINTS` (e.g. `v2026-03-11a` → `v2026-03-11b`)
3. Deploy: `./infra/deploy.sh backend`
4. Restart: `az functionapp restart --name psr-functions-dev --resource-group rg-sermon-rating-dev`
5. Rescore: `{"staleOnly": true, "all": true}` — auto-detects the changed pass

## Key Behaviors

- Composite score only recomputed if passes 1-3 change
- previousScores audit trail only grows if scoring passes change
- Summary auto-regenerates if scoring passes change
- Classification auto-reruns if scoring passes change

## Deploy + Rescore Workflow

### Quick (no active orchestrators, trivial change)

```bash
./infra/deploy.sh backend
az functionapp restart --name psr-functions-dev --resource-group rg-sermon-rating-dev
```

### Full (prompt changes, active orchestrators, or uncertain state)

```bash
# 1. Terminate any running orchestrators
MASTER_KEY=$(az functionapp keys list --name psr-functions-dev --resource-group rg-sermon-rating-dev --query "masterKey" -o tsv)
# List running instances
curl -s "https://psr-functions-dev.azurewebsites.net/runtime/webhooks/durabletask/instances?code=$MASTER_KEY&runtimeStatus=Running&top=10"
# Terminate stale ones
curl -s -X POST "https://psr-functions-dev.azurewebsites.net/runtime/webhooks/durabletask/instances/<id>/terminate?reason=stale&code=$MASTER_KEY"

# 2. Deploy
./infra/deploy.sh backend

# 3. Restart
az functionapp restart --name psr-functions-dev --resource-group rg-sermon-rating-dev

# 4. Wait 30s, warm up
sleep 30 && curl -s "https://psr-functions-dev.azurewebsites.net/api/sermons" > /dev/null && sleep 10

# 5. Rescore single test sermon
# 6. Poll for completion (check rescoredAt timestamp changes)
```

### Gotchas

- **Terminate stale orchestrators BEFORE deploying new code.** Old Durable Functions instances can clog the activity queue.
- **After deploying backend, restart the Function App** — Consumption plan may cache old code.
- **Don't panic at `TaskScheduled`** — Durable Functions history only updates when the activity completes. A rescore can sit at `TaskScheduled` for 3-5 minutes while LLM passes run.
- **Single sermon: ~3-5 min. Full rescore: ~90 min.**
