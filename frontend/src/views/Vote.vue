<template>
  <div class="vote-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>🗳️ 股东大会</h1>
      <p>家庭重大决策民主投票，全员同意才能通过</p>
    </div>

    <!-- 创建提案按钮 -->
    <div class="action-bar">
      <button class="btn-create" @click="showCreateModal = true">
        📝 发起新提案
      </button>
      <div class="filter-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.value"
          :class="['tab-btn', { active: currentTab === tab.value }]"
          @click="currentTab = tab.value"
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

    <!-- 提案列表 -->
    <div v-else class="proposal-list">
      <div v-if="filteredProposals.length === 0" class="empty-state">
        <div class="empty-icon">📋</div>
        <p>暂无{{ currentTab === 'all' ? '' : tabs.find(t => t.value === currentTab)?.label }}提案</p>
      </div>

      <div 
        v-for="proposal in filteredProposals" 
        :key="proposal.id" 
        class="proposal-card"
        :class="getStatusClass(proposal.status)"
        @click="viewProposal(proposal)"
      >
        <div class="proposal-header">
          <span class="status-badge" :class="proposal.status">
            {{ getStatusText(proposal.status) }}
          </span>
          <span class="proposal-date">{{ formatDate(proposal.created_at) }}</span>
        </div>
        
        <h3 class="proposal-title">{{ proposal.title }}</h3>
        <p class="proposal-desc">{{ proposal.description }}</p>
        
        <div class="proposal-meta">
          <span class="meta-item creator-info">
            <UserAvatar 
              :userId="proposal.creator_id" 
              :name="proposal.creator_name" 
              :size="20" 
              :avatarVersion="proposal.creator_avatar_version" 
            />
            <span>发起人: {{ proposal.creator_name }}</span>
          </span>
          <span class="meta-item">
            🗳️ {{ proposal.voted_count }}/{{ proposal.total_members }} 已投票
          </span>
          <span class="meta-item" v-if="proposal.status === 'voting'">
            ⏰ 截止: {{ formatDate(proposal.deadline) }}
          </span>
        </div>

        <!-- 投票结果（仅在投票结束后显示） -->
        <div class="vote-result-summary" v-if="proposal.status !== 'voting' && proposal.votes_summary">
          <div 
            v-for="(item, idx) in proposal.votes_summary" 
            :key="idx" 
            class="result-bar"
            :class="{ winner: idx === 0 && proposal.status === 'passed' }"
          >
            <div class="result-label">
              <span>{{ item.option }}</span>
              <span>{{ item.count }}票 ({{ item.weight_percent }}%)</span>
            </div>
            <div class="result-progress">
              <div 
                class="result-fill" 
                :style="{ width: item.weight_percent + '%' }"
                :class="{ 'agree': idx === 0, 'disagree': idx === 1 }"
              ></div>
            </div>
          </div>
        </div>

        <div class="vote-progress">
          <div 
            class="progress-bar" 
            :style="{ width: (proposal.voted_count / proposal.total_members * 100) + '%' }"
          ></div>
        </div>

        <div class="my-vote" v-if="proposal.my_vote !== null">
          ✅ 我已投票: {{ proposal.options[proposal.my_vote] }}
        </div>
        <div class="my-vote pending" v-else-if="proposal.status === 'voting'">
          ⏳ 等待我投票
        </div>
      </div>
    </div>

    <!-- 创建提案弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <h2>📝 发起新提案</h2>
        
        <div class="form-group">
          <label>提案标题</label>
          <input v-model="newProposal.title" placeholder="请输入提案标题" />
        </div>

        <div class="form-group">
          <label>详细说明</label>
          <textarea v-model="newProposal.description" placeholder="请描述提案详情..." rows="4"></textarea>
        </div>

        <div class="form-group">
          <label>投票选项</label>
          <div class="options-list">
            <div v-for="(opt, idx) in newProposal.options" :key="idx" class="option-item">
              <input v-model="newProposal.options[idx]" :placeholder="'选项 ' + (idx + 1)" />
              <button v-if="newProposal.options.length > 2" @click="removeOption(idx)" class="btn-remove">✕</button>
            </div>
            <button @click="addOption" class="btn-add-option">+ 添加选项</button>
          </div>
        </div>

        <div class="form-group">
          <label>投票期限 (天)</label>
          <input v-model.number="newProposal.deadline_days" type="number" min="1" max="30" />
        </div>

        <div class="modal-actions">
          <button class="btn-cancel" @click="showCreateModal = false">取消</button>
          <button class="btn-submit" @click="createProposal" :disabled="creating">
            {{ creating ? '提交中...' : '提交提案' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 提案详情弹窗 -->
    <div v-if="selectedProposal" class="modal-overlay" @click.self="selectedProposal = null">
      <div class="modal-content proposal-detail">
        <div class="detail-header">
          <span class="status-badge" :class="selectedProposal.status">
            {{ getStatusText(selectedProposal.status) }}
          </span>
          <h2>{{ selectedProposal.title }}</h2>
        </div>

        <div class="detail-body">
          <p class="description">{{ selectedProposal.description }}</p>
          
          <div class="detail-info">
            <div class="info-row creator-row">
              <UserAvatar 
                :userId="selectedProposal.creator_id" 
                :name="selectedProposal.creator_name" 
                :size="24" 
                :avatarVersion="selectedProposal.creator_avatar_version" 
              />
              <span>发起人: {{ selectedProposal.creator_name }}</span>
            </div>
            <p>📅 发起时间: {{ formatDate(selectedProposal.created_at) }}</p>
            <p>⏰ 截止时间: {{ formatDate(selectedProposal.deadline) }}</p>
            <p>🗳️ 投票进度: {{ selectedProposal.voted_count }}/{{ selectedProposal.total_members }}</p>
          </div>

          <!-- 投票选项 -->
          <div class="vote-options">
            <h4>投票选项</h4>
            <div 
              v-for="(detail, idx) in selectedProposal.votes_detail" 
              :key="idx"
              class="option-result"
              :class="{ selected: selectedProposal.my_vote === idx }"
            >
              <div class="option-info">
                <span class="option-text">{{ detail.option }}</span>
                <span class="vote-count">{{ detail.count }} 票</span>
              </div>
              <div class="voters-list" v-if="detail.voters.length > 0">
                <div class="voter-item" v-for="voter in detail.voters" :key="voter.user_id">
                  <UserAvatar :userId="voter.user_id" :name="voter.name" :size="24" :avatarVersion="voter.avatar_version" />
                  <span class="voter-name">{{ voter.name }}</span>
                </div>
              </div>
              
              <!-- 投票按钮 -->
              <button 
                v-if="selectedProposal.status === 'voting' && selectedProposal.my_vote === null"
                class="btn-vote"
                @click="castVote(idx)"
                :disabled="voting"
              >
                选择此项
              </button>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-cancel" @click="selectedProposal = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { api } from '@/api'
import UserAvatar from '@/components/UserAvatar.vue'

const message = useMessage()

// 状态
const loading = ref(false)
const creating = ref(false)
const voting = ref(false)
const proposals = ref([])
const currentTab = ref('all')
const showCreateModal = ref(false)
const selectedProposal = ref(null)

// 新提案表单
const newProposal = ref({
  title: '',
  description: '',
  options: ['同意', '反对'],
  deadline_days: 7
})

// 标签页
const tabs = [
  { label: '全部', value: 'all' },
  { label: '投票中', value: 'voting' },
  { label: '已通过', value: 'passed' },
  { label: '未通过', value: 'rejected' },
  { label: '已过期', value: 'expired' }
]

// 过滤后的提案列表
const filteredProposals = computed(() => {
  if (currentTab.value === 'all') return proposals.value
  return proposals.value.filter(p => p.status === currentTab.value)
})

// 获取提案列表
const loadProposals = async () => {
  loading.value = true
  try {
    const res = await api.get('/vote/proposals')
    proposals.value = res.data
  } catch (err) {
    console.error('获取提案失败:', err)
  } finally {
    loading.value = false
  }
}

// 创建提案
const createProposal = async () => {
  if (!newProposal.value.title.trim()) {
    message.warning('请输入提案标题')
    return
  }
  if (newProposal.value.options.filter(o => o.trim()).length < 2) {
    message.warning('至少需要2个有效选项')
    return
  }

  creating.value = true
  try {
    await api.post('/vote/proposals', {
      title: newProposal.value.title,
      description: newProposal.value.description,
      options: newProposal.value.options.filter(o => o.trim()),
      deadline_days: newProposal.value.deadline_days
    })
    showCreateModal.value = false
    newProposal.value = { title: '', description: '', options: ['同意', '反对'], deadline_days: 7 }
    message.success('提案创建成功')
    await loadProposals()
  } catch (err) {
    message.error(err.response?.data?.detail || '创建提案失败')
  } finally {
    creating.value = false
  }
}

// 查看提案详情
const viewProposal = async (proposal) => {
  try {
    const res = await api.get(`/vote/proposals/${proposal.id}`)
    selectedProposal.value = res.data
  } catch (err) {
    console.error('获取提案详情失败:', err)
  }
}

// 投票
const castVote = async (optionIndex) => {
  voting.value = true
  try {
    await api.post(`/vote/proposals/${selectedProposal.value.id}/vote`, {
      option_index: optionIndex
    })
    message.success('投票成功')
    await viewProposal(selectedProposal.value)
    await loadProposals()
  } catch (err) {
    message.error(err.response?.data?.detail || '投票失败')
  } finally {
    voting.value = false
  }
}

// 选项操作
const addOption = () => {
  newProposal.value.options.push('')
}

const removeOption = (idx) => {
  newProposal.value.options.splice(idx, 1)
}

// 工具函数
const getStatusText = (status) => {
  const map = {
    voting: '投票中',
    passed: '已通过',
    rejected: '未通过',
    expired: '已过期'
  }
  return map[status] || status
}

const getStatusClass = (status) => {
  return `status-${status}`
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  loadProposals()
})
</script>

<style scoped>
.vote-page {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin-bottom: 8px;
}

.page-header p {
  color: #666;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

/* 移动端响应式 */
@media (max-width: 768px) {
  .action-bar {
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }
  
  .btn-create {
    width: 100%;
    max-width: 280px;
    text-align: center;
  }
  
  .filter-tabs {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }
  
  .tab-btn {
    padding: 6px 12px;
    font-size: 13px;
  }
}

.btn-create {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-create:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.filter-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  padding: 8px 16px;
  border: 1px solid #e0e0e0;
  background: white;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.spinner {
  display: inline-block;
  width: 30px;
  height: 30px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.proposal-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.proposal-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border-left: 4px solid #e0e0e0;
}

.proposal-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}

.proposal-card.status-voting {
  border-left-color: #4caf50;
}

.proposal-card.status-passed {
  border-left-color: #2196f3;
}

.proposal-card.status-rejected {
  border-left-color: #f44336;
}

.proposal-card.status-expired {
  border-left-color: #9e9e9e;
}

.proposal-header {
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

.status-badge.voting {
  background: #e8f5e9;
  color: #4caf50;
}

.status-badge.passed {
  background: #e3f2fd;
  color: #2196f3;
}

.status-badge.rejected {
  background: #ffebee;
  color: #f44336;
}

.status-badge.expired {
  background: #fafafa;
  color: #9e9e9e;
}

.proposal-date {
  font-size: 12px;
  color: #999;
}

.proposal-title {
  font-size: 18px;
  margin: 0 0 8px 0;
  color: #333;
}

.proposal-desc {
  color: #666;
  font-size: 14px;
  margin: 0 0 12px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.proposal-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.vote-progress {
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #8bc34a);
  border-radius: 3px;
  transition: width 0.3s;
}

.my-vote {
  font-size: 13px;
  color: #4caf50;
}

.my-vote.pending {
  color: #ff9800;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  padding: 24px;
  max-width: 500px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-item {
  display: flex;
  gap: 8px;
}

.option-item input {
  flex: 1;
}

.btn-remove {
  background: #f44336;
  color: white;
  border: none;
  width: 36px;
  border-radius: 8px;
  cursor: pointer;
}

.btn-add-option {
  padding: 10px;
  border: 1px dashed #ccc;
  background: none;
  border-radius: 8px;
  cursor: pointer;
  color: #666;
}

.btn-add-option:hover {
  border-color: #667eea;
  color: #667eea;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.btn-cancel {
  padding: 10px 20px;
  border: 1px solid #e0e0e0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
}

.btn-submit {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Proposal Detail */
.proposal-detail {
  max-width: 600px;
}

.detail-header {
  margin-bottom: 16px;
}

.detail-header h2 {
  margin: 12px 0 0 0;
}

.detail-body .description {
  color: #555;
  line-height: 1.6;
  margin-bottom: 16px;
}

.detail-info {
  background: #f9f9f9;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.detail-info p {
  margin: 4px 0;
  font-size: 14px;
  color: #666;
}

.vote-options h4 {
  margin: 0 0 12px 0;
  color: #333;
}

.option-result {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.option-result.selected {
  background: #e8f5e9;
  border: 1px solid #4caf50;
}

.option-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.option-text {
  font-weight: 500;
}

.vote-count {
  color: #666;
  font-size: 14px;
}

.voters {
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
}

.voters-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0;
}

.voter-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  padding: 4px 10px 4px 4px;
  border-radius: 16px;
  border: 1px solid #e0e0e0;
}

.voter-name {
  font-size: 13px;
  color: #555;
}

.btn-vote {
  width: 100%;
  padding: 10px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-vote:hover {
  background: #5a6fd6;
}

.btn-vote:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 发起人信息 */
.creator-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 投票结果汇总 */
.vote-result-summary {
  margin: 12px 0;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.result-bar {
  margin-bottom: 10px;
}

.result-bar:last-child {
  margin-bottom: 0;
}

.result-bar.winner .result-fill.agree {
  background: linear-gradient(90deg, #4caf50, #81c784);
}

.result-label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 4px;
  color: #555;
}

.result-progress {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.result-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.result-fill.agree {
  background: linear-gradient(90deg, #66bb6a, #a5d6a7);
}

.result-fill.disagree {
  background: linear-gradient(90deg, #ef5350, #e57373);
}

/* 详情页发起人头像 */
.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0;
  font-size: 14px;
  color: #666;
}

.detail-info .creator-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
