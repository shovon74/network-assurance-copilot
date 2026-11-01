---
id: RB-CORE-001
title: Core MME S1AP Signaling Storm and CPU Overload
domain: CORE
risk_level: low
safe_to_automate: true
recommended_action: clear_stuck_session
---

# RB-CORE-001: Core MME S1AP Signaling Storm and CPU Overload

## Symptoms
- Major `SIGNALING_OVERLOAD` and `CPU_HIGH` alarms on the core Mobility Management Entity (`CORE-MME-01`), followed by multiple `S1AP_REJECT_RATE_HIGH` (major) alarms.
- `signaling_load_pct` KPI on `CORE-MME-01` ramps sharply from baseline (~40%) up to ~96-99%.
- RAN site throughput and PRB metrics remain near baseline unless S1AP attach rejections cascade.

## Likely causes
- Hung S1AP/NAS signaling state machines or mass IoT/UE registration retry storm overwhelming MME signaling processors (`root_cause: core_signaling_overload`).
- Stale bearer context table exhaustion on `CORE-MME-01` causing high CPU and S1AP overload control rejections.

## Diagnostic steps
1. Inspect alarms on `CORE-MME-01` for `SIGNALING_OVERLOAD`, `CPU_HIGH`, and repeated `S1AP_REJECT_RATE_HIGH`.
2. Query `get_kpi_trend` on `CORE-MME-01` for `signaling_load_pct` and confirm it has spiked above 90% from its ~40% baseline.
3. Confirm no transport `LINK_DOWN` alarm is active. Note that `CORE-MME-01` has no parent node in the topology table.

## Remediation
- Execute automated action `clear_stuck_session` (flush orphaned NAS/S1AP signaling sessions and enable MME overload pacing) on `CORE-MME-01`.
- Flushing orphaned/stuck signaling contexts is non-destructive to established active voice/data bearers, so `risk_level` is `low` and `safe_to_automate` is `true` when confidence meets the policy threshold.
- Post-check `signaling_load_pct` on `CORE-MME-01` to confirm recovery back toward the ~40% baseline.

## Rollback/escalation
- If `signaling_load_pct` stays above 85% after clearing stuck sessions, escalate to Core Network Tier-3 for controlled MME process restart (`restart_service`, medium risk, requires human approval).
