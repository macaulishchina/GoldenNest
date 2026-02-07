# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Golden Nest (小金库) is a family wealth management web application using a "shareholding" model where family deposits become equity shares. The system uses time-weighted compound interest calculations to incentivize early deposits and includes gamification features like pets, achievements, and voting systems.

**Tech Stack**: Vue 3 + TypeScript + Vite + Naive UI (frontend), FastAPI + SQLAlchemy 2.0 + SQLite (backend)

**Key Frontend Libraries**: Naive UI (component library, `n-` prefix), ECharts + vue-echarts (data visualization), dayjs + lunar-javascript (date/lunar calendar utilities), Pinia (state), Axios (HTTP client)

**Key Business Concepts**:
- Family members deposit funds that convert to equity shares
- Time-weighted compound interest rewards early deposits (default 3% annual rate)
- Unanimous approval required for expense requests (one-vote veto system)
- Gamification through pets (4 evolution stages), achievements (60+), and voting proposals

## Development Commands

### Backend Development

**⚠️ CRITICAL: Backend commands MUST be run from the `backend/` directory, not the repository root!**

```bash
# Method 1: Using convenience scripts (recommended)
cd backend
./run.sh           # Linux/Mac - auto-creates venv, installs deps, starts server
run.bat            # Windows - auto-creates venv, installs deps, starts server

# Method 2: Manual startup
cd backend  # ⚠️ MUST cd into backend/ first!
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000  # ⚠️ Must run from backend/ directory

# Backend runs with SQL logging enabled (echo=True in database.py)
# Database auto-initializes on startup via lifespan event
# Server URLs:
# - Main: http://localhost:8000
# - API Docs: http://localhost:8000/api/docs
# - Health: http://localhost:8000/api/health
```

**Common Error**: Running `uvicorn app.main:app` from repository root will fail with `ModuleNotFoundError: No module named 'app'`. Always `cd backend` first!

### Frontend Development
```bash
cd frontend
npm install
npm run dev          # Dev server on :5173, proxies /api to localhost:8000
npm run build        # Production build (no type check)
npm run build:check  # Type check with vue-tsc, then build
npm run preview      # Preview production build
```

### Docker Deployment
```bash
docker-compose up -d --build       # Build and start services
docker-compose logs -f backend     # Follow backend logs
docker-compose logs -f frontend    # Follow frontend logs
docker-compose down                # Stop and remove containers
```
- Frontend (Nginx): http://localhost:8088
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/api/docs (OpenAPI/Swagger)
- Health check: http://localhost:8000/api/health

### Testing
No formal testing framework configured. To add:
- Backend: `pytest` + `pytest-asyncio` + `httpx` for async tests
- Frontend: `vitest` (Vite-native) or `@vue/test-utils`

## Architecture Overview

### Backend Structure (FastAPI)

**Layered Architecture:**
```
Routes (app/api/*.py)
  ↓ Pydantic schemas validate request/response
  ↓ Depends(get_current_user) for auth
  ↓ Depends(get_db) for database session
Service Layer (app/services/*.py)
  ↓ Business logic (equity calc, achievements)
Models (app/models/models.py)
  ↓ SQLAlchemy ORM (async)
SQLite Database
```

**Key Components:**
- **API Routes** (`app/api/`): 16 modules with REST endpoints
  - Auth, family, deposit, equity, investment, transaction
  - Approval (universal approval workflow), vote, gift
  - Pet, achievement, announcement, report, todo, calendar
  - `expense.py`: **Deprecated** — functionality moved to universal approval workflow in `approval.py`
- **Business Logic** (`app/services/`):
  - `equity.py`: Time-weighted compound interest calculation
  - `achievement.py`: 60+ achievement definitions with auto-detection logic
  - `calendar.py`: Recurring event generation
  - `notification.py`: Enterprise WeChat (企业微信) notification integration
  - `approval.py`: Approval workflow orchestration
- **Database** (`app/models/models.py`):
  - 15+ tables with proper relationships
  - Async SQLAlchemy 2.0 with `AsyncSession`
  - Database auto-creates tables via `init_db()` on startup
