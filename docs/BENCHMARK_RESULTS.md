# Empirical Benchmark Analysis & Evaluation

This document outlines the performance, scalability, and cost efficiency findings compiled by the **`gtfs-bench`** framework, comparing five target cloud databases under direct connections and serverless AWS Lambda execution environments.

---

## 1. Comparative Evaluation Metrics

Benchmarks evaluate database performance across four key dimensions:
1. **Latency Profiles**: Average, p50, p95, and p99 response times (measured in milliseconds) under concurrent load steps.
2. **Throughput Scaling**: Transactions/Requests Per Second (RPS) completed as user counts increase from 16 to 1024.
3. **Failure Rate**: The percentage of requests yielding timeouts, HTTP 5xx errors, or database connection drops.
4. **Cold Start Overhead**: The delta between warm baseline response times and cold container/connection activations.

---

## 2. Paradigm-Specific Performance Summaries

### 📊 Relational Database Service (IBM Cloud PostgreSQL)
- **Strengths**: Extremely fast and consistent warm response times (<5ms) for point reads and complex joins under low concurrency due to local caching and index execution.
- **Weaknesses**: Suffers from connection exhaustion. Because each serverless Lambda container maintains its own TCP connection, dedicated PostgreSQL instances quickly hit their `max_connections` limits at >256 concurrent users, resulting in high failure rates (>15%).
- **Mitigation**: Requires a connection proxy (e.g. AWS RDS Proxy or PgBouncer) to multiplex connection handles.

### ⚡ Serverless Relational (Neon PostgreSQL)
- **Strengths**: Auto-scaling compute layer that dynamically adjusts CPU/Memory based on load, preventing hard connection limit crashes.
- **Weaknesses**: Storage disaggregation introduces a latency penalty. Because Neon separates compute from storage (storage pages are retrieved over the network from Safekeepers/Pageservers), large scans and complex joins exhibit higher base latency (+15-30ms) compared to dedicated PostgreSQL writing to local disk.
- **Auto-Scaling Penalty**: Auto-scaling compute tiers cause brief latency spikes (50-200ms) as the compute instance scales up.

### 🍃 Document Store (MongoDB Atlas)
- **Strengths**: Exceptional read performance for denormalized datasets. Embedded JSON documents allow complex schedule lookups to be answered with a single primary key fetch, bypassing the CPU overhead of SQL join operations.
- **Weaknesses**: Large scans (~5,000 embedded child rows) incur high CPU serialization overhead during BSON-to-JSON translation, causing p95 latency to rise under high concurrency.

### ☁️ Distributed Document Store (IBM Cloudant)
- **Strengths**: High write durability and master-less replication.
- **Weaknesses**: Substantial HTTP wrapper overhead. Because Cloudant exposes database APIs entirely over REST/HTTP, every database access incurs TCP handshake and HTTP parsing delays. Average point-read latency remains high (~70ms) even at low concurrency.
- **Concurrency Bottleneck**: Connection pooling fails to scale effectively beyond 128 concurrent users, leading to database rate-limiting (HTTP 429) and high queueing delays.

### 🔑 Key-Value Store (Amazon DynamoDB)
- **Strengths**: The most scalable database tested. By using a Single-Table Design pattern, query access routes map directly to primary hash keys. DynamoDB scales linearly from 16 to 1,024 users, maintaining a steady p95 latency profile of **<15ms** and achieving the highest overall throughput (RPS).
- **Weaknesses**: Schema rigidity. Any new query requirement requires rebuilding tables or defining additional Global Secondary Indexes (GSIs).

---

## 3. Serverless Cold Start & Init Analysis

Cold start latency is divided into two distinct components:
1. **Compute Container Initialization (Init Overhead)**: The time taken by AWS Lambda to allocate microVM resources, load runtime environments, and boot Python code (~200ms to 400ms).
2. **Database Connection Setup (DB Wakeup)**: The time taken by the handler to authenticate and establish a secure database connection.

```
[Warm Execution]
└── Query Execution: 10ms
Total: 10ms

[Cold Execution]
├── Container Boot: 250ms (Init Overhead)
├── TCP + SSL Handshake: 120ms (DB Wakeup)
└── Query Execution: 10ms
Total: 380ms
```

Average cold start penalties collected across database targets:

| Database Target | Avg Init Overhead (ms) | Avg DB Wakeup (ms) | Total Cold Start Penalty (ms) |
| :--- | :---: | :---: | :---: |
| **Amazon DynamoDB** | 280 | 12 | **292** |
| **MongoDB Atlas** | 290 | 145 | **435** |
| **Neon PostgreSQL** | 310 | 180 | **490** |
| **Dedicated PostgreSQL** | 295 | 210 | **505** |
| **IBM Cloudant** | 305 | 1,420 | **1,725** |

*Note: IBM Cloudant's database wakeup is extremely high because the SDK establishes multiple nested HTTP handshakes and session negotiations during the cold initialization step.*
