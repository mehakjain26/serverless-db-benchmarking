import json
import logging
import os

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibmcloudant.cloudant_v1 import CloudantV1

# Import the benchmarking query engine
from core import Request, RequestType
from database_clients.req_cloudant import execute

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global client to keep persistent across warm starts
cloudant_client = None

def get_client():
    global cloudant_client
    
    if cloudant_client is not None:
        return cloudant_client

    apikey = os.environ['CLOUDANT_APIKEY']
    url = os.environ['CLOUDANT_URL']

    logger.info(f"Connecting to Cloudant at: {url}")
    auth = IAMAuthenticator(apikey)
    cloudant_client = CloudantV1(authenticator=auth)
    cloudant_client.set_service_url(url)
    return cloudant_client

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

        # 2. Get Persistent Client
        client = get_client()

        # 3. Execute Benchmarking Logic
        rows, latency_ms = execute(client, req)

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