- **Security** (`app/core/security.py`):
  - JWT tokens (7-day expiration, HS256 algorithm)
  - BCrypt password hashing with salt
  - OAuth2 Bearer scheme

**Critical Patterns:**
```python
# Standard route pattern with dependency injection
@router.post("/endpoint")
async def endpoint(
    request_data: RequestSchema,
    current_user: User = Depends(get_current_user),  # JWT auth
    db: AsyncSession = Depends(get_db)               # DB session
) -> ResponseSchema:
    # get_db auto-commits on success, rollback on exception
    # Business logic here
    return response_data

# Database session management (handled by get_db dependency)
async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Auto-commit
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Important Enums** (in `models.py`):
- `TransactionType`: deposit, withdrawal, income, dividend, gift
- `InvestmentType`: fund, stock, bond, deposit, other
- `ExpenseStatus`: pending, approved, rejected
- `AchievementCategory`: deposit, streak, family, equity, investment, expense, vote, hidden, special
- `AchievementRarity`: common, rare, epic, legendary, mythic
- `ApprovalRequestType`: deposit, expense, withdrawal
- `ApprovalRequestStatus`: pending, approved, rejected
- `TodoPriority`: low, medium, high
- `CalendarRepeatType`: none, daily, weekly, monthly, yearly

### Frontend Structure (Vue 3 + TypeScript)

**Application Flow:**
```
App.vue (root)
  ↓
Router (src/router/index.ts)
  ↓ beforeEach: Check auth, redirect to /login if needed
  ↓ afterEach: Fetch unshown achievements (300ms delay)
Layout.vue (authenticated routes wrapper)
  ↓ Responsive: desktop sidebar OR mobile drawer + bottom tabs
  ↓ <router-view> outlet
Views (19 pages in src/views/)
  ↓ Composition API with <script setup lang="ts">
  ↓ Access Pinia stores, call API client
API Client (src/api/index.ts)
  ↓ Axios instance with interceptors
  ↓ Request: Auto-attach JWT Bearer token
  ↓ Response: 401 → logout + redirect to /login
Backend API
```

**Key Components:**
- **Layout** (`src/views/Layout.vue`):
  - Desktop: Collapsible sidebar (220px ↔ 64px) + top header
  - Mobile: Hamburger drawer + bottom tabbar (4 fixed + quick shortcuts)
  - Breakpoint detection for responsive switching
- **Routing** (`src/router/index.ts`):
  - `beforeEach` guard: Requires auth for all routes except /login
  - `afterEach` hook: Auto-checks for new achievements on route change
  - Lazy-loaded components for code splitting
- **State Management** (Pinia):
  - `userStore`: Auth token (localStorage), user profile, login/logout
  - `achievementStore`: Achievement notification queue
  - `privacyStore`: User privacy preferences
  - `approvalStore`: Approval workflow state
- **API Client** (`src/api/index.ts`):
  - Centralized Axios with `/api` base URL
  - Request interceptor: Attach `Authorization: Bearer ${token}`
  - Response interceptor: Auto-logout on 401
  - Organized API modules: authApi, familyApi, depositApi, equityApi, etc.

**Responsive Strategy:**
- Mobile breakpoint: `<768px` (detected via window width or Naive UI's useMediaQuery)
- Desktop: Sidebar navigation, always visible
- Mobile: Hidden drawer + persistent bottom tabbar with customizable shortcuts

### Core Business Logic

**1. Equity Calculation Algorithm** (`services/equity.py`)

Time-weighted compound interest incentivizes early deposits:

```python
# Formula: weighted_amount = amount × (1 + rate)^years
def calculate_weighted_amount(amount, deposit_date, rate, calculate_date=now):
    years = (calculate_date - deposit_date).days / 365.0
    if years < 0: years = 0  # Future deposits not weighted
    weighted = amount * (1 + rate) ** years
    return round(weighted, 2)

