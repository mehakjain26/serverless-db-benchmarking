# System Architecture & Technical Specifications

This document detailing the system architecture, workload modeling, data schema transformations, and serverless compute wrapper design implemented in **`gtfs-bench`**.

---

## 1. Workload Modeling & Access Patterns

To evaluate database performance under realistic production loads, the framework generates query workloads modeled after real-world public transit applications. It targets public transit General Transit Feed Specification (GTFS) schedules, which combine static structural data (stops, routes, trips) with high-density dynamic schedule data (stop times).

The workload generator (`req_gen.py`) outputs six distinct data access patterns:

| Access Pattern | Technical Implementation | Research Objective |
| :--- | :--- | :--- |
| **Point Read** (`point_read`) | Primary Key lookup of a stop entry by `(transport_id, stop_id)`. | Measures baseline network round-trip time (RTT) and connection setup overhead by minimizing database processing time. |
| **Next Departures** (`next_departures`) | 3-way join of `stop_times` to `trips` and `routes` filtered by time window and sorted. | Tests join performance, secondary indexing efficiency, and execution plan optimization under concurrent workloads. |
| **Large Scan** (`large_scan`) | Index range scan + sort with a large result set (~5,000 rows). | Stresses database network throughput, disaggregated storage reading pipelines, and serialization/deserialization limits. |
| **Trips Per Route** (`trips_per_route`) | CPU-bound `GROUP BY` and `COUNT` aggregation across a relational join. | Tests how serverless compute throttling or CPU allocation constraints influence analytical query performance. |
| **Bulk Update** (`bulk_update_departures`) | Multi-row `UPDATE` statement shifting departure times. | Stresses database write throughput, concurrency control mechanisms (MVCC, locking, write ahead logs), and WAL network transfer times. |
| **Triple Aggregation** (`triple_agg`) | Multi-table correlated subquery aggregation without data transfer. | Evaluates database CPU limits under intense compute stress without introducing network I/O serialization bottlenecks. |

### Traffic Generators & Diurnal Simulation
Benchmarks can be run in two modes:
1. **Concurrency Steps**: Fixed concurrency levels (e.g. 16, 64, 128, 256, 512, 1024 concurrent users) executing workloads for a fixed period to observe saturation thresholds.
2. **Diurnal Load Curve (`diurnal_shape.py`)**: Simulates a 24-hour transit demand pattern, transitioning from low night traffic to high morning/evening rush hours. This evaluates auto-scaling responsiveness, connection scaling bottlenecks, and queueing delays.

---

## 2. Database Schema Transformations

A key objective of the research is analyzing how mapping relational transit data to different storage models affects scalability.

```
       [Raw Relational GTFS Data]
             /       |        \
            /        |         \
           v         v          v
   [Relational]  [Document]  [Key-Value]
   (PostgreSQL)  (MongoDB)   (DynamoDB)
```

### Relational Schema (PostgreSQL / Neon)
We map GTFS tables directly to a highly normalized relational model with primary and foreign key constraints:
- `stops` (PK: `transport_id, gtfs_stop_id`)
- `routes` (PK: `transport_id, gtfs_route_id`)
- `trips` (PK: `transport_id, gtfs_trip_id`, FK: `gtfs_route_id`)
- `stop_times` (PK: `id`, FK: `transport_id, gtfs_trip_id`, FK: `gtfs_stop_id`, Indices: composite index on `(transport_id, gtfs_stop_id, departure_time)`)

### Document Schema (MongoDB / Cloudant)
To leverage document-store patterns, relational schemas are denormalized into hierarchical JSON documents.
- Instead of executing multi-table joins at query time, child records (such as trip routing and calendar dates) are embedded directly within the parent document.
- Queries are answered by fetching a single rich document by key, avoiding join computation at the cost of document write size and storage redundancy.

### Key-Value Schema (Amazon DynamoDB Single-Table Design)
To achieve sub-15ms scaling at 1,024 concurrent connections in DynamoDB, we implement a **Single-Table Design**. All GTFS entities are stored in a single table, using generic primary keys `pk` and `sk` to group heterogeneous data types:
- **Stop records**: `pk = STOP#<transport_id>#<stop_id>`, `sk = METADATA`
- **Departure schedules**: `pk = STOP#<transport_id>#<stop_id>`, `sk = DEPARTURE#<departure_time>#<trip_id>`
- **Global Secondary Indexes (GSIs)**:
  - `gsi_stop_departure` (PK: `stop_pk`, SK: `departure_time`): Used to quickly perform range scans for next departures.
  - `gsi_trip` (PK: `trip_pk`, SK: `sk`): Used to fetch trip metadata and route info.

---

## 3. Serverless Compute Wrapper Design

To execute benchmarks under realistic serverless conditions, database requests are proxied through an **AWS Lambda Compute Layer**:

- **Lambda Handlers** (`infrastructure/lambda/`): Small Python scripts written with database drivers (e.g. `psycopg2` for PostgreSQL, `pymongo` for MongoDB, `boto3` for DynamoDB).
- **Execution Lifecycle**:
  - The Locust harness calls the Lambda's public **Function URL** via HTTP.
  - The Lambda receives the payload, executes the database query, measures database internal processing time (`latency_ms`), and returns a JSON response.
  - The benchmark harness captures both the **HTTP Round-Trip Time (RTT)** and the **Internal Database Latency**, allowing us to isolate compute cold start overheads from database execution delays.
- **Connection Management**:
  - Direct database connections from serverless runtimes are highly expensive because each container initialization requires a new TCP handshake and SSL negotiation.
  - In our Lambda adapters, database connections are initialized **outside the handler function** (global scope). This allows connection reuse across warm invocations of the same container instance.
