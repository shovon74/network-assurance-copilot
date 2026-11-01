---
id: RB-CORE-002
title: Core SGW GTP-U User Plane Tunnel Drop
domain: CORE
risk_level: medium
safe_to_automate: false
recommended_action: restart_service
---

# RB-CORE-002: Core SGW GTP-U User Plane Tunnel Drop

## Symptoms
- `GTPU_PATH_FAILURE` and `BEARER_DROP_HIGH` alarms on the Serving Gateway (SGW) user plane.
- `CORE-MME-01` control-plane `signaling_load_pct` remains normal (~40%) with no `SIGNALING_OVERLOAD` or `S1AP_REJECT_RATE_HIGH` alarms.

## Likely causes
- Stuck GTP-U echo responder thread on an SGW-U line card or S1-U routing table mismatch.

## Diagnostic steps
1. Verify alarms reference `GTPU_PATH_FAILURE` rather than MME `SIGNALING_OVERLOAD` / `S1AP_REJECT_RATE_HIGH` (`RB-CORE-001`).
2. Check `signaling_load_pct` on `CORE-MME-01` to confirm control-plane load is normal.

## Remediation
- Recommend `restart_service` on the SGW-U GTP-U worker daemon (`risk_level: medium`, `safe_to_automate: false`, requires human operator approval).

## Rollback/escalation
- If GTP-U path failures persist after service restart, drain the SGW-U blade and escalate to Packet Core engineering.
