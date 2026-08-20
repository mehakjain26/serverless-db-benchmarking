# Scalability and Performance Analysis of Data Access Patterns in Serverless Applications

[![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![AWS Lambda](https://img.shields.io/badge/Compute-AWS%20Lambda-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/lambda/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![MongoDB Atlas](https://img.shields.io/badge/Database-MongoDB%20Atlas-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![Amazon DynamoDB](https://img.shields.io/badge/Database-Amazon%20DynamoDB-4053F6?logo=amazondynamodb&logoColor=white)](https://aws.amazon.com/dynamodb/)
[![Locust](https://img.shields.io/badge/Testing-Locust-B4A228?logo=python&logoColor=white)](https://locust.io/)

This repository hosts **`gtfs-bench`**, a cloud infrastructure database benchmarking suite designed to evaluate the trade-offs of relational, document, serverless SQL, and key-value database paradigms in serverless microservices. Using public transit data structured under the **General Transit Feed Specification (GTFS)**, this framework evaluates how database selection impacts latency, throughput, connection overhead, cold-start times, and overall cost efficiency.

---

## 🎯 Executive Summary & Research Motivation

Serverless compute layers (like AWS Lambda) scale rapidly, spinning up hundreds of isolated execution environments in milliseconds. However, traditional database backends are not designed for the highly dynamic, ephemeral connection scaling of serverless runtimes. Choosing the wrong database model can result in:
- **Severe connection exhaustion** under sudden traffic spikes.
- **High cold start latencies** due to connection setup and container initialization.
- **Performance bottlenecks** caused by disaggregated storage models (e.g. Serverless SQL).
- **Extremely high long-term maintenance costs**, forcing late-stage migrations.

This project empirically compares five prominent database options under realistic access patterns and concurrent user spikes up to **1,024 users**:
1. **Dedicated Relational**: PostgreSQL (IBM Cloud Databases)
2. **Serverless Relational**: Neon Serverless PostgreSQL
3. **Document Store**: MongoDB Atlas (JSON Document Model)
4. **Distributed NoSQL Document Store**: IBM Cloudant (CouchDB Engine)
5. **NoSQL Key-Value**: Amazon DynamoDB (Single-Table Design Pattern)

---

## 🏗️ Architecture Design

```mermaid
flowchart TB
    subgraph Client/Test Layer
        Harness[Locust Benchmark Harness]
    end

    subgraph Serverless Compute Layer (AWS Account A)
        Lambda[AWS Lambda Query Functions]
        API[Lambda Function URLs]
    end

    subgraph Data Access Layer
        subgraph Relational Backends
            IBM_PG[(IBM Cloud PostgreSQL)]
            Neon_PG[(Neon Serverless PostgreSQL)]
        end
        
        subgraph Document Backends
            Mongo[(MongoDB Atlas)]
            Cloudant[(IBM Cloudant)]
        end
        
        subgraph Key-Value Backends
            Dynamo[(Amazon DynamoDB - Account B)]
        end
    end

    Harness -->|HTTP Requests| API
    API --> Lambda
    
    Lambda -->|psycopg2 + Connection Pooling| IBM_PG
    Lambda -->|Serverless Connection Proxy| Neon_PG
    Lambda -->|pymongo| Mongo
    Lambda -->|ibmcloudant SDK| Cloudant
    Lambda -->|boto3 / Cross-Account IAM| Dynamo
```

---

## 📂 Reorganized Repository Structure

```
├── README.md                 # Project showcase (this file)
├── pyproject.toml            # Python build system metadata
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── bench.py                  # CLI benchmark orchestration entrypoint
├── cold_start.py            # CLI cold start measurement entrypoint
├── core/                     # Isolated Core Engine Package
│   ├── req_gen.py            # GTFS synthetic workload generator
│   ├── globals.py            # Global settings and workload weights
│   ├── locust_base.py        # Base Locust benchmark User class
│   ├── diurnal_shape.py      # Diurnal curve traffic generator
│   ├── fetch_catalog.py      # Ingestion helper to scan dataset catalog
│   ├── catalog_cache.json    # Cached keys to optimize query generation
│   └── codebook.toml         # Benchmark metadata
├── database_clients/         # Database Query Execution Engine
│   ├── README.md             # Query adapters documentation
│   ├── db_config.py          # Centralized database connection configurations
│   ├── req_sql.py            # PostgreSQL & Neon query execution engine
│   ├── req_mongo.py          # MongoDB Atlas document query adapter
│   ├── req_cloudant.py       # IBM Cloudant CouchDB query adapter
│   └── req_dynamodb.py       # Amazon DynamoDB key-value single-table adapter
├── adapters/                 # Database schema scripts & ingestion loaders
│   ├── README.md             # Ingestion & schemas documentation
│   ├── cloudant/             # IBM Cloudant view definitions & loader
│   ├── dynamodb/             # DynamoDB table definitions & query helpers
│   ├── mongo/                # MongoDB setup & catalog scripts
│   └── sql/                  # PostgreSQL schemas & SSL certificates
├── infrastructure/           # Multi-Cloud IaC (Terraform) and Serverless Compute
│   ├── README.md             # Infrastructure deployment guide
│   ├── terraform/            # IaC scripts (provider, variables, resources)
│   ├── lambda/               # Serverless AWS Lambda handler code
│   └── scripts/              # Lambda zip-packaging build shell scripts
├── analytics/                # Data Analytics & Plot generation scripts
│   ├── plot_results.py       # Generates latency, throughput, and error graphs
│   └── plot_diurnal.py       # Generates diurnal test analytical graphs
├── docs/                     # Academic Specifications
│   ├── ARCHITECTURE.md       # Technical design spec (workloads, schemas)
│   └── BENCHMARK_RESULTS.md  # Detailed research outcomes & analysis
└── results/                  # Locust CSV statistics, execution logs & output plots
```

---

## 📈 Key Findings & Performance Visualizations

Detailed analytical breakdowns are available in [docs/BENCHMARK_RESULTS.md](docs/BENCHMARK_RESULTS.md). Key takeaways include:

1. **Connection Pooling Trade-Offs**: Dedicated PostgreSQL scales poorly beyond 256 concurrent connections without a connection pooler (like PgBouncer).
2. **Key-Value Efficiency**: Amazon DynamoDB achieved sub-15ms p95 latencies up to 1,024 concurrent connections due to its decentralized storage and HTTP connection model.
3. **Disaggregated Storage Latency**: Neon Serverless SQL experiences minor latency spikes during compute-tier auto-scaling and storage-node WAL reads.
4. **Cold Start Init Penalties**: Python AWS Lambda containers require ~250-400ms container start-up times, while database connection setups add an extra 100ms (PostgreSQL/Mongo) to 1500ms (Cloudant handshake).

---

## 🚀 Quickstart Guide

### 1. Installation
Install the project dependencies locally in your Python environment:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the configuration template and fill in your connection credentials:
```bash
cp .env.example .env
```

### 3. Deploy Multi-Cloud Infrastructure (Terraform)
Navigate to the Terraform folder, configure your access variables, and deploy:
```bash
cd infrastructure/terraform
terraform init
terraform apply
```
*For detailed infrastructure deployment steps, see [infrastructure/README.md](infrastructure/README.md).*

### 4. Database Setup & Ingestion
To populate the databases with sample GTFS transit datasets, navigate to the adapters folder and follow the instructions in [adapters/README.md](adapters/README.md):
```bash
# Example: PostgreSQL ingestion
python adapters/sql/setup_db.py
python adapters/sql/ingest.py
```

### 5. Running Benchmark Workloads
Run fixed concurrency benchmark trials or simulate a diurnal transit curve load:
```bash
# Run a direct benchmark on the SQL adapter with 16, 64, and 128 users
python bench.py --mode direct --adapters sql --users 16 64 128 --time 2m

# Run an HTTP mode benchmark simulating diurnal traffic
python bench.py --mode http --adapters dynamodb mongo --diurnal
```

### 6. Cold Start Microbenchmarking
Measure the exact cold start penalty (container init + connection setup) vs. warm execution:
```bash
python cold_start.py --service neon --mode http --url https://your-lambda-url.on.aws/ --samples 5 --idle 480
```

### 7. Analytical Plotting
Compile Locust benchmark logs and generate latency, throughput, and error graphs:
```bash
python analytics/plot_results.py
```
Output charts are saved directly under the `results/figures/` folder.

---

## 👥 Authors
- **Mehak Jain**
- **Raghavan Balanathan**
- **Zach Heskett**

Developed as a Cloud Computing research project (CS 551). For detailed queries regarding schema designs or performance metrics, refer to the [docs/](docs/) directory.
