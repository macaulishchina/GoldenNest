# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Golden Nest (小金库) is a family wealth management web application using a "shareholding" model where family deposits become equity shares. The system uses time-weighted compound interest calculations to incentivize early deposits and includes gamification features like pets, achievements, and voting systems.

**Tech Stack**: Vue 3 + TypeScript + Vite (frontend), FastAPI + SQLAlchemy + SQLite (backend)

## Development Commands

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev          # Start dev server on port 5173
npm run build        # Production build
npm run build:check  # Type check + build
```

### Docker Deployment
```bash
docker-compose up -d --build    # Build and start services
docker-compose logs backend     # View backend logs
docker-compose logs frontend    # View frontend logs
```
- Frontend: http://localhost:8088 (Nginx)
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Single Test Commands
No formal testing framework is currently configured. Consider adding:
- Backend: `pytest` with `pytest-asyncio`
- Frontend: `vitest` or Jest

## Architecture Overview

### Backend Structure (FastAPI)
- **API Routes**: 16 modules in `app/api/` covering auth, family, deposits, equity, investments, approvals, voting, pets, achievements, etc.
- **Business Logic**: Service classes in `app/services/` for complex operations (equity calculations, achievements)
- **Database**: SQLAlchemy 2.0 async ORM with SQLite, 15+ tables in `models.py`
- **Authentication**: JWT tokens with 7-day expiration, BCrypt password hashing

Key API patterns:
```python
# Dependency injection for auth and DB
async def endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
```

### Frontend Structure (Vue 3)
- **Layout**: Responsive `Layout.vue` with desktop sidebar/mobile bottom tabs
- **Views**: 19 page components in `src/views/`
- **State**: Pinia stores for user auth, achievements, privacy
- **API Client**: Centralized Axios instance with JWT auto-attachment
- **UI**: Naive UI component library

### Core Business Logic

**Equity Calculation Algorithm:**
```python
# Time-weighted compound interest (default 3% annual rate)
weighted_amount = deposit_amount × (1 + annual_rate)^years_held
equity_percentage = individual_weighted / total_weighted × 100%
```

**Pet Evolution System:**
- 4 stages: 🥒 Cucumber Bug → 🐛 Caterpillar → 🦋 Butterfly → 🐉 Rainbow Dragon
- EXP sources: Daily check-in (+10), deposits (+5), investments (+10), voting (+3), etc.

**Achievement System:**
- 60+ achievements across 9 categories with 5 rarity levels
- Auto-trigger detection in `services/achievement.py`

## Database Schema Key Points

- **User/Family**: Many-to-many via `FamilyMember` with roles
- **Financial**: `Deposit` → time-weighted equity, `Transaction` audit trail
- **Approval System**: `ExpenseRequest` + `ExpenseApproval` for unanimous voting
- **Gamification**: `Pet`, `Achievement`, `UserAchievement` tables

## Development Patterns

### Backend
- Always use async/await with `AsyncSession`
- Validation via Pydantic schemas for request/response
- HTTPException for errors with appropriate status codes
- Service layer separation for business logic

### Frontend
- Vue 3 Composition API with `<script setup lang="ts">`
- Reactive refs and computed properties
- Proper TypeScript typing throughout
- Mobile-responsive design with breakpoint detection

### File Structure
```
backend/app/
├── api/          # Route handlers (auth, family, deposit, etc.)
├── core/         # Config, database connection, security
├── models/       # SQLAlchemy ORM models
├── schemas/      # Pydantic validation schemas
└── services/     # Business logic (equity, achievements)

frontend/src/
├── api/          # Axios API client modules
├── views/        # Page components (Dashboard, Family, etc.)
├── stores/       # Pinia state management
├── components/   # Reusable UI components
└── router/       # Vue Router configuration
```

## Code Modifications Guidelines

When working with this codebase:

1. **API Changes**: Update both backend route + frontend API client
2. **Database Changes**: Modify `models.py` + corresponding schemas
3. **New Features**: Follow existing patterns (service layer, Pinia stores)
4. **UI Updates**: Use Naive UI components, maintain responsive design
5. **Authentication**: All protected routes use `get_current_user` dependency
6. **Equity Calculations**: Core logic in `services/equity.py`
7. **Achievement Triggers**: Add to `services/achievement.py` service class

## Environment Configuration

Required environment variables:
- `SECRET_KEY`: JWT signing key (change in production)
- `DATABASE_URL`: SQLite path (default: `sqlite+aiosqlite:////data/golden_nest.db`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT expiration (default: 10080 = 7 days)

## API Documentation

FastAPI auto-generates OpenAPI docs at `/docs` endpoint when backend is running.