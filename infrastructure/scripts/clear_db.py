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

    print(f"Connecting to DSQL at {DSQL_ENDPOINT}...")
    conn = dsql.connect(
        host=DSQL_ENDPOINT,
        region=DB_REGION,
        user="admin"
    )
    conn.autocommit = True
    cur = conn.cursor()

    for table in TABLES:
        print(f"Clearing table: {table}")
        while True:
            cur.execute(f"DELETE FROM {table} WHERE id IN (SELECT id FROM {table} LIMIT 3000);")
            rows_deleted = cur.rowcount
            print(f"  Deleted {rows_deleted} rows...")
            if rows_deleted == 0:
                break

    cur.close()
    conn.close()

    print("All tables cleared successfully!")

if __name__ == "__main__":
    main()
