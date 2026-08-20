# Database Schemas & Data Ingestion Adapters

This folder contains the database schema creation, indexing patterns, data loaders, and database-specific Locust entrypoints used during direct database benchmarking.

---

## 📂 Database Adapter Structures

Each subdirectory corresponds to a target database backend:

### 1. [SQL / PostgreSQL](sql)
- **`setup_db.py`**: Drops and recreates the normalized GTFS relational tables (`stops`, `routes`, `calendar`, `trips`, `stop_times`) and applies composite indexing.
- **`ingest.py`**: Reads raw GTFS schedules from `data/` and streams multi-row SQL INSERT batches.
- **`locustfile_sql.py`**: Direct-mode Locust benchmarking runner executing relational SQL transactions.
- **`locustfile_http.py`**: Direct-mode Locust runner executing SQL benchmarks using HTTP requests.

### 2. [MongoDB](mongo)
- **`setup_db.py`**: Recreates collections and registers compound indices on Stop identifiers.
- **`ingest.py`**: Denormalizes and uploads transit schedules as JSON documents.
- **`locustfile_mongo.py`**: Direct-mode Locust runner executing BSON document queries.

### 3. [IBM Cloudant](cloudant)
- **`setup_db.py`**: Verifies CouchDB document databases and creates JSON query indexes.
- **`ingest.py`**: Denormalizes schedules and uploads documents via CouchDB bulk insert endpoints.
- **`locustfile_cloudant.py`**: Direct-mode Locust runner testing IBM Cloudant connections.

### 4. [Amazon DynamoDB](dynamodb)
- **`indices_dynamodb.py`**: Configures Global Secondary Indexes (`gsi_stop_departure` and `gsi_trip`) on the generic `pk` and `sk` primary attributes.
- **`ingest_dynamodb.py`**: Implements the Single-Table Design schema, parsing trips and stop times, mapping them to partition/sort keys, and executing high-throughput batch writes.
- **`query_dynamodb.py`**: Implements benchmark query operations using DynamoDB Key Expressions.

---

## ⚡ How to Set Up & Ingest Data

Before running workloads, you must initialize tables and ingest GTFS datasets into each database:

```bash
# 1. PostgreSQL Ingestion
python adapters/sql/setup_db.py
python adapters/sql/ingest.py

# 2. MongoDB Ingestion
python adapters/mongo/setup_db.py
python adapters/mongo/ingest.py

# 3. Cloudant Ingestion
python adapters/cloudant/setup_db.py
python adapters/cloudant/ingest.py

# 4. Amazon DynamoDB Ingestion
python adapters/dynamodb/ingest_dynamodb.py
```
Ensure that raw GTFS CSV schedule files are stored under the `data/` directory before starting ingestion.
