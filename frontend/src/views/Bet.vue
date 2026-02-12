<template>
  <div class="bet-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>🎲 家庭赌注</h1>
      <p>与家人一起进行友好的预测游戏，增添生活乐趣</p>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <button class="btn-create" @click="showCreateModal = true">
        ➕ 创建赌注
      </button>
      <div class="filter-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          :class="['tab-btn', { active: currentTab === tab.value }]"
          @click="changeTab(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span>
      <p>加载中...</p>
    </div>

    <!-- 赌注列表 -->
    <div v-else class="bet-list">
      <div v-if="bets.length === 0" class="empty-state">
        <div class="empty-icon">🎲</div>
        <p>暂无{{ currentTab === 'all' ? '' : tabs.find(t => t.value === currentTab)?.label }}赌注</p>
        <button class="btn-create-empty" @click="showCreateModal = true">
          创建第一个赌注
        </button>
      </div>

      <div
        v-for="bet in bets"
        :key="bet.id"
        class="bet-card"
        :class="[getStatusClass(bet.status), { 'needs-vote': needsMyVote(bet) }]"
        @click="viewBet(bet)"
      >
        <div class="bet-header">
          <span class="status-badge" :class="bet.status">
            {{ getStatusText(bet.status) }}
          </span>
          <span v-if="needsMyVote(bet)" class="needs-vote-badge">🔴 {{ getActionText(bet) }}</span>
          <span class="bet-date">{{ formatDate(bet.created_at) }}</span>
        </div>

        <h3 class="bet-title">{{ bet.title }}</h3>
        <p class="bet-desc">{{ bet.description }}</p>

        <div class="bet-meta">
          👤 {{ bet.participants.length }}参与
          <span class="meta-sep">·</span>
          🎯 {{ bet.options.length }}选项
          <template v-if="bet.status === 'active'">
            <span class="meta-sep">·</span>
            ⏰ {{ getTimeRemaining(bet.end_date) }}
            <span class="meta-sep">·</span>
            🗳️ {{ bet.voted_count || 0 }}/{{ bet.participants.length }}已投票
          </template>
          <template v-if="bet.status === 'awaiting_result'">
            <span class="meta-sep">·</span>
            📝 等待结果登记
          </template>
          <template v-if="bet.status === 'result_pending'">
            <span class="meta-sep">·</span>
            📋 结果待确认
          </template>
        </div>

        <!-- 参与者投票状态 -->
        <div class="participants-status" v-if="bet.status === 'active'">
          <div
            v-for="p in bet.participants"
            :key="p.id"
            class="participant-item"
            :class="{ voted: p.selected_option_id }"
          >
            <span class="participant-name">{{ p.user_nickname }}</span>
            <span class="vote-status">
              {{ p.selected_option_id ? '✅' : '⏳' }}
            </span>
          </div>
        </div>

        <!-- 参与者确认状态 -->
        <div class="participants-status" v-if="bet.status === 'result_pending'">
          <div
            v-for="p in bet.participants"
            :key="p.id"
            class="participant-item"
            :class="{ voted: p.has_approved }"
          >
            <span class="participant-name">{{ p.user_nickname }}</span>
            <span class="vote-status">
              {{ p.has_approved ? '✅' : '⏳' }}
            </span>
          </div>
        </div>

        <!-- 赌注结果 -->
        <div class="bet-result" v-if="bet.status === 'settled'">
          <div
            v-for="opt in bet.options"
            :key="opt.id"
            class="result-item"
            :class="{ winner: opt.is_winning_option }"
          >
          <span class="option-text">{{ opt.option_text }}</span>
          <span v-if="opt.is_winning_option" class="winner-badge">🏆</span>
          <span class="vote-count">
            {{ getOptionVoteCount(bet, opt.id) }}人选择
          </span>
          </div>
        </div>

      </div>
    </div>

    <!-- 创建赌注模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal-card" @click.stop>
        <div class="modal-header-row">
          <h2>创建新赌注</h2>
          <button
            class="btn-ai-fill"
            :disabled="!createForm.title.trim() || aiFillingForm"
            @click="aiAutoFill"
            :title="createForm.title.trim() ? 'AI 辅助填写' : '请先输入标题'"
          >
            {{ aiFillingForm ? '⏳ 填写中...' : '🤖 AI 辅助' }}
          </button>
        </div>
        <div class="modal-body">
          <div class="form-item">
            <label>赌注标题*</label>
            <input v-model="createForm.title" placeholder="例如：明天会下雨吗？" />
          </div>

          <div class="form-item">
            <label>详细描述*</label>
            <textarea v-model="createForm.description" rows="3" placeholder="详细说明赌注内容和规则"></textarea>
          </div>

          <div class="form-item">
            <label>下注截止时间*</label>
            <div class="deadline-selector">
              <button
                v-for="opt in deadlineOptions"
                :key="opt.value"
                :class="['deadline-btn', { active: createForm.deadline_hours === opt.value }]"
                @click="createForm.deadline_hours = opt.value"
                type="button"
              >
                {{ opt.label }}
              </button>
            </div>
            <div v-if="createForm.deadline_hours === -1" class="custom-deadline-row">
              <input
                v-model.number="customDeadlineValue"
                type="number"
                min="1"
                placeholder="数值"
                class="custom-deadline-input"
              />
              <select v-model="customDeadlineUnit" class="custom-deadline-select">
                <option value="minutes">分钟</option>
                <option value="hours">小时</option>
                <option value="days">天</option>
              </select>
            </div>
            <span class="form-hint">赌注创建后开始倒计时，截止前参与者可以投票</span>
          </div>

          <div class="form-item">
            <label>参与者* (至少2人)</label>
            <div v-if="familyMembers.length === 0" class="form-hint" style="color: var(--theme-error);">
              ⚠️ 无法加载家庭成员，请确认已加入家庭
            </div>
            <div class="participants-selector">
              <div
                v-for="member in familyMembers"
                :key="member.user_id"
                class="member-checkbox"
                :class="{ selected: isParticipantSelected(member.user_id) }"
                @click="toggleParticipant(member.user_id)"
              >
                <input type="checkbox" :checked="isParticipantSelected(member.user_id)" />
                <span>{{ member.nickname || member.user_nickname }}</span>
              </div>
            </div>
          </div>

          <div class="form-item">
            <label>赌注选项* (至少2个)</label>
            <div class="options-list">
              <div v-for="(opt, idx) in createForm.options" :key="idx" class="option-input">
                <input v-model="createForm.options[idx]" placeholder="选项内容" />
                <button v-if="createForm.options.length > 2" class="btn-remove" @click="removeOption(idx)">
                  ✕
                </button>
              </div>
              <button class="btn-add-option" @click="addOption">
                ➕ 添加选项
              </button>
            </div>
          </div>

          <div class="form-item">
            <label>押注内容 (可选)</label>
            <input v-model="createForm.stake_description" placeholder="例如：请客吃饭、做一周家务..." />
            <span class="form-hint">描述输掉的一方需要做什么，留空表示仅娱乐</span>
          </div>

          <div class="form-item">
            <label>押注股份 (可选)</label>
            <div class="stake-row">
              <div class="stake-input-group">
                <label class="stake-sub-label">价值(¥)</label>
                <input
                  v-model.number="stakeValue"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  @input="onStakeValueChange"
                />
              </div>
              <span class="stake-separator">⇄</span>
              <div class="stake-input-group">
                <label class="stake-sub-label">股份(%)</label>
                <input
                  v-model.number="createForm.stake_amount"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  @input="onStakeAmountChange"
                />
              </div>
            </div>
            <span class="form-hint">
              输入0表示不押注股份，仅娱乐{{ equityInfo ? `（当前家庭总资产 ¥${formatNumber(equityInfo.total_savings)}）` : '' }}
            </span>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-cancel" @click="showCreateModal = false">取消</button>
          <button class="btn-confirm" @click="createBet" :disabled="creating || !isCreateFormValid">
            {{ creating ? '创建中...' : '创建赌注' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 赌注详情模态框 -->
    <div v-if="showDetailModal && selectedBet" class="modal-overlay" @click="showDetailModal = false">
      <div class="modal-card bet-detail-modal" @click.stop>
        <div class="detail-header">
          <div class="detail-header-top">
            <div class="detail-header-actions">
              <button
                v-if="canCloseVoting"
                class="btn-settle"
                @click="closeVoting"
                :disabled="closingVoting"
              >
                ⏰ {{ closingVoting ? '处理中...' : '提前截止投票' }}
              </button>
              <button
                v-if="canDeclareResult"
                class="btn-settle"
                @click="showSettleModal = true"
              >
                📝 登记结果
              </button>
              <button
                v-if="canCancel"
                class="btn-danger"
                @click="showCancelConfirm = true"
              >
                取消赌注
              </button>
            </div>
            <button class="btn-close-x" @click="showDetailModal = false">✕</button>
          </div>
          <h2>{{ selectedBet.title }}</h2>
        </div>

        <div class="detail-section">
          <h3>赌注描述</h3>
          <p>{{ selectedBet.description }}</p>
        </div>

        <div class="detail-section">
          <h3>时间信息</h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">创建时间</span>
              <span>{{ formatFullDate(selectedBet.created_at) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">下注截止</span>
              <span>{{ formatFullDate(selectedBet.end_date) }}</span>
              <span v-if="selectedBet.status === 'active'" class="countdown-badge">
                {{ getTimeRemaining(selectedBet.end_date) }}
              </span>
              <span v-if="isDetailExpired && selectedBet.status !== 'settled'" class="expired-badge">已截止</span>
            </div>
            <div class="info-item" v-if="selectedBet.settlement_date">
              <span class="info-label">结算时间</span>
              <span>{{ formatFullDate(selectedBet.settlement_date) }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h3>选项与投票</h3>
          <div class="options-voting">
            <div
              v-for="opt in selectedBet.options"
              :key="opt.id"
              class="vote-option"
              :class="{
                selected: isMyVote(opt.id) || pendingVoteOptionId === opt.id,
                winner: opt.is_winning_option,
                disabled: !canVote
              }"
              @click="selectVoteOption(opt.id)"
            >
              <div class="option-header">
                <span class="option-text">{{ opt.option_text }}</span>
                <span v-if="pendingVoteOptionId === opt.id && canVote" class="pending-vote-badge">👈 已选择</span>
                <span v-if="opt.is_winning_option" class="winner-badge">🏆 获胜</span>
              </div>
              <div class="option-voters">
                <span v-for="p in getOptionVoters(opt.id)" :key="p.id" class="voter-name">
                  {{ p.user_nickname }}
                </span>
                <span v-if="getOptionVoters(opt.id).length === 0" class="no-voters">
                  暂无投票
                </span>
              </div>
            </div>
          </div>
          <!-- 确认下注按钮 -->
          <div v-if="canVote && pendingVoteOptionId" class="vote-confirm-bar">
            <span class="vote-confirm-text">已选择: <strong>{{ getOptionText(pendingVoteOptionId) }}</strong></span>
            <button class="btn-confirm" @click="confirmVote" :disabled="votingInProgress">
              {{ votingInProgress ? '提交中...' : '✅ 确认下注' }}
            </button>
          </div>
        </div>

        <div class="detail-section">
          <h3>参与者</h3>
          <div class="participants-detail">
            <div v-for="p in selectedBet.participants" :key="p.id" class="participant-card">
              <span class="participant-name">{{ p.user_nickname }}</span>
              <span class="participant-stake" v-if="p.stake_amount > 0">
                押注: {{ p.stake_amount }}% 股份
                <span v-if="equityInfo?.total_savings">(≈¥{{ formatNumber(p.stake_amount / 100 * equityInfo.total_savings) }})</span>
              </span>
              <span class="participant-stake-desc" v-if="p.stake_description">
                    <span class="participant-stake">附加：</span>
                🎯 {{ p.stake_description }}
              </span>
              <span class="participant-vote">
                {{ p.selected_option_text || '未投票' }}
              </span>
              <span v-if="p.is_winner !== null" class="winner-status">
                {{ p.is_winner ? '✅ 获胜' : '❌ 失败' }}
              </span>
            </div>
          </div>
        </div>

        <!-- 结果确认区域 (RESULT_PENDING) -->
        <div v-if="selectedBet.status === 'result_pending'" class="detail-section result-confirmation-section">
          <h3>📋 结果确认</h3>
          <div class="declared-result">
            <p>创建者 <strong>{{ selectedBet.creator_nickname }}</strong> 登记的获胜选项：</p>
            <div class="declared-winner">
              🏆 {{ getDeclaredWinnerText() }}
            </div>
          </div>
          <div class="approval-status-list">
            <div v-for="p in selectedBet.participants" :key="p.id" class="approval-item">
              <span class="participant-name">{{ p.user_nickname }}</span>
              <span :class="['approval-badge', p.has_approved ? 'approved' : 'pending']">
                {{ p.has_approved ? '✅ 已确认' : '⏳ 待确认' }}
              </span>
            </div>
          </div>
          <div v-if="canApproveResult" class="approval-actions">
            <button class="btn-confirm" @click="approveResult(true)" :disabled="approvingResult">
              {{ approvingResult ? '处理中...' : '✅ 同意结果' }}
            </button>
            <button class="btn-danger" @click="approveResult(false)" :disabled="approvingResult">
              {{ approvingResult ? '处理中...' : '❌ 驳回结果' }}
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- 取消赌注确认框 -->
    <div v-if="showCancelConfirm" class="modal-overlay" @click="showCancelConfirm = false">
      <div class="modal-card cancel-confirm-modal" @click.stop>
        <h2>⚠️ 确认取消赌注</h2>
        <div class="modal-body">
          <p>确定要取消赌注「{{ selectedBet?.title }}」吗？</p>
          <p class="cancel-warning">取消后无法恢复，已投票的记录将作废。</p>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showCancelConfirm = false">再想想</button>
          <button class="btn-danger" @click="cancelBet">确认取消</button>
        </div>
      </div>
    </div>

    <!-- 登记结果模态框 -->
    <div v-if="showSettleModal && selectedBet" class="modal-overlay" @click="showSettleModal = false">
      <div class="modal-card" @click.stop>
        <h2>📝 登记赌局结果</h2>
        <div class="modal-body">
          <p>请选择获胜的选项（提交后需其他参与者确认）：</p>
          <div class="settle-options">
            <div
              v-for="opt in selectedBet.options"
              :key="opt.id"
              class="settle-option"
              :class="{ selected: settleWinningOption === opt.id }"
              @click="settleWinningOption = opt.id"
            >
              <input type="radio" :checked="settleWinningOption === opt.id" />
              <span>{{ opt.option_text }}</span>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showSettleModal = false">取消</button>
          <button
            class="btn-confirm"
            @click="settleBet"
            :disabled="!settleWinningOption || settling"
          >
            {{ settling ? '提交中...' : '提交结果' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { api, equityApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useBetStore } from '@/stores/bet'

const message = useMessage()
const userStore = useUserStore()
const betStore = useBetStore()

// Tabs
const tabs = [
  { label: '全部', value: 'all' },
  { label: '进行中', value: 'active' },
  { label: '待处理', value: 'pending_action' },
  { label: '已结算', value: 'settled' },
  { label: '已取消', value: 'cancelled' }
]

// State
const loading = ref(false)
const creating = ref(false)
const settling = ref(false)
const currentTab = ref('all')
const bets = ref<any[]>([])
const familyMembers = ref<any[]>([])
const selectedBet = ref<any>(null)

// Modals
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const showSettleModal = ref(false)
const settleWinningOption = ref<number | null>(null)

// AI fill
const aiFillingForm = ref(false)

// Result approval
const approvingResult = ref(false)

// Equity info for share ⇄ value conversion
const equityInfo = ref<any>(null)
const stakeValue = ref(0)

// Deadline options
const deadlineOptions = [
  { label: '3分钟', value: 0.05 },
  { label: '1小时', value: 1 },
  { label: '1天', value: 24 },
  { label: '自定义', value: -1 }
]
const customDeadlineValue = ref(1)
const customDeadlineUnit = ref('hours')

// Create form
// Vote selection (local only, submit on confirm)
const pendingVoteOptionId = ref<number | null>(null)
const votingInProgress = ref(false)

const createForm = ref({
  title: '',
  description: '',
  deadline_hours: 1,
  participants: [] as number[],
  options: ['', ''],
  stake_amount: 0,
  stake_description: ''
})

// Bidirectional share ⇄ value conversion
function onStakeAmountChange() {
  if (equityInfo.value && equityInfo.value.total_savings > 0) {
    stakeValue.value = Math.round((createForm.value.stake_amount / 100) * equityInfo.value.total_savings * 100) / 100
  } else {
    stakeValue.value = 0
  }
}

function onStakeValueChange() {
  if (equityInfo.value && equityInfo.value.total_savings > 0) {
    createForm.value.stake_amount = Math.round((stakeValue.value / equityInfo.value.total_savings) * 100 * 100) / 100
  } else {
    createForm.value.stake_amount = 0
  }
}

function formatNumber(num: number): string {
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// Computed
const isCreateFormValid = computed(() => {
  const deadlineValid = createForm.value.deadline_hours > 0 ||
    (createForm.value.deadline_hours === -1 && customDeadlineValue.value > 0)
  return createForm.value.title.trim() &&
    createForm.value.description.trim() &&
    deadlineValid &&
    createForm.value.participants.length >= 2 &&
    createForm.value.options.filter(o => o.trim()).length >= 2
})

const canVote = computed(() => {
  if (!selectedBet.value) return false
  return selectedBet.value.status === 'active' && !selectedBet.value.is_expired
})

const canDeclareResult = computed(() => {
  if (!selectedBet.value) return false
  const isCreator = selectedBet.value.creator_id === userStore.user?.id
  return isCreator && selectedBet.value.status === 'awaiting_result'
})

const canApproveResult = computed(() => {
  if (!selectedBet.value) return false
  if (selectedBet.value.status !== 'result_pending') return false
  const myParticipant = selectedBet.value.participants?.find((p: any) => p.user_id === userStore.user?.id)
  return myParticipant && !myParticipant.has_approved
})

const isDetailExpired = computed(() => {
  if (!selectedBet.value?.end_date) return false
  return parseUTCDate(selectedBet.value.end_date) < new Date()
})

const canCancel = computed(() => {
  if (!selectedBet.value) return false
  const isCreator = selectedBet.value.creator_id === userStore.user?.id
  const cancelable = ['active', 'awaiting_result', 'result_pending', 'draft', 'pending']
  return isCreator && cancelable.includes(selectedBet.value.status)
})

// Cancel confirmation
const showCancelConfirm = ref(false)

// Close voting early
const closingVoting = ref(false)
const canCloseVoting = computed(() => {
  if (!selectedBet.value) return false
  if (selectedBet.value.status !== 'active') return false
  const isCreator = selectedBet.value.creator_id === userStore.user?.id
  if (!isCreator) return false
  // All participants must have voted
  const totalParticipants = selectedBet.value.participants?.length || 0
  return totalParticipants >= 2 && selectedBet.value.voted_count === totalParticipants
})

// Functions
function isAdmin() {
  // TODO: Check if user is admin
  return true // Placeholder
}

function getStatusClass(status: string) {
  return `status-${status}`
}

function getStatusText(status: string) {
  const statusMap: Record<string, string> = {
    draft: '草稿',
    pending: '待审批',
    active: '进行中',
    awaiting_result: '等待结果',
    result_pending: '结果确认中',
    settled: '已结算',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

function getActionText(bet: any): string {
  if (bet.status === 'active') return '待投票'
  if (bet.status === 'awaiting_result') return '待登记结果'
  if (bet.status === 'result_pending') return '待确认结果'
  return '待处理'
}

function getDeclaredWinnerText(): string {
  if (!selectedBet.value?.declared_winning_option_id) return '未知'
  const opt = selectedBet.value.options?.find((o: any) => o.id === selectedBet.value.declared_winning_option_id)
  return opt?.option_text || '未知'
}

function parseUTCDate(dateStr: string): Date {
  // Backend returns UTC times without 'Z' suffix — ensure proper parsing
  if (dateStr && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
    return new Date(dateStr + 'Z')
  }
  return new Date(dateStr)
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const date = parseUTCDate(dateStr)
  const now = new Date()
  const diff = date.getTime() - now.getTime()
  const absDiff = Math.abs(diff)

  if (absDiff < 60000) {
    return '刚刚'
  }
  if (absDiff < 3600000) {
    const minutes = Math.floor(absDiff / 60000)
    return diff > 0 ? `${minutes}分钟后` : `${minutes}分钟前`
  }
  if (absDiff < 86400000) {
    const hours = Math.floor(absDiff / 3600000)
    return diff > 0 ? `${hours}小时后` : `${hours}小时前`
  }

  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function formatFullDate(dateStr: string) {
  if (!dateStr) return ''
  const date = parseUTCDate(dateStr)
  return date.toLocaleString('zh-CN')
}

function getTimeRemaining(endDate: string) {
  const end = parseUTCDate(endDate)
  const now = new Date()
  const diff = end.getTime() - now.getTime()

  if (diff < 0) return '已截止'

  const days = Math.floor(diff / 86400000)
  const hours = Math.floor((diff % 86400000) / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)

  if (days > 0) return `剩余${days}天${hours}小时`
  if (hours > 0) return `剩余${hours}小时${minutes}分`
  if (minutes > 0) return `剩余${minutes}分钟`
  return '即将截止'
}

function getOptionVoteCount(bet: any, optionId: number) {
  return bet.participants.filter((p: any) => p.selected_option_id === optionId).length
}

function isParticipantSelected(userId: number) {
  return createForm.value.participants.includes(userId)
}

function toggleParticipant(userId: number) {
  const idx = createForm.value.participants.indexOf(userId)
  if (idx === -1) {
    createForm.value.participants.push(userId)
  } else {
    createForm.value.participants.splice(idx, 1)
  }
}

function addOption() {
  createForm.value.options.push('')
}

function removeOption(idx: number) {
  createForm.value.options.splice(idx, 1)
}

function isMyVote(optionId: number) {
  if (!selectedBet.value) return false
  const myParticipant = selectedBet.value.participants.find((p: any) => p.user_id === userStore.user?.id)
  return myParticipant?.selected_option_id === optionId
}

function getOptionVoters(optionId: number) {
  if (!selectedBet.value) return []
  return selectedBet.value.participants.filter((p: any) => p.selected_option_id === optionId)
}

function needsMyVote(bet: any): boolean {
  if (bet.status === 'active') {
    const myParticipant = bet.participants?.find((p: any) => p.user_id === userStore.user?.id)
    return myParticipant && !myParticipant.selected_option_id
  }
  if (bet.status === 'result_pending') {
    const myParticipant = bet.participants?.find((p: any) => p.user_id === userStore.user?.id)
    return myParticipant && !myParticipant.has_approved
  }
  if (bet.status === 'awaiting_result') {
    return bet.creator_id === userStore.user?.id
  }
  return false
}

async function loadBets() {
  loading.value = true
  try {
    let status: string | undefined = currentTab.value === 'all' ? undefined : currentTab.value
    // 特殊 tab：待处理 = awaiting_result + result_pending
    if (currentTab.value === 'pending_action') {
      // 加载两种状态的赌注
      const [r1, r2] = await Promise.all([
        api.get('/bet/list', { params: { status: 'awaiting_result', page: 1, page_size: 50 } }),
        api.get('/bet/list', { params: { status: 'result_pending', page: 1, page_size: 50 } })
      ])
      bets.value = [...(r1.data.items || []), ...(r2.data.items || [])]
    } else {
      const { data } = await api.get('/bet/list', { params: { status, page: 1, page_size: 50 } })
      bets.value = data.items || []
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '加载赌注失败')
  } finally {
    loading.value = false
  }
}

async function loadFamilyMembers() {
  try {
    const { data } = await api.get('/family/my')
    familyMembers.value = (data.members || []).map((m: any) => ({
      user_id: m.user_id,
      nickname: m.nickname,
      user_nickname: m.nickname,
      username: m.username
    }))
    // Auto-select current user as participant
    if (userStore.user?.id && !createForm.value.participants.includes(userStore.user.id)) {
      createForm.value.participants.push(userStore.user.id)
    }
  } catch (error: any) {
    console.error('加载家庭成员失败:', error)
    familyMembers.value = []
  }
}

async function loadEquityInfo() {
  try {
    const { data } = await equityApi.getSummary()
    equityInfo.value = data
  } catch {
    equityInfo.value = null
  }
}

async function createBet() {
  creating.value = true
  try {
    const participants = createForm.value.participants.map(userId => ({
      user_id: userId,
      stake_amount: createForm.value.stake_amount,
      stake_description: createForm.value.stake_description || null
    }))

    const options = createForm.value.options
      .filter(o => o.trim())
      .map(text => ({ option_text: text }))

    // 计算实际截止小时数
    let deadlineHours = createForm.value.deadline_hours
    if (deadlineHours === -1) {
      // 自定义模式
      if (customDeadlineUnit.value === 'days') {
        deadlineHours = customDeadlineValue.value * 24
      } else if (customDeadlineUnit.value === 'minutes') {
        deadlineHours = customDeadlineValue.value / 60
      } else {
        deadlineHours = customDeadlineValue.value
      }
    }

    await api.post('/bet/create', {
      title: createForm.value.title,
      description: createForm.value.description,
      deadline_hours: deadlineHours,
      participants,
      options
    })

    message.success('赌注创建成功！参与者现在可以选择选项了')
    showCreateModal.value = false
    resetCreateForm()
    await loadBets()
    await betStore.refreshNow()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function resetCreateForm() {
  createForm.value = {
    title: '',
    description: '',
    deadline_hours: 1,
    participants: userStore.user?.id ? [userStore.user.id] : [],
    options: ['', ''],
    stake_amount: 0,
    stake_description: ''
  }
  stakeValue.value = 0
  customDeadlineValue.value = 1
  customDeadlineUnit.value = 'hours'
}

async function viewBet(bet: any) {
  try {
    const { data } = await api.get(`/bet/${bet.id}`)
    selectedBet.value = data
    pendingVoteOptionId.value = null
    showDetailModal.value = true
  } catch (error: any) {
    message.error(error.response?.data?.detail || '加载详情失败')
  }
}

function selectVoteOption(optionId: number) {
  if (!canVote.value) return
  pendingVoteOptionId.value = pendingVoteOptionId.value === optionId ? null : optionId
}

function getOptionText(optionId: number): string {
  if (!selectedBet.value) return ''
  const opt = selectedBet.value.options?.find((o: any) => o.id === optionId)
  return opt?.option_text || ''
}

async function confirmVote() {
  if (!pendingVoteOptionId.value || !selectedBet.value) return

  votingInProgress.value = true
  try {
    const { data } = await api.post(`/bet/${selectedBet.value.id}/vote`, {
      option_id: pendingVoteOptionId.value
    })
    selectedBet.value = data
    pendingVoteOptionId.value = null
    message.success('下注成功！')
    await loadBets()
    await betStore.refreshNow()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '下注失败')
  } finally {
    votingInProgress.value = false
  }
}

async function settleBet() {
  if (!settleWinningOption.value || !selectedBet.value) return

  settling.value = true
  try {
    const { data } = await api.post(`/bet/${selectedBet.value.id}/settle`, {
      winning_option_id: settleWinningOption.value
    })
    message.success('结果已提交，等待其他参与者确认')
    showSettleModal.value = false
    selectedBet.value = data
    settleWinningOption.value = null
    await loadBets()
    await betStore.refreshNow()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '提交失败')
  } finally {
    settling.value = false
  }
}

async function approveResult(approved: boolean) {
  if (!selectedBet.value) return

  approvingResult.value = true
  try {
    const { data } = await api.post(`/bet/${selectedBet.value.id}/approve-result`, {
      approved,
      note: null
    })
    if (approved) {
      if (data.status === 'settled') {
        message.success('🎉 所有参与者已确认，赌注已结算！')
      } else {
        message.success('已确认结果')
      }
    } else {
      message.info('已驳回结果，创建者可以重新登记')
    }
    selectedBet.value = data
    await loadBets()
    await betStore.refreshNow()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '操作失败')
  } finally {
    approvingResult.value = false
  }
}

async function cancelBet() {
  if (!selectedBet.value) return

  try {
    await api.post(`/bet/${selectedBet.value.id}/cancel`)
    message.success('已取消赌注')
    showCancelConfirm.value = false
    showDetailModal.value = false
    await loadBets()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '取消失败')
  }
}

async function closeVoting() {
  if (!selectedBet.value) return
  closingVoting.value = true
  try {
    const { data } = await api.post(`/bet/${selectedBet.value.id}/close-voting`)
    message.success('投票已提前截止，请登记结果')
    selectedBet.value = data
    await loadBets()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '操作失败')
  } finally {
    closingVoting.value = false
  }
}

function changeTab(value: string) {
  currentTab.value = value
  loadBets()
}

// AI auto-fill form based on title
async function aiAutoFill() {
  if (!createForm.value.title.trim()) {
    message.warning('请先输入赌注标题')
    return
  }
  aiFillingForm.value = true
  try {
    const prompt = `你是一个家庭赌注助手。用户想创建一个标题为「${createForm.value.title}」的家庭赌注。
请帮忙生成合适的赌注内容，严格按以下 JSON 格式回复，不要添加任何其他文字：
{
  "description": "详细描述赌注内容和规则（1-3句话）",
  "options": ["选项1", "选项2"],
  "stake_description": "押注内容建议，例如：请客吃饭"
}
注意：选项数量2-4个，要合理且有趣。`

    const { data } = await api.post('/ai/chat', {
      message: prompt,
      context_type: 'general'
    })

    // Parse AI response
    const reply = data.reply || ''
    try {
      // Try to extract JSON from the reply
      const jsonMatch = reply.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0])
        if (parsed.description) {
          createForm.value.description = parsed.description
        }
        if (parsed.options && Array.isArray(parsed.options) && parsed.options.length >= 2) {
          createForm.value.options = parsed.options
        }
        if (parsed.stake_description) {
          createForm.value.stake_description = parsed.stake_description
        }
        message.success('AI 已辅助填写表单')
      } else {
        message.warning('AI 返回格式异常，请手动填写')
      }
    } catch {
      message.warning('AI 返回解析失败，请手动填写')
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || 'AI 服务暂时不可用')
  } finally {
    aiFillingForm.value = false
  }
}

onMounted(() => {
  loadBets()
  loadFamilyMembers()
  loadEquityInfo()
})
</script>

<style scoped>
.bet-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 32px;
  margin-bottom: 8px;
  color: var(--theme-text-primary);
}

.page-header p {
  color: var(--theme-text-secondary);
  font-size: 14px;
}

/* Action bar */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.btn-create {
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: opacity 0.2s;
}

.btn-create:hover {
  opacity: 0.9;
}

.filter-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  padding: 8px 16px;
  background: var(--theme-bg-secondary);
  color: var(--theme-text-secondary);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: var(--theme-bg-hover);
}

.tab-btn.active {
  background: var(--theme-primary);
  color: white;
}

/* Loading */
.loading {
  text-align: center;
  padding: 60px 20px;
  color: var(--theme-text-secondary);
}

.spinner {
  display: inline-block;
  width: 32px;
  height: 32px;
  border: 3px solid var(--theme-border);
  border-top: 3px solid var(--theme-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--theme-text-tertiary);
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.btn-create-empty {
  margin-top: 16px;
  padding: 10px 24px;
  background: var(--theme-primary);
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
}

/* Bet list */
.bet-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.bet-card {
  background: var(--theme-bg-card);
  border-radius: 16px;
  padding: 20px;
  border: 2px solid var(--theme-border-light);
  box-shadow: 0 4px 16px var(--theme-shadow);
  cursor: pointer;
  transition: all 0.3s;
}

.bet-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px var(--theme-shadow-hover);
}

.bet-card.status-active {
  border-color: #667eea;
}

.bet-card.status-settled {
  border-color: #18a058;
}

.bet-card.status-pending {
  border-color: #f0a020;
}

.bet-card.needs-vote {
  border-color: #d03050;
  animation: pulse-border 2s infinite;
}

@keyframes pulse-border {
  0%, 100% { box-shadow: 0 4px 16px var(--theme-shadow); }
  50% { box-shadow: 0 4px 16px rgba(208, 48, 80, 0.25); }
}

.needs-vote-badge {
  font-size: 12px;
  font-weight: 500;
  color: #d03050;
  animation: pulse-text 1.5s infinite;
}

@keyframes pulse-text {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.bet-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

.status-badge.settled {
  background: rgba(24, 160, 88, 0.1);
  color: #18a058;
}

.status-badge.pending {
  background: rgba(240, 160, 32, 0.1);
  color: #f0a020;
}

.status-badge.cancelled {
  background: rgba(208, 48, 80, 0.1);
  color: #d03050;
}

.status-badge.awaiting_result {
  background: rgba(240, 160, 32, 0.1);
  color: #f0a020;
}

.status-badge.result_pending {
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

.bet-date {
  font-size: 12px;
  color: var(--theme-text-tertiary);
}

.bet-title {
  font-size: 18px;
  margin-bottom: 8px;
  color: var(--theme-text-primary);
}

.bet-desc {
  font-size: 14px;
  color: var(--theme-text-secondary);
  margin-bottom: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.bet-meta {
  margin-bottom: 12px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--theme-text-secondary);
}

.bet-meta .meta-sep {
  margin: 0 4px;
  opacity: 0.35;
}

.participants-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.participant-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--theme-bg-secondary);
  border-radius: 12px;
  font-size: 12px;
}

.participant-item.voted {
  background: rgba(24, 160, 88, 0.1);
  color: #18a058;
}

.bet-result {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--theme-bg-secondary);
  border-radius: 8px;
  font-size: 13px;
}

.result-item.winner {
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.3);
}

