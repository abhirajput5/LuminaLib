Here is your **modified full `ARCHITECTURE.md`** with review analysis + TinyLlama constraints added cleanly:

---

```markdown
## LuminaLib – System Architecture

---

## 1. Introduction

LuminaLib is a **content-aware library system** designed to manage book ingestion, enable user interactions, and leverage **Generative AI for summarization and review analysis**, along with a **machine learning-based recommendation engine**.

The system is built with a strong emphasis on:

- Clean Architecture
- Asynchronous processing
- Interface-driven design
- Extensibility and configurability

Rather than being a simple CRUD application, LuminaLib treats **book content as first-class data**, enabling intelligent processing pipelines powered by LLMs.

---

## 2. High-Level Architecture

The system is composed of multiple decoupled services:
```

Client
↓
FastAPI (API Layer)
↓
Service Layer (Business Logic)
↓
Repository Layer (Data Access)
↓
PostgreSQL (Database)

Async Flow:
FastAPI → Service Layer → Task Publisher → Redis → Celery Worker → LLM → Database/Storage

```

### Key Design Principles

- **Separation of concerns** between API, business logic, and infrastructure
- **Async-first design** for heavy workloads
- **Replaceable components** via abstraction layers
- **Stateless API with externalized state**

---

## 3. API Layer (FastAPI)

The API layer is responsible for:

- Request validation using Pydantic
- Authentication via JWT
- Routing and response formatting

All endpoints defined in the specification are implemented, including authentication, book management, review submission, and analysis retrieval.

### Design Rationale

FastAPI was chosen because:

- Native support for async operations
- Strong typing via Pydantic
- High performance compared to traditional frameworks
- Automatic OpenAPI generation

Controllers are intentionally **thin**, delegating all business logic to the service layer.

---

## 4. Service Layer (Business Logic)

The service layer acts as the **core of the application** and is responsible for:

- Enforcing business rules (e.g., a user must borrow a book before reviewing it)
- Coordinating between repositories and async tasks
- Triggering background processing workflows

### Example Flow: Book Creation

1. Validate input
2. Store metadata and file reference
3. Publish async task for summarization

### Example Flow: Review Submission

1. Validate user has borrowed the book
2. Store review in database
3. Publish async task for review analysis

This ensures the API remains **responsive** while heavy processing happens asynchronously.

---

## 5. Repository Layer (Data Access)

The repository layer abstracts all database operations.

Responsibilities include:

- CRUD operations
- Query encapsulation
- Isolation from database implementation

### Design Rationale

- Prevents business logic from being tightly coupled to SQL/ORM
- Enables easy replacement of database systems
- Improves testability through mocking

PostgreSQL is used as the primary database due to its reliability and strong support for structured queries.

---

## 6. Storage Layer (Book Content)

Book files are treated as **external assets**, not embedded in the database.

- Current implementation: MinIO (S3-compatible object storage)
- Stored as file paths in the database

### Design Rationale

- Keeps database lightweight
- Enables horizontal scaling of storage
- Allows seamless migration to AWS S3 or other cloud providers

---

## 7. Asynchronous Processing (Celery + Redis)

### Problem

LLM-based processing (summarization, sentiment analysis) is:

- Time-consuming
- Resource-intensive
- Unsuitable for synchronous APIs

### Solution

Celery is used for distributed background processing:

- Redis acts as the message broker
- Celery workers process tasks independently

---

## 8. Intelligence Layer (LLM Processing)

### 8.1 Book Summarization Flow

1. Download file from storage
2. Extract text
3. Split into chunks
4. Summarize each chunk
5. Combine summaries
6. Store final summary in DB

---

### 8.2 Review Analysis Flow (Rolling Consensus)

1. Fetch all reviews for a book
2. Combine reviews into structured input
3. Send to LLM for:
   - aggregated summary
   - sentiment score
4. Store result in `book_review_analysis` table (UPSERT)

```

reviews → Celery → LLM → book_review_analysis

```

### Key Insight

Review analysis is **not a one-time computation**, but a **continuously updated intelligence layer**.

Each new review triggers recomputation of the consensus.

---

## 9. LLM Integration (Ollama + TinyLlama)

A local LLM (via Ollama) is used.

### Current Model

- TinyLlama (lightweight, CPU-friendly)

### Responsibilities

- Summarization
- Review sentiment analysis

---

### Limitations of TinyLlama

- Weak instruction following
- Inconsistent structured output
- Poor JSON adherence

### Mitigation Strategy

- Keep prompts simple and direct
- Avoid complex formatting expectations
- Use defensive parsing
- Treat LLM output as **best-effort, not guaranteed**

---

### Design Decision

LLM logic is encapsulated in `LLMProvider`:

```

