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
      
      <n-form :model="formData" label-placement="left" label-width="100px">
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
                  <n-avatar :size="40" round>
                    {{ gift.from_user_nickname.charAt(0) }}
                  </n-avatar>
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
                  <n-avatar :size="40" round>
                    {{ gift.to_user_nickname.charAt(0) }}
                  </n-avatar>
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
import dayjs from 'dayjs'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const showSuccessAnimation = ref(false)

// 数据
const sentGifts = ref<any[]>([])
const receivedGifts = ref<any[]>([])
const pendingCount = ref(0)
const familyMembers = ref<any[]>([])
const myEquity = ref(0)

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

// 方法
function formatTime(dateStr: string): string {
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
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
    
    // 计算我的股权比例
    const myMember = equityRes.data.members?.find((m: any) => m.user_id === userStore.user?.id)
    myEquity.value = myMember?.equity_ratio || 0
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
</style>
