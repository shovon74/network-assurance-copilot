---
id: RB-RAN-003
title: RAN eNodeB Baseband Unit Software Hang
domain: RAN
risk_level: medium
safe_to_automate: false
recommended_action: restart_service
---

# RB-RAN-003: RAN eNodeB Baseband Unit Software Hang

## Symptoms
- `BBU_PROCESS_HANG` or `WATCHDOG_TIMEOUT` alarm on a single RAN site, sometimes accompanied by `CELL_DOWN`.
- No `POWER_FAILURE` or `BATTERY_DISCHARGING` alarms are present on the site (mains and DC power remain healthy).
- Parent `TRN-AGG` switch has no `LINK_DOWN` alarm.

## Likely causes
- Memory leak or deadlock in the eNodeB L2/L3 baseband scheduler process following a configuration push.

## Diagnostic steps
1. Confirm the site has `BBU_PROCESS_HANG` or `WATCHDOG_TIMEOUT` without `POWER_FAILURE` or `BATTERY_DISCHARGING` (which would indicate `RB-RAN-002`).
2. Confirm the site remains reachable over the OAM management plane even if user-plane traffic dropped.

## Remediation
- Recommend `restart_service` (warm restart of the eNodeB baseband daemon). Because a baseband warm restart briefly drops active calls on that site, `risk_level` is `medium` and `safe_to_automate` is `false` (requires human approval).

## Rollback/escalation
- If the eNodeB fails to recover within 10 minutes of `restart_service`, escalate to the RAN vendor support team for cold board reset.
