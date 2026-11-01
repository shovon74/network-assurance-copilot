---
id: RB-RAN-004
title: RAN Antenna VSWR High and RET Tilt Motor Fault
domain: RAN
risk_level: high
safe_to_automate: false
recommended_action: dispatch_field_team
---

# RB-RAN-004: RAN Antenna VSWR High and RET Tilt Motor Fault

## Symptoms
- `VSWR_HIGH` or `RET_MOTOR_FAULT` alarm on a single RAN sector, optionally paired with `TX_POWER_DEGRADED`.
- Site remains online with normal AC power (`POWER_FAILURE` is absent) and active S1 link (`S1_LINK_FAILURE` is absent).
- PRB utilization stays near baseline (~40-50%) while coverage footprint shrinks on one sector.

## Likely causes
- Water ingress in the RF jumper coaxial cable between the Remote Radio Unit (RRU) and antenna port, or a jammed Remote Electrical Tilt (RET) actuator.

## Diagnostic steps
1. Check for `VSWR_HIGH` or `RET_MOTOR_FAULT` alarms.
2. Confirm `prb_utilization_pct` is not spiking to 95% (ruling out `RB-RAN-001` cell congestion) and site power is healthy (ruling out `RB-RAN-002`).

## Remediation
- Create a `pending_approval` action for `dispatch_field_team` (`risk_level: high`, `safe_to_automate: false`) so tower riggers can inspect the RF jumper and RRU connector weatherproofing.

## Rollback/escalation
- Keep RRU TX power backoff enabled until field sweep testing confirms VSWR is below 1.4:1.
