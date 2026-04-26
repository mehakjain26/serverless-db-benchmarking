import json
from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# --- CREDENTIALS (from your db_config) ---
URL = "https://c078c512-de59-4236-8ebf-39f311b26cae-bluemix.cloudantnosqldb.appdomain.cloud"
APIKEY = "suNVFvme59ieXqmRCTTJNaLeFenMzhj0YsrKca-in6Kc"
DB_NAME = "gtfs"

def main():
    print(f"--- Connecting to Cloudant: {URL} ---")
    
    auth = IAMAuthenticator(APIKEY)
    client = CloudantV1(authenticator=auth)
    client.set_service_url(URL)

    # 1. List all databases
    print("\n1. Databases on this account:")
    dbs = client.get_all_dbs().get_result()
    for db in dbs:
        print(f"  - {db}")

    if DB_NAME not in dbs:
        print(f"\n[ERROR] Database '{DB_NAME}' DOES NOT EXIST!")
        return

    # 2. Get DB Info (Count)
    print(f"\n2. Statistics for '{DB_NAME}':")
    info = client.get_database_information(db=DB_NAME).get_result()
    doc_count = info.get('doc_count')
    print(f"  - Document Count: {doc_count}")
    print(f"  - Size on Disk: {info.get('sizes', {}).get('file', 0) / (1024*1024):.2f} MB")

    # 3. Sample Stops from View
    if doc_count > 0:
        print("\n3. Real STOP data (from Views):")
        try:
            result = client.post_view(
                db=DB_NAME,
                ddoc="stop_times",
                view="by_stop_departure",
                limit=5
            ).get_result()
            
            for row in result.get('rows', []):
                # row['key'] is likely [transport_id, stop_id, departure_time]
                tid, sid, dep = row['key']
                print(f"  - MATCH: transport_id={tid}, stop_id={sid} (departure: {dep})")
        except Exception as e:
            print(f"  - Could not query view: {e}")
            print("  - Falling back to document sampling...")
            docs = client.post_all_docs(db=DB_NAME, limit=10, include_docs=True).get_result()
            for row in docs.get('rows', []):
                doc = row.get('doc', {})
                if doc.get('type') == 'stops':
                    print(f"  - FOUND STOP: transport_id={doc.get('transport_id')}, stop_id={doc.get('stop_id')}")

    else:
        print("\n[INFO] The database is currently empty.")

if __name__ == "__main__":
    main()
