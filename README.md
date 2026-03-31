# 📦 Archive API

A FastAPI-based service that accepts archive files (`.zip`, `.tar.gz`), extracts their text content, stores raw archives in MinIO (S3-compatible), persists extracted data in PostgreSQL, and provides both keyword-based (BM25) and semantic vector (RAG) search powered by OpenAI embeddings.

---

## 🏗️ Architecture

```
POST /upload-archives/
        │
        ├── Validates file type
        ├── Saves archive metadata to DB (status: PENDING)
        ├── Uploads raw archive to MinIO (S3)
        └── Dispatches task to Celery
                │
                ├── Extracts text files (streaming, no OOM)
                ├── Saves extracted files to DB
                ├── Updates status → COMPLETED
                └── On failure → rollback MinIO + status → FAILED

POST /rag/index/{archive_id}
        │
        └── Publishes indexing command to Redis
                │
                └── RAG Service (subscriber)
                        ├── Downloads files from MinIO
                        ├── Splits text into chunks (LangChain)
                        ├── Generates embeddings (OpenAI)
                        └── Stores vectors in PostgreSQL (pgvector)

POST /rag/search
        │
        ├── Publishes search request to Redis (with correlation_id)
        ├── Subscribes to rag_responses:<correlation_id>
        └── RAG Service (subscriber)
                ├── Rewrites query for better retrieval
                ├── Generates query embedding (OpenAI)
                ├── Searches similar chunks via cosine distance
                ├── Applies token budgeting + lost-in-the-middle
                ├── Generates answer (gpt-4o-mini)
                └── Publishes answer back to Redis → Main API → Client
```

**Key patterns used:**
- **Repository Pattern** — all DB operations isolated in repository classes
- **Factory Pattern** — `ExtractorFactory` dynamically selects `.zip` or `.tar.gz` extractor
- **Saga Pattern** — S3 file is deleted if DB transaction fails
- **Unit of Work** — single `session.commit()` per background task
- **Lifespan** — global S3 client and Redis pool initialized once on server start
- **Publisher/Subscriber** — Main API and RAG Service communicate via Redis Pub/Sub

---

## 🚀 Quick Start (Docker)

### 1. Clone the repository

```bash
git clone <repo-url>
cd archive-api
```

### 2. Create `.env` files

```bash
cp .env.example .env
cp rag-service/.env.example rag-service/.env
```

Edit `rag-service/.env` and set your OpenAI API key:
```
OPENAI_API_KEY=sk-proj-your-real-key-here
```

### 3. Start all services

```bash
docker-compose up --build
```

This will start:
- **PostgreSQL** (pgvector) on port `5432`
- **PgBouncer** on port `6432`
- **Redis** on port `6379`
- **MinIO** on port `9005` (API) and `9091` (Console)
- **FastAPI Main API** behind Nginx on port `80`
- **RAG Service** on port `8001`
- **Celery Workers** (3 instances)

Alembic migrations run automatically before the API starts.

### 4. Verify the API is running

```bash
curl http://localhost/docs
```

---

## ⚙️ Environment Variables

### Main API (`.env`)

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `postgrespassword` |
| `POSTGRES_DB` | Database name | `archive_db` |
| `DATABASE_URL` | Direct async DB connection string | `postgresql+asyncpg://postgres:postgrespassword@db:5432/archive_db` |
| `DATABASE_URL_PGBOUNCER` | PgBouncer connection string | `postgresql+asyncpg://postgres:postgrespassword@pgbouncer:5432/archive_db` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `MINIO_ENDPOINT` | MinIO endpoint URL | `http://minio:9000` |
| `MINIO_ROOT_USER` | MinIO access key | `minioadmin` |
| `MINIO_ROOT_PASSWORD` | MinIO secret key | `minioadmin` |
| `MINIO_BUCKET_NAME` | Bucket name for archives | `archives-bucket` |
| `MAX_UPLOAD_SIZE_MB` | Max upload file size in MB | `50` |
| `MAX_EXTRACT_SIZE_MB` | Max single extracted file size in MB | `200` |

### RAG Service (`rag-service/.env`)

| Variable | Description | Example |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-...` |
| `DATABASE_URL` | Direct async DB connection string | `postgresql+asyncpg://postgres:postgrespassword@db:5432/archive_db` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `MINIO_ENDPOINT` | MinIO endpoint URL | `http://minio:9000` |
| `MINIO_ROOT_USER` | MinIO access key | `minioadmin` |
| `MINIO_ROOT_PASSWORD` | MinIO secret key | `minioadmin` |
| `MINIO_BUCKET_NAME` | Bucket name for archives | `archives-bucket` |
| `LLM_MODEL_NAME` | OpenAI LLM model | `gpt-4o-mini` |
| `EMBEDDING_MODEL_NAME` | OpenAI embedding model | `text-embedding-3-small` |

> ⚠️ For local development use `localhost` instead of `db`, `minio`, `redis` in the URLs.

---

## 📡 API Endpoints

### `POST /upload-archives/`

Upload an archive file for processing.

**Accepts:** `.zip`, `.tar.gz`, `.tgz`

**Returns:** `202 Accepted` with archive ID and `PENDING` status immediately.

```bash
curl -X POST http://localhost/upload-archives/ \
  -F "file=@/path/to/archive.zip"
```

