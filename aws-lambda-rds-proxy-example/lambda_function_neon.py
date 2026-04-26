import json
import logging
import os
import psycopg2
from req_gen import Request, RequestType
from server.req_sql import execute

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global connection to keep it warm across invocations
_conn = None

def get_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(
            host=os.environ['NEON_HOST'],
            database=os.environ['NEON_DB'],
            user=os.environ['NEON_USER'],
            password=os.environ['NEON_PASSWORD'],
            sslmode=os.environ['NEON_SSLMODE']
        )
    return _conn

def lambda_handler(event, context):
    try:
        # 1. Parse params
        if 'queryStringParameters' in event and event['queryStringParameters']:
            params = event['queryStringParameters']
            op_name = params.get('op', 'point_read')
        else:
            op_name = 'point_read'
            params = {}

        # 2. Build Request
        req = Request(type=RequestType(op_name), params=params)
        logger.info(f"Handling Neon op: {op_name}")

        # 3. Execute using shared SQL logic
        conn = get_connection()
        cur = conn.cursor()
        try:
            rows, latency_ms = execute(conn, cur, req)
        finally:
            cur.close()

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'adapter': 'neon',
                'op': op_name,
                'latency_ms': latency_ms,
                'row_count': len(rows),
                'data': rows
            })
        }

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.error(f"Error in Neon Lambda: {err_msg}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(type(e).__name__),
                'details': str(e),
                'traceback': err_msg
            })
        }
