# Contributing to One Piece TCG Assistant

Thank you for your interest in contributing! This guide covers the basics.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
```

## Architecture

This project follows **Clean Architecture**:

```
domain/          → Pure business logic (no framework imports)
application/     → Use cases, orchestration
infrastructure/  → Database, external APIs, embeddings, jobs
presentation/    → FastAPI routers + Pydantic schemas
```

**Key rule:** The `domain/` layer must never import from infrastructure, presentation, FastAPI, SQLAlchemy, or Pydantic.

## Code Style

### Backend (Python)

- **Linter:** Ruff (line-length 100, target py311)
- Run: `cd backend && ruff check`

### Frontend (TypeScript/React)

- **Linter:** ESLint + typescript-eslint
- Run: `cd frontend && npm run lint`
- All user-facing strings must use the i18n system (`useI18n` hook + `t('key')`)
- Both `es.json` and `en.json` must have the same keys

## Testing

### Backend

```bash
cd backend && pytest -v
```

### Frontend

```bash
cd frontend && npm run lint && npm run build
```

## Pull Request Process

1. Fork the repository and create a feature branch
2. Write tests for new functionality
3. Ensure all checks pass:
   - `ruff check` (backend)
   - `pytest -v` (backend)
   - `npm run lint` (frontend)
   - `npm run build` (frontend)
4. Keep changes focused — one feature/fix per PR
5. Write a clear PR description explaining what and why

## Internationalization (i18n)

The app supports Spanish (`es`) and English (`en`). When adding UI text:

1. Add keys to **both** `frontend/src/i18n/es.json` and `frontend/src/i18n/en.json`
2. Use `const { t } = useI18n()` in your component
3. Reference strings via `t('your.key')`
4. Never hardcode user-facing strings in JSX
