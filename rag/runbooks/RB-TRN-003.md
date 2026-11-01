---
id: RB-TRN-003
title: Transport Backhaul Microwave Packet Loss and Jitter
domain: TRANSPORT
risk_level: medium
safe_to_automate: false
recommended_action: reroute_traffic
---

# RB-TRN-003: Transport Backhaul Microwave Packet Loss and Jitter

## Symptoms
- Warning or minor `PACKET_LOSS_HIGH` and `LATENCY_JITTER_HIGH` alarms on a transport link during heavy rain fade or modulation downshift.
- No `LINK_DOWN` alarm on the aggregation switch and no `S1_LINK_FAILURE` storm across all child sites.
- Downlink throughput degrades moderately (40-55 Mbps) without dropping to zero, while PRB utilization stays normal (~45%).

## Likely causes
- Adaptive Coding and Modulation (ACM) downshift on a microwave hop or dirty optical connector introducing CRC errors on an Ethernet trunk.

## Diagnostic steps
1. Verify presence of `PACKET_LOSS_HIGH` or `CRC_ERROR_HIGH` alarms rather than `LINK_DOWN` or `HIGH_PRB_UTILIZATION`.
2. Check that `prb_utilization_pct` is near baseline (~45%), ruling out RAN cell congestion (`RB-RAN-001`).
3. Verify child sites remain reachable with non-zero throughput, ruling out `RB-TRN-001`.

## Remediation
- Request operator approval (`risk_level: medium`) to execute `reroute_traffic` onto the secondary transport VLAN if packet loss exceeds 2% for more than 15 minutes.

## Rollback/escalation
- Revert VLAN weight changes once optical CRC errors or microwave SNR metrics return to normal.
