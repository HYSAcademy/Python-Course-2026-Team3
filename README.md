# 📦 Archive API
 
A FastAPI-based service that accepts archive files (`.zip`, `.tar.gz`), extracts their text content, stores raw archives in MinIO (S3-compatible), and persists extracted data in PostgreSQL.
 
---
 
## 🏗️ Architecture
 
```
POST /upload-archives/
        │
        ├── Validates file type
        ├── Saves archive metadata to DB (status: PENDING)
        ├── Uploads raw archive to MinIO (S3)
        └── Dispatches BackgroundTask
                │
                ├── Extracts text files (streaming, no OOM)
                ├── Saves extracted files to DB
                ├── Updates status → COMPLETED
                └── On failure → rollback MinIO + status → FAILED
```
 
**Key patterns used:**
- **Repository Pattern** — all DB operations isolated in `ArchiveRepository`
- **Factory Pattern** — `ExtractorFactory` dynamically selects `.zip` or `.tar.gz` extractor
- **Saga Pattern** — S3 file is deleted if DB transaction fails
- **Unit of Work** — single `session.commit()` per background task
- **Lifespan** — global `aioboto3` S3 client initialized once on server start
 
---
 
## 🚀 Quick Start (Docker)
 
### 1. Clone the repository
 
```bash
git clone <repo-url>
cd archive-api
```
 
### 2. Create `.env` file
 
```bash
cp .env.example .env
```
 
Edit `.env` if needed (default values work out of the box with Docker).
 
### 3. Start all services
 
```bash
docker-compose up --build
```
 
This will start:
- **PostgreSQL** on port `5432`
- **MinIO** on port `9005` (API) and `9091` (Console)
- **FastAPI** on port `8000`
 
Alembic migrations run automatically before the API starts.
 
### 4. Verify the API is running
 
```bash
curl http://localhost:8000/docs
```
 
---
 
## ⚙️ Environment Variables
 
| Variable | Description | Example |
|---|---|---|
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `postgrespassword` |
| `POSTGRES_DB` | Database name | `archive_db` |
| `DATABASE_URL` | Full async DB connection string | `postgresql+asyncpg://postgres:postgrespassword@db:5432/archive_db` |
| `MINIO_ENDPOINT` | MinIO endpoint URL | `http://minio:9000` |
| `MINIO_ROOT_USER` | MinIO access key | `minioadmin` |
| `MINIO_ROOT_PASSWORD` | MinIO secret key | `minioadmin` |
| `MINIO_BUCKET_NAME` | Bucket name for archives | `archives-bucket` |
| `MAX_UPLOAD_SIZE_MB` | Max upload file size in MB | `50` |
| `MAX_EXTRACT_SIZE_MB` | Max single extracted file size in MB | `200` |
 
> ⚠️ For local development use `localhost` instead of `db` and `minio` in the URLs.
 
---
 
## 📡 API Endpoints
 
### `POST /upload-archives/`
 
Upload an archive file for processing.
 
**Accepts:** `.zip`, `.tar.gz`, `.tgz`
 
**Returns:** `202 Accepted` with archive ID and `PENDING` status immediately.
 
```bash
curl -X POST http://localhost:8000/upload-archives/ \
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
curl http://localhost:8000/archives/3f2a1b4c-...
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
 
**Response (FAILED):**
```json
{
  "archive_id": "3f2a1b4c-...",
  "status": "failed",
  "error_message": "Unsupported format for file.pdf. Only .zip and .tar.gz are allowed.",
  "extracted_files": []
}
```
 
---
 
## 🗂️ Project Structure
 
```
archive-api/
│
├── app/
│   ├── api/
│   │   └── endpoints.py        # POST /upload-archives/, GET /archives/{id}
│   ├── core/
│   │   ├── config.py           # Pydantic Settings (.env validation)
│   │   ├── exceptions.py       # Global exception handlers
│   │   └── logger.py           # Loguru logger setup
│   ├── db/
│   │   └── database.py         # Async SQLAlchemy engine and session
│   ├── models/
│   │   └── archive.py          # Archive and ExtractedFile ORM models
│   ├── repositories/
│   │   └── archive_repo.py     # Repository pattern for DB operations
│   ├── schemas/
│   │   └── contracts.py        # Pydantic DTOs and ArchiveStatus enum
│   ├── services/
│   │   ├── archive_svc.py      # Main service (S3 + extractor + DB)
│   │   ├── extractor.py        # Factory pattern for zip/tar.gz extraction
│   │   └── s3_service.py       # MinIO integration via aioboto3
│   └── main.py                 # FastAPI app with lifespan
│
├── alembic/                    # DB migrations
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
| Developer A | PostgreSQL, SQLAlchemy models, Alembic, Repository pattern, Pydantic config, Exception middleware |
| Developer B | FastAPI endpoints, S3 integration, archive extraction, Docker infrastructure, documentation |