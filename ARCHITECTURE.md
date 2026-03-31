# 🏛️ Architecture & Design Decisions

This document describes the architectural decisions, design patterns, and HighLoad optimizations applied in the Archive API project.

---

## 📐 Design Patterns

### Repository Pattern
All database operations are isolated in repository classes (`ArchiveRepository`, `PgIndexRepository`, `ChunkRepository`). Endpoints and services never write SQL directly — they call high-level methods like `create_archive()`, `bulk_upsert_indices()`, or `search_similar_chunks()`.

**Why:** Decouples business logic from the database layer. Swapping PostgreSQL for another DB requires changes only in the repository, not across the entire codebase.

### Factory Pattern
`ExtractorFactory` dynamically selects the correct extractor class based on the file extension (`.zip` → `ZipExtractor`, `.tar.gz` → `TarExtractor`).

**Why:** Eliminates `if/else` chains. Adding support for a new archive format requires only creating a new extractor class — no changes to existing code (OCP).

### Chain of Responsibility
`ValidationService` runs a file through a sequential chain of validators: `SizeValidator` → `MimeTypeValidator` → `SecurityValidator`. The first failure stops the chain immediately.

**Why:** Each validator has a single responsibility (SRP). Adding a new validation rule requires only creating a new `IFileValidator` subclass — no modifications to existing validators (OCP).

### Saga Pattern
When processing an archive fails after it was already uploaded to S3, the system rolls back by deleting the S3 object via `s3_service.delete_file()`. This prevents orphaned files accumulating in MinIO.

**Why:** Ensures consistency between S3 and PostgreSQL even when partial failures occur.

### Unit of Work
Each background task opens its own isolated database session and commits exactly once at the end of successful processing. On failure — `session.rollback()` reverts all changes atomically.

**Why:** Prevents partial writes. Either all extracted files are saved and the status is COMPLETED, or nothing is saved and the status is FAILED.

### Lifespan (Shared Clients)
The `aioboto3` S3 client and Redis connection pool are created once at server startup via FastAPI `lifespan` and shared across all requests through `app.state`.

**Why:** Creating a new S3 or Redis connection per request would exhaust the connection pool under load.

### Publisher/Subscriber (Redis Pub/Sub)
The Main API and RAG Service communicate exclusively via Redis Pub/Sub channels. The Main API publishes commands and subscribes to response channels. The RAG Service subscribes to command channels and publishes results back.

**Why:** Fully decouples the two services. The Main API never imports RAG code — it only knows about Redis channel names. Either service can be restarted independently without affecting the other.

---

## ⚡ HighLoad Optimizations

### Nginx (Reverse Proxy)
Nginx sits in front of FastAPI and buffers incoming file uploads before forwarding them to Uvicorn workers.

**Problem solved:** Without buffering, slow clients (Slowloris attack) hold Uvicorn worker threads open for the entire upload duration, exhausting the worker pool.

**Result:** Uvicorn workers receive complete requests instantly — slow clients only affect Nginx, not the application.

### PgBouncer (Connection Pooling)
PgBouncer runs in `transaction` mode between FastAPI/Celery workers and PostgreSQL.

**Problem solved:** Each async SQLAlchemy connection to PostgreSQL is a real OS-level TCP connection. Under load (20+ concurrent workers), opening hundreds of direct connections causes PostgreSQL to run out of `max_connections` and reject new ones.

**Configuration notes:**
- `prepared_statement_cache_size=0` — required for PgBouncer transaction mode compatibility
- Alembic connects directly to PostgreSQL (bypasses PgBouncer) to avoid migration issues
- FastAPI and Celery workers connect via PgBouncer on port `6432`

### Redis + Celery (Async Workers)
Archive processing is handled by Celery workers consuming tasks from a Redis queue, replacing FastAPI `BackgroundTasks`.

**Problem solved:** `BackgroundTasks` run in the same process as the API — a CPU-heavy extraction blocks the event loop. Celery workers run in separate processes and can be scaled horizontally.

**Scaling:** `docker-compose up --scale worker=3` launches 3 independent worker processes.

### Redis Connection Pool (Main API)
The Main API manages a single `ConnectionPool` initialized at startup and shared across all requests. Individual `Redis` instances borrow connections from the pool per request.

**Problem solved:** Creating a new physical Redis connection on every HTTP request would exhaust available sockets under load and add unnecessary latency.

### Dead Letter Queue (DLQ)
Tasks that fail 3 times are automatically moved to a Dead Letter Queue. The archive status is updated to `FAILED` with the error message preserved.

