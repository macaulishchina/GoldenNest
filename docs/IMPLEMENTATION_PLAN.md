# GoldenNest Enhancement Implementation Plan

## Overview
This document outlines the implementation plan for the following features requested:

1. Complete missing AI features from AI_QUICK_REFERENCE.md
2. Add floating AI assistant component (cat character)
3. Add Family Bet (家庭赌注) system
4. Add Accounting (记账) system with AI features

## Current Status

### Completed (From AI_QUICK_REFERENCE.md)
- ✅ Dashboard AI Financial Coach
- ✅ Pet View AI Pet Personality
- ✅ Transaction AI Insights
- ✅ Todo AI Task Assistant
- ✅ Investment AI Portfolio Analyzer (backend ready)
- ✅ Announcement AI Content Assistant (backend ready)

### Missing
- ❌ Investment AI button in frontend UI
- ❌ Announcement AI buttons in frontend UI

## Implementation Phases

### Phase 1: Quick Wins - Missing AI Buttons ⚡ (PRIORITY 1 - 2 hours)

#### 1.1 Investment AI Button
**Files to modify:**
- `frontend/src/views/Investment.vue`

**Changes:**
1. Add AI analysis button in the header area
2. Create modal to display AI analysis results
3. Connect to existing `investmentAiApi.analyze()` endpoint
4. Display:
   - Portfolio risk assessment
   - Diversification score
   - Asset allocation recommendations
   - Improvement suggestions

**Implementation:**
```vue
<!-- Add button near top of Investment.vue -->
<n-button
  type="primary"
  style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
  @click="showAIAnalysis"
>
  🤖 AI 投资分析
</n-button>

<!-- Add modal for results -->
<n-modal v-model:show="showAiModal" preset="card" title="AI 投资组合分析">
  <!-- Display analysis results -->
</n-modal>
```

#### 1.2 Announcement AI Buttons
**Files to modify:**
- `frontend/src/views/Announcement.vue`

**Changes:**
1. Add "AI 草稿" button in publish area
2. Add "AI 优化" button for existing content
3. Connect to existing `announcementAiApi.draft()` and `announcementAiApi.improve()` endpoints
4. Support style options: formal/casual/humorous

**Implementation:**
```vue
<!-- In publish-actions div -->
<button class="ai-draft-btn" @click="showAIDraftDialog">
  🤖 AI 草稿
</button>
<button class="ai-improve-btn" @click="improveContent" v-if="newContent.trim()">
  ✨ AI 优化
</button>
```

### Phase 2: Floating AI Assistant 🐱 (PRIORITY 2 - 4 hours)

**New files:**
- `frontend/src/components/FloatingAIAssistant.vue`

**Features:**
- Draggable floating character (cat by default)
- Click to open quick chat dialog
- Position persistence in localStorage
- Multiple character appearances (cat, dog, robot)
- Idle animations using CSS
- Quick access to AI features

**Implementation Structure:**
```vue
<template>
  <div
    class="floating-assistant"
    :style="{ left: position.x + 'px', top: position.y + 'px' }"
    @mousedown="startDrag"
    @click="toggleChat"
  >
    <div class="assistant-character">
      <span class="character-emoji">{{ characters[selectedCharacter].emoji }}</span>
    </div>
  </div>

  <!-- Quick chat dialog -->
  <AIChatDialog
    v-model:show="showChat"
    :on-chat="handleChat"
    title="AI 助手"
  />
</template>
```

**Character options:**
```typescript
const characters = {
  cat: { emoji: '🐱', name: '小喵' },
  dog: { emoji: '🐶', name: '汪汪' },
  robot: { emoji: '🤖', name: 'AI助手' },
  dragon: { emoji: '🐉', name: '小龙' }
}
```

### Phase 3: Family Bet System 🎲 (PRIORITY 3 - 8 hours)

#### 3.1 Backend Models
**Files to create/modify:**
- `backend/app/models/models.py` - Add new models