# Equity percentage for each member
equity_percentage = (member_weighted_total / family_weighted_total) × 100%
```

**Example**:
- Member A deposits ¥10,000 one year ago → weighted: ¥10,300 (3% rate)
- Member B deposits ¥10,000 today → weighted: ¥10,000
- Total weighted: ¥20,300
- A's equity: 50.74%, B's equity: 49.26%

**Daily weighted growth** is calculated for dashboard display:
```python
daily_growth = total_weighted × (rate / 365)
```

**2. Achievement System** (`services/achievement.py`)

60+ achievements auto-trigger based on user actions. Achievement definitions include:
- `trigger_type`: deposit_count, total_deposit, single_deposit, deposit_days, family_members, equity_ratio, pet_level, etc.
- `trigger_value`: Threshold (e.g., "10000" for ¥10k deposit)
- `is_hidden`: Hidden achievements revealed upon unlock

**Detection workflow**:
```python
# After any significant action (deposit, investment, etc.)
await detect_user_achievements(user_id, family_id, db)
# Checks all achievement conditions, unlocks new ones
# Frontend polls for unshown achievements on route change
```

**3. Pet Evolution System**

4-stage evolution based on experience points:
```
Level 1-9:   🥒 Cucumber Bug (黄瓜虫)
Level 10-19: 🐛 Caterpillar (毛毛虫)
Level 20-29: 🦋 Butterfly (花蝴蝶)
Level 30+:   🐉 Rainbow Dragon (彩虹龙)
```

EXP sources (tracked in pet.py):
- Daily check-in: +10 EXP
- Deposit: +5 EXP
- Investment income: +10 EXP
- Vote: +3 EXP
- Announcement: +2 EXP
- Complete todo: +5 EXP
- Create calendar event: +3 EXP

Level progression: `level = floor(sqrt(experience))`

**4. Approval System** (Universal Workflow)

All significant operations (deposits, expenses, withdrawals) can require unanimous approval:
- Create `ApprovalRequest` with type (deposit/expense/withdrawal)
- All family members must approve (one-vote veto)
- Status: pending → approved/rejected
- On approval: Execute corresponding transaction

**5. Recurring Events** (Calendar & Todo)

Both calendar and todo support recurring patterns:
- `repeat_type`: none, daily, weekly, monthly, yearly
- `repeat_interval`: Every N days/weeks/months/years
- System generates instances on-demand based on pattern

## Database Schema Key Points

**Relationships:**
- `User` ↔ `FamilyMember` ↔ `Family` (many-to-many with role: admin/member)
- `Deposit` → user_id, family_id (for equity calculation)
- `Transaction` → Complete audit trail (type: deposit/withdrawal/income/dividend/gift)
- `ExpenseRequest` → `ExpenseApproval[]` (unanimous voting)
- `Investment` → `InvestmentIncome[]` (dividends distributed by equity)
- `Achievement` ↔ `UserAchievement` (many-to-many with unlock tracking)
- `Pet` → One per family, tracks experience/level/stage
- `ApprovalRequest` → Universal approval for deposits/expenses/withdrawals
- `Vote` → `VoteOption[]` + `VoteRecord[]` (proposal voting)
- `Todo` → `TodoItem[]` (task lists)
- `Calendar` → Recurring events with participant tracking

**Critical Fields:**
- `User.avatar`: Base64 encoded image (max 3MB), versioned with `avatar_version`
- `Family.time_value_rate`: Equity calculation rate (default 0.03)
- `Family.invite_code`: 8-char code for joining family
- `Deposit.deposit_date`: Used for time-weighted calculation
- `Pet.experience`: Calculated from multiple sources, determines level
- `Achievement.trigger_type` + `trigger_value`: Auto-detection rules
- `ApprovalRequest.request_data`: JSON blob with type-specific data

**Database Initialization:**
- Tables auto-create on startup via `init_db()` in lifespan event
- No migrations framework configured (consider Alembic for production)

## Development Patterns

### Gotchas
- Frontend uses **snake_case** field names matching the backend (no auto camelCase conversion)
- `get_db()` dependency auto-commits on success and rolls back on exception — do not manually commit
- No linting or formatting tools configured (no eslint, prettier)
- No migration framework — schema changes require manual data migration or DB recreation
- Root-level `package.json` exists with `lunar-javascript` dependency (used for lunar calendar features)

### File Structure Overview

```
backend/app/
├── api/              # Route handlers (16 modules)
│   ├── auth.py           # Login, register, avatar upload
│   ├── family.py         # Create/join family, invite codes
│   ├── deposit.py        # Record deposits
│   ├── equity.py         # Calculate equity distribution
│   ├── investment.py     # Portfolio management
│   ├── transaction.py    # Financial audit trail
│   ├── approval.py       # Universal approval workflow
│   ├── vote.py           # Shareholder proposals
│   ├── pet.py            # Pet adoption, feeding, check-in
│   ├── achievement.py    # Achievement list and unlocks
│   ├── announcement.py   # Family bulletin board
│   ├── gift.py           # Equity gifting
│   ├── report.py         # Annual financial reports
│   ├── todo.py           # Task lists
│   └── calendar.py       # Shared calendar events
├── core/             # Config, database, security utilities
│   ├── config.py         # Pydantic settings
│   ├── database.py       # Async SQLAlchemy setup
│   └── security.py       # JWT + bcrypt functions
├── models/           # SQLAlchemy ORM models (single file)
│   └── models.py         # 15+ tables + enums
├── schemas/          # Pydantic validation schemas
└── services/         # Business logic layer
    ├── equity.py         # Time-weighted calculations
    ├── achievement.py    # Achievement definitions + detection
    ├── approval.py       # Approval workflow orchestration
    ├── calendar.py       # Recurring event logic
    └── notification.py   # Enterprise WeChat notifications

