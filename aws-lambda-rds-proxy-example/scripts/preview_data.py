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
    cur = conn.cursor()

    for table in TABLES:
        print(f"\n=== Sample from {table} ===")
        try:
            # Get column names
            cur.execute(f"SELECT * FROM {table} LIMIT 0")
            colnames = [desc[0] for desc in cur.description]
            print(" | ".join(colnames))
            print("-" * 50)

            # Get 5 sample rows
            cur.execute(f"SELECT * FROM {table} LIMIT 5")
            rows = cur.fetchall()
            for row in rows:
                print(" | ".join(map(str, row)))
        except Exception as e:
            print(f"Error reading {table}: {e}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
