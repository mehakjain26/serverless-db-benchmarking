import os
import json
import boto3
import psycopg2
from decimal import Decimal

# Import the logic from your server package
from req_gen import Request, RequestType
from server.req_sql import execute

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    try:
        # 1. Database Configuration from Environment Variables
        # This keeps your credentials secure and decoupled from the code
        endpoint = os.environ['AURORA_ENDPOINT']
        user = os.environ['DB_USER']
        dbname = os.environ['DB_NAME']
        region = os.environ['DB_REGION']
        
        # 2. Parse the operation (from query string or direct event)
        params = event.get('queryStringParameters') or event
        op_name = params.get('op')
        
        if not op_name:
            return {'statusCode': 400, 'body': 'Missing "op" parameter'}
            
        # Convert the string name (e.g. "point_read") to a RequestType enum
        try:
            rtype = RequestType(op_name)
        except ValueError:
            return {'statusCode': 400, 'body': f'Invalid operation: {op_name}'}

        # 3. Setup Connection using IAM Auth
        rds_client = boto3.client('rds')
        token = rds_client.generate_db_auth_token(
            DBHostname=endpoint, Port=5432, DBUsername=user, Region=region
        )
        
        conn = psycopg2.connect(
            host=endpoint, port=5432, database=dbname,
            user=user, password=token, sslmode='require'
        )
        
        # 4. Prepare and Run the Query
        # We reuse the logic from server/req_sql.py
        req = Request(type=rtype, params=params)
        
        with conn.cursor() as cur:
            # Reusing the shared execute function from server.req_sql
            rows, latency_ms = execute(conn, cur, req)
            
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'op': op_name,
                'latency_ms': latency_ms,
                'row_count': len(rows),
                'data': rows
            }, default=decimal_default)
        }
    except Exception as e:
        print(f"Error handling request: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
