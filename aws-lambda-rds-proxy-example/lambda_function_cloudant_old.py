import os
from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

def lambda_handler(event, context):
    try:
        apikey = os.environ['CLOUDANT_APIKEY']
        url = os.environ['CLOUDANT_URL']
        
        print(f"Connecting to Cloudant at: {url}")
        
        authenticator = IAMAuthenticator(apikey)
        client = CloudantV1(authenticator=authenticator)
        client.set_service_url(url)
        
        # Test connection
        info = client.get_server_information().get_result()
        
        return {
            'statusCode': 200,
            'body': {
                'message': "Successfully connected to Cloudant",
                'version': info.get("version")
            }
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': {
                'error': "Cloudant Connection Failed",
                'details': str(e)
            }
        }
    finally:
        # Clean up client
        if 'client' in locals():
            del client
