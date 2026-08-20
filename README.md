# Scalability and Performance Analysis of Data Access Patterns in Serverless Applications

[![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![AWS Lambda](https://img.shields.io/badge/Compute-AWS%20Lambda-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/lambda/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![MongoDB Atlas](https://img.shields.io/badge/Database-MongoDB%20Atlas-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![Amazon DynamoDB](https://img.shields.io/badge/Database-Amazon%20DynamoDB-4053F6?logo=amazondynamodb&logoColor=white)](https://aws.amazon.com/dynamodb/)
[![Locust](https://img.shields.io/badge/Testing-Locust-B4A228?logo=python&logoColor=white)](https://locust.io/)
[![Presentation](https://img.shields.io/badge/Google_Slides-Presentation-EA4335?logo=googleslides&logoColor=white)](https://docs.google.com/presentation/d/1G8OUM8Bu_zObg03lvbxhDjvKZT5IqSJHlNo0c8yxtC4/edit?usp=sharing)

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
    subgraph "Client / Test Layer"
        Harness[Locust Benchmark Harness]
    end

    subgraph "Serverless Compute Layer (AWS Account A)"
        Lambda[AWS Lambda Query Functions]
        API[Lambda Function URLs]
    end

    subgraph "Data Access Layer"
        subgraph "Relational Backends"
            IBM_PG[(IBM Cloud PostgreSQL)]
            Neon_PG[(Neon Serverless PostgreSQL)]
        end
        
        subgraph "Document Backends"
            Mongo[(MongoDB Atlas)]
            Cloudant[(IBM Cloudant)]
        end
        
        subgraph "Key-Value Backends"
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

## 📂 Repository Structure

- **`README.md`**: Project showcase with dynamic badges, system architecture diagrams, key research findings, and quickstart commands.
- **`core/`**: Workload generator ([req_gen.py](core/req_gen.py)), Locust base classes, and diurnal curve engines.
- **`database_clients/`**: Query execution adapters for PostgreSQL, Neon, MongoDB, Cloudant, and DynamoDB.
- **`adapters/`**: Schemas, index creation scripts, and data loaders.
- **`infrastructure/`**: Modular Terraform (IaC) files (`provider.tf`, `dynamo.tf`, `neon.tf`, `ibm_postgres.tf`) and AWS Lambda handlers.
- **`analytics/`**: Latency, throughput, and error plot generation scripts.
- **`docs/`**: Technical architecture spec ([ARCHITECTURE.md](docs/ARCHITECTURE.md)) and empirical benchmark evaluation results ([BENCHMARK_RESULTS.md](docs/BENCHMARK_RESULTS.md)).

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

## 🤖 AI Agents & Agentic Engineering

This repository leverages **Agentic Coding Workflows** and AI Agent tooling for system architecture refactoring, automated benchmark orchestration, and security sanitization:

- **Architectural Refactoring**: Autonomous package isolation (`core/`, `database_clients/`, `adapters/`, `infrastructure/`, `analytics/`) and clean modular separation.
- **Security & Secret Sanitization**: Automated parameterization of database credentials into `.env.example` templates and dynamic environment lookups (`os.getenv`), eliminating hardcoded keys across multi-cloud Terraform setups.
- **Automated Benchmarking & Analytics**: Agent-assisted synthetic GTFS load generation (`req_gen.py`), Locust load testing harness automation, and automated plot generation (`plot_results.py`).
- **IaC Verification & System Documentation**: Multi-cloud Infrastructure as Code (Terraform) validation, cross-account IAM policy generation, and empirical performance evaluation documentation ([ARCHITECTURE.md](docs/ARCHITECTURE.md), [BENCHMARK_RESULTS.md](docs/BENCHMARK_RESULTS.md)).

---

## 👥 Authors & Presentation
- **Mehak Jain**
- **Raghavan Balanathan**
- **Zach Heskett**

📊 **Project Presentation**: [CS 551 Google Slides Presentation Deck](https://docs.google.com/presentation/d/1G8OUM8Bu_zObg03lvbxhDjvKZT5IqSJHlNo0c8yxtC4/edit?usp=sharing)

Developed as a Cloud Computing research project (CS 551). For detailed queries regarding schema designs or performance metrics, refer to the [docs/](docs/) directory.
