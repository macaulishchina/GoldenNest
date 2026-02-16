# Copilot Instructions

## Project Overview

**Golden Nest (小金库)** — Family wealth management web app with a "shareholding" model.  
**Studio (设计院)** — AI-assisted project design tool embedded in the same monorepo.

### Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + TypeScript + Vite + Naive UI (`n-` prefix components) + Pinia |
| Backend (main app) | FastAPI + SQLAlchemy 2.0 (async) + SQLite (`backend/`) |
| Backend (studio) | FastAPI + SQLAlchemy 2.0 (async) + SQLite (`studio/backend/`) |
| Deployment | Docker Compose with Nginx gateway |

### Key Libraries
- **Naive UI** — All UI components use `n-` prefix
- **ECharts + vue-echarts** — Data visualization
- **dayjs + lunar-javascript** — Date/calendar utilities
- **Pinia** — State management (stores in `src/stores/`)
- **Axios** — HTTP client with centralized interceptors

## Development Commands

### Backend (MUST run from `backend/` directory)
```bash
cd backend && ./run.sh          # Auto-creates venv, installs deps, starts server
# OR manually:
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000
```
**⚠️ Never run `uvicorn` from repository root — it will fail with ModuleNotFoundError.**

### Studio Backend
```bash
cd studio && uvicorn backend.main:app --reload --port 8001
```

### Frontend
```bash
cd frontend && npm run dev      # Dev server on :5173, proxies /api to :8000
cd studio/frontend && npm run dev  # Studio dev on :5174, proxies /studio-api to :8001
```

### Docker
```bash
docker-compose up -d --build
# Frontend: http://localhost:8088, Backend API: http://localhost:8000
```

## Architecture Patterns

### Backend Route Pattern
```python
@router.post("/endpoint")
async def endpoint(
    data: RequestSchema,
    current_user: User = Depends(get_current_user),  # JWT auth
    db: AsyncSession = Depends(get_db),               # Auto-commits on success
) -> ResponseSchema:
    pass  # Business logic
```
- `get_db()` auto-commits on success, rolls back on exception — **never manually commit**
- All protected routes use `Depends(get_current_user)` for JWT authentication
- Errors return `{"detail": "message"}` with appropriate HTTP status

### Frontend Component Pattern
```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
// Composition API with <script setup> — no Options API
</script>
```
- Frontend uses **snake_case** field names matching backend (no camelCase conversion)
- Date/datetime fields are ISO strings
- API client in `src/api/index.ts` with auto Bearer token attachment

### Database
- SQLAlchemy 2.0 async with `AsyncSession`
- No migration framework — schema changes require `ALTER TABLE` in startup or DB recreation
- Auto-migration pattern in `main.py` lifespan event for new columns

## Code Style

- Python: Standard formatting, type hints encouraged, async/await throughout
- TypeScript/Vue: Composition API only, `<script setup lang="ts">`, Naive UI components
- No ESLint/Prettier configured — maintain existing formatting
- Chinese comments/strings used throughout (this is a Chinese-language application)

## Key Business Logic

### Equity Calculation
```python
weighted_amount = amount × (1 + rate)^years
equity_percentage = member_weighted_total / family_weighted_total × 100%
```
Rate is per-family in `Family.time_value_rate` (default 3%).

### Achievement System
60+ achievements auto-detect in `services/achievement.py`. Call `detect_user_achievements()` after any action that could trigger one.

### Tool Calling (Studio)
Studio AI uses OpenAI-native function calling with tools: `read_file`, `search_text`, `list_directory`, `get_file_tree`. Defined in `studio/backend/services/tool_registry.py`. Permissions controlled per-project via `Project.tool_permissions`.

## File Structure Reference

```
backend/app/api/          # 16+ REST endpoint modules
backend/app/services/     # Business logic (equity, achievement, notification)
backend/app/models/       # SQLAlchemy ORM models + enums
backend/app/core/         # Config, database, security, AI functions
frontend/src/views/       # 19 page components
frontend/src/stores/      # Pinia state management
frontend/src/api/         # Centralized Axios API client
studio/backend/           # Studio FastAPI app
studio/frontend/          # Studio Vue app
```

## Protected / Sensitive Areas

- `backend/app/core/security.py` — JWT + bcrypt, handle with care
- `backend/app/core/encryption.py` — Webhook encryption
- `backend/app/services/equity.py` — Core financial calculation, changes affect all users
- Database files (`*.db`) — Never commit to VCS
- `.env` files — Contain secrets, never commit
- `data/` directory — User uploads and persistent data

## Testing

No formal test framework configured. To add:
- Backend: `pytest` + `pytest-asyncio` + `httpx`
- Frontend: `vitest` + `@vue/test-utils`
