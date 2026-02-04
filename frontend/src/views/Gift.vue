<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">🎁</span> 股权赠与</h1>
    
    <!-- 发送赠与卡片 -->
    <n-card class="card-hover gift-send-card" style="margin-bottom: 24px">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px">
          <span>💝</span> 赠送股权
        </div>
      </template>
      
      <!-- 桌面端表单 -->
      <n-form class="desktop-only" :model="formData" label-placement="left" label-width="100px">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="赠送对象">
              <n-select
                v-model:value="formData.to_user_id"
                :options="memberOptions"
                placeholder="选择家庭成员"
              />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="赠送比例">
              <n-input-number 
                v-model:value="formData.amount" 
                :min="0.01" 
                :max="myEquity * 100"
                :step="0.1"
                style="width: 100%"
              >
                <template #suffix>%</template>
              </n-input-number>
            </n-form-item>
          </n-gi>
        </n-grid>
        
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="对应金额">
              <n-input 
                :value="'¥' + formatMoney(calculatedAmount)" 
                readonly 
                placeholder="自动计算"
                style="width: 100%"
              />
            </n-form-item>
          </n-gi>
        </n-grid>
        
        <n-form-item label="祝福语">
          <n-input 
            v-model:value="formData.message" 
            type="textarea" 
            placeholder="写下你的祝福（可选）"
            :rows="2"
            maxlength="500"
            show-count
          />
        </n-form-item>
        
        <n-form-item>
          <n-space>
            <n-button 
              type="primary" 
              :loading="submitting" 
              :disabled="!canSend"
              @click="handleSend"
            >
              <template #icon>🎁</template>
              发送赠与
            </n-button>
            <n-text depth="3">
              我的股权：{{ (myEquity * 100).toFixed(2) }}%
            </n-text>
          </n-space>
        </n-form-item>
      </n-form>
      
      <!-- 移动端紧凑表单 -->
      <div class="mobile-only mobile-gift-form">
        <!-- 第一行：赠送对象 + 比例 -->
        <div class="form-row">
          <div class="form-col target-col">
            <label>赠送对象</label>
            <n-select
              v-model:value="formData.to_user_id"
              :options="memberOptions"
              placeholder="选择"
              size="small"
            />
          </div>
          <div class="form-col amount-col">
            <label>赠送比例</label>
            <div class="amount-input-wrapper">
              <n-input-number 
                v-model:value="formData.amount" 
                :min="0.01" 
                :max="myEquity * 100"
                :step="0.1"
                :show-button="false"
                size="small"
                placeholder="0.00"
              />
              <span class="amount-suffix">%</span>
            </div>
          </div>
        </div>
        <!-- 第二行：祝福语（单行输入） -->
        <div class="form-row">
          <div class="form-col message-col">
            <label>祝福语</label>
            <n-input 
              v-model:value="formData.message" 
              placeholder="写下祝福（可选）"
              size="small"
              maxlength="100"
            />
          </div>
        </div>
        <!-- 第三行：发送按钮 + 对应金额 + 股权信息 -->
        <div class="form-row submit-row">
          <n-button 
            type="primary" 
            :loading="submitting" 
            :disabled="!canSend"
            @click="handleSend"
            size="small"
            class="send-btn"
          >
            🎁 发送赠与
          </n-button>
          <div class="submit-info">
            <span class="calculated-amount" v-if="calculatedAmount > 0">≈ ¥{{ formatMoney(calculatedAmount) }}</span>
            <span class="my-equity">我的股权：{{ (myEquity * 100).toFixed(2) }}%</span>
          </div>
        </div>
      </div>
    </n-card>
    
    <!-- 统计卡片 -->
    <n-grid :cols="4" :x-gap="16" style="margin-bottom: 24px">
      <n-gi>
        <n-card class="stat-card card-hover">
          <n-statistic label="发送次数" :value="stats.total_sent">
            <template #prefix>📤</template>
          </n-statistic>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card class="stat-card card-hover">
          <n-statistic label="接收次数" :value="stats.total_received">
            <template #prefix>📥</template>
          </n-statistic>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card class="stat-card card-hover">
          <n-statistic label="送出股权" :value="(stats.total_sent_amount * 100).toFixed(2)">
            <template #suffix>%</template>
          </n-statistic>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card class="stat-card card-hover">
          <n-statistic label="收到股权" :value="(stats.total_received_amount * 100).toFixed(2)">
            <template #suffix>%</template>
          </n-statistic>
        </n-card>
      </n-gi>
    </n-grid>
    
    <!-- 赠与记录 -->
    <n-tabs type="card" animated>
      <n-tab-pane name="received" tab="收到的赠与">
        <template #tab>
          <div style="display: flex; align-items: center; gap: 6px">
            📥 收到的赠与
            <n-badge v-if="pendingCount > 0" :value="pendingCount" type="error" />
          </div>
        </template>
        
        <n-card class="card-hover">
          <div v-if="receivedGifts.length === 0" class="empty-state">
            <n-empty description="还没有收到任何赠与">
              <template #icon>🎁</template>
            </n-empty>
          </div>
          
          <n-space vertical :size="16" v-else>
            <div 
              v-for="gift in receivedGifts" 
              :key="gift.id" 
              class="gift-item"
              :class="{ 'gift-pending': gift.status === 'pending' }"
            >
              <div class="gift-content">
                <div class="gift-header">
                  <UserAvatar :userId="gift.from_user_id" :name="gift.from_user_nickname" :avatarVersion="gift.from_avatar_version" :size="40" />
                  <div class="gift-info">
                    <div class="gift-title">
                      <span class="sender-name">{{ gift.from_user_nickname }}</span>
                      送给你
                      <n-tag type="warning" size="small">{{ (gift.amount * 100).toFixed(2) }}% 股权</n-tag>
                    </div>
                    <div class="gift-time">{{ formatTime(gift.created_at) }}</div>
                  </div>
                  <n-tag :type="getStatusType(gift.status)" size="small">
                    {{ getStatusLabel(gift.status) }}
                  </n-tag>
                </div>
                
                <div v-if="gift.message" class="gift-message">
                  <n-card size="small" style="background: #fffbe6; border: 1px dashed #ffe58f">
                    💌 {{ gift.message }}
                  </n-card>
                </div>
                
                <div v-if="gift.status === 'pending'" class="gift-actions">
                  <n-space>
                    <n-button type="success" size="small" @click="handleRespond(gift.id, true)">
                      ✅ 接受
                    </n-button>
                    <n-button type="error" size="small" @click="handleRespond(gift.id, false)">
                      ❌ 拒绝
                    </n-button>
                  </n-space>
                </div>
              </div>
            </div>
          </n-space>
        </n-card>
      </n-tab-pane>
      
      <n-tab-pane name="sent" tab="发出的赠与">
        <template #tab>📤 发出的赠与</template>
        
        <n-card class="card-hover">
          <div v-if="sentGifts.length === 0" class="empty-state">
            <n-empty description="还没有发送任何赠与">
              <template #icon>💝</template>
            </n-empty>
          </div>
          
          <n-space vertical :size="16" v-else>
            <div 
              v-for="gift in sentGifts" 
              :key="gift.id" 
              class="gift-item"
            >
              <div class="gift-content">
                <div class="gift-header">
                  <UserAvatar :userId="gift.to_user_id" :name="gift.to_user_nickname" :avatarVersion="gift.to_avatar_version" :size="40" />
                  <div class="gift-info">
                    <div class="gift-title">
                      送给
                      <span class="sender-name">{{ gift.to_user_nickname }}</span>
                      <n-tag type="warning" size="small">{{ (gift.amount * 100).toFixed(2) }}% 股权</n-tag>
                    </div>
                    <div class="gift-time">{{ formatTime(gift.created_at) }}</div>
                  </div>
                  <n-tag :type="getStatusType(gift.status)" size="small">
                    {{ getStatusLabel(gift.status) }}
                  </n-tag>
                </div>
                
                <div v-if="gift.message" class="gift-message">
                  <n-card size="small" style="background: #f6ffed; border: 1px dashed #b7eb8f">
                    💌 {{ gift.message }}
                  </n-card>
                </div>
                
                <div v-if="gift.status === 'pending'" class="gift-actions">
                  <n-popconfirm @positive-click="handleCancel(gift.id)">
                    <template #trigger>
                      <n-button type="warning" size="small">撤销赠与</n-button>
                    </template>
                    确定要撤销这个赠与吗？
                  </n-popconfirm>
                </div>
              </div>
            </div>
          </n-space>
        </n-card>
      </n-tab-pane>
    </n-tabs>
    
    <!-- 成功动画 -->
    <Teleport to="body">
      <div v-if="showSuccessAnimation" class="gift-success-overlay" @click="showSuccessAnimation = false">
        <div class="gift-success-content">
          <div class="gift-animation">🎁</div>
          <div class="gift-success-text">赠与发送成功！</div>
          <div class="gift-confetti">🎉🎊✨💖🌟</div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { giftApi, familyApi, equityApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { usePrivacyStore } from '@/stores/privacy'
import { formatShortDateTime } from '@/utils/date'
import { checkAndShowAchievements } from '@/utils/achievement'
import UserAvatar from '@/components/UserAvatar.vue'

const message = useMessage()
const userStore = useUserStore()
const privacyStore = usePrivacyStore()
const loading = ref(false)
const submitting = ref(false)
const showSuccessAnimation = ref(false)

// 数据
const sentGifts = ref<any[]>([])
const receivedGifts = ref<any[]>([])
const pendingCount = ref(0)
const familyMembers = ref<any[]>([])
const myEquity = ref(0)
const totalSavings = ref(0) // 家庭总储蓄

const stats = ref({
  total_sent: 0,
  total_received: 0,
  total_sent_amount: 0,
  total_received_amount: 0
})

const formData = ref({
  to_user_id: null as number | null,
  amount: null as number | null,
  message: ''
})

// 计算属性
const memberOptions = computed(() => {
  return familyMembers.value
    .filter(m => m.user_id !== userStore.user?.id)
    .map(m => ({
      label: m.nickname,
      value: m.user_id
    }))
})

const canSend = computed(() => {
  return formData.value.to_user_id && 
         formData.value.amount && 
         formData.value.amount > 0 &&
         formData.value.amount <= myEquity.value * 100
})

// 计算赠送股权对应的金额
const calculatedAmount = computed(() => {
  if (!formData.value.amount || formData.value.amount <= 0) {
    return 0
  }
  return totalSavings.value * (formData.value.amount / 100)
})

// 格式化金额显示（支持隐私模式）
const formatMoney = (num: number) => {
  if (privacyStore.privacyMode) return '****'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 方法
function formatTime(dateStr: string): string {
  return formatShortDateTime(dateStr)
}

function getStatusType(status: string): 'success' | 'warning' | 'error' | 'default' {
  const map: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
    pending: 'warning',
    accepted: 'success',
    rejected: 'error',
    expired: 'default'
  }
  return map[status] || 'default'
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待接收',
    accepted: '已接受',
    rejected: '已拒绝',
    expired: '已过期'
  }
  return map[status] || status
}

