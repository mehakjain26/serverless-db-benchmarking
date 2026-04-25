import psycopg2
import os

# Using the configuration from your setup_db.py
DB_CONFIG = {
    "host": "d5e65386-f8fc-4847-8272-f2bcabdf6bc3.0135ec03d5bf43b196433793c98e8bd5.databases.appdomain.cloud",
    "port": 31604,
    "dbname": "ibmclouddb",
    "user": "ibm_cloud_c56b4076_94db_4c14_bdea_e54446df05d2",
    "password": "mKfSwfgwlWEkwZQlvbHTCa2TNGqln2le",
    "sslmode": "verify-full",
    "sslrootcert": "ibm_postgres_ca.crt"
}

def test_connection():
    print(f"Attempting to connect to IBM Cloud Postgres at {DB_CONFIG['host']}...")
    try:
        # We ensure we are in the correct directory so the .crt file is found
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connection successful!")
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print(f"Database version: {cur.fetchone()[0]}")
        
        cur.close()
        conn.close()
        print("Connection closed safely.")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
