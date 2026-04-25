import psycopg2

DB_CONFIG = {
    "host": "6c431a8d-a72f-4597-b8ee-b353e6e82086.c5km1ted03t0e8geevf0.databases.appdomain.cloud",
    "port": 32563,
    "dbname": "ibmclouddb",
    "user": "ibm_cloud_326db193_fdb8_4342_b196_4cde1b6c8061",
    "password": "FeBAgu8Un96H4rfueCe2LNssmxgNYX78",
    "sslmode": "verify-full",
    "sslrootcert": "ibm_postgres_ca.crt"
}

TABLES = ["stops", "routes", "calendar", "trips", "stop_times"]

def main():
    conn = psycopg2.connect(**DB_CONFIG)
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