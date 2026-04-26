import psycopg2

DB_CONFIG = {
    "host": "d5e65386-f8fc-4847-8272-f2bcabdf6bc3.0135ec03d5bf43b196433793c98e8bd5.databases.appdomain.cloud",
    "port": 31604,
    "dbname": "ibmclouddb",
    "user": "ibm_cloud_c56b4076_94db_4c14_bdea_e54446df05d2",
    "password": "mKfSwfgwlWEkwZQlvbHTCa2TNGqln2le",
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