import os
import aurora_dsql_psycopg2 as dsql

def lambda_handler(event, context):
    try:
        endpoint = os.environ['DSQL_ENDPOINT']
        region = os.environ['DB_REGION']
        
        # Connect to DSQL
        conn = dsql.connect(
            host=endpoint,
            region=region,
            user="admin"
        )
        
        tables = ["stops", "routes", "calendar", "trips", "stop_times"]
        counts = {}
        
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            
        conn.close()
        
        return {
            'statusCode': 200,
            'body': {
                'message': "Data Health Check Successful",
                'counts': counts
            }
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': {
                'error': "Connection Failed",
                'details': str(e)
            }
        }
