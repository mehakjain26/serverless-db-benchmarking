# Database Query Adapter Package (`database_clients/`)

This directory is a Python package containing the core database query adapters and client initialization logic. It acts as the translation layer mapping synthetic workloads (`core/req_gen.py`) to native driver queries across PostgreSQL, Neon, MongoDB Atlas, IBM Cloudant, and Amazon DynamoDB.

---

## 🏗️ Design & Role in Architecture

Rather than maintaining separate codebases for local benchmarks and remote serverless microservices, this project uses a unified **Adapter Pattern**. The scripts in this directory are imported directly by:
1. **Local Direct Benchmarks**: `bench.py --mode direct` and `cold_start.py --mode direct` load these adapters directly into the Locust thread pool.
2. **Serverless AWS Lambda Functions**: The Terraform deployment pipeline packages this folder into AWS Lambda handlers that call these exact adapters under HTTP trigger events.

```
                      [bench.py (Direct Mode)]
                                 |
                                 v
 [AWS Lambda (HTTP Mode)] -> [database_clients/req_*.py] -> [Target Database]
```

---

## 📂 Submodule Specifications

- **`db_config.py`**: Reads connection configurations (hosts, ports, database names, users, and passwords) from environment variables using `os.getenv` with fallback defaults.
- **`req_sql.py`**: Relational adapter using `psycopg2`. Implements parametrized SQL queries for Stop schedules, Next Departure joins, Scans, and Aggregations.
- **`req_mongo.py`**: Document adapter using `pymongo`. Connects to MongoDB Atlas cluster URIs and queries denormalized stop documents.
- **`req_cloudant.py`**: CouchDB document adapter using `ibmcloudant` SDK. Connects via API keys and translates queries to JSON payloads over HTTPS.
- **`req_dynamodb.py`**: Key-value adapter using `boto3`. Connects to Amazon DynamoDB and performs Query, Scan, GetItem, and BatchWriteItem operations mapping to Single-Table indices.

---

## 🔒 Security & CA Certificate

- **`ibm_postgres_ca.crt`**: The Root Certificate Authority (CA) cert needed to authorize secure SSL/TLS sessions (`verify-full`) with IBM Cloud PostgreSQL databases.
- **Note**: Connection passwords are **never** hardcoded in this codebase. Refer to the root `.env.example` to define connection credentials locally.