.winner-badge {
  font-size: 16px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.modal-card {
  background: var(--theme-bg-card);
  border-radius: 16px;
  padding: 24px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.3);
}

.bet-detail-modal {
  max-width: 800px;
}

.detail-header {
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
  gap: 8px;
}

.detail-header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.detail-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--theme-text-primary);
}

.detail-header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.btn-close-x {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--theme-bg-secondary);
  color: var(--theme-text-secondary);
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-close-x:hover {
  background: var(--theme-error);
  color: white;
}

.modal-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header-row h2 {
  margin: 0;
  font-size: 20px;
  color: var(--theme-text-primary);
}

.btn-ai-fill {
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 16px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: opacity 0.2s;
  white-space: nowrap;
}

.btn-ai-fill:hover:not(:disabled) {
  opacity: 0.85;
}

.btn-ai-fill:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-card h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: var(--theme-text-primary);
}

.stake-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.stake-input-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stake-sub-label {
  font-size: 12px !important;
  color: var(--theme-text-tertiary);
  font-weight: 400 !important;
  margin-bottom: 0 !important;
}

.stake-separator {
  font-size: 18px;
  color: var(--theme-text-tertiary);
  padding-bottom: 10px;
}

.member-checkbox.selected {
  background: rgba(102, 126, 234, 0.15);
  border: 1px solid rgba(102, 126, 234, 0.4);
}

