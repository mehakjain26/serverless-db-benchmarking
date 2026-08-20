import json
import logging
import os
import time
from datetime import datetime, date
from decimal import Decimal

import psycopg2

# Import the benchmarking query engine
from database_clients.req_sql import execute
from core import Request, RequestType

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global connection to keep persistent across warm starts
db_conn = None

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError

def get_connection():
    global db_conn
    
    # Check if connection is still alive
    if db_conn is not None:
        try:
            with db_conn.cursor() as cur:
                cur.execute("SELECT 1")
            return db_conn
        except Exception:
            logger.info("Connection lost, reconnecting...")
            db_conn = None

    host = os.environ['IBM_DB_HOST']
    port = os.environ['IBM_DB_PORT']
    dbname = os.environ['IBM_DB_NAME']
    user = os.environ['IBM_DB_USER']
    password = os.environ['IBM_DB_PASSWORD']
    sslrootcert = '/var/task/ibm_postgres_ca.crt'

    logger.info(f"Connecting to IBM Cloud Postgres: {host}")
    db_conn = psycopg2.connect(
        host=host,
        port=port,
        database=dbname,
        user=user,
        password=password,
        sslmode='verify-full',
        sslrootcert=sslrootcert
    )
    return db_conn

def lambda_handler(event, context):
    try:
        # 1. Route the Request
        if 'queryStringParameters' in event and event['queryStringParameters']:
            params = event['queryStringParameters']
            op_name = params.get('op', 'point_read')
        else:
            op_name = 'point_read'
            params = {}

        req = Request(type=RequestType(op_name), params=params)
        logger.info(f"Handling op: {op_name}")

        # 2. Get Persistent Connection
        conn = get_connection()

        # 3. Execute Benchmarking Logic
        with conn.cursor() as cur:
            rows, latency_ms = execute(conn, cur, req)

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
        logger.error(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(type(e).__name__),
                'details': str(e)
            })
        }
