---
id: RB-TRN-001
title: Transport Aggregation Switch Uplink Down
domain: TRANSPORT
risk_level: low
safe_to_automate: true
recommended_action: reroute_traffic
---

# RB-TRN-001: Transport Aggregation Switch Uplink Down

## Symptoms
- Critical `LINK_DOWN` alarm raised on a transport aggregation switch (`TRN-AGG-01` or `TRN-AGG-02`).
- Immediate storm of downstream RAN alarms across all child eNodeB sites connected to that switch, including repeated `S1_LINK_FAILURE` (major) and `CELL_UNREACHABLE` (major).
- Downlink throughput (`dl_throughput_mbps`) drops abruptly to 0.0 Mbps across all child sites simultaneously while PRB utilization stops reporting normal traffic.

## Likely causes
- Primary optical uplink fiber cut or SFP transceiver failure on the aggregation switch (`root_cause: transport_link_down`).
- Upstream IP/MPLS core router port shutdown affecting the primary transport trunk.
- Note: Do not confuse this with individual site power failures (`RB-RAN-002`). When multiple sites behind the same `TRN-AGG` switch fail within seconds of a `LINK_DOWN` alarm, the aggregation switch is the single root cause node.

## Diagnostic steps
1. Query incident alarms and identify whether a `LINK_DOWN` alarm is present on `TRN-AGG-01` or `TRN-AGG-02`.
2. Check topology neighbors of the aggregation switch to list its child RAN sites (`SITE-001..003` for `TRN-AGG-01`, `SITE-004..006` for `TRN-AGG-02`).
3. Verify `dl_throughput_mbps` KPI trends on the child sites to confirm simultaneous drop to 0 Mbps.

## Remediation
- Execute automated action `reroute_traffic` on the affected `TRN-AGG` node to shift traffic onto the standby ring protection path.
- Because the standby MPLS path is pre-provisioned, `risk_level` is `low` and `safe_to_automate` is `true` when RCA confidence is at least 0.80.
- Run a post-check on child site `dl_throughput_mbps` to verify recovery back toward the ~80 Mbps baseline.

## Rollback/escalation
- If `dl_throughput_mbps` remains at 0 Mbps after 5 minutes, revert the protection switch and escalate to the Transport Field Optics team (`dispatch_field_team`) to inspect both primary and secondary fibers.