LLMProvider
├── summarize()
├── combine()
└── analyze_reviews()

```

This ensures:

- Prompt logic is centralized
- Tasks remain clean and reusable
- Easy swap to OpenAI or other providers

---

## 10. Recommendation Engine

A **content-based recommendation approach** is implemented.

### Data Sources

- User borrow history
- Book metadata
- Review signals

### Flow

1. Extract user preferences
2. Compute similarity
3. Rank books

---

## 11. User Preferences Design

User preferences are derived using:

### Implicit Signals

- Borrow history
- Reviews

### Rationale

- No friction for users
- Automatically evolves over time

---

## 12. Authentication & Security

- JWT-based stateless authentication
- Access + refresh tokens

---

## 13. Docker-Based Deployment

Services:

- FastAPI backend
- PostgreSQL
- Redis
- Celery worker
- MinIO
- Ollama
- Grafana + Loki

---

## 14. Observability

- Centralized logging via Loki
- Monitoring via Grafana

---

## 15. Extensibility

| Component | Replaceable With |
|----------|----------------|
| LLM | OpenAI / Claude |
| Storage | AWS S3 |
| Database | MySQL / NoSQL |
| Queue | Kafka / SQS |

---

## 16. Trade-offs & Limitations

- TinyLlama produces inconsistent structured outputs
- Full recomputation of review analysis is not optimal at scale
- Celery adds operational complexity

---

## 17. Future Improvements

- Switch to stronger LLM (Phi-3 / Llama3)
- Incremental review analysis instead of full recompute
- Embedding-based recommendations
- Parallel chunk processing
```

Here are **clean, recruiter-grade sequence diagrams** you can directly add to your `ARCHITECTURE.md`.

---

# 🔁 1. Book Ingestion & Summarization Flow

```markdown
## 🔄 Sequence: Book Ingestion & Summarization
```

Client
|
| POST /books (file upload)
↓
FastAPI Router
↓
Service Layer
↓
Storage Provider (MinIO)
|-- upload file -->
↓
Repository (DB)
|-- insert book (status=processing) -->
↓
Task Publisher
|-- publish "process_book" -->
↓
Redis (Broker)
↓
Celery Worker
↓
Storage Provider
|-- download file -->
↓
PDF Parser
|-- extract text -->
↓
Chunking Logic
↓
LLM Provider (TinyLlama via Ollama)
|-- summarize chunks -->
↓
LLM Provider
|-- combine summaries -->
↓
Database
|-- update books.summary + status=ready -->

```

```

---

# 🔁 2. Review Submission & Analysis Flow (IMPORTANT)

```markdown
## 🔄 Sequence: Review Submission & Analysis
```

Client
|
| POST /books/{id}/reviews
↓
FastAPI Router
↓
Service Layer
|-- validate borrow -->
↓
Repository
|-- insert review -->
↓
Task Publisher
|-- publish "process_review" -->
↓
Redis (Broker)
↓
Celery Worker
↓
Database
|-- fetch all reviews -->
↓
LLM Provider (TinyLlama)
|-- analyze_reviews -->
↓
Database
|-- upsert book_review_analysis -->

```

```

---

# 🔁 3. Fetch Review Analysis (Read Path)

```markdown
## 🔄 Sequence: Fetch Review Analysis
```

Client
|
| GET /books/{id}/analysis
↓
FastAPI Router
↓
Service Layer
↓
Repository
|-- fetch from book_review_analysis -->
↓
Response

CASE 1:
analysis exists → return summary + score

CASE 2:
no analysis → return status = "not_ready"

```

```

---

# 🔁 4. Recommendation Flow (Bonus)

```markdown
## 🔄 Sequence: Recommendation Flow
```

Client
|
| GET /recommendations
↓
FastAPI Router
↓
Service Layer
↓
Repository
|-- fetch user_preferences -->
|-- fetch user_books -->
|-- fetch books -->
↓
Recommendation Engine
|-- compute similarity -->
↓
Response (ranked books)

```

```
