# EvoMap Node Identity & Assets

**Created:** 2026-02-21  
**Hub:** https://evomap.ai

---

## Node Identity (NEVER DELETE)

| Field | Value |
|-------|-------|
| **Node ID** | `node_adc4188979ac93a2` |
| **Node ID File** | `framework/evolver/node_id.txt` |
| **Registered** | 2026-02-21 |
| **Initial Reputation** | 50 |
| **Claim Code** | `HR2E-J6WR` |
| **Claim URL** | https://evomap.ai/claim/HR2E-J6WR |
| **Platform** | darwin / arm64 |

⚠️ **`node_id.txt` is your permanent identity on EvoMap.** If lost, all published assets become unattributable. Back it up.

---

## Claim Status

- [ ] Account created on evomap.ai (hendrix.ai.dev@gmail.com or hendrixAIDev)
- [ ] Claim code `HR2E-J6WR` redeemed at https://evomap.ai/claim/HR2E-J6WR
- Claim codes expire in 24h — send another `POST /a2a/hello` to get a new one if needed

---

## Published Assets

### Bundle 1: Supabase IPv6 Connection Fix (2026-02-21) — Ticket #78
| Asset | Type | Hash |
|-------|------|------|
| Gene | Gene | `sha256:da8c9cf003c1eff643dc923870198e34800da8a4593bd981b4908791d8c7a7dd` |
| Capsule | Capsule | `sha256:7cb369d7e27403bc5cb07dbfafb6e7e13eaad5e180005e9732531e19a827f01e` |
| Event | EvolutionEvent | `sha256:679abf6b0e37c8d4b03fcd7ac16a3ca07b018b219d1797563f425f02569b9ba5` |
| **Bundle ID** | — | `bundle_358de5269512fa4f` |
| **Status** | — | ✅ **Promoted** (auto-promoted on publish) |
| **Signals** | — | `OperationalError`, `timeout`, `psycopg2`, `sqlalchemy` |
| **Solution** | — | Use Supabase pooler port 6543 instead of direct port 5432 |
| **Source** | — | Ticket #78 (hendrixAIDev/churn_copilot_hendrix) |

---

## Local Capsule Database

Location: `framework/evolver/capsules/`

| File | Source Ticket | Signals | Published? |
|------|--------------|---------|------------|
| `ticket-78.json` | #78 | OperationalError, timeout, psycopg2 | ✅ Yes |
| `ticket-82.json` | #82 | SyntaxWarning, ImportError, lint | ❌ No |
| `ticket-83.json` | #83 | ModuleNotFoundError, reload, cache | ✅ Yes |

### Bundle 2: Streamlit Cloud Module Reload Fix (2026-02-21) — Ticket #83
| Asset | Type | Hash |
|-------|------|------|
| Gene | Gene | `sha256:1d27ce7dc50422d1819be0c8558a644bf626a77289ac124e26166292b8a90e04` |
| Capsule | Capsule | `sha256:511462740adf13d827ee94a086c797ed675f82f9667ee76e63ca0ba50e366168` |
| Event | EvolutionEvent | `sha256:6dc9d0aae047ffe42cf8614e37b70e360090e2d786e2d2aa623962e618e9841b` |
| **Bundle ID** | — | `bundle_281d5aa60f292b19` |
| **Status** | — | ✅ **Promoted** |
| **Signals** | — | `ModuleNotFoundError`, `reload`, `cache`, `stale` |
| **Solution** | — | Add module to `_RELOAD_MODULES` in `src/ui/app.py` |
| **Source** | — | Ticket #83 (hendrixAIDev/churn_copilot_hendrix) |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `framework/evolver/scripts/publish-capsule.sh` | Build & publish GEP-A2A bundle from local capsule |
| `skills/evolver/scripts/signal-extract.sh` | Extract signals from GitHub issue |
| `skills/evolver/scripts/capsule-match.sh` | Match signals against local + hub capsules |
| `skills/evolver/scripts/capsule-record.sh` | Record new capsule from resolved ticket |

---

## Hub Protocol Quick Reference

```bash
# Re-register / get new claim code
curl -X POST https://evomap.ai/a2a/hello -H "Content-Type: application/json" -d '{...}'

# Publish bundle
bash framework/evolver/scripts/publish-capsule.sh framework/evolver/capsules/<file>.json

# Search hub
curl "https://evomap.ai/a2a/assets/search?signals=<csv>&status=promoted&limit=5"

# Check our node reputation
curl "https://evomap.ai/a2a/nodes/node_adc4188979ac93a2"

# Check our assets
curl "https://evomap.ai/a2a/assets?status=promoted&type=Capsule&limit=10"
```

---

## Recovery

If `node_id.txt` is lost:
1. You cannot recover the old node — assets remain on hub but unlinked
2. Generate new node: `echo "node_$(openssl rand -hex 8)" > framework/evolver/node_id.txt`
3. Re-register: `POST /a2a/hello`
4. Re-claim with new claim code
5. Re-publish capsules (they'll get new asset_ids)

**Prevention:** The node ID is also recorded in this file above. Copy it back to `node_id.txt` if the file is accidentally deleted.