**New Models:**
```python
class BetStatus(str, enum.Enum):
    DRAFT = "draft"           # 草稿
    PENDING = "pending"       # 待审批
    ACTIVE = "active"         # 进行中
    SETTLED = "settled"       # 已结算
    CANCELLED = "cancelled"   # 已取消

class Bet(Base):
    """家庭赌注表"""
    __tablename__ = "bets"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[BetStatus] = mapped_column(SQLEnum(BetStatus), default=BetStatus.DRAFT)
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    settlement_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    participants: Mapped[List["BetParticipant"]] = relationship(back_populates="bet")
    options: Mapped[List["BetOption"]] = relationship(back_populates="bet")

class BetParticipant(Base):
    """赌注参与者表"""
    __tablename__ = "bet_participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    bet_id: Mapped[int] = mapped_column(ForeignKey("bets.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    selected_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bet_options.id"), nullable=True)
    stake_amount: Mapped[float] = mapped_column(Float)  # 股份押注（可为0）
    stake_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 其他押注内容
    is_winner: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    bet: Mapped["Bet"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()
    selected_option: Mapped[Optional["BetOption"]] = relationship()

class BetOption(Base):
    """赌注选项表"""
    __tablename__ = "bet_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    bet_id: Mapped[int] = mapped_column(ForeignKey("bets.id"))
    option_text: Mapped[str] = mapped_column(String(200))
    is_winning_option: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Relationships
    bet: Mapped["Bet"] = relationship(back_populates="options")
```

#### 3.2 Backend API
**Files to create:**
- `backend/app/api/bet.py`
- `backend/app/schemas/bet.py`

**Endpoints:**
- `POST /bet/create` - Create bet (auto-creates approval request)
- `GET /bet/list` - List all bets
- `GET /bet/{id}` - Get bet details
- `POST /bet/{id}/vote` - Vote for an option
- `POST /bet/{id}/settle` - Settle bet (admin only)
- `POST /bet/{id}/cancel` - Cancel bet

**Approval workflow:**
1. Creator creates bet → approval request
2. All participants must approve
3. Once approved, bet becomes active
4. Participants vote for options
5. After end_date, creator/admin settles bet
6. Winners gain equity, losers lose equity (automatic via approval system)

#### 3.3 Frontend Views
**Files to create:**
- `frontend/src/views/Bet.vue`

**Sections:**
1. **Create Bet**
   - Title, description, dates
   - Add participants
   - Add options
   - Define stakes (equity or other)

2. **Active Bets List**
   - Card layout showing:
     - Title, description
     - Participants & their choices
     - Status (pending approval/active/settled)
     - Time remaining

3. **Bet Detail View**
   - Full bet information
   - Voting interface (if active)
   - Settlement interface (if admin & past end_date)
   - History log

### Phase 4: Accounting System 📊 (PRIORITY 4 - 12 hours)

#### 4.1 Backend Models
**Files to create/modify:**
- `backend/app/models/models.py`

**New Models:**
```python
class AccountingCategory(str, enum.Enum):
    FOOD = "food"                    # 餐饮
    TRANSPORT = "transport"          # 交通
    SHOPPING = "shopping"            # 购物
    ENTERTAINMENT = "entertainment"  # 娱乐
    HEALTHCARE = "healthcare"        # 医疗
    EDUCATION = "education"          # 教育
    HOUSING = "housing"              # 住房
    UTILITIES = "utilities"          # 水电煤
    OTHER = "other"                  # 其他

class AccountingEntrySource(str, enum.Enum):
    MANUAL = "manual"          # 手动输入
    PHOTO = "photo"            # 拍照识别
    VOICE = "voice"            # 语音输入
    IMPORT = "import"          # 批量导入
    AUTO = "auto"              # 自动生成

class AccountingEntry(Base):
    """记账条目表"""
    __tablename__ = "accounting_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 记账人
    consumer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)  # 消费者

    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[AccountingCategory] = mapped_column(SQLEnum(AccountingCategory))
    description: Mapped[str] = mapped_column(String(500))
    entry_date: Mapped[datetime] = mapped_column(DateTime)  # 消费日期

    source: Mapped[AccountingEntrySource] = mapped_column(SQLEnum(AccountingEntrySource), default=AccountingEntrySource.MANUAL)
    image_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Base64 receipt image

    is_accounted: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已入账
    expense_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("expense_requests.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    family: Mapped["Family"] = relationship()
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    consumer: Mapped[Optional["User"]] = relationship(foreign_keys=[consumer_id])
```

