# Data Model Documentation

This document describes the data model for the application, backed by **PostgreSQL**. It defines the modeling conventions to be used and will hold entity definitions, relationships, and the entity-relationship diagram as the domain design is completed.

> **STATUS: entities not yet designed.** The domain entities for the AI services have not been defined. This document currently establishes conventions only; add entity sections and the ER diagram as the design lands.

## Modeling Conventions

### Naming

- **Tables**: snake_case, plural (e.g., `users`, `chat_sessions`)
- **Columns**: snake_case (e.g., `created_at`, `user_id`)
- **Primary keys**: `id` (`BIGINT GENERATED ALWAYS AS IDENTITY` or `UUID` — `[DECISION PENDING]`, choose one convention and apply it consistently)
- **Foreign keys**: `<singular_table>_id` (e.g., `user_id` referencing `users.id`)
- **Indexes**: `ix_<table>_<columns>`; unique constraints: `uq_<table>_<columns>`; foreign keys: `fk_<table>_<referenced_table>`
- All names in English

### Column Standards

- **Timestamps**: every table includes `created_at` and `updated_at` as `TIMESTAMPTZ` with `DEFAULT now()`; always store UTC
- **Text**: prefer `TEXT` with application-level length validation (Pydantic) over arbitrary `VARCHAR(n)` limits; use `VARCHAR(n)` only when the limit is a real domain rule
- **Booleans**: `BOOLEAN NOT NULL` with an explicit default
- **Enumerations**: `[DECISION PENDING]` — PostgreSQL `ENUM` types vs. `TEXT` + `CHECK` constraint; `TEXT` + `CHECK` is the recommended default for easier migrations
- **Money/decimals**: `NUMERIC(precision, scale)`, never floating point
- **JSON payloads** (e.g., AI request/response metadata): `JSONB`, indexed with GIN only when queried

### Integrity and Relationships

- **Referential integrity**: all relationships enforced with foreign key constraints; define `ON DELETE` behavior explicitly (`CASCADE`, `RESTRICT`, or `SET NULL`) per relationship
- **NOT NULL by default**: columns are nullable only when absence is a meaningful domain state
- **Unique constraints**: enforce natural uniqueness (e.g., email addresses) at the database level, not only in application code
- **Normalization**: aim for third normal form; denormalize only with a documented justification

### Migrations

- All schema changes are applied through **Alembic** migrations (see [Backend Standards](./backend-standards.md#migrations))
- The migration history is the source of truth for schema evolution; never modify the database schema manually
- Each migration must be reversible (`downgrade`) unless explicitly documented otherwise

### Mapping to Application Code

- The data access layer choice (SQLAlchemy 2.x async vs. thin `asyncpg`) is `[DECISION PENDING]` — see [Backend Standards](./backend-standards.md#database)
- Regardless of the choice, database rows map to typed domain models in `app/domain/models/`; API payloads use separate Pydantic schemas
- Repository implementations are the only code that touches tables directly

## Entities

`[PLACEHOLDER — no entities defined yet]`

When adding an entity, document it with this template:

```markdown
### <EntityName>
Short description of what the entity represents.

**Fields:**
- `id`: Primary key
- `<field>`: Type, constraints, and meaning
- `created_at` / `updated_at`: Standard timestamps

**Validation Rules:**
- Database-level constraints and application-level (Pydantic) rules

**Relationships:**
- `<relation>`: Cardinality and referenced entity
```

## Entity Relationship Diagram

`[PLACEHOLDER — add a Mermaid erDiagram once entities are defined]`

```mermaid
erDiagram
    %% Add entities and relationships here as the domain design is completed
```

## Key Design Principles

1. **Referential Integrity**: All foreign key relationships are enforced by the database to ensure consistency.
2. **Explicit Constraints**: Uniqueness, nullability, and checks live in the schema, not only in application code.
3. **Audit Trail**: Standard timestamps on every table provide a baseline change timeline.
4. **Extensibility**: Conventions above keep the model consistent as new entities are added.
5. **Data Normalization**: The model follows normalization principles to minimize redundancy and ensure integrity.