frontend/src/
├── api/              # Axios API client modules
│   └── index.ts          # Centralized axios + API methods
├── views/            # Page components (19 routes)
│   ├── Login.vue / Register.vue
│   ├── Layout.vue        # Responsive wrapper
│   ├── Dashboard.vue     # Home overview
│   ├── Family.vue        # Member management
│   ├── Deposit.vue       # Deposit form
│   ├── Equity.vue        # Equity visualization
│   ├── Investment.vue    # Portfolio table
│   ├── Expense.vue       # Expense requests
│   ├── Approval.vue      # Approval inbox
│   ├── Transaction.vue   # Transaction history
│   ├── Vote.vue          # Voting proposals
│   ├── Pet.vue           # Pet interaction
│   ├── Achievement.vue   # Achievement gallery
│   ├── Announcement.vue  # Bulletin board
│   ├── Gift.vue          # Equity gifting
│   ├── Report.vue        # Annual reports
│   ├── Todo.vue          # Task lists
│   └── Calendar.vue      # Calendar view
├── stores/           # Pinia state management
│   ├── user.ts           # Auth + user profile
│   ├── achievement.ts    # Achievement notifications
│   ├── approval.ts       # Approval workflow state
│   └── privacy.ts        # Privacy settings
├── components/       # Reusable UI components
│   ├── AchievementToast.vue
│   ├── TimeRangeSelector.vue
│   └── UserAvatar.vue
├── router/           # Vue Router configuration
│   └── index.ts          # Routes + guards + achievement polling
└── utils/            # Helper functions
    ├── achievement.ts    # Achievement polling logic
    ├── avatar.ts         # Avatar handling utilities
    ├── date.ts           # Date formatting utilities
    └── holiday.ts        # Lunar calendar / Chinese holiday utilities
