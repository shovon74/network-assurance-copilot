"""Seed the static topology (safe to run repeatedly)."""
from simulate import CORE_NODES, SITES_BEHIND, get_conn

SQL = (
    "INSERT INTO topology_nodes (node_id, domain, node_type, parent_id) "
    "VALUES (%s, %s, %s, %s) ON CONFLICT (node_id) DO NOTHING"
)


def main():
    with get_conn() as conn, conn.cursor() as cur:
        for agg, sites in SITES_BEHIND.items():
            cur.execute(SQL, (agg, "TRANSPORT", "aggregation_switch", None))
            for site in sites:
                cur.execute(SQL, (site, "RAN", "cell_site", agg))
        for node in CORE_NODES:
            cur.execute(SQL, (node, "CORE", "mme", None))
    print("Topology seeded")


if __name__ == "__main__":
    main()
