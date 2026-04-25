import os
import boto3
import psycopg2

# Fetch Aurora configuration
AURORA_ENDPOINT = os.environ.get("AURORA_ENDPOINT")
DB_REGION = os.environ.get("DB_REGION", "us-east-1")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_NAME = os.environ.get("DB_NAME", "postgres")

TABLES = ["stops", "routes", "calendar", "trips", "stop_times"]

def main():
    if not AURORA_ENDPOINT:
        print("Error: AURORA_ENDPOINT environment variable not set.")
        return

    # Generate Token
    rds_client = boto3.client('rds', region_name=DB_REGION)
    token = rds_client.generate_db_auth_token(DBHostname=AURORA_ENDPOINT, Port=5432, DBUsername=DB_USER)

    print(f"Connecting to Aurora at {AURORA_ENDPOINT}...")
    conn = psycopg2.connect(host=AURORA_ENDPOINT, port=5432, database=DB_NAME, user=DB_USER, password=token, sslmode='require')
    cur = conn.cursor()

    for table in TABLES:
        print(f"\n=== Sample from {table} ===")
        try:
            cur.execute(f"SELECT * FROM {table} LIMIT 5")
            colnames = [desc[0] for desc in cur.description]
            print(" | ".join(colnames))
            print("-" * 50)
            for row in cur.fetchall():
                print(" | ".join(map(str, row)))
        except Exception as e:
            print(f"Error reading {table}: {e}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
