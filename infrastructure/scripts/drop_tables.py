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

    print("\n⚠️  Dropping all tables...")

    for table in TABLES:
        print(f"Dropping table: {table}")
        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

    cur.close()
    conn.close()

    print("\nAll tables dropped successfully! You can now run setup_db.py to recreate them.")

if __name__ == "__main__":
    main()
