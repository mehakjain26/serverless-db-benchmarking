import os
import json
import time
import boto3
import psycopg2
from decimal import Decimal

# Import the logic from your database_clients package
from core import Request, RequestType
from database_clients.req_sql import execute

# --- GLOBAL VARIABLES (Persist between warm invocations) ---
# This is the "Connection Pooling" logic that prevents the 429 
# (Too Many Requests) errors from the Aurora IAM Auth throttle.
_conn = None
_token = None
_token_expires = 0

def get_connection():
    global _conn, _token, _token_expires
    
    current_time = time.time()
    endpoint = os.environ['AURORA_ENDPOINT']
    user = os.environ['DB_USER']
    dbname = os.environ['DB_NAME']
    region = os.environ['DB_REGION']

    # 1. Reuse existing connection if it's still healthy
    if _conn is not None and not _conn.closed:
        # Check if IAM token is still valid (they last 15 mins, we refresh at 10)
        if current_time < _token_expires:
            return _conn
        else:
            _conn.close()

    # 2. Generate new IAM Auth Token
    rds_client = boto3.client('rds')
    _token = rds_client.generate_db_auth_token(
        DBHostname=endpoint, Port=5432, DBUsername=user, Region=region
    )
    _token_expires = current_time + 600 # 10 minutes
    
    # 3. Establish new connection
    _conn = psycopg2.connect(
        host=endpoint, port=5432, database=dbname,
        user=user, password=_token, sslmode='require'
    )
    # Ensure it's not in an old transaction
    _conn.autocommit = True 
    return _conn

def decimal_default(obj):
    if isinstance(obj, Decimal): return float(obj)
    raise TypeError

def lambda_handler(event, context):
    try:
        # Parse the operation (from query string or direct event)
        params = event.get('queryStringParameters') or event
        op_name = params.get('op')
        
        if not op_name:
            return {'statusCode': 400, 'body': 'Missing "op" parameter'}
            
        rtype = RequestType(op_name)
        req = Request(type=rtype, params=params)

        # 3. Get or Reuse Connection
        db_conn = get_connection()
        
        # 4. Prepare and Run the Query
        with db_conn.cursor() as cur:
            # Reusing the shared execute function from database_clients.req_sql
            rows, latency_ms = execute(db_conn, cur, req)
            
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
        # If connection failed, clear it so next invocation tries fresh
        global _conn
        _conn = None 
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
