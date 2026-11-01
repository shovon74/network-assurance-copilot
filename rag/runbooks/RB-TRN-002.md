---
id: RB-TRN-002
title: Transport Aggregation Interface Flapping (Minor Noise)
domain: TRANSPORT
risk_level: low
safe_to_automate: true
recommended_action: none
---

# RB-TRN-002: Transport Aggregation Interface Flapping (Minor Noise)

## Symptoms
- Burst of 8 to 12 minor `INTERFACE_FLAP` alarms on a transport aggregation switch (`TRN-AGG-01` or `TRN-AGG-02`) spaced 20 to 50 seconds apart.
- No `LINK_DOWN` critical alarm on the switch.
- No downstream `S1_LINK_FAILURE` or `CELL_UNREACHABLE` alarms on child sites (`SITE-001..006`).
- Downlink throughput (`dl_throughput_mbps`) and PRB utilization (`prb_utilization_pct`) on child sites remain stable near baseline (~80 Mbps and ~45%).

## Likely causes
- Transient optical power jitter or LACP member link micro-bounce on a non-primary port (`root_cause: interface_flapping`).
- Hardware hold-off timer sensitivity on the aggregation switch port causing minor alarm chatter without service impact.

## Diagnostic steps
1. Inspect all alarms in the cluster and confirm severity is strictly `minor` (`INTERFACE_FLAP`) with no `major` or `critical` service alarms.
2. Check topology child sites and verify that `dl_throughput_mbps` shows no degradation or zero-traffic outage during the alarm window.
3. Confirm that triage classifies the cluster as `noise` (`is_noise = true`).

## Remediation
- No active network mutation is required (`recommended_action: none`). Keep the incident suppressed as operational noise and log for scheduled maintenance review.
- If RCA is explicitly invoked on a flapping cluster, classify root cause as `interface_flapping` on the aggregation switch and recommend `RB-TRN-002` with damping timer tuning during maintenance hours.

## Rollback/escalation
- If `INTERFACE_FLAP` escalates into a persistent `LINK_DOWN` alarm or child site throughput drops to 0 Mbps, reclassify under `RB-TRN-001` and trigger `reroute_traffic`.
