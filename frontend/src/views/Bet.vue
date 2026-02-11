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
        :class="getStatusClass(bet.status)"
        @click="viewBet(bet)"
      >
        <div class="bet-header">
          <span class="status-badge" :class="bet.status">
            {{ getStatusText(bet.status) }}
          </span>
          <span class="bet-date">{{ formatDate(bet.created_at) }}</span>
        </div>

        <h3 class="bet-title">{{ bet.title }}</h3>
        <p class="bet-desc">{{ bet.description }}</p>

        <div class="bet-meta">
          <span class="meta-item">
            👤 {{ bet.participants.length }} 参与者
          </span>
          <span class="meta-item">
            🎯 {{ bet.options.length }} 选项
          </span>
          <span class="meta-item" v-if="bet.status === 'active'">
            ⏰ {{ getTimeRemaining(bet.end_date) }}
          </span>
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

        <!-- 赌注结果 -->
        <div class="bet-result" v-if="bet.status === 'settled'">
          <div
            v-for="opt in bet.options"
            :key="opt.id"
            class="result-item"
            :class="{ winner: opt.is_winning_option }"
          >
            <span class="option-text">{{ opt.option_text }}</span>
            <span class="vote-count">
              {{ getOptionVoteCount(bet, opt.id) }}人选择
            </span>
            <span v-if="opt.is_winning_option" class="winner-badge">🏆</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建赌注模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal-card" @click.stop>
        <h2>创建新赌注</h2>
        <div class="modal-body">
          <div class="form-item">
            <label>赌注标题*</label>
            <input v-model="createForm.title" placeholder="例如：明天会下雨吗？" />
          </div>

          <div class="form-item">
            <label>详细描述*</label>
            <textarea v-model="createForm.description" rows="3" placeholder="详细说明赌注内容和规则"></textarea>
          </div>

          <div class="form-row">
            <div class="form-item">
              <label>开始日期*</label>
              <input v-model="createForm.start_date" type="datetime-local" />
            </div>
            <div class="form-item">
              <label>结束日期*</label>
              <input v-model="createForm.end_date" type="datetime-local" />
            </div>
          </div>

          <div class="form-item">
            <label>参与者* (至少2人)</label>
            <div class="participants-selector">
              <div
                v-for="member in familyMembers"
                :key="member.user_id"
                class="member-checkbox"
                @click="toggleParticipant(member.user_id)"
              >
                <input type="checkbox" :checked="isParticipantSelected(member.user_id)" />
                <span>{{ member.user_nickname }}</span>
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
            <label>押注股份 (可选)</label>
            <input v-model.number="createForm.stake_amount" type="number" min="0" step="0.01" placeholder="0.00" />
            <span class="form-hint">输入0表示不押注股份，仅娱乐</span>
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
        <h2>{{ selectedBet.title }}</h2>

        <div class="detail-section">
          <h3>赌注描述</h3>
          <p>{{ selectedBet.description }}</p>
        </div>

        <div class="detail-section">
          <h3>时间信息</h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">开始时间</span>
              <span>{{ formatFullDate(selectedBet.start_date) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">结束时间</span>
              <span>{{ formatFullDate(selectedBet.end_date) }}</span>
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
                selected: isMyVote(opt.id),
                winner: opt.is_winning_option,
                disabled: !canVote
              }"
              @click="vote(opt.id)"
            >
              <div class="option-header">
                <span class="option-text">{{ opt.option_text }}</span>
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
        </div>

        <div class="detail-section">
          <h3>参与者</h3>
          <div class="participants-detail">
            <div v-for="p in selectedBet.participants" :key="p.id" class="participant-card">
              <span class="participant-name">{{ p.user_nickname }}</span>
              <span class="participant-stake" v-if="p.stake_amount > 0">
                押注: {{ p.stake_amount }} 股份
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

        <div class="modal-actions">
          <button class="btn-cancel" @click="showDetailModal = false">关闭</button>
          <button
            v-if="canSettle"
            class="btn-settle"
            @click="showSettleModal = true"
          >
            🏆 结算赌注
          </button>
          <button
            v-if="canCancel"
            class="btn-danger"
            @click="cancelBet"
          >
            取消赌注
          </button>
        </div>
      </div>
    </div>

    <!-- 结算模态框 -->
    <div v-if="showSettleModal && selectedBet" class="modal-overlay" @click="showSettleModal = false">
      <div class="modal-card" @click.stop>
        <h2>结算赌注</h2>
        <div class="modal-body">
          <p>请选择获胜的选项：</p>
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
            {{ settling ? '结算中...' : '确认结算' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'
import UserAvatar from '@/components/UserAvatar.vue'

const message = useMessage()
const userStore = useUserStore()

// Tabs
const tabs = [
  { label: '全部', value: 'all' },
  { label: '待审批', value: 'pending' },
  { label: '进行中', value: 'active' },
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

// Create form
const createForm = ref({
  title: '',
  description: '',
  start_date: '',
  end_date: '',
  participants: [] as number[],
  options: ['', ''],
  stake_amount: 0
})

// Computed
const isCreateFormValid = computed(() => {
  return createForm.value.title.trim() &&
    createForm.value.description.trim() &&
    createForm.value.start_date &&
    createForm.value.end_date &&
    createForm.value.participants.length >= 2 &&
    createForm.value.options.filter(o => o.trim()).length >= 2
})

const canVote = computed(() => {
  if (!selectedBet.value) return false
  return selectedBet.value.status === 'active' && !selectedBet.value.is_expired
})

const canSettle = computed(() => {
  if (!selectedBet.value) return false
  return selectedBet.value.can_settle && isAdmin()
})

const canCancel = computed(() => {
  if (!selectedBet.value) return false
  const isCreator = selectedBet.value.creator_id === userStore.user?.id
  return (isCreator || isAdmin()) && selectedBet.value.status !== 'settled'
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
    settled: '已结算',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = date.getTime() - now.getTime()

  if (Math.abs(diff) < 86400000) {
    const hours = Math.floor(Math.abs(diff) / 3600000)
    return diff > 0 ? `${hours}小时后` : `${hours}小时前`
  }

  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function formatFullDate(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

function getTimeRemaining(endDate: string) {
  const end = new Date(endDate)
  const now = new Date()
  const diff = end.getTime() - now.getTime()

  if (diff < 0) return '已结束'

  const days = Math.floor(diff / 86400000)
  const hours = Math.floor((diff % 86400000) / 3600000)

  if (days > 0) return `剩余${days}天`
  return `剩余${hours}小时`
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

async function loadBets() {
  loading.value = true
  try {
    const status = currentTab.value === 'all' ? undefined : currentTab.value
    const { data } = await api.get('/bet/list', { params: { status, page: 1, page_size: 50 } })
    bets.value = data.items || []
  } catch (error: any) {
    message.error(error.response?.data?.detail || '加载赌注失败')
  } finally {
    loading.value = false
  }
}

async function loadFamilyMembers() {
  try {
    const { data } = await api.get('/family/members')
    familyMembers.value = data || []
  } catch (error: any) {
    console.error('加载家庭成员失败:', error)
  }
}

async function createBet() {
  creating.value = true
  try {
    const participants = createForm.value.participants.map(userId => ({
      user_id: userId,
      stake_amount: createForm.value.stake_amount,
      stake_description: null
    }))

    const options = createForm.value.options
      .filter(o => o.trim())
      .map(text => ({ option_text: text }))

    await api.post('/bet/create', {
      title: createForm.value.title,
      description: createForm.value.description,
      start_date: new Date(createForm.value.start_date).toISOString(),
      end_date: new Date(createForm.value.end_date).toISOString(),
      participants,
      options
    })

    message.success('赌注创建成功！')
    showCreateModal.value = false
    resetCreateForm()
    await loadBets()
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
    start_date: '',
    end_date: '',
    participants: [],
    options: ['', ''],
    stake_amount: 0
  }
}

async function viewBet(bet: any) {
  try {
    const { data } = await api.get(`/bet/${bet.id}`)
    selectedBet.value = data
    showDetailModal.value = true
  } catch (error: any) {
    message.error(error.response?.data?.detail || '加载详情失败')
  }
}

async function vote(optionId: number) {
  if (!canVote.value || !selectedBet.value) return

  try {
    const { data } = await api.post(`/bet/${selectedBet.value.id}/vote`, {
      option_id: optionId
    })
    selectedBet.value = data
    message.success('投票成功！')
    await loadBets()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '投票失败')
  }
}

async function settleBet() {
  if (!settleWinningOption.value || !selectedBet.value) return

  settling.value = true
  try {
    await api.post(`/bet/${selectedBet.value.id}/settle`, {
      winning_option_id: settleWinningOption.value
    })
    message.success('结算成功！')
    showSettleModal.value = false
    showDetailModal.value = false
    settleWinningOption.value = null
    await loadBets()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '结算失败')
  } finally {
    settling.value = false
  }
}

async function cancelBet() {
  if (!selectedBet.value) return

  try {
    await api.post(`/bet/${selectedBet.value.id}/cancel`)
    message.success('已取消赌注')
    showDetailModal.value = false
    await loadBets()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '取消失败')
  }
}

function changeTab(value: string) {
  currentTab.value = value
  loadBets()
}

onMounted(() => {
  loadBets()
  loadFamilyMembers()
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
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--theme-text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
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

.modal-card h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: var(--theme-text-primary);
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
}
</style>
