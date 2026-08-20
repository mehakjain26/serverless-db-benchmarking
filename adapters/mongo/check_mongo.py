import json
from pymongo import MongoClient

# --- CONFIG (derived from db_config.py & environment) ---
import os
from database_clients.db_config import MONGO

MONGO_URI = os.getenv("MONGO_URI", MONGO["uri"])
DB_NAME = os.getenv("MONGO_DB", MONGO["db"])
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", MONGO["collection"])

def main():
    print(f"--- Connecting to MongoDB Atlas ---")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Trigger connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 1. List Databases
    print("\n1. Databases on this cluster:")
    dbs = client.list_database_names()
    for db in dbs:
        print(f"  - {db}")

    if DB_NAME not in dbs:
        print(f"\n[INFO] Database '{DB_NAME}' does not exist yet.")
        return

    # 2. Check Collection and Counts
    db = client[DB_NAME]
    cols = db.list_collection_names()
    print(f"\n2. Collections in '{DB_NAME}':")
    for c in cols:
        count = db[c].count_documents({})
        print(f"  - {c}: {count:,} documents")

    # 3. Sample Documents
    if COLLECTION_NAME in cols:
        col = db[COLLECTION_NAME]
        print(f"\n3. Sample Documents in '{COLLECTION_NAME}':")
        samples = list(col.find({}, {"_id": 0, "type": 1, "transport_id": 1, "stop_id": 1, "trip_id": 1}).limit(5))
        
        if samples:
            for i, doc in enumerate(samples):
                print(f"  [{i+1}] {doc}")
        else:
            print("  - (Collection is empty)")

    client.close()

if __name__ == "__main__":
    main()