async function loadData() {
  loading.value = true
  try {
    // 并行加载所有数据
    const [giftListRes, statsRes, familyRes, equityRes] = await Promise.all([
      giftApi.list(),
      giftApi.getStats(),
      familyApi.getMy(),
      equityApi.getSummary()
    ])
    
    sentGifts.value = giftListRes.data.sent
    receivedGifts.value = giftListRes.data.received
    pendingCount.value = giftListRes.data.pending_count
    stats.value = statsRes.data
    familyMembers.value = familyRes.data.members || []
    
    // 计算我的股权比例和总储蓄
    const myMember = equityRes.data.members?.find((m: any) => m.user_id === userStore.user?.id)
    myEquity.value = myMember?.equity_ratio || 0
    totalSavings.value = equityRes.data.total_savings || 0
  } catch (error: any) {
    message.error(error.response?.data?.detail || '加载数据失败')
  } finally {
    loading.value = false
  }
}

async function handleSend() {
  if (!canSend.value) return
  
  submitting.value = true
  try {
    await giftApi.send({
      to_user_id: formData.value.to_user_id!,
      amount: formData.value.amount! / 100, // 转换为小数
      message: formData.value.message || undefined
    })
    
    // 显示成功动画
    showSuccessAnimation.value = true
    setTimeout(() => {
      showSuccessAnimation.value = false
    }, 2500)
    
    message.success('赠与发送成功！等待对方接收')
    
    // 重置表单
    formData.value = {
      to_user_id: null,
      amount: null,
      message: ''
    }
    
    // 重新加载数据
    await loadData()
    
    // 检查成就
    setTimeout(() => checkAndShowAchievements(), 500)
  } catch (error: any) {
    message.error(error.response?.data?.detail || '发送失败')
  } finally {
    submitting.value = false
  }
}

