#pip install ibmcloudant ibm-cloud-sdk-core

from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

APIKEY = "JjKdiiC57TeQuW3ymUe-CFyQSumbNBYDYGr-Cddv0FNa"
URL = "https://41d4f0e7-8673-4ce6-998c-3906c7106fea-bluemix.cloudantnosqldb.appdomain.cloud"

client = None

try:
    authenticator = IAMAuthenticator(APIKEY)

    client = CloudantV1(authenticator=authenticator)
    client.set_service_url(URL)

    info = client.get_server_information().get_result()

    print("Connected to Cloudant!")
    print("Version:", info.get("version"))

finally:
    if client:
        del client
        client = None
        print("Client cleaned up.")