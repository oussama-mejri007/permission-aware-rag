# Permission-Aware Multi-Tenant RAG

A secure, multi-tenant Retrieval-Augmented Generation (RAG) API built with **FastAPI, PostgreSQL, pgvector, and Groq**.

The application retrieves document chunks according to tenant isolation and role-based access control (RBAC) before passing authorized context to a language model.

The core security principle is simple: **authorization must be enforced during database retrieval, before document content reaches the LLM.**

## Key Features

- **Multi-tenant isolation:** separates data belonging to different organizations.
- **Role-based access control:** restricts document retrieval according to the authenticated user's role.
- **JWT authentication:** protects API access with bearer tokens.
- **Semantic search:** uses Sentence Transformers embeddings and PostgreSQL with pgvector.
- **Permission-aware retrieval:** applies tenant and role restrictions in the database query.
- **LLM integration:** generates answers using retrieved document context.
- **Audit logging:** records RAG query outcomes and the number of retrieved chunks.
- **Automated security tests:** checks tenant isolation, role restrictions, and audit-log creation.

## Tech Stack

| Component | Technology |
|---|---|
| API | FastAPI |
| ASGI server | Uvicorn |
| Database | PostgreSQL |
| Vector search | pgvector |
| ORM and migrations | SQLAlchemy, Alembic |
| Embeddings | Sentence Transformers |
| Language model | Groq API |
| Authentication | JWT |
| Testing | Pytest |
| Local infrastructure | Docker Compose |

## Architecture

The application follows this workflow:

1. A user authenticates through `POST /auth/login`.
2. The API issues a signed JWT.
3. The authenticated user's identity, tenant, and role determine their access permissions.
4. The retrieval layer filters chunks by tenant and allowed role in the database query.
5. Only authorized chunks are passed to the answer-generation layer.
6. The application records the retrieval outcome in the audit log.

### Security Design

Tenant and role restrictions are enforced **before retrieved content is sent to the language model**.

The application must not trust client-supplied tenant IDs or roles as evidence of authorization. Access decisions should be based on the authenticated user's server-side identity and permissions.

## Project Structure

```text
permission-aware-rag/
├── alembic/
├── app/
│   ├── models/
│   ├── retrieval/
│   ├── auth.py
│   ├── database.py
│   ├── embeddings.py
│   ├── embed_chunks.py
│   ├── llm.py
│   ├── main.py
│   ├── rag.py
│   └── seed.py
├── tests/
│   ├── test_retrieval.py
│   └── test_security.py
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Prerequisites

- Python compatible with the project's dependencies
- Docker Desktop with Docker Compose
- A Groq API key
- Git

## Local Setup

### 1. Clone the repository

```powershell
git clone https://github.com/oussama-mejri007/permission-aware-rag.git
cd permission-aware-rag
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file based on `.env.example` and configure the values required by your local environment.

At minimum, verify the database connection and Groq API configuration. Use strong, unique credentials for local accounts and never commit real secrets.

**Important:** `.env.example` contains placeholders. Replace them in your local `.env` file, not in the example file.

### 5. Start PostgreSQL

Start the PostgreSQL service defined in Docker Compose:

```powershell
docker compose up -d postgres
```

Confirm that the database is healthy before continuing.

### 6. Apply database migrations

```powershell
alembic upgrade head
```

### 7. Initialize sample data

Run the project's seed procedure using the environment variables configured for your local setup.

Ensure that the database schema exists and that the seed credentials are configured before running the seed procedure.

If the database is empty, follow the project's data-ingestion and embedding workflow to populate documents and their vector embeddings.

## Run the API

Start the development server:

```powershell
uvicorn app.main:app --reload
```

Open the interactive API documentation:

**Swagger UI:** http://127.0.0.1:8000/docs

## API Usage

### Authenticate

Send a form-encoded request to `POST /auth/login`.

Use a seeded account's email as the username and its locally configured password.

A successful login returns a bearer access token. Keep this token private.

### Ask a question

Send a `POST /rag/ask` request with a JSON body:

```json
{
  "question": "What happened to Company A quarterly revenue?"
}
```

Include the access token in the request's `Authorization` header:

```text
Authorization: Bearer <access_token>
```

The answer depends on the documents that the authenticated user is authorized to access and the relevance of the retrieved context.

If no authorized chunks are available, the application returns a fallback response instead of generating an answer from unauthorized content.

## Security and Testing

The automated test suite covers:

- Administrator retrieval
- Finance-role retrieval
- Retrieval for a second tenant's administrator
- Tenant isolation
- Cross-tenant data-leakage prevention
- Role-based access control
- Audit-log creation when no authorized chunks are available

Run all tests with:

```powershell
python -m pytest -v
```

**Latest recorded result: 8 tests passed.**

Run the tests again after code changes and before publishing updates.

## Limitations and Future Improvements

Potential next steps include:

- Add tests for missing, invalid, and expired JWTs.
- Test unauthorized API requests and authentication failures.
- Expand audit-log assertions and monitoring.
- Add document-ingestion validation and retrieval-quality evaluations.
- Improve API error handling and observability.
- Add rate limiting and production deployment guidance.
- Evaluate answer grounding and resistance to prompt injection.

## Security Notice

This repository is a development project and should be reviewed before production deployment.

Never commit API keys, JWTs, passwords, database credentials, private documents, or production data.

Review authentication, authorization, database configuration, dependency versions, logging, and deployment settings before exposing the API to untrusted users.