import os
import psycopg2

def lambda_handler(event, context):
    try:
        host = os.environ['IBM_DB_HOST']
        port = os.environ['IBM_DB_PORT']
        dbname = os.environ['IBM_DB_NAME']
        user = os.environ['IBM_DB_USER']
        password = os.environ['IBM_DB_PASSWORD']
        
        # Path where the CA cert is included in the Lambda ZIP
        sslrootcert = '/var/task/ibm_postgres_ca.crt'
        
        print(f"Connecting to IBM Cloud Postgres: {host}")
        
        # Connect to IBM Cloud Postgres
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=dbname,
            user=user,
            password=password,
            sslmode='verify-full',
            sslrootcert=sslrootcert
        )
        
        # Health check: Query GTFS tables
        tables = ["stops", "routes", "calendar", "trips", "stop_times"]
        counts = {}
        
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'")
                if cur.fetchone()[0] > 0:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cur.fetchone()[0]
                else:
                    counts[table] = "Table not found"
            
        conn.close()
        
        return {
            'statusCode': 200,
            'body': {
                'message': "IBM Cloud Data Health Check Successful",
                'counts': counts
            }
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': {
                'error': "IBM Cloud Connection Failed",
                'details': str(e)
            }
        }
