---
id: RB-CORE-003
title: Core HSS Diameter S6a Authentication Latency
domain: CORE
risk_level: medium
safe_to_automate: false
recommended_action: clear_stuck_session
---

# RB-CORE-003: Core HSS Diameter S6a Authentication Latency

## Symptoms
- `DIAMETER_TIMEOUT` and `S6A_AUTH_FAILURE` alarms between MME and Home Subscriber Server (HSS).
- MME CPU (`CPU_HIGH`) is normal and `signaling_load_pct` stays near 40-50%, without `SIGNALING_OVERLOAD`.

## Likely causes
- Stale SCTP association stream congestion on the Diameter Routing Agent (DRA) or HSS database query lock.

## Diagnostic steps
1. Check for `DIAMETER_TIMEOUT` and `S6A_AUTH_FAILURE` alarms.
2. Differentiate from `RB-CORE-001` by verifying that `SIGNALING_OVERLOAD` is absent and `signaling_load_pct` on `CORE-MME-01` has not ramped above 90%.

## Remediation
- Recommend `clear_stuck_session` on the Diameter peer pool or escalate to Core Subscriber Data management if HSS backend latency exceeds 500 ms.

## Rollback/escalation
- Fail over S6a traffic to the geo-redundant mate HSS if Diameter timeouts continue for more than 5 minutes.
