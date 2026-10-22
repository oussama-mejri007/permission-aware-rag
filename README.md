# Permission-Aware Multi-Tenant RAG

A secure Retrieval-Augmented Generation (RAG) API built with FastAPI, PostgreSQL, and pgvector. The system retrieves document chunks according to tenant isolation and role-based access control before passing authorized context to a language model.

## Key Features

- **Multi-tenant isolation:** separates documents belonging to different organizations.
- **Role-based access control (RBAC):** restricts document retrieval according to user roles.
- **JWT authentication:** protects API endpoints with bearer tokens.
- **Vector search:** uses embeddings and PostgreSQL with pgvector to retrieve relevant document chunks.
- **LLM integration:** generates answers using retrieved context.
- **Audit logging:** records authorized retrieval activity.
- **Automated tests:** covers retrieval permissions, tenant isolation, and audit logging.

## Tech Stack

- Python
- FastAPI and Uvicorn
- PostgreSQL and pgvector
- SQLAlchemy and Alembic
- Sentence Transformers
- Groq API
- JWT authentication
- Pytest
- Docker Compose

## Architecture

1. A user authenticates through the login endpoint.
2. The API issues a signed JWT.
3. The authenticated user's identity, tenant, and role are validated.
4. The retrieval layer applies tenant and role restrictions to the database query.
5. Only authorized document chunks are provided as context to the generation layer.
6. Retrieval activity is recorded for auditing.

**Security principle:** access restrictions must be enforced during retrieval, before document content is sent to the language model. Client-supplied tenant IDs or roles must not be trusted as authorization evidence.

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
├── data/
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.11 or newer, compatible with the dependencies
- Docker Desktop with Docker Compose
- A Groq API key
- A Hugging Face-compatible environment for embedding models if required

## Configuration

Create a local `.env` file in the project root. Configure the database URL, JWT secret, and Groq API credentials using the variable names expected by the application.

Do not commit `.env` or real credentials to version control. Use strong, unique secrets for any deployed environment.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start PostgreSQL with pgvector:

```powershell
docker compose up -d postgres
```

Apply database migrations if required by the current project setup:

```powershell
alembic upgrade head
```

Initialize sample data using the project's seed procedure. Verify the required environment variables and database configuration before running it.

## Run the API

```powershell
uvicorn app.main:app --reload
```

Open the interactive API documentation:

- Swagger UI: http://127.0.0.1:8000/docs

## API Workflow

### 1. Authenticate

Send a form-encoded request to `POST /auth/login` using a seeded account's email as the username and its password.

A successful response returns a bearer access token. Keep this token private.

### 2. Ask a question

Use `POST /rag/ask` with a JSON body:

```json
{
  "question": "What happened to Company A quarterly revenue?"
}
```

Include the bearer token in the `Authorization` header.

The answer depends on the documents available to the authenticated user and the relevance of the retrieved context.

## Security and Testing

The test suite covers:

- Company administrator retrieval
- Finance-role retrieval
- Retrieval for a second tenant's administrator
- Tenant isolation
- Cross-tenant data leakage prevention
- Role-based access control
- Audit logging for authorized searches

Run the tests:

```powershell
python -m pytest -v
```

**Recorded development result:** 7 tests passed. Re-run the suite after making changes and before publishing.

## Limitations and Future Improvements

- Expand tests for unauthorized requests, expired tokens, and missing credentials.
- Add document-ingestion validation and more retrieval-quality tests.
- Improve observability and audit-log review.
- Add deployment guidance, rate limiting, and production secret management.
- Evaluate retrieval quality and answer grounding with a representative dataset.

## Security Notice

This repository is a development project. Review authentication, authorization, configuration, dependency versions, and deployment settings before exposing it to untrusted users.

Never commit API keys, JWTs, passwords, database credentials, private documents, or production data.