```

**Note**: `frontend/src/thirdparty/GameZone/` contains an embedded open-source game collection (separate git repo). Not integrated into the main application workflow.

## Code Modification Guidelines

When working with this codebase:

1. **Adding New API Endpoints**:
   - Create route in `backend/app/api/` with proper schema validation
   - Add corresponding function to frontend `api/index.ts` (e.g., `exportedApi.newMethod()`)
   - Use `Depends(get_current_user)` for protected endpoints
   - Use `Depends(get_db)` for database access (auto-commits on success)

2. **Database Schema Changes**:
   - Modify `backend/app/models/models.py` (add/change tables/columns)
   - Update corresponding Pydantic schemas in `backend/app/schemas/`
   - Consider data migration strategy (no Alembic configured currently)
   - Restart backend to auto-create new tables via `init_db()`

3. **New Features with Business Logic**:
   - Extract complex logic into service modules (`backend/app/services/`)
   - For frontend state, add to existing Pinia stores or create new store
   - Follow Vue 3 Composition API pattern with `<script setup lang="ts">`

4. **UI Components**:
   - Use Naive UI components (prefix `n-`) for consistency
   - Maintain mobile responsiveness (test breakpoint <768px)
   - Update `Layout.vue` sidebar menu if adding new top-level page
   - Add route to `frontend/src/router/index.ts` with `requiresAuth: true`

5. **Authentication & Authorization**:
   - All protected API routes use `current_user: User = Depends(get_current_user)`
   - Frontend stores token in localStorage, axios auto-attaches as Bearer
   - Family-specific operations check `current_user` is member via `FamilyMember` lookup

6. **Equity System Modifications**:
   - Core calculation in `services/equity.py::calculate_weighted_amount()`
   - Rate configured per-family in `Family.time_value_rate` (default 3%)
   - Deposits must have `deposit_date` for time-weighting
   - Call `calculate_family_equity()` to regenerate full equity summary

7. **Achievement Triggers**:
   - Definitions in `services/achievement.py::ACHIEVEMENT_DEFINITIONS`
   - Detection logic in same file's `detect_user_achievements()`
   - Call after any action that could unlock achievements (deposit, investment, etc.)
   - Frontend auto-polls for unshown achievements on route change (300ms delay)

8. **Pet Experience System**:
   - All EXP sources defined in `backend/app/api/pet.py`
   - Update pet EXP after corresponding actions (deposit, vote, todo completion, etc.)
   - Evolution triggers auto-calculated from experience level

9. **Approval Workflow**:
   - Use `ApprovalRequest` + `ApprovalRequestType` for any action needing consensus
   - Check all family members have approved before executing
   - One rejection = entire request rejected (unanimous required)

10. **Frontend-Backend Contract**:
    - API returns Pydantic schemas serialized as JSON
    - Frontend uses snake_case matching the backend (no auto camelCase conversion)
    - Date/datetime fields serialized as ISO strings
    - Errors return `{"detail": "error message"}` with appropriate HTTP status

## Environment Configuration

**Backend** (`.env` or environment variables):
- `SECRET_KEY`: JWT signing key (auto-generated via `secrets.token_urlsafe(32)`, **must change in production**)
- `DATABASE_URL`: SQLite path (default: `sqlite+aiosqlite:///./golden_nest.db`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT expiration (default: 10080 = 7 days)
- `ALGORITHM`: JWT algorithm (default: HS256)
- `BACKEND_CORS_ORIGINS`: Allowed origins for CORS (default: `["http://localhost:5173", "http://localhost:3000"]`)

**Frontend** (`vite.config.ts`):
- Dev server proxies `/api` requests to `http://localhost:8000`
- Path alias: `@/` maps to `src/`
- Host: `0.0.0.0` (accessible from any network interface)

**Docker** (`docker-compose.yml`):
- Backend container: `golden-nest-backend` (internal port 8000)
- Frontend container: `golden-nest-frontend` (exposed port 8088)
- Shared volume: `./data` → `/data` (SQLite database persistence)
- Network: `golden-nest-network` (bridge mode for inter-container communication)
- Environment: `SECRET_KEY` from `.env` file or defaults to placeholder

## Important Configuration Details

**CORS Setup**: Backend allows specified origins for cross-origin requests. Add production domains to `BACKEND_CORS_ORIGINS` in settings.

**Database Path**:
- Local dev: `./golden_nest.db` in backend directory
- Docker: `/data/golden_nest.db` inside container, mounted from `./data` host directory

**API Documentation**:
- FastAPI auto-generates OpenAPI docs at `/api/docs` (Swagger UI)
- ReDoc version at `/api/redoc`
- OpenAPI schema at `/api/openapi.json`

**SQL Logging**: Enabled in development (`echo=True` in `database.py` engine config). Disable for production by setting `echo=False`.