**Response:**
```json
{
  "archive_id": "3f2a1b4c-...",
  "filename": "archive.zip",
  "status": "pending",
  "message": "Archive is being processed in the background."
}
```

---

### `GET /archives/{archive_id}`

Check the processing status of an uploaded archive.

```bash
curl http://localhost/archives/3f2a1b4c-...
```

**Response (COMPLETED):**
```json
{
  "archive_id": "3f2a1b4c-...",
  "status": "completed",
  "s3_url": "http://minio:9000/archives-bucket/3f2a1b4c_archive.zip",
  "error_message": null,
  "extracted_files": [
    { "file_name": "readme.txt", "size_bytes": 1024 },
    { "file_name": "data.json", "size_bytes": 2048 }
  ]
}
```

---

### `POST /search`

Keyword-based search using BM25 / JSONB index.

```bash
curl -X POST http://localhost/search \
  -H "Content-Type: application/json" \
  -d '{"query": "server configuration", "top_k": 5}'
```

**Response:**
```json
{
  "query": "server configuration",
  "results": [
    {
      "archive_id": "3f2a1b4c-...",
      "filename": "config.txt",
      "s3_object_name": "http://...",
      "score": 0.85
    }
  ]
}
```

---

### `POST /rag/index/{archive_id}`

Trigger vector indexing for an archive. Downloads files from MinIO, splits them into chunks, generates embeddings via OpenAI, and stores vectors in PostgreSQL.

```bash
curl -X POST http://localhost/rag/index/3f2a1b4c-...
```

**Response:**
```json
{
  "archive_id": "3f2a1b4c-...",
  "correlation_id": "a1b2c3d4-...",
  "message": "Vector indexing task has been queued."
}
```

---

### `POST /rag/search`

Semantic vector search with LLM-generated answer. Returns a natural language response based on the most relevant document chunks.

```bash
curl -X POST http://localhost/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to configure the server timeout?", "top_k": 10}'
```

**Response:**
```json
{
  "correlation_id": "a1b2c3d4-...",
  "query": "how to configure the server timeout?",
  "answer": "According to the documentation, the server timeout can be configured by setting the `timeout` parameter in config.yml to the desired value in seconds..."
}
```

> ⚠️ Returns `504 Gateway Timeout` if the RAG service does not respond within 15 seconds.

---

## 🗂️ Project Structure

```
archive-api/
│
├── app/                              # Main API
│   ├── api/
│   │   ├── endpoints.py              # Archives + BM25 search endpoints
│   │   └── rag_endpoints.py          # RAG index + search endpoints
│   ├── core/
│   │   ├── config.py                 # Pydantic Settings (.env validation)
│   │   ├── exceptions.py             # Global exception handlers
│   │   ├── logger.py                 # Loguru logger setup
│   │   └── redis.py                  # Redis connection pool dependency
│   ├── db/
│   │   └── database.py               # Async SQLAlchemy engine and session
│   ├── models/
│   │   ├── archive.py                # Archive and ExtractedFile ORM models
│   │   ├── word_index.py             # WordIndex ORM model (BM25)
│   │   └── document_chunk.py         # DocumentChunk ORM model (pgvector)
│   ├── repositories/
│   │   └── archive_repo.py           # Repository pattern for DB operations
│   ├── schemas/
│   │   └── contracts.py              # Pydantic DTOs and enums
│   ├── services/
│   │   ├── archive_svc.py            # Main service (S3 + extractor + DB)
│   │   ├── extractor.py              # Factory pattern for zip/tar.gz extraction
│   │   └── s3_service.py             # MinIO integration via aioboto3
│   └── main.py                       # FastAPI app with lifespan
│
├── rag-service/                      # RAG Microservice
│   ├── app/
│   │   ├── api/
│   │   │   └── system.py             # Health check endpoint
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings
│   │   │   ├── db.py                 # Async SQLAlchemy session
│   │   │   ├── logger.py             # Loguru with correlation_id
│   │   │   ├── redis_client.py       # Redis connection pool
│   │   │   └── s3.py                 # MinIO client
│   │   ├── models/
│   │   │   └── chunk.py              # DocumentChunk ORM model
│   │   ├── repositories/
│   │   │   ├── archive_repository.py # Fetch extracted files from DB
│   │   │   └── chunk_repository.py   # Save and search chunks
│   │   ├── services/
│   │   │   ├── context_processor.py  # Token budgeting + lost-in-the-middle
│   │   │   ├── embedding_service.py  # Chunking + OpenAI embeddings
│   │   │   ├── handlers.py           # Index and search command handlers
│   │   │   ├── llm_service.py        # Query rewriting + answer generation
│   │   │   ├── pubsub_handler.py     # Redis Pub/Sub subscriber
│   │   │   └── s3_service.py         # MinIO file download
│   │   └── main.py                   # FastAPI app with lifespan + subscriber
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
│
├── alembic/                          # DB migrations
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## 👥 Team

| Developer | Responsibility |
|---|---|
| Developer A | PostgreSQL + pgvector, SQLAlchemy models, Alembic migrations, Redis Pub/Sub infrastructure (Main API), RAG endpoints, fault tolerance (504 timeout) |
| Developer B | RAG microservice, embedding pipeline, vector search, LLM integration, Docker infrastructure, documentation |