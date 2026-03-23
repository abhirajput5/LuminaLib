# Lumina 📚⚡

AI-powered document processing and summarization system built with a scalable, serverless-inspired architecture.

---

## 🚀 Overview

Lumina is a backend system that:

- Accepts document uploads (PDFs)
- Stores them in object storage (MinIO/S3)
- Processes them asynchronously using Celery
- Uses LLMs (Ollama/OpenAI-compatible) to generate summaries
- Updates results in a PostgreSQL database

---

## 🧠 Why Lumina?

This project is designed to demonstrate:

- Clean Architecture (Controller → Service → Repository)
- Async + Sync separation (FastAPI vs Celery)
- Pluggable LLM providers
- Pluggable storage backends
- Production-ready patterns (queue, workers, retries)

---

## 🏗️ Architecture

```

Client → FastAPI → PostgreSQL
↓
Celery Queue (Redis)
↓
Worker
↓
Storage (MinIO/S3) + LLM (Ollama/OpenAI)

```

---

## 📦 Features

- 📄 PDF upload & storage
- 🔄 Background processing using Celery
- 🧠 LLM-based summarization
- ⚙️ Configurable storage backend (MinIO / S3)
- 🤖 Configurable LLM provider (Ollama / OpenAI)
- 🧩 Modular codebase (easy to extend)

---

## 🛠️ Tech Stack

- **Backend**: FastAPI
- **Queue**: Celery + Redis
- **Database**: PostgreSQL (psycopg3)
- **Storage**: MinIO (S3-compatible)
- **LLM**: Ollama / OpenAI-compatible APIs
- **Containerization**: Docker

---

## ⚡ Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/lumina.git
cd lumina
```

---

### 2. Create `.env` file

```env
POSTGRES_USER=lumina_user
POSTGRES_PASSWORD=lumina_superuser_password
POSTGRES_DB=lumina_db
POSTGRES_PORT=5432
POSTGRES_HOST=db

DB_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

STORAGE_PROVIDER=minio
LLM_PROVIDER=ollama

MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=lumina

S3_BUCKET_NAME=lumina
S3_REGION=us-east-1
S3_ACCESS_KEY=s3-access-key-for-lumina
S3_SECRET_KEY=s3-secret-key-for-lumina

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

OLLAMA_API_BASE=http://ollama:11434
OLLAMA_MODEL_NAME=tinyllama


OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o-mini
```

---

### 3. Run with Docker

```bash
docker compose up --build
```

---

### 4. Access services

Here’s a clean, production-style version of your **“Access services”** section with endpoints + credentials added:

---

### 4. Access Services

#### 🚀 Application & Core APIs

- **FastAPI Backend**
  [http://localhost:8000](http://localhost:8000)

- **Ollama (LLM API)**
  [http://localhost:11434](http://localhost:11434)

---

#### 🗄️ Database & Admin

- **PostgreSQL**
  - Host: `localhost`
  - Port: `5432`
  - Database: `lumina_db`
  - User: `lumina_user`
  - Password: `lumina_superuser_password`

- **PgAdmin (DB GUI)**
  [http://localhost:5050](http://localhost:5050)
  - Email: `lumina@example.com`
  - Password: `lumina_pgadmin_password`

---

#### 📦 Object Storage

- **MinIO API**
  [http://localhost:9000](http://localhost:9000)

- **MinIO Console (UI)**
  [http://localhost:9001](http://localhost:9001)
  - Username: `minioadmin`
  - Password: `minioadmin123`

---

#### ⚡ Background Processing

- **Redis (Broker)**
  - Host: `localhost`
  - Port: `6379`

- **Celery Worker**
  - Runs internally (no direct UI)

- **Flower (Celery Monitoring UI)**
  [http://localhost:5555](http://localhost:5555)

---

#### 📊 Observability & Logging

- **Grafana Dashboard**
  [http://localhost:3000](http://localhost:3000)
  - Username: `admin`
  - Password: `admin`

- **Loki (Log Aggregation API)**
  [http://localhost:3100](http://localhost:3100)

- **Promtail (Log Shipper)**
  - Runs internally (no UI)

---

### Why this structure matters (think like a system designer)

- You access APIs → FastAPI / Ollama
- You debug DB → PgAdmin
- You track async jobs → Flower
- You monitor system → Grafana
- You store files → MinIO

- **Data layer** → PostgreSQL + MinIO
- **Compute layer** → FastAPI + Celery
- **Messaging layer** → Redis
- **AI layer** → Ollama
- **Observability layer** → Loki + Grafana
- **Control layer (human interface)** → PgAdmin, Flower, Grafana

---

## 🔄 How It Works

### Step-by-step flow:

1. User uploads a document via API
2. File is stored in MinIO/S3
3. Database record is created (`status=processing`)
4. Celery task is triggered
5. Worker:
   - Downloads file
   - Extracts text
   - Sends to LLM
   - Saves summary

6. Status updated to `completed`

---

## 🔌 Switching Providers (No Code Change)

### LLM Switching

| Provider | Config                |
| -------- | --------------------- |
| Ollama   | `LLM_PROVIDER=ollama` |
| OpenAI   | `LLM_PROVIDER=openai` |

---

### Storage Switching

| Storage | Config               |
| ------- | -------------------- |
| MinIO   | `STORAGE_TYPE=minio` |
| S3      | `STORAGE_TYPE=s3`    |

---

## 📂 Project Structure

```
app/
│
├── api/                # FastAPI routes
├── services/           # Business logic
├── repositories/       # DB access layer
├── models/             # Data schemas
├── tasks/              # Celery tasks
├── llm/                # LLM providers
├── storage/            # Storage abstraction
├── db/                 # DB connection (sync + async)
├── core/               # Config, utils
```

---

## 🧩 Key Design Decisions

### 1. Sync vs Async Separation

- FastAPI → async DB (high concurrency)
- Celery → sync DB (simpler, stable for workers)

---

### 2. LLM Abstraction

Factory pattern:

```python
provider = get_llm_provider()
provider.generate_summary(text)
```

➡️ Allows easy extension to:

- Claude
- Gemini
- Local models

---

### 3. Storage Abstraction

```python
storage = get_storage()
storage.upload(file)
storage.download(path)
```

➡️ Avoids vendor lock-in

---

### 4. Background Processing

- Heavy tasks offloaded to Celery
- Prevents API blocking
- Scales independently

---

## 🧪 Example API

### Upload Book

```http
POST /books
```

Response:

```json
{
  "id": 1,
  "status": "processing"
}
```

---

### Get Book

```http
GET /books/{id}
```

Response:

```json
{
  "id": 1,
  "title": "Sample",
  "summary": "Generated summary...",
  "status": "completed"
}
```

---

## 📈 Future Improvements

- Streaming summarization
- Chunk-based processing for large PDFs
- Embeddings + semantic search
- Multi-tenant support
- Rate limiting & auth
- UI dashboard

---

## 🤝 Why This Project Matters

This project demonstrates:

- Real-world backend architecture
- Cloud-ready design
- Async + distributed systems understanding
- LLM integration patterns

---

## 👨‍💻 Author

Abhimanyu
Software Engineer | Cloud & AI Systems Builder

---

## ⭐ If you like this project

Give it a star ⭐ and feel free to fork!

````

---

# 🔍 Now let’s challenge you a bit

You’ve built something solid — but think deeper:

### 1. Is this just a “task processor” or a **workflow engine**?
Right now:
- Upload → Process → Done

But you can evolve into:
- Event-driven pipelines (Step Functions style)

---

### 2. Where does this break at scale?

Think:
- Large PDFs (100MB+)
- Long LLM context limits
- Worker memory pressure

👉 Next step could be:
- Chunking + map-reduce summarization

---

### 3. Can this become your SaaS idea?

This is already close to:
- “Document intelligence API”
- “AI processing pipeline”

---

If you want, next we can:
- Turn this README into a **recruiter pitch (1-page story)**
- Or design **v2 architecture (production-grade, AWS-native)**


Nice — your README is already strong. What you're missing is a **complete API reference section** that reflects your actual system capabilities (auth + books + workflows).

Let’s extend your README cleanly without breaking its structure.

---

# ✅ Add this section to your README

You can paste this **below your existing `## 🧪 Example API` section**.

