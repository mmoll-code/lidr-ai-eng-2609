---
description: Backend development standards, best practices, and conventions for the Python/FastAPI backend exposing AI services, including project layout, API patterns, PostgreSQL access patterns, migrations, testing with pytest, and security practices
globs: ["backend/app/**/*.py", "backend/tests/**/*.py", "backend/alembic/**/*", "backend/pyproject.toml", "estimador-cag/app/**/*.py", "estimador-cag/ui/**/*.py", "estimador-cag/tests/**/*.py", "estimador-cag/pyproject.toml"]
alwaysApply: true
---

# Backend Project Standards and Best Practices

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
  - [Core Technologies](#core-technologies)
  - [Database](#database)
  - [Testing Framework](#testing-framework)
  - [Development Tools](#development-tools)
  - [Dependency Management](#dependency-management)
- [Architecture Overview](#architecture-overview)
  - [Layered Architecture](#layered-architecture)
  - [Project Structure](#project-structure)
- [API Design Standards](#api-design-standards)
  - [Routers](#routers)
  - [Dependency Injection](#dependency-injection)
  - [Pydantic Models](#pydantic-models)
  - [REST Endpoints](#rest-endpoints)
  - [Error Response Format](#error-response-format)
  - [CORS Configuration](#cors-configuration)
- [AI Service Patterns](#ai-service-patterns)
- [Coding Standards](#coding-standards)
  - [Naming Conventions](#naming-conventions)
  - [Type Safety](#type-safety)
  - [Error Handling](#error-handling)
  - [Validation Patterns](#validation-patterns)
  - [Logging Standards](#logging-standards)
- [Database Patterns](#database-patterns)
  - [Database Access](#database-access)
  - [Migrations](#migrations)
  - [Repository Pattern](#repository-pattern)
- [Testing Standards](#testing-standards)
  - [Test File Structure](#test-file-structure)
  - [Test Organization Pattern](#test-organization-pattern)
  - [Mocking Standards](#mocking-standards)
  - [Test Coverage Requirements](#test-coverage-requirements)
  - [Integration Testing](#integration-testing)
- [Performance Best Practices](#performance-best-practices)
- [Security Best Practices](#security-best-practices)
- [Development Workflow](#development-workflow)

---

## Overview

This document outlines the best practices, conventions, and standards for the backend application: a Python service built with FastAPI that exposes AI-powered endpoints, backed by PostgreSQL. It follows a layered architecture to ensure code consistency, maintainability, and scalability.

## Technology Stack

### Core Technologies
- **Python 3.12+**: Runtime
- **FastAPI**: Web framework with async support and automatic OpenAPI generation
- **Pydantic v2**: Data validation and settings management
- **Uvicorn**: ASGI server

### Database
- **PostgreSQL**: Relational database (Docker container for local development)
- **Data access layer**: `[DECISION PENDING]` — SQLAlchemy 2.x (async) is the recommended default; a thin `asyncpg` layer is the alternative. All examples below assume SQLAlchemy until the decision is finalized.
- **Alembic**: Database migration tool (applies if SQLAlchemy is chosen)

### Testing Framework
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **httpx**: Async HTTP client for API tests (via FastAPI's `TestClient`/`AsyncClient`)
- **Coverage Threshold**: 90% for branches, functions, lines, and statements (`pytest-cov`)

### Development Tools
- **uv** (or pip + venv): Dependency and environment management
- **ruff**: Linting and formatting
- **mypy**: Static type checking (strict mode)

### Dependency Management

- **Add through `uv` only**: Use `uv add <package>` (or `uv add --dev <package>` for the `dev` group); never hand-edit the `dependencies` list in `pyproject.toml`
- **Every dependency is constrained**: No bare package names. Each entry declares at least a lower bound pinned to the version that was tested (`"fastapi>=0.115.0"`), which is what `uv add` produces by default
- **Compatible-release for major-version-sensitive packages**: AI provider SDKs and other libraries with frequent breaking changes use `~=` (`"openai~=3.16"`) so a major bump requires an explicit decision
- **Lock file is source of truth**: `uv.lock` is committed and updated in the same commit as any `pyproject.toml` dependency change
- **Reproducible installs**: Local setup and CI use `uv sync --frozen`; upgrades happen deliberately with `uv lock --upgrade-package <package>`, never as a side effect of an install
- **Review on change**: Any dependency addition or upgrade is called out in the commit message and PR description with the reason

## Architecture Overview

### Layered Architecture

The backend follows a layered architecture:

**API Layer** (`app/api/`)
- FastAPI routers define endpoints and handle HTTP concerns
- Request/response models (Pydantic schemas) live close to the routes
- Routers delegate to services; no business logic in route handlers

**Service Layer** (`app/services/`)
- Business logic and orchestration, including AI service calls
- Services depend on repository abstractions, not on the database directly

**Domain Layer** (`app/domain/`)
- Core entities and value objects as typed Python classes
- Repository interfaces (protocols) defining data access contracts
- Pure business logic without external dependencies

**Infrastructure Layer** (`app/infrastructure/`)
- Database engine/session management
- Repository implementations satisfying domain protocols
- External integrations (AI providers, storage, etc.)

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/           # FastAPI routers per resource
│   │   └── deps.py           # Shared dependencies (DB session, auth, etc.)
│   ├── services/             # Business logic and AI orchestration
│   ├── domain/
│   │   ├── models/           # Domain entities and value objects
│   │   └── repositories/     # Repository protocols (interfaces)
│   ├── infrastructure/
│   │   ├── db.py             # Engine/session setup
│   │   ├── repositories/     # Repository implementations
│   │   └── ai/               # AI provider clients
│   ├── schemas/              # Pydantic request/response models
│   ├── core/
│   │   ├── config.py         # Settings via pydantic-settings
│   │   └── logging.py        # Logging configuration
│   └── main.py               # Application entry point
├── alembic/                  # Database migrations
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml            # Dependencies, tool config
└── alembic.ini               # Alembic configuration
```

## API Design Standards

### Routers

- One router per resource/feature under `app/api/routes/`
- Register routers in `main.py` with a versioned prefix (`/api/v1`)
- Use tags for OpenAPI grouping

```python
from fastapi import APIRouter

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, service: ItemService = Depends(get_item_service)) -> ItemResponse:
    return await service.get_by_id(item_id)
```

### Dependency Injection

- Use FastAPI's `Depends` for all shared resources: DB sessions, repositories, services, current user
- Define reusable dependencies in `app/api/deps.py`
- Never instantiate database clients or services inside route handlers

```python
from collections.abc import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def get_item_service(session: AsyncSession = Depends(get_db_session)) -> ItemService:
    return ItemService(ItemRepository(session))
```

### Pydantic Models

- Define request and response schemas in `app/schemas/`, separate from domain models
- Use explicit response models on every route (`response_model=` or return type annotation)
- Validate at the boundary: constraints (`Field`, validators) belong in schemas, not in services

```python
from pydantic import BaseModel, Field


class ItemCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}
```

### REST Endpoints

- **RESTful Naming**: Resource-based URLs, not actions
- **HTTP Methods**: Use appropriate methods (GET, POST, PUT, PATCH, DELETE)
- **Status Codes**: 200/201/204 for success, 400/404/422 for client errors, 500 for server errors (FastAPI returns 422 for validation errors by default)

```
GET    /api/v1/items          # List items
GET    /api/v1/items/{id}     # Get item by ID
POST   /api/v1/items          # Create item
PUT    /api/v1/items/{id}     # Update item
DELETE /api/v1/items/{id}     # Delete item
```

### Error Response Format

- Raise `HTTPException` (or custom subclasses) from services/routes
- Register exception handlers in `main.py` to keep a consistent error shape

```json
{
    "detail": {
        "message": "Error description",
        "code": "ERROR_CODE"
    }
}
```

```python
class NotFoundError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": {"message": exc.message, "code": "NOT_FOUND"}})
```

### CORS Configuration

- Allow only the frontend origin; configure via environment variables

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## AI Service Patterns

`[PLACEHOLDER — concrete AI endpoints and providers are not yet defined]`

Conventions to follow once AI features are implemented:

- Encapsulate each AI provider behind an interface in `app/domain/` with the implementation in `app/infrastructure/ai/`; services must not call provider SDKs directly
- Keep prompts and model parameters in version-controlled configuration, not inline strings
- Use async calls for all provider I/O; apply timeouts and retries with backoff
- For long-running generations, prefer streaming responses (`StreamingResponse`) or background jobs
- Never log prompts/completions containing sensitive user data; log request IDs and latency instead
- Mock AI providers in unit tests; never call real providers from the test suite

## Coding Standards

### Naming Conventions

- **Variables/functions**: snake_case (e.g., `item_id`, `find_item_by_id`)
- **Classes**: PascalCase (e.g., `ItemService`, `ItemRepository`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_ITEMS_PER_PAGE`)
- **Modules/files**: snake_case (e.g., `item_service.py`, `item_repository.py`)
- **English only**: All names, comments, error messages, and log messages must be in English

```python
# Good: English naming
class ItemRepository:
    async def find_by_id(self, item_id: int) -> Item | None: ...

# Avoid: non-English naming
class RepositorioArticulo:
    async def buscar_por_id(self, id_articulo: int) -> Articulo | None: ...
```

### Type Safety

- All code fully typed; `mypy --strict` must pass
- Use modern syntax: `int | None` instead of `Optional[int]`, built-in generics (`list[str]`)
- Avoid `Any`; use `object`, protocols, or generics instead
- Annotate all function parameters and return types, including tests

```python
# Good: explicit types
async def find_item_by_id(item_id: int) -> Item | None: ...

# Avoid: untyped or Any
def process_data(data): ...
```

### Error Handling

- Define domain-specific exceptions; translate them to HTTP responses via exception handlers
- Let unexpected errors propagate to the global handler; do not swallow exceptions
- Error messages must be descriptive and in English

### Validation Patterns

- Input validation belongs in Pydantic schemas (API boundary)
- Business-rule validation belongs in the service layer, raising domain exceptions
- Never trust raw request data past the schema layer

### Logging Standards

- Use the standard `logging` module configured in `app/core/logging.py`
- Use appropriate levels (debug, info, warning, error)
- Structured context: pass identifiers as extra fields, not interpolated into messages

```python
logger.info("Item created", extra={"item_id": item.id})
logger.error("Failed to create item", extra={"error": str(exc)})
```

## Database Patterns

### Database Access

- PostgreSQL is the single supported database
- Use async sessions; one session per request, provided through dependency injection
- Keep SQL/ORM specifics inside repository implementations only
- Naming: snake_case for tables and columns, plural table names (see [Data Model](./data-model.md))

### Migrations

- All schema changes are version-controlled through Alembic migrations
- Use descriptive migration names; review autogenerated migrations before applying
- Never edit an applied migration; create a new one

```bash
# Create migration
alembic revision --autogenerate -m "descriptive_migration_name"

# Apply migrations
alembic upgrade head
```

### Repository Pattern

- Repository interfaces defined as `Protocol` classes in the domain layer
- Implementations in the infrastructure layer receive the session via constructor injection

```python
from typing import Protocol


class ItemRepositoryProtocol(Protocol):
    async def find_by_id(self, item_id: int) -> Item | None: ...
    async def save(self, item: Item) -> Item: ...


class ItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, item_id: int) -> Item | None:
        result = await self._session.get(ItemRow, item_id)
        return Item.from_row(result) if result else None
```

## Testing Standards

The project has strict requirements for code quality. TDD applies: write a failing test before implementing new behavior.

### Test File Structure

- Tests live under `backend/tests/`, mirroring the `app/` package structure
- File names: `test_<module_name>.py`
- Use pytest with `pytest-asyncio` for async tests
- Maintain 90% coverage threshold

### Test Organization Pattern

```python
import pytest


class TestItemServiceFindById:
    @pytest.fixture
    def repository(self) -> Mock:
        return Mock(spec=ItemRepositoryProtocol)

    async def test_returns_item_when_found(self, repository: Mock) -> None:
        # Arrange
        expected = Item(id=1, name="Example")
        repository.find_by_id = AsyncMock(return_value=expected)
        service = ItemService(repository)

        # Act
        result = await service.get_by_id(1)

        # Assert
        assert result == expected
        repository.find_by_id.assert_awaited_once_with(1)
```

- Naming: `test_<expected_behavior>_when_<condition>`
- Follow the Arrange-Act-Assert pattern
- Group related cases in classes or modules per unit under test

### Mocking Standards

- Mock all external dependencies: repositories in service tests, services in route tests, AI providers everywhere
- Use `unittest.mock.AsyncMock` for async collaborators and `spec=` for interface fidelity
- Prefer pytest fixtures over module-level setup; keep tests isolated
- Use factory functions or fixtures for realistic test data

### Test Coverage Requirements

Include these categories for each function:
1. **Happy Path Tests**: Valid inputs producing expected outputs
2. **Error Handling Tests**: Invalid inputs, missing data, database errors
3. **Edge Cases**: Boundary values, `None` inputs, empty data
4. **Validation Tests**: Schema validation, business rule enforcement
5. **Integration Points**: External service calls, database operations

- **Threshold**: 90% (branches, functions, lines, statements) via `pytest-cov`
- **Coverage Reports**: `pytest --cov=app --cov-report=term-missing`
- **Coverage Files**: Reports in `coverage/` directory named `YYYYMMDD-backend-coverage.md`

### Integration Testing

- **API tests**: Use `httpx.AsyncClient` against the FastAPI app with dependency overrides
- **Database tests**: Run against a disposable PostgreSQL instance (Docker); wrap each test in a rolled-back transaction
- Do not use real database connections or external AI services in unit tests

```python
from httpx import ASGITransport, AsyncClient


async def test_get_item_returns_200() -> None:
    app.dependency_overrides[get_item_service] = lambda: fake_service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/items/1")
    assert response.status_code == 200
```

### Common Anti-Patterns to Avoid

- Don't test implementation details; test behavior
- Don't ignore failing tests or skip error scenarios
- Don't create tests that depend on external services or shared mutable state

## Performance Best Practices

- **Async everywhere**: All I/O (database, AI providers, HTTP) must be async; never block the event loop with sync calls
- **Avoid N+1 queries**: Use eager loading (`selectinload`) for related data
- **Select specific columns** when full rows are not needed
- **Indexes**: Ensure indexes for frequently queried fields (see [Data Model](./data-model.md))
- **Parallel operations**: Use `asyncio.gather()` for independent awaits
- **Connection pooling**: Configure pool size on the async engine; do not create engines per request

## Security Best Practices

### Input Validation
- Validate all inputs through Pydantic schemas before processing
- Parameterized queries only (the ORM/driver handles this); never build SQL from strings

### Environment Variables
- Never commit `.env` files or secrets to version control
- Manage configuration with `pydantic-settings`; required variables fail fast at startup

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}
```

### Authentication & Authorization

`[DECISION PENDING]` — the auth strategy (e.g., OAuth2 with JWT bearer tokens via FastAPI security utilities) has not been defined yet. Once decided, document the scheme here and implement it as a router dependency.

### AI-Specific Security
- Sanitize and bound user input passed into prompts (length limits, content filtering as required)
- Never expose provider API keys to the client; all AI calls go through the backend
- Rate-limit AI endpoints to control cost and abuse

## Development Workflow

### Git Workflow

- **Branch Naming**: Follow `docs/base-standards.md` section 8 (`<type>/session-<N>-<slug>`); use the `new-branch` skill when creating branches
- **Feature Branches**: Develop features in separate branches with clear descriptive names
- **Descriptive Commits**: Write descriptive commit messages in English
- **Code Review**: Review before merging
- **Small Branches**: Keep branches small and focused

### Development Scripts

```bash
uvicorn app.main:app --reload      # Development server with hot reload
pytest                             # Run tests
pytest --cov=app                   # Run tests with coverage
ruff check . && ruff format .      # Lint and format
mypy app                           # Type checking
alembic upgrade head               # Apply migrations
```

### Code Quality

- **ruff** passes with no errors before commits
- **mypy** strict type checking passes
- **All tests passing** before merging
- Code review for adherence to these standards

This document serves as the foundation for maintaining code quality and consistency across the backend application. All team members should follow these practices to ensure a maintainable, scalable, and testable codebase.
