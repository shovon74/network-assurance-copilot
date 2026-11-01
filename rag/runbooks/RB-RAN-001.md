---
id: RB-RAN-001
title: RAN Cell PRB Congestion and Throughput Degradation
domain: RAN
risk_level: low
safe_to_automate: true
recommended_action: reroute_traffic
---

# RB-RAN-001: RAN Cell PRB Congestion and Throughput Degradation

## Symptoms
- Sequential `HIGH_PRB_UTILIZATION` alarms (escalating from `minor` to `major`) followed by a `LOW_THROUGHPUT` (`major`) alarm on a single RAN site (`SITE-001` through `SITE-006`).
- `prb_utilization_pct` KPI on the affected site ramps from baseline (~45%) up to ~95% over 10-20 minutes.
- `dl_throughput_mbps` KPI on the same site degrades from ~80 Mbps down to ~24-28 Mbps (partial degradation, NOT 0 Mbps).
- Neighboring sites under the same `TRN-AGG` parent switch remain healthy.

## Likely causes
- Localized subscriber traffic surge or uneven MLB (Mobility Load Balancing) cell reselection weights causing Physical Resource Block exhaustion (`root_cause: cell_congestion`).
- Secondary carrier sleep mode stuck inactive during a busy traffic period.

## Diagnostic steps
1. Verify that alarms on the site are `HIGH_PRB_UTILIZATION` and `LOW_THROUGHPUT`, without `POWER_FAILURE`, `CELL_DOWN`, or parent `LINK_DOWN` alarms.
2. Query `get_kpi_trend` for `prb_utilization_pct` and `dl_throughput_mbps` on the affected site. Confirm `prb_utilization_pct` exceeds 85% while `dl_throughput_mbps` drops to ~25 Mbps (non-zero).
3. Check topology parent (`TRN-AGG-01` or `TRN-AGG-02`) to verify no transport outage is present.

## Remediation
- Execute low-risk automated action `reroute_traffic` (RAN Mobility Load Balancing / carrier load offload) on the congested site to shift edge UEs to adjacent cells/carriers.
- Because MLB parameter adjustment within pre-approved bounds is non-disruptive, `risk_level` is `low` and `safe_to_automate` is `true`.
- Post-check `prb_utilization_pct` and `dl_throughput_mbps` after execution to confirm PRB drops below 70% and throughput recovers toward 80 Mbps.

## Rollback/escalation
- If PRB utilization remains above 90% after load offload, restore default cell individual offsets (CIO) and escalate to RAN RF Optimization engineering.