async function handleRespond(giftId: number, accept: boolean) {
  try {
    await giftApi.respond(giftId, accept)
    message.success(accept ? '已接受赠与！股权已转入' : '已拒绝赠与')
    await loadData()
    
    // 接受赠与后检查成就
    if (accept) {
      setTimeout(() => checkAndShowAchievements(), 500)
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '操作失败')
  }
}

async function handleCancel(giftId: number) {
  try {
    await giftApi.cancel(giftId)
    message.success('赠与已撤销')
    await loadData()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '撤销失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.stat-card {
  text-align: center;
}

.gift-send-card {
  background: linear-gradient(135deg, #fff9f0 0%, #fff0f5 100%);
}

.gift-item {
  padding: 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
  border: 1px solid #eee;
  transition: all 0.3s ease;
}

.gift-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.gift-pending {
  background: linear-gradient(135deg, #fffbe6 0%, #fff7e6 100%);
  border-color: #ffe58f;
}

.gift-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gift-info {
  flex: 1;
}

.gift-title {
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sender-name {
  font-weight: 600;
  color: #1890ff;
}

.gift-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.gift-message {
  margin-top: 12px;
}

.gift-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #eee;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

/* 成功动画 */
.gift-success-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.3s ease;
}

.gift-success-content {
  text-align: center;
  color: white;
}

.gift-animation {
  font-size: 80px;
  animation: bounce 0.6s ease infinite alternate;
}

.gift-success-text {
  font-size: 24px;
  font-weight: bold;
  margin-top: 20px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.gift-confetti {
  font-size: 32px;
  margin-top: 16px;
  animation: confetti 1s ease infinite;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes bounce {
  from { transform: scale(1) rotate(-5deg); }
  to { transform: scale(1.1) rotate(5deg); }
}

@keyframes confetti {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-10px) scale(1.1); }
}

/* 桌面/移动端显示控制 */
.desktop-only {
  display: block;
}
.mobile-only {
  display: none;
}

/* ===== 移动端紧凑表单样式 ===== */
.mobile-gift-form {
  display: none;
}

.mobile-gift-form .form-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.mobile-gift-form .form-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mobile-gift-form .form-col label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.mobile-gift-form .target-col {
  flex: 1;
}

.mobile-gift-form .amount-col {
  width: 110px;
  flex-shrink: 0;
}

.mobile-gift-form .message-col {
  flex: 1;
}

.mobile-gift-form .amount-input-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mobile-gift-form .amount-input-wrapper .n-input-number {
  flex: 1;
}

.mobile-gift-form .amount-suffix {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.mobile-gift-form .submit-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.mobile-gift-form .send-btn {
  height: 32px !important;
  padding: 0 16px !important;
}

.mobile-gift-form .submit-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mobile-gift-form .calculated-amount {
  font-size: 13px;
  font-weight: 600;
  color: #059669;
}

.mobile-gift-form .my-equity {
  font-size: 11px;
  color: #94a3b8;
}

/* ===== 移动端适配 ===== */
@media (max-width: 767px) {
  .desktop-only {
    display: none !important;
  }
  .mobile-only {
    display: block !important;
  }
  .mobile-gift-form {
    display: block !important;
  }
  
  .page-container {
    padding: 12px;
  }
  
  /* 卡片内边距 */
  :deep(.n-card-header) {
    padding: 10px 12px !important;
  }
  
  :deep(.n-card__content) {
    padding: 12px !important;
  }
  
  /* 移动端表单输入框样式 */
  .mobile-gift-form :deep(.n-select),
  .mobile-gift-form :deep(.n-input),
  .mobile-gift-form :deep(.n-input-number) {
    height: 32px !important;
  }
  
  .mobile-gift-form :deep(.n-base-selection) {
    height: 32px !important;
    min-height: 32px !important;
  }
  
  .mobile-gift-form :deep(.n-base-selection-label) {
    height: 32px !important;
    line-height: 32px !important;
  }
  
  .mobile-gift-form :deep(.n-input__input-el) {
    height: 30px !important;
  }

  /* 旧的表单样式（隐藏） */
  :deep(.n-form .n-grid) {
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
  }
  
  :deep(.n-form .n-gi) {
    width: 100% !important;
  }
  
  :deep(.n-form-item) {
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
  }
  
  :deep(.n-form-item-label) {
    display: block !important;
    text-align: left !important;
    padding-bottom: 8px;
    width: auto !important;
  }
  
  :deep(.n-form-item-blank) {
    min-height: auto;
  }
  
  /* 输入框宽度 */
  :deep(.n-input),
  :deep(.n-select),
  :deep(.n-input-number),
  :deep(.n-input[type="textarea"]) {
    width: 100% !important;
    font-size: 16px; /* 防止 iOS 自动放大 */
  }
  
  /* 修复 n-input-number 布局 */
  :deep(.n-input-number) {
    flex-direction: row !important;
    display: flex !important;
  }
  
  :deep(.n-input-number .n-input) {
    flex: 1 !important;
  }
  
  :deep(.n-input-number .n-input-wrapper) {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
  }
  
  :deep(.n-input-number .n-input__input-el) {
    text-align: left !important;
  }
  
  :deep(.n-input-number .n-input__suffix) {
    margin-left: auto !important;
    white-space: nowrap !important;
  }
  
  :deep(.n-input-number-button-group) {
    display: flex !important;
    flex-direction: row !important;
    flex-shrink: 0 !important;
  }
  
  /* 统计卡片2x2布局 */
  :deep(.n-grid[style*="margin-bottom: 24px"]) {
    display: grid !important;
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 12px !important;
  }
  
  :deep(.n-grid[style*="margin-bottom: 24px"] .n-gi) {
    width: 100% !important;
  }
  
  .stat-card {
    padding: 12px;
  }
  
  .stat-card :deep(.n-statistic .n-statistic-value) {
    font-size: 20px !important;
  }
  
  .stat-card :deep(.n-statistic .n-statistic__label) {
    font-size: 12px !important;
  }
  
  /* 赠与记录卡片优化 */
  .gift-item {
    padding: 12px;
  }
  
  .gift-header {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .gift-info {
    min-width: 0;
    flex: 1;
  }
  
  .gift-title {
    font-size: 14px;
    flex-wrap: wrap;
    gap: 6px;
  }
  
  .gift-time {
    font-size: 11px;
  }
  
  .gift-message {
    margin-top: 10px;
  }
  
  .gift-message :deep(.n-card) {
    padding: 10px !important;
    font-size: 13px;
  }
  
  .gift-actions {
    margin-top: 10px;
    padding-top: 10px;
  }
  
  .gift-actions :deep(.n-button) {
    flex: 1;
    height: 36px;
  }
  
  .gift-actions :deep(.n-space) {
    width: 100%;
    display: flex !important;
  }
  
  /* 标签页优化 */
  :deep(.n-tabs-tab) {
    padding: 8px 12px !important;
    font-size: 14px !important;
  }
  
  :deep(.n-badge) {
    transform: scale(0.85);
  }
  
  /* 提交按钮 */
  :deep(.n-form-item:last-child .n-space) {
    flex-direction: column;
    width: 100%;
    gap: 12px;
  }
  
  :deep(.n-form-item:last-child .n-button) {
    width: 100%;
    height: 48px;
    font-size: 15px;
  }
  
  :deep(.n-form-item:last-child .n-text) {
    text-align: center;
  }
  
  /* 卡片间距 */
  :deep(.n-card) {
    margin-bottom: 16px !important;
  }
  
  /* 空状态 */
  .empty-state {
    padding: 30px 0;
  }
  
  /* 成功动画适配 */
  .gift-animation {
    font-size: 60px;
  }
  
  .gift-success-text {
    font-size: 20px;
  }
  
  .gift-confetti {
    font-size: 24px;
  }
}
</style>
