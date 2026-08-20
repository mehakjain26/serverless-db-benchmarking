import json
import logging
import os
from core import Request, RequestType
from database_clients.req_dynamodb import execute

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # 1. Parse Parameters
        if 'queryStringParameters' in event and event['queryStringParameters']:
            params = event['queryStringParameters']
            op_name = params.get('op', 'point_read')
        else:
            op_name = 'point_read'
            params = {}

        # 2. Build Request
        req = Request(type=RequestType(op_name), params=params)
        logger.info(f"Handling DynamoDB op: {op_name}")

        # 3. Execute
        rows, latency_ms = execute(req)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'adapter': 'dynamodb',
                'op': op_name,
                'latency_ms': latency_ms,
                'row_count': len(rows),
                'data': rows
            })
        }

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.error(f"Error: {err_msg}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(type(e).__name__),
                'details': str(e),
                'traceback': err_msg
            })
        }