**Why:** Prevents infinite retry loops that would block the worker queue and consume resources indefinitely.

### Bulk Upserts (INSERT ... ON CONFLICT)
When saving TF-IDF/BM25 index scores to PostgreSQL, all records for a document are inserted in a single `INSERT ... VALUES (...), (...), (...)` statement with `ON CONFLICT DO UPDATE`.

**Problem solved:** N individual `INSERT` statements for N tokens would generate N round-trips to the database. A single bulk statement reduces this to 1 round-trip regardless of token count.

### GIN Index on JSONB
The `word_indices.scores` column stores token scores as JSONB. A GIN (Generalized Inverted Index) index is created on this column.

**Why:** GIN indexes decompose JSONB keys into individual index entries, making `WHERE scores ? 'word'` queries (existence check) extremely fast — O(log N) instead of O(N) full table scan.

### On-the-fly Indexing
The extractor streams file content directly into `IndexingService` during extraction — before writing to S3. This eliminates a second read pass from MinIO after extraction.

**Problem solved:** Without on-the-fly indexing, indexing would require: read from S3 → extract → index. With on-the-fly: extract → index simultaneously → write to S3. Eliminates N+1 I/O requests to MinIO.

### Token Budgeting & Lost-in-the-Middle Mitigation (RAG)
Before sending context to the LLM, `ContextProcessor` applies two optimizations. First, it counts tokens via `tiktoken` and drops chunks that would exceed the 3000-token budget. Second, it reorders remaining chunks so the highest-relevance chunks appear at the beginning and end of the prompt — since LLMs tend to lose attention to content in the middle of long contexts.

**Why:** Prevents token limit errors and improves answer quality without increasing API costs.

### Exponential Backoff on OpenAI Calls (RAG)
All OpenAI API calls in the RAG Service are wrapped with `tenacity` — up to 3 retries with exponential backoff starting at 2 seconds.

**Why:** OpenAI's API occasionally returns 429 (rate limit) or 5xx errors under load. Retrying with backoff handles transient failures transparently without crashing the handler.

---

## 🗄️ Database Schema

```
archives
├── id (PK, UUID)
├── filename
├── s3_object_name
├── status (ENUM: pending/processing/completed/failed)
├── error_message
└── created_at

extracted_files
├── id (PK, autoincrement)
├── archive_id (FK → archives.id)
├── file_name
├── size_bytes
└── s3_object_name

word_indices
├── id (PK, autoincrement)
├── archive_id (FK → archives.id)
├── filename
└── scores (JSONB) ← GIN index

document_chunks
├── id (PK, autoincrement)
├── archive_id (FK → archives.id)
├── filename
├── chunk_text
└── embedding (vector(1536)) ← pgvector cosine similarity
```

---

## 🧪 Load Testing Results

Load test conducted with **Locust** simulating 20-30 concurrent users performing:
1. `POST /upload-archives/` — uploading a 1MB ZIP archive
2. `POST /archives/{id}/index` — triggering indexing
3. `GET /search?q=word` — querying the search index

| Metric | Result |
|---|---|
| Peak RPS | 20+ |
| Median response time | < 200ms |
| 95th percentile | < 500ms |
| Error rate | < 1% |
| Workers scaled | 3 Celery workers |

---

## 🐳 Infrastructure Overview

```
                    ┌─────────┐
         Internet → │  Nginx  │ ← buffers uploads, protects from Slowloris
                    └────┬────┘
                         │
                    ┌────▼──────────┐
                    │   FastAPI     │ ← async API, returns 202 immediately
                    │   Main API    │
                    └────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
     publishes tasks         publishes RAG commands
              │                     │
    ┌─────────▼──────┐     ┌────────▼────────┐
    │  Redis (Celery) │     │  Redis (Pub/Sub) │
    │  task queue     │     │  rag_index_cmds  │
    └─────────┬───────┘     │  rag_search_reqs │
              │             └────────┬─────────┘
    ┌─────────▼──────────┐          │ subscribes
    │   Celery Workers   │  ┌───────▼──────────┐
    │  archive extraction│  │   RAG Service     │
    └──────┬─────────────┘  │  embeddings + LLM │
           │                └───────┬───────────┘
           │                        │
    ┌──────▼──────┐         ┌───────▼──────────────────┐
    │   MinIO     │         │  PgBouncer → PostgreSQL   │
    │  S3 storage │         │  pgvector (embeddings)    │
    └─────────────┘         │  JSONB (BM25 index)       │
                            └──────────────────────────┘
```