.modal-body {
  margin-bottom: 20px;
}

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--theme-text-primary);
  font-size: 14px;
}

.form-item input,
.form-item textarea {
  width: 100%;
  padding: 10px 16px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--theme-bg-card);
  color: var(--theme-text-primary);
  box-sizing: border-box;
}

.form-item input:focus,
.form-item textarea:focus {
  outline: none;
  border-color: var(--theme-primary);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--theme-text-tertiary);
}

.participants-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.member-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--theme-bg-secondary);
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.member-checkbox:hover {
  background: var(--theme-bg-hover);
}

.member-checkbox input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-input {
  display: flex;
  gap: 8px;
  align-items: center;
}

.option-input input {
  flex: 1;
}

.btn-remove {
  padding: 8px 12px;
  background: var(--theme-error);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.btn-add-option {
  padding: 8px 16px;
  background: var(--theme-bg-secondary);
  color: var(--theme-text-primary);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}

.btn-add-option:hover {
  background: var(--theme-bg-hover);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-cancel,
.btn-confirm,
.btn-settle,
.btn-danger {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: opacity 0.2s;
}

.btn-cancel {
  background: var(--theme-bg-secondary);
  color: var(--theme-text-primary);
}

.btn-confirm,
.btn-settle {
  background: var(--theme-primary);
  color: white;
}

.btn-danger {
  background: var(--theme-error);
  color: white;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel:hover,
.btn-confirm:hover:not(:disabled),
.btn-settle:hover,
.btn-danger:hover {
  opacity: 0.9;
}

/* Detail sections */
.detail-section {
  margin-bottom: 24px;
}

.detail-section h3 {
  font-size: 16px;
  margin-bottom: 12px;
  color: var(--theme-text-primary);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: var(--theme-text-tertiary);
}

.options-voting {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.vote-option {
  padding: 16px;
  background: var(--theme-bg-secondary);
  border: 2px solid var(--theme-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.vote-option:not(.disabled):hover {
  border-color: var(--theme-primary);
  background: var(--theme-bg-hover);
}

.vote-option.selected {
  border-color: var(--theme-primary);
  background: rgba(102, 126, 234, 0.1);
}

.vote-option.winner {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.vote-option.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.option-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.option-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--theme-text-primary);
}

.option-voters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13px;
  color: var(--theme-text-secondary);
}

.voter-name {
  padding: 4px 8px;
  background: var(--theme-bg-card);
  border-radius: 6px;
}

.no-voters {
  color: var(--theme-text-tertiary);
}

.pending-vote-badge {
  font-size: 12px;
  color: var(--theme-primary);
  font-weight: 500;
}

.vote-confirm-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding: 12px 16px;
  background: rgba(102, 126, 234, 0.08);
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 12px;
}

.vote-confirm-text {
  font-size: 14px;
  color: var(--theme-text-secondary);
}

.vote-confirm-text strong {
  color: var(--theme-primary);
}

.participants-detail {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}

.participant-card {
  padding: 12px;
  background: var(--theme-bg-secondary);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.participant-name {
  font-weight: 500;
  color: var(--theme-text-primary);
}

.participant-stake {
  color: var(--theme-text-secondary);
}

.participant-stake-desc {
  color: var(--theme-primary);
  font-size: 13px;
}

.participant-vote {
  color: var(--theme-text-secondary);
}

.winner-status {
  font-weight: 500;
}

.settle-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.settle-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--theme-bg-secondary);
  border: 2px solid var(--theme-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.settle-option:hover {
  border-color: var(--theme-primary);
}

.settle-option.selected {
  border-color: var(--theme-primary);
  background: rgba(102, 126, 234, 0.1);
}

.settle-option input[type="radio"] {
  width: auto;
  margin: 0;
}

/* Deadline selector */
.deadline-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.deadline-btn {
  padding: 8px 16px;
  background: var(--theme-bg-secondary);
  color: var(--theme-text-secondary);
  border: 1px solid var(--theme-border);
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.deadline-btn:hover {
  background: var(--theme-bg-hover);
  border-color: var(--theme-primary);
}

.deadline-btn.active {
  background: var(--theme-primary);
  color: white;
  border-color: var(--theme-primary);
}

.custom-deadline-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.custom-deadline-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--theme-bg-card);
  color: var(--theme-text-primary);
}

.custom-deadline-select {
  padding: 8px 12px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--theme-bg-card);
  color: var(--theme-text-primary);
}

/* Countdown & expired badges */
.countdown-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.expired-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  background: rgba(208, 48, 80, 0.1);
  color: #d03050;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

/* Result confirmation section */
.result-confirmation-section {
  background: var(--theme-bg-secondary);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--theme-border);
}

.declared-result {
  margin-bottom: 16px;
}

.declared-result p {
  margin: 0 0 8px 0;
  color: var(--theme-text-secondary);
  font-size: 14px;
}

.declared-winner {
  padding: 12px 16px;
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  color: var(--theme-text-primary);
}

.approval-status-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.approval-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--theme-bg-card);
  border-radius: 8px;
}

.approval-badge {
  font-size: 13px;
  font-weight: 500;
}

.approval-badge.approved {
  color: #18a058;
}

.approval-badge.pending {
  color: #f0a020;
}

.approval-actions {
  display: flex;
  gap: 12px;
}

.approval-actions .btn-confirm,
.approval-actions .btn-danger {
  flex: 1;
}

/* Card status colors for new statuses */
.bet-card.status-awaiting_result {
  border-color: #f0a020;
}

.bet-card.status-result_pending {
  border-color: #667eea;
}

/* Mobile responsive */
@media (max-width: 767px) {
  .bet-page {
    padding: 12px;
  }

  .page-header h1 {
    font-size: 24px;
  }

  .action-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-tabs {
    justify-content: center;
    flex-wrap: wrap;
  }

  .bet-list {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .participants-detail {
    grid-template-columns: 1fr;
  }

  .detail-header-actions {
    flex-wrap: wrap;
  }
}

/* Cancel confirmation modal */
.cancel-confirm-modal {
  max-width: 400px;
  text-align: center;
}

.cancel-confirm-modal h2 {
  margin-bottom: 16px;
}

.cancel-warning {
  color: var(--theme-error);
  font-size: 13px;
  margin-top: 8px;
}
</style>
