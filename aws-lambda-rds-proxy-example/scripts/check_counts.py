import os
import aurora_dsql_psycopg2 as dsql

# Fetch DSQL configuration from environment variables
DSQL_ENDPOINT = os.environ.get("DSQL_ENDPOINT")
DB_REGION = os.environ.get("DB_REGION", "us-east-1")


TABLES = ["stops", "routes", "calendar", "trips", "stop_times"]

def main():
    if not DSQL_ENDPOINT:
        print("Error: DSQL_ENDPOINT environment variable not set.")
        return

    conn = dsql.connect(
        host=DSQL_ENDPOINT,
        region=DB_REGION,
        user="admin"
    )
    cur = conn.cursor()

    print("\n===== TOTAL ROW COUNTS =====\n")

    for table in TABLES:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table}: {count:,} rows")

    print("\n===== ROWS PER CITY (transport_id) =====\n")

    for table in ["stops", "routes", "trips", "stop_times"]:
        print(f"\n--- {table} ---")
        cur.execute(f"""
            SELECT transport_id, COUNT(*)
            FROM {table}
            GROUP BY transport_id
            ORDER BY transport_id
        """)
        rows = cur.fetchall()

        for r in rows:
            print(f"City {r[0]} → {r[1]:,} rows")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()