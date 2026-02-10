<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💰</span> 资金注入</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <template #header>
        <n-space align="center">
          <span>发起资金注入申请</span>
          <n-tag type="info" size="small">需全员通过</n-tag>
        </n-space>
      </template>
      <n-form :model="formData" @submit.prevent="handleSubmit" class="deposit-form">
        <!-- 第一行：金额 + 日期 -->
        <div class="form-row">
          <n-form-item label="存入金额" class="form-item-half">
            <n-input-number v-model:value="formData.amount" :min="1" placeholder="金额">
              <template #prefix>¥</template>
            </n-input-number>
          </n-form-item>
          <n-form-item label="存入日期" class="form-item-half">
            <n-date-picker v-model:value="formData.deposit_date" type="datetime" style="width: 100%" />
          </n-form-item>
        </div>
        <!-- 第二行：备注 + 按钮 -->
        <div class="form-row">
          <n-form-item label="备注" class="form-item-flex">
            <n-input v-model:value="formData.note" placeholder="可选" />
          </n-form-item>
          <n-form-item class="form-item-btn">
            <n-button type="primary" :loading="submitting" @click="handleSubmit">
              <template #icon><n-icon><SendOutline /></n-icon></template>
              发起申请
            </n-button>
          </n-form-item>
        </div>
      </n-form>
    </n-card>
    
    <!-- 待审批的资金注入申请 -->
    <n-card title="待审批申请" class="card-hover" style="margin-bottom: 24px" v-if="pendingApprovals.length > 0">
      <!-- 桌面端：表格 -->
      <n-data-table class="desktop-only" :columns="approvalColumns" :data="pendingApprovals" :bordered="false" />
      <!-- 移动端：卡片 -->
      <div class="mobile-only">
        <div class="record-cards">
          <div v-for="item in pendingApprovals" :key="item.id" class="record-card pending-card">
            <div class="record-card-header">
              <span class="record-user">{{ item.requester_nickname }}</span>
              <n-tag type="warning" size="small">{{ item.approved_count || 0 }}/{{ Math.max((item.total_members || 1) - 1, 1) }} 已审批</n-tag>
            </div>
            <div class="record-card-body">
              <div class="record-amount">¥{{ parseRequestData(item).amount?.toLocaleString() }}</div>
              <div class="record-note">{{ parseRequestData(item).note || '无备注' }}</div>
            </div>
            <div class="record-card-footer">
              <span class="record-time">{{ formatShortDateTime(item.created_at) }}</span>
              <div class="record-actions">
                <template v-if="item.requester_id !== userStore.user?.id && !item.has_voted">
                  <n-button size="tiny" type="success" @click="handleApprove(item.id, true)">同意</n-button>
                  <n-button size="tiny" type="error" @click="handleApprove(item.id, false)">拒绝</n-button>
                </template>
                <span v-else class="record-status">{{ item.has_voted ? '已投票' : '等待他人' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </n-card>
    
    <!-- 时间范围选择器 -->
    <TimeRangeSelector v-model="timeRange" @change="loadData" />
    
    <n-card title="存款记录" class="card-hover">
      <!-- 桌面端：表格 -->
      <n-data-table class="desktop-only" :columns="columns" :data="deposits" :loading="loading" :bordered="false" />
      <!-- 移动端：卡片 -->
      <div class="mobile-only">
        <n-spin :show="loading">
          <div class="record-cards" v-if="deposits.length > 0">
            <div v-for="item in deposits" :key="item.id" class="record-card deposit-card">
              <div class="record-card-header">
                <span class="record-user">{{ item.user_nickname }}</span>
                <n-tag type="success" size="small">已入账</n-tag>
              </div>
              <div class="record-card-body">
                <div class="record-amount">¥{{ item.amount?.toLocaleString() }}</div>
                <div class="record-note">{{ item.note || '无备注' }}</div>
              </div>
              <div class="record-card-footer">
                <span class="record-time">{{ formatShortDateTime(item.deposit_date) }}</span>
              </div>
            </div>
          </div>
          <n-empty v-else description="暂无存款记录" />
        </n-spin>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, useDialog, NButton, NTag, NSpace, NInput } from 'naive-ui'
import { depositApi, approvalApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useApprovalStore } from '@/stores/approval'
import { SendOutline } from '@vicons/ionicons5'
import { formatShortDateTime } from '@/utils/date'
import { checkAndShowAchievements } from '@/utils/achievement'
import TimeRangeSelector from '@/components/TimeRangeSelector.vue'

const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()
const approvalStore = useApprovalStore()
const loading = ref(false)
const submitting = ref(false)
const deposits = ref<any[]>([])
const pendingApprovals = ref<any[]>([])
const timeRange = ref('month')
const formData = ref({ amount: null as number | null, deposit_date: Date.now(), note: '' })

const columns = [
  { title: '存入人', key: 'user_nickname' },
  { title: '金额', key: 'amount', render: (row: any) => `¥${row.amount.toLocaleString()}` },
  { title: '存入日期', key: 'deposit_date', render: (row: any) => formatShortDateTime(row.deposit_date) },
  { title: '备注', key: 'note', render: (row: any) => row.note || '-' }
]

const approvalColumns = [
  { title: '申请人', key: 'requester_nickname' },
  { 
    title: '金额', 
    key: 'amount', 
    render: (row: any) => {
      const data = JSON.parse(row.request_data)
      return `¥${data.amount?.toLocaleString() || '-'}`
    }
  },
  { 
    title: '备注', 
    key: 'note', 
    render: (row: any) => {
      const data = JSON.parse(row.request_data)
      return data.note || '-'
    }
  },
  { title: '申请时间', key: 'created_at', render: (row: any) => formatShortDateTime(row.created_at) },
  { 
    title: '审批进度', 
    key: 'progress',
    render: (row: any) => `${row.approved_count || 0}/${Math.max((row.total_members || 1) - 1, 1)}`
  },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => {
      const canApprove = row.requester_id !== userStore.user?.id && !row.has_voted
      if (!canApprove) return h('span', { style: 'color: var(--theme-text-tertiary)' }, row.has_voted ? '已投票' : '等待他人')
      return h(NSpace, { size: 'small' }, { default: () => [
        h(NButton, { size: 'small', type: 'success', onClick: () => handleApprove(row.id, true) }, { default: () => '同意' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleApprove(row.id, false) }, { default: () => '拒绝' })
      ]})
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const [depositsRes, approvalsRes] = await Promise.all([
      depositApi.list({ time_range: timeRange.value }),
      approvalApi.list({ status: 'pending', request_type: 'deposit' })
    ])
    deposits.value = depositsRes.data
    pendingApprovals.value = approvalsRes.data
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formData.value.amount) { message.warning('请输入金额'); return }
  submitting.value = true
  try {
    await approvalApi.createDeposit({
      amount: formData.value.amount,
      deposit_date: new Date(formData.value.deposit_date).toISOString(),
      note: formData.value.note
    })
    message.success('申请已提交，等待审批！💰')
    formData.value = { amount: null, deposit_date: Date.now(), note: '' }
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function doApprove(id: number, approved: boolean, reason?: string) {
  try {
    if (approved) {
      await approvalApi.approve(id)
    } else {
      await approvalApi.reject(id, reason || '未说明原因')
    }
    message.success(approved ? '已同意' : '已拒绝')
    loadData()
    
    // 立即刷新审批红点
    await approvalStore.refreshNow()
    
    // 审批后检查成就
    if (approved) {
      setTimeout(() => checkAndShowAchievements(), 500)
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

function handleApprove(id: number, approved: boolean) {
  if (approved) {
    doApprove(id, true)
  } else {
    dialog.create({
      title: '拒绝原因',
      content: () => h(NInput, {
        id: 'reject-reason-input',
        placeholder: '请输入拒绝原因（可选）',
        style: { width: '100%' }
      }),
      positiveText: '确认拒绝',
      negativeText: '取消',
      onPositiveClick: () => {
        const reason = (document.getElementById('reject-reason-input') as HTMLInputElement)?.value || ''
        doApprove(id, false, reason)
      }
    })
  }
}

// 解析审批请求数据
function parseRequestData(item: any) {
  try {
    return JSON.parse(item.request_data)
  } catch {
    return {}
  }
}

onMounted(loadData)
</script>

<style scoped>
/* 桌面/移动端显示控制 */
.desktop-only {
  display: block;
}
.mobile-only {
  display: none;
}

/* 表单布局 */
.deposit-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.form-item-half {
  flex: 1;
  min-width: 0;
}

.form-item-flex {
  flex: 1;
  min-width: 0;
}

.form-item-btn {
  flex-shrink: 0;
}

/* 表单项样式调整 */
:deep(.n-form-item) {
  margin-bottom: 0;
}

:deep(.n-form-item-label) {
  font-size: 13px;
  color: var(--theme-text-secondary);
  padding-bottom: 4px;
}

/* 输入框100%宽度 */
.form-item-half :deep(.n-input-number),
.form-item-half :deep(.n-date-picker),
.form-item-flex :deep(.n-input) {
  width: 100% !important;
}

/* 按钮样式 */
.form-item-btn :deep(.n-button) {
  height: 34px;
  font-size: 14px;
}

/* 移动端响应式 */
@media (max-width: 767px) {
  .page-container {
    padding: 12px;
  }
  
  /* 卡片更紧凑 */
  :deep(.n-card) {
    margin-bottom: 12px !important;
  }
  
  :deep(.n-card-header) {
    padding: 12px 14px !important;
  }
  
  :deep(.n-card__content) {
    padding: 12px 14px !important;
  }
  
  /* 表单行布局 */
  .form-row {
    gap: 10px;
  }
  
  /* 第一行：金额和日期各占一半 */
  .form-item-half {
    flex: 1;
    min-width: 0;
  }
  
  /* 第二行：备注占剩余空间，按钮固定宽度 */
  .form-item-flex {
    flex: 1;
    min-width: 0;
  }
  
  .form-item-btn {
    flex-shrink: 0;
  }
  
  .form-item-btn :deep(.n-button) {
    height: 34px;
    padding: 0 16px;
  }
  
  /* ===== 修复 n-input-number 按钮布局 ===== */
  :deep(.n-input-number) {
    display: flex !important;
    flex-direction: row !important;
    width: 100% !important;
  }
  
  /* 让输入区域占满剩余空间 */
  :deep(.n-input-number .n-input) {
    flex: 1 !important;
    min-width: 0 !important;
  }
  
  /* 确保输入框内部布局正确 */
  :deep(.n-input-number .n-input-wrapper) {
    display: flex !important;
    flex-direction: row !important;
    width: 100% !important;
  }
  
  /* 按钮组紧贴输入框 */
  :deep(.n-input-number .n-input-number-button-group) {
    flex-shrink: 0 !important;
    display: flex !important;
  }
  
  /* 防止 iOS 输入框自动放大 */
  :deep(.n-input__input-el),
  :deep(.n-date-picker input) {
    font-size: 16px !important;
  }
  
  /* 日期选择器全宽 */
  :deep(.n-date-picker) {
    width: 100% !important;
  }
  
  /* 表格在移动端简化 */
  :deep(.n-data-table) {
    font-size: 13px;
  }
  
  :deep(.n-data-table-th),
  :deep(.n-data-table-td) {
    padding: 10px 8px !important;
  }
}

/* 更小屏幕：第一行改为垂直堆叠 */
@media (max-width: 400px) {
  .form-row:first-child {
    flex-direction: column;
    gap: 12px;
  }
  
  .form-item-half {
    width: 100%;
  }
}

/* ===== 移动端卡片列表样式 ===== */
@media (max-width: 767px) {
  .desktop-only {
    display: none !important;
  }
  .mobile-only {
    display: block !important;
  }
}

.record-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.record-card {
  background: var(--theme-bg-card);
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
  border: 1px solid var(--theme-border-light);
}

.record-card.pending-card {
  background: var(--theme-warning-bg);
  border-color: var(--theme-warning-light);
}

.record-card.deposit-card {
  background: var(--theme-success-bg);
  border-color: var(--theme-success-light);
}

.record-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.record-user {
  font-weight: 600;
  font-size: 14px;
  color: var(--theme-text-primary);
}

.record-card-body {
  margin-bottom: 8px;
}

.record-amount {
  font-size: 20px;
  font-weight: 700;
  color: var(--theme-success);
  margin-bottom: 2px;
}

.record-note {
  font-size: 12px;
  color: var(--theme-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--theme-border-light);
}

.record-time {
  font-size: 11px;
  color: var(--theme-text-tertiary);
}

.record-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.record-status {
  font-size: 12px;
  color: var(--theme-text-tertiary);
}
</style>
