---
id: RB-RAN-002
title: RAN Site Mains Power Failure and Battery Exhaustion
domain: RAN
risk_level: high
safe_to_automate: false
recommended_action: dispatch_field_team
---

# RB-RAN-002: RAN Site Mains Power Failure and Battery Exhaustion

## Symptoms
- Critical `POWER_FAILURE` alarm on a single RAN site (`SITE-001` through `SITE-006`), rapidly followed within 1-4 minutes by `BATTERY_DISCHARGING` (major), `CELL_DOWN` (major), and repeated `SITE_UNREACHABLE` (major) alarms on the same site.
- Both `dl_throughput_mbps` and `prb_utilization_pct` on the affected site drop completely to 0.0 for the duration of the outage.
- Other sibling sites connected to the same parent `TRN-AGG` switch remain up with normal KPIs and no `LINK_DOWN` alarm on the switch.

## Likely causes
- Commercial AC grid outage combined with depleted backup VRLA/Li-ion battery bank or failed diesel generator auto-start at the cell site (`root_cause: site_power_failure`).
- Main DC rectifier breaker trip inside the site power cabinet.

## Diagnostic steps
1. Check incident alarms for the signature sequence on a single site: `POWER_FAILURE` -> `BATTERY_DISCHARGING` -> `CELL_DOWN` -> `SITE_UNREACHABLE`.
2. Query `get_kpi_trend` for `dl_throughput_mbps` and `prb_utilization_pct` on the site and verify both drop to 0.0 simultaneously.
3. Check `get_topology_neighbors` to confirm the parent `TRN-AGG` switch has no `LINK_DOWN` alarm and sibling sites are unaffected (distinguishing this from `RB-TRN-001`).

## Remediation
- Recommend action `dispatch_field_team` to send a field maintenance crew with a portable generator to the physical site.
- Because physical field dispatch incurs operational cost and software actions cannot restore dead site power, `risk_level` is `high` and `safe_to_automate` is `false`. Human operator approval (`pending_approval`) is mandatory.

## Rollback/escalation
- Once mains or generator power is restored and `SITE_UNREACHABLE` clears, verify that `dl_throughput_mbps` returns to ~80 Mbps and `prb_utilization_pct` returns to ~45%. If the eNodeB baseband unit fails to boot after power recovery, escalate to RAN Tier-2 support.
