import json
import logging
import os

from pymongo import MongoClient

# Import the benchmarking query engine
from req_gen import Request, RequestType
from server.req_mongo import execute, get_col

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global client to keep persistent across warm starts
mongo_client = None

def get_mongo_client():
    global mongo_client
    
    if mongo_client is not None:
        return mongo_client

    mongo_uri = os.environ['MONGO_URI']
    logger.info("Connecting to MongoDB...")
    # We set a fast connect timeout because SRV records can sometimes be slow to resolve initially
    mongo_client = MongoClient(mongo_uri, connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
    return mongo_client

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

        # 2. Get Persistent Client and Collection
        client = get_mongo_client()
        col = get_col(client)

        # 3. Execute Benchmarking Logic
        rows, latency_ms = execute(col, req)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'op': op_name,
                'latency_ms': latency_ms,
                'row_count': len(rows),
                'data': rows
            })
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
