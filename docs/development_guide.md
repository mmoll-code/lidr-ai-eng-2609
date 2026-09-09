# Development Guide

This guide provides step-by-step instructions for setting up the development environment and running tests for the project: a Python (FastAPI) backend exposing AI services with PostgreSQL, and a Next.js frontend.

## 🚀 Setup Instructions

### Prerequisites

Ensure you have the following installed:
- **Python** (3.12 or higher)
- **uv** (recommended) or pip + venv
- **Node.js** (v20 or higher) and **npm**
- **Docker** and **Docker Compose**
- **Git**

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Environment Configuration

Create environment files for both backend and frontend:

**Backend Environment** (`backend/.env`):
```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://app_user:change_me@localhost:5432/app_db

# Application Configuration
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000

# AI Provider Configuration (placeholder — provider not yet chosen)
# AI_PROVIDER_API_KEY=<your-key>
```

**Frontend Environment** (`frontend/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> Never commit `.env` files. Values above are local-development defaults; replace credentials before any shared deployment.

### 3. Database Setup (PostgreSQL with Docker)

Start the PostgreSQL database using Docker Compose:

```bash
# Start PostgreSQL container
docker-compose up -d

# Verify the database is running
docker-compose ps
```

The PostgreSQL database will be available at:
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `app_db`
- **Username**: `app_user`
- **Password**: as configured in `docker-compose.yml` / `.env`

### 4. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create environment and install dependencies
uv sync            # or: python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

The backend API will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

### 5. Frontend Setup

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend application will be available at `http://localhost:3000`.

## 🧪 Testing

### Backend Testing

```bash
cd backend

# Run all tests
pytest

# Run tests in watch mode
pytest-watch          # if installed

# Run tests with coverage
pytest --cov=app --cov-report=term-missing
```

### Frontend Testing

```bash
cd frontend

# Run unit/component tests
npm run test

# Run E2E tests with Playwright
npm run test:e2e

# Open Playwright UI mode
npx playwright test --ui
```
