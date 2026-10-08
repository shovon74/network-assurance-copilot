"""Network simulator - Step 2e: five scenarios, many incidents.

Each incident occupies a 30-minute slot. Alarms for the scenario land in the first ~10 minutes,
optional background noise lands later in the slot, so triage can separate them.
"""
import argparse
import os
import random
from collections import Counter
from datetime import datetime, timedelta, timezone

SITES_BEHIND = {
    "TRN-AGG-01": ["SITE-001", "SITE-002", "SITE-003"],
    "TRN-AGG-02": ["SITE-004", "SITE-005", "SITE-006"],
}
ALL_SITES = [s for sites in SITES_BEHIND.values() for s in sites]
CORE_NODES = ["CORE-MME-01"]
SLOT = timedelta(minutes=30)
NOISE_TYPES = [("TEMPERATURE_HIGH", "warning"), ("FAN_SPEED_LOW", "minor"), ("BATTERY_LOW", "warning")]


def get_conn():
    import psycopg
    from psycopg.conninfo import make_conninfo

    return psycopg.connect(
        make_conninfo(
            host=os.environ.get("POSTGRES_HOST", "postgres"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
        )
    )


def minute_range(start, end):
    t = start
    while t < end:
        yield t
        t += timedelta(minutes=1)


def at(t0, rng, lo, hi):
    return t0 + timedelta(seconds=rng.randint(lo, hi))


def clamp(value, lo=0.0, hi=100.0):
    return round(min(hi, max(lo, value)), 2)


# ---------------------------------------------------------------- scenarios
# Each returns (alarms, truth). Alarm tuple: (raised_at, node, domain, type, severity, message)

def link_down(rng, t0, kpi):
    agg = rng.choice(list(SITES_BEHIND))
    affected = SITES_BEHIND[agg]
    alarms = [(t0, agg, "TRANSPORT", "LINK_DOWN", "critical", f"Uplink down on {agg}")]
    for site in affected:
        first = at(t0, rng, 5, 40)
        alarms.append((first, site, "RAN", "S1_LINK_FAILURE", "major", f"S1 link failure at {site}"))
        for i in range(rng.randint(1, 3)):
            alarms.append((first + timedelta(seconds=60 * (i + 1) + rng.randint(0, 10)),
                           site, "RAN", "S1_LINK_FAILURE", "major", f"S1 link failure at {site}"))
        alarms.append((at(t0, rng, 20, 90), site, "RAN", "CELL_UNREACHABLE", "major",
                       f"Cell unreachable at {site}"))
    end = t0 + timedelta(minutes=25)
    for ts in minute_range(t0, end):
        for site in affected:
            kpi[(site, "dl_throughput_mbps", ts)] = 0.0
    truth = dict(scenario_type="transport_link_down", root_cause="transport_link_down",
                 root_cause_node=agg, correct_runbook="RB-TRN-001", expected_severity="critical",
                 is_noise=False, affected_nodes=[agg] + affected, started_at=t0, ended_at=end)
    return alarms, truth


def cell_degradation(rng, t0, kpi):
    site = rng.choice(ALL_SITES)
    alarms = [
        (t0 + timedelta(minutes=2), site, "RAN", "HIGH_PRB_UTILIZATION", "minor", f"High PRB utilization at {site}"),
        (t0 + timedelta(minutes=5, seconds=rng.randint(0, 30)), site, "RAN", "HIGH_PRB_UTILIZATION", "major",
         f"High PRB utilization at {site}"),
        (t0 + timedelta(minutes=8), site, "RAN", "LOW_THROUGHPUT", "major", f"Low throughput at {site}"),
    ]
    end = t0 + timedelta(minutes=20)
    for m, ts in enumerate(minute_range(t0, end)):
        frac = min(1.0, m / 10)
        kpi[(site, "dl_throughput_mbps", ts)] = clamp(80 * (1 - 0.7 * frac) + rng.gauss(0, 3), 0, 200)
        kpi[(site, "prb_utilization_pct", ts)] = clamp(45 + 50 * frac + rng.gauss(0, 2))
    truth = dict(scenario_type="cell_degradation", root_cause="cell_congestion", root_cause_node=site,
                 correct_runbook="RB-RAN-001", expected_severity="major", is_noise=False,
                 affected_nodes=[site], started_at=t0, ended_at=end)
    return alarms, truth


def site_power_failure(rng, t0, kpi):
    site = rng.choice(ALL_SITES)
    alarms = [
        (t0, site, "RAN", "POWER_FAILURE", "critical", f"Mains power failure at {site}"),
        (at(t0, rng, 20, 40), site, "RAN", "BATTERY_DISCHARGING", "major", f"Battery discharging at {site}"),
        (at(t0, rng, 60, 100), site, "RAN", "CELL_DOWN", "major", f"Cell down at {site}"),
        (at(t0, rng, 110, 150), site, "RAN", "SITE_UNREACHABLE", "major", f"Site unreachable: {site}"),
        (at(t0, rng, 200, 260), site, "RAN", "SITE_UNREACHABLE", "major", f"Site unreachable: {site}"),
    ]
    end = t0 + timedelta(minutes=20)
    for ts in minute_range(t0, end):
        kpi[(site, "dl_throughput_mbps", ts)] = 0.0
        kpi[(site, "prb_utilization_pct", ts)] = 0.0
    truth = dict(scenario_type="site_power_failure", root_cause="site_power_failure", root_cause_node=site,
                 correct_runbook="RB-RAN-002", expected_severity="critical", is_noise=False,
                 affected_nodes=[site], started_at=t0, ended_at=end)
    return alarms, truth


def core_signaling_overload(rng, t0, kpi):
    node = CORE_NODES[0]
    alarms = [
        (t0, node, "CORE", "SIGNALING_OVERLOAD", "major", f"Signaling overload on {node}"),
        (at(t0, rng, 20, 60), node, "CORE", "CPU_HIGH", "major", f"CPU high on {node}"),
    ]
    for i in range(rng.randint(3, 5)):
        alarms.append((t0 + timedelta(seconds=90 + 60 * i + rng.randint(0, 20)), node, "CORE",
                       "S1AP_REJECT_RATE_HIGH", "major", f"S1AP reject rate high on {node}"))
    end = t0 + timedelta(minutes=20)
    for m, ts in enumerate(minute_range(t0 - timedelta(minutes=6), end)):
        frac = min(1.0, m / 6)
        kpi[(node, "signaling_load_pct", ts)] = clamp(40 + 58 * frac + rng.gauss(0, 1.5))
    truth = dict(scenario_type="core_signaling_overload", root_cause="core_signaling_overload",
                 root_cause_node=node, correct_runbook="RB-CORE-001", expected_severity="major",
                 is_noise=False, affected_nodes=[node], started_at=t0, ended_at=end)
    return alarms, truth


def flapping_interface(rng, t0, kpi):
    agg = rng.choice(list(SITES_BEHIND))
    alarms, t = [], t0
    for _ in range(rng.randint(8, 12)):
        alarms.append((t, agg, "TRANSPORT", "INTERFACE_FLAP", "minor", f"Interface flap on {agg}"))
        t += timedelta(seconds=rng.randint(20, 50))
    truth = dict(scenario_type="flapping_interface", root_cause="interface_flapping", root_cause_node=agg,
                 correct_runbook="RB-TRN-002", expected_severity="minor", is_noise=True,
                 affected_nodes=[agg], started_at=t0, ended_at=t)
    return alarms, truth


# name -> (function, weight)
SCENARIOS = {
    "transport_link_down": (link_down, 25),
    "cell_degradation": (cell_degradation, 25),
    "site_power_failure": (site_power_failure, 20),
    "core_signaling_overload": (core_signaling_overload, 15),
    "flapping_interface": (flapping_interface, 15),
}


def background_noise(rng, t0):
    alarms = []
    for _ in range(rng.randint(0, 2)):
        a_type, sev = rng.choice(NOISE_TYPES)
        node = rng.choice(ALL_SITES)
        alarms.append((at(t0, rng, 16 * 60, 24 * 60), node, "RAN", a_type, sev, f"{a_type} at {node}"))
    return alarms


def baseline(rng, start, end):
    kpi = {}
    for ts in minute_range(start, end):
        for site in ALL_SITES:
            kpi[(site, "dl_throughput_mbps", ts)] = clamp(rng.gauss(80, 6), 0, 200)
            kpi[(site, "prb_utilization_pct", ts)] = clamp(rng.gauss(45, 7))
        for node in CORE_NODES:
            kpi[(node, "signaling_load_pct", ts)] = clamp(rng.gauss(40, 5))
    return kpi


def generate(seed, count, only=None, now=None):
    rng = random.Random(seed)
    now = (now or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    lead, tail = timedelta(minutes=35), timedelta(minutes=30)
    total = lead + SLOT * count + tail
    start = now - total - timedelta(minutes=5)

    kpi = baseline(rng, start, start + total)
    names = [only] if only else list(SCENARIOS)
    weights = [SCENARIOS[n][1] for n in names]

    alarms, truths, counts = [], [], Counter()
    for i in range(count):
        name = rng.choices(names, weights)[0]
        t0 = start + lead + SLOT * i
        scenario_alarms, truth = SCENARIOS[name][0](rng, t0, kpi)
        alarms += scenario_alarms + background_noise(rng, t0)
        truths.append(truth)
        counts[name] += 1

    kpi_rows = sorted((ts, node, metric, val) for (node, metric, ts), val in kpi.items())
    return sorted(alarms), kpi_rows, truths, counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=20, help="number of incidents to simulate")
    parser.add_argument("--only", choices=list(SCENARIOS), help="use a single scenario type")
    parser.add_argument("--reset", action="store_true", help="wipe all simulated data first")
    args = parser.parse_args()

    alarms, kpi_rows, truths, counts = generate(args.seed, args.count, args.only)

    with get_conn() as conn, conn.cursor() as cur:
        if args.reset:
            cur.execute("TRUNCATE actions, rca_results, alarms, kpi_samples, ground_truth, incidents "
                        "RESTART IDENTITY CASCADE")
        cur.executemany(
            "INSERT INTO alarms (raised_at, node_id, domain, alarm_type, severity, message) "
            "VALUES (%s, %s, %s, %s, %s, %s)", alarms)
        cur.executemany(
            "INSERT INTO kpi_samples (sampled_at, node_id, metric, value) VALUES (%s, %s, %s, %s)", kpi_rows)
        cur.executemany(
            "INSERT INTO ground_truth (scenario_type, root_cause, root_cause_node, correct_runbook, "
            "expected_severity, is_noise, affected_nodes, started_at, ended_at) "
            "VALUES (%(scenario_type)s, %(root_cause)s, %(root_cause_node)s, %(correct_runbook)s, "
            "%(expected_severity)s, %(is_noise)s, %(affected_nodes)s, %(started_at)s, %(ended_at)s)", truths)

    print(f"Inserted {len(alarms)} alarms, {len(kpi_rows)} KPI samples, {len(truths)} ground-truth rows")
    for name, n in sorted(counts.items()):
        print(f"  {name}: {n}")


if __name__ == "__main__":
    main()