---

## 🔗 API Reference

This section provides a complete overview of available endpoints.

Source: OpenAPI spec

---

# 🔐 Authentication APIs

### Signup

```http
POST /auth/signup
````

Request:

```json
{
  "email": "user@example.com",
  "password": "StrongPass123",
  "first_name": "John",
  "last_name": "Doe"
}
```

Response:

```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true
  },
  "access_token": "jwt_token"
}
```

---

### Login

```http
POST /auth/login
```

Response:

```json
{
  "access_token": "jwt",
  "refresh_token": "refresh",
  "token_type": "bearer"
}
```

---

### Refresh Token

```http
POST /auth/refresh
```

---

### Get Profile

```http
GET /auth/me
Authorization: Bearer <token>
```

---

### Update Profile

```http
PUT /auth/me
Authorization: Bearer <token>
```

---

### List Users

```http
GET /auth/users
```

---

# 📚 Book APIs

---

### Create Book (Upload PDF)

```http
POST /books
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

Fields:

- title
- author
- file (PDF)

---

### List Books

```http
GET /books?limit=10&offset=0
Authorization: Bearer <token>
```

Response:

```json
{
  "items": [...],
  "total": 1
}
```

---

### Get Book

```http
GET /books/{book_id}
```

---

### Update Book

```http
PUT /books/{book_id}
```

---

### Delete Book

```http
DELETE /books/{book_id}
```

---

# 🔄 Book Actions (Workflow Layer)

This is where your system becomes **more than CRUD**.

---

### Borrow Book

```http
POST /books/{book_id}/borrow
Authorization: Bearer <token>
```

---

### Return Book

```http
POST /books/{book_id}/return
Authorization: Bearer <token>
```

---

### Add Review

```http
POST /books/{book_id}/review
Authorization: Bearer <token>
```

Request:

```json
{
  "content": "Great book!"
}
```

---

### Get Book Analysis (LLM-powered)

```http
GET /books/{book_id}/analysis
```

Response:

```json
{
  "themes": ["habit building", "productivity"],
  "difficulty": "easy",
  "insights": "..."
}
```

---

### Get Recommendations (Personalized)

```http
GET /books/book/recommendations
Authorization: Bearer <token>
```

💡 Internally:

- Uses user history
- Applies ranking logic
- Returns personalized suggestions

---

# 🧠 Design Insight (Important for Interviews)

You’ve unknowingly built **3 layers of APIs**:

### 1. CRUD Layer

- `/books`
- `/books/{id}`

### 2. Action Layer

- `/borrow`
- `/return`
- `/review`

### 3. Intelligence Layer (🔥 most valuable)

- `/analysis`
- `/recommendations`
