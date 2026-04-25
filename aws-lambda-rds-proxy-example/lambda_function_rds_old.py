import os
import boto3
import psycopg2

def lambda_handler(event, context):
    try:
        endpoint = os.environ['AURORA_ENDPOINT']
        user = os.environ['DB_USER']
        dbname = os.environ['DB_NAME']
        region = os.environ['DB_REGION']
        
        print(f"Connecting to Aurora Cluster: {endpoint}")
        
        # Generate IAM Auth Token
        rds_client = boto3.client('rds')
        token = rds_client.generate_db_auth_token(
            DBHostname=endpoint,
            Port=5432,
            DBUsername=user,
            Region=region
        )
        
        # Connect using the token as password
        conn = psycopg2.connect(
            host=endpoint,
            port=5432,
            database=dbname,
            user=user,
            password=token,
            sslmode='require'
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
                'message': "Aurora Data Health Check Successful",
                'counts': counts
            }
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': {
                'error': "Aurora Connection Failed",
                'details': str(e)
            }
        }