#### 4.2 Backend API with AI Features
**Files to create:**
- `backend/app/api/accounting.py`
- `backend/app/schemas/accounting.py`
- `backend/app/services/accounting_ai.py` (AI features)

**Endpoints:**
- `POST /accounting/entry` - Create entry
- `POST /accounting/entry/photo` - Create from photo (AI OCR)
- `POST /accounting/entry/voice` - Create from voice (AI transcription)
- `POST /accounting/entry/import` - Batch import (CSV/Excel)
- `GET /accounting/list` - List entries with filters
- `PUT /accounting/{id}` - Update entry
- `DELETE /accounting/{id}` - Delete entry
- `POST /accounting/batch-expense` - Create expense request from selected entries

**AI Services:**
```python
# accounting_ai.py
async def parse_receipt_image(image_base64: str) -> dict:
    """AI OCR to extract amount, merchant, date from receipt"""
    result = await ai_service.chat_vision_json(
        text="Extract: amount, merchant name, date from this receipt",
        image_base64=image_base64,
        system_prompt="You are a receipt OCR assistant..."
    )
    return result

async def categorize_entry(description: str, amount: float) -> str:
    """AI auto-categorize based on description"""
    # Similar to transaction categorization

async def transcribe_voice(audio_base64: str) -> str:
    """Transcribe voice input to text"""
    # Note: Requires additional audio API support
```

#### 4.3 Frontend Views
**Files to create:**
- `frontend/src/views/Accounting.vue`
- `frontend/src/components/AccountingEntryForm.vue`

**Features:**

1. **Multi-entry methods:**
   - 📝 Manual form
   - 📷 Photo upload with AI OCR
   - 🎤 Voice input
   - 📂 Batch import (CSV/Excel)
   - 🤖 AI auto-fill

2. **Entry list with filters:**
   - Date range (day/week/month/year)
   - Category
   - Consumer
   - Amount range
   - Accounted status
   - Search by description

3. **Batch operations:**
   - Select multiple entries
   - One-click create expense request
   - Include all entry details in request
   - Bulk delete/edit

4. **Statistics dashboard:**
   - Total by category (pie chart)
   - Daily/weekly/monthly trends (line chart)
   - Top consumers
   - Pending vs accounted ratio

### Phase 5: Testing & Validation ✅ (PRIORITY 5 - 4 hours)

#### 5.1 Mobile Responsiveness
- Test all new features on mobile viewport (<768px)
- Verify touch interactions
- Check scrolling and gestures
- Validate form inputs (prevent iOS zoom on focus)

#### 5.2 Theme Compatibility
- Test light theme
- Test dark theme
- Verify color variables usage
- Check contrast ratios

#### 5.3 End-to-End Testing
- Create test scenarios
- Verify approval workflows
- Test AI features with mock data
- Validate equity calculations for bets

## Timeline Estimation

| Phase | Feature | Estimated Time |
|-------|---------|----------------|
| 1 | Missing AI Buttons | 2 hours |
| 2 | Floating AI Assistant | 4 hours |
| 3 | Family Bet System | 8 hours |
| 4 | Accounting System | 12 hours |
| 5 | Testing & Validation | 4 hours |
| **Total** | | **30 hours** |

## Dependencies

- AI service must be configured in system settings
- Approval system must be functioning
- Equity calculation system must be working
- For voice input: requires additional audio API (optional for MVP)

## Notes

- All features follow existing patterns in the codebase
- Mobile-first design approach
- Dark/light theme support built-in
- Reuse existing components (AIChatDialog, TimeRangeSelector, etc.)
- Follow Vue 3 Composition API with `<script setup>`
- Use Naive UI components consistently
- Backend uses FastAPI async patterns
- Database uses SQLAlchemy 2.0 async

## Next Steps

1. Implement Phase 1 (Quick wins) - IMMEDIATE
2. Implement Phase 2 (Floating assistant) - HIGH PRIORITY
3. Design detailed UI mockups for Phases 3-4
4. Break down Phases 3-4 into smaller tasks
5. Implement and test incrementally
6. Document API usage for future developers

---

**Status**: Phase 1 in progress
**Last Updated**: 2026-02-11
