<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💸</span> 支出申请</h1>
    
    <n-card class="card-hover expense-form-card" style="margin-bottom: 24px">
      <n-form :model="formData" label-placement="left" label-width="100px" class="expense-form">
        <!-- 桌面端布局 -->
        <div class="desktop-only">
          <n-grid :cols="2" :x-gap="16">
            <n-gi>
              <n-form-item label="支出标题">
                <n-input v-model:value="formData.title" placeholder="如：购买家电" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="支出金额">
                <n-input-number v-model:value="formData.amount" :min="1" style="width: 100%">
                  <template #prefix>¥</template>
                </n-input-number>
              </n-form-item>
            </n-gi>
          </n-grid>
          <n-form-item label="支出原因">
            <n-input v-model:value="formData.reason" type="textarea" placeholder="请详细说明支出原因" :rows="2" />
          </n-form-item>
          <n-form-item label="股权扣减分配">
            <div style="width: 100%">
              <n-alert type="info" style="margin-bottom: 12px">
                拖动滑块调整各成员承担比例，系统会自动保持总和为100%
              </n-alert>
              <n-space vertical>
                <div v-for="(ratio, index) in formData.deduction_ratios" :key="ratio.user_id" style="display: flex; align-items: center; gap: 12px">
                  <span style="min-width: 80px">{{ getMemberNickname(ratio.user_id) }}</span>
                  <n-slider 
                    :value="ratio.ratio" 
                    @update:value="(val) => handleRatioChange(index, val)"
                    :min="0" 
                    :max="100" 
                    :step="1" 
                    :disabled="isSingleMember"
                    style="flex: 1" 
                  />
                  <n-input-number 
                    :value="ratio.ratio"
                    @update:value="(val) => handleRatioChange(index, val || 0)"
                    :min="0"
                    :max="100"
                    :disabled="isSingleMember"
                    size="small"
                    style="width: 80px"
                  >
                    <template #suffix>%</template>
                  </n-input-number>
                </div>
              </n-space>
              <n-text type="success" style="display: block; margin-top: 8px">
                当前总比例：{{ totalRatio }}% ✓
              </n-text>
            </div>
          </n-form-item>
          <n-form-item>
            <n-button type="primary" :loading="submitting" :disabled="totalRatio !== 100" @click="handleSubmit">提交申请</n-button>
          </n-form-item>
        </div>
        
        <!-- 移动端紧凑布局 -->
        <div class="mobile-only mobile-expense-form">
          <!-- 第一行：标题 + 金额 -->
          <div class="form-row">
            <div class="form-col title-col">
              <label>标题</label>
              <n-input v-model:value="formData.title" placeholder="购买家电" size="small" />
            </div>
            <div class="form-col amount-col">
              <label>金额</label>
              <n-input-number v-model:value="formData.amount" :min="1" size="small" placeholder="0">
                <template #prefix>¥</template>
              </n-input-number>
            </div>
          </div>
          
          <!-- 第二行：原因 -->
          <div class="form-row">
            <div class="form-col full">
              <label>原因</label>
              <n-input v-model:value="formData.reason" placeholder="简要说明" size="small" />
            </div>
          </div>
          
          <!-- 第三行：股权分配（紧凑） -->
          <div class="ratio-section">
            <label class="ratio-label">扣减分配 <span class="ratio-hint">(总{{ totalRatio }}%)</span></label>
            <div class="ratio-list">
              <div v-for="(ratio, index) in formData.deduction_ratios" :key="ratio.user_id" class="ratio-item">
                <span class="ratio-name">{{ getMemberNickname(ratio.user_id) }}</span>
                <n-slider 
                  :value="ratio.ratio" 
                  @update:value="(val) => handleRatioChange(index, val)"
                  :min="0" :max="100" :step="1" 
                  :disabled="isSingleMember"
                  class="ratio-slider"
                />
                <span class="ratio-value">{{ ratio.ratio }}%</span>
              </div>
            </div>
          </div>
          
          <!-- 提交按钮 -->
          <n-button type="primary" block :loading="submitting" :disabled="totalRatio !== 100" @click="handleSubmit" size="small" class="submit-btn">
            提交申请
          </n-button>
        </div>
      </n-form>
    </n-card>

    <!-- 时间范围选择器 -->
    <TimeRangeSelector v-model="timeRange" />

    <n-card title="申请记录" class="card-hover">
      <!-- 桌面端：表格 -->
      <n-data-table class="desktop-only" :columns="columns" :data="expenses" :loading="loading" :bordered="false" />
      <!-- 移动端：卡片列表 -->
      <div class="mobile-only">
        <n-spin :show="loading">
          <div class="expense-cards" v-if="expenses.length > 0">
            <div v-for="item in expenses" :key="item.id" class="expense-card" :class="'status-' + item.status">
              <div class="expense-card-header">
                <span class="expense-title">{{ item.title }}</span>
                <n-tag :type="statusMap[item.status]?.type || 'default'" size="small">
                  {{ statusMap[item.status]?.label || item.status }}
                </n-tag>
              </div>
              <div class="expense-card-body">
                <div class="expense-amount">¥{{ item.amount?.toLocaleString() }}</div>
                <div class="expense-reason">{{ item.description || '无描述' }}</div>
              </div>
              <div class="expense-card-footer">
                <div class="expense-meta">
                  <span class="expense-requester">{{ item.requester_nickname }}</span>
                  <span class="expense-time">{{ formatShortDateTime(item.created_at) }}</span>
                </div>
                <div class="expense-actions" v-if="item.status === 'pending'">
                  <template v-if="item.requester_id === userStore.user?.id">
                    <n-button size="tiny" type="warning" @click="handleCancel(item.id)">取消</n-button>
                  </template>
                  <template v-else-if="item.pending_approvers?.includes(userStore.user?.id)">
                    <n-button size="tiny" type="success" @click="handleApprove(item.id, true)">同意</n-button>
                    <n-button size="tiny" type="error" @click="handleApprove(item.id, false)">拒绝</n-button>
                  </template>
                  <span v-else class="expense-wait">已审批</span>
                </div>
              </div>
            </div>
          </div>
          <n-empty v-else description="暂无申请记录" />
        </n-spin>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h, watch } from 'vue'
import { useMessage, NButton, NTag, NSpace, NTooltip, NProgress } from 'naive-ui'
import { approvalApi, familyApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { formatShortDateTime } from '@/utils/date'
import TimeRangeSelector from '@/components/TimeRangeSelector.vue'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const expenses = ref<any[]>([])
const familyMembers = ref<any[]>([])
const timeRange = ref('month')

const formData = ref({
  title: '',
  amount: null as number | null,
  reason: '',
  deduction_ratios: [] as Array<{ user_id: number; ratio: number }>
})

const totalRatio = computed(() => {
  return formData.value.deduction_ratios.reduce((sum, r) => sum + r.ratio, 0)
})

// 判断是否只有单个成员
const isSingleMember = computed(() => {
  return formData.value.deduction_ratios.length <= 1
})

// 处理比例变化 - 联动调整其他成员的比例
function handleRatioChange(changedIndex: number, newValue: number) {
  // 限制范围 0-100
  newValue = Math.max(0, Math.min(100, newValue))
  
  const ratios = formData.value.deduction_ratios
  const memberCount = ratios.length
  
  // 单成员时固定100%
  if (memberCount <= 1) {
    ratios[0].ratio = 100
    return
  }
  
  // 计算当前成员之外的其他成员总比例
  const otherIndices = ratios.map((_, i) => i).filter(i => i !== changedIndex)
  const oldOtherTotal = otherIndices.reduce((sum, i) => sum + ratios[i].ratio, 0)
  
  // 计算剩余需要分配给其他成员的比例
  const remainingForOthers = 100 - newValue
  
  // 设置当前成员的新值
  ratios[changedIndex].ratio = newValue
  
  if (remainingForOthers <= 0) {
    // 如果当前成员占了100%或更多，其他成员都设为0
    otherIndices.forEach(i => {
      ratios[i].ratio = 0
    })
  } else if (oldOtherTotal === 0) {
    // 如果其他成员原来总和为0，平均分配剩余比例
    const avgRatio = Math.floor(remainingForOthers / otherIndices.length)
    const remainder = remainingForOthers - avgRatio * otherIndices.length
    otherIndices.forEach((idx, i) => {
      ratios[idx].ratio = avgRatio + (i === 0 ? remainder : 0)
    })
  } else {
    // 按比例调整其他成员
    let distributed = 0
    otherIndices.forEach((idx, i) => {
      if (i === otherIndices.length - 1) {
        // 最后一个成员获得剩余的所有比例（避免四舍五入误差）
        ratios[idx].ratio = remainingForOthers - distributed
      } else {
        const proportion = ratios[idx].ratio / oldOtherTotal
        const newRatio = Math.round(remainingForOthers * proportion)
        ratios[idx].ratio = Math.max(0, Math.min(100, newRatio))
        distributed += ratios[idx].ratio
      }
    })
  }
  
  // 确保每个比例都在有效范围内
  ratios.forEach(r => {
    r.ratio = Math.max(0, Math.min(100, r.ratio))
  })
}

function getMemberNickname(userId: number): string {
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || `用户${userId}`
}

const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'default', label: string }> = {
  pending: { type: 'warning', label: '审批中' },
  approved: { type: 'success', label: '已通过' },
  rejected: { type: 'error', label: '已拒绝' },
  cancelled: { type: 'default', label: '已取消' }
}

const columns = [
  { title: '申请人', key: 'requester_nickname' },
  { title: '标题', key: 'title' },
  { title: '金额', key: 'amount', render: (row: any) => `¥${row.amount.toLocaleString()}` },
  { title: '原因', key: 'description', ellipsis: { tooltip: true } },
  { 
    title: '审批进度', 
    key: 'progress',
    width: 150,
    render: (row: any) => {
      const total = row.total_members
      const approved = row.approved_count
      const rejected = row.rejected_count
      const pending = total - approved - rejected
      
      if (row.status !== 'pending') {
        return h(NTag, { 
          type: statusMap[row.status]?.type || 'default', 
          size: 'small' 
        }, { default: () => statusMap[row.status]?.label || row.status })
      }
      
      return h('div', { style: 'display: flex; align-items: center; gap: 8px' }, [
        h(NProgress, {
          type: 'line',
          percentage: Math.round((approved / total) * 100),
          status: 'success',
          showIndicator: false,
          style: 'flex: 1'
        }),
        h('span', { style: 'font-size: 12px; color: #666' }, `${approved}/${total}`)
      ])
    }
  },
  { title: '申请时间', key: 'created_at', render: (row: any) => formatShortDateTime(row.created_at) },
  { 
    title: '操作', 
    key: 'actions',
    width: 180,
    render: (row: any) => {
      // 不是待审批状态，显示状态标签
      if (row.status !== 'pending') {
        return '-'
      }
      
      const isRequester = row.requester_id === userStore.user?.id
      const hasApproved = !row.pending_approvers.includes(userStore.user?.id)
      
      // 申请人可以取消
      if (isRequester) {
        return h(NSpace, {}, { default: () => [
          h(NButton, { 
            size: 'small', 
            type: 'warning',
            onClick: () => handleCancel(row.id)
          }, { default: () => '取消申请' })
        ]})
      }
      
      // 已经审批过
      if (hasApproved) {
        return h('span', { style: 'color:#94a3b8' }, '已审批')
      }
      
      // 待审批
      return h(NSpace, {}, { default: () => [
        h(NButton, { size: 'small', type: 'success', onClick: () => handleApprove(row.id, true) }, { default: () => '同意' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleApprove(row.id, false) }, { default: () => '拒绝' })
      ]})
    }
  }
]

async function loadFamilyMembers() {
  try {
    const res = await familyApi.getMy()
    familyMembers.value = res.data.members || []
    // 初始化扣减比例 - 平均分配
    if (familyMembers.value.length > 0) {
      const avgRatio = Math.floor(100 / familyMembers.value.length)
      const remainder = 100 - avgRatio * familyMembers.value.length
      formData.value.deduction_ratios = familyMembers.value.map((m, index) => ({
        user_id: m.user_id,
        ratio: avgRatio + (index === 0 ? remainder : 0) // 余数给第一个人
      }))
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadData() {
  loading.value = true
  try {
    // 从审批中心获取支出类型的申请
    const res = await approvalApi.list({ request_type: 'expense', time_range: timeRange.value })
    expenses.value = res.data.items || []
  } finally {
    loading.value = false
  }
}

// 时间范围变化时重新加载数据
watch(timeRange, () => {
  loadData()
})

async function handleSubmit() {
  if (!formData.value.title || !formData.value.amount || !formData.value.reason) { 
    message.warning('请填写完整信息')
    return 
  }
  if (totalRatio.value !== 100) {
    message.warning('股权扣减比例总和必须为100%')
    return
  }
  submitting.value = true
  try {
    await approvalApi.createExpense({
      title: formData.value.title,
      amount: formData.value.amount,
      reason: formData.value.reason,
      deduction_ratios: formData.value.deduction_ratios.map(r => ({
        user_id: r.user_id,
        ratio: r.ratio / 100 // 转换为0-1的小数
      }))
    })
    message.success('申请已提交，等待审批！')
    formData.value.title = ''
    formData.value.amount = null
    formData.value.reason = ''
    await loadFamilyMembers() // 重新初始化比例
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleApprove(id: number, approved: boolean) {
  try {
    if (approved) {
      await approvalApi.approve(id)
      message.success('已同意')
    } else {
      await approvalApi.reject(id)
      message.success('已拒绝')
    }
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleCancel(id: number) {
  try {
    await approvalApi.cancel(id)
    message.success('已取消申请')
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(async () => {
  await loadFamilyMembers()
  loadData()
})
</script>

<style scoped>
/* 桌面/移动端显示控制 */
.desktop-only {
  display: block;
}
.mobile-only {
  display: none;
}

/* 移动端响应式 */
@media (max-width: 767px) {
  .desktop-only {
    display: none !important;
  }
  .mobile-only {
    display: block !important;
  }

  .page-container {
    padding: 12px;
  }
  
  :deep(.n-card-header) {
    padding: 12px 14px !important;
  }
  
  :deep(.n-card__content) {
    padding: 12px 14px !important;
  }
  
  /* 表单垂直布局 */
  :deep(.n-grid) {
    display: flex !important;
    flex-direction: column;
    gap: 0;
  }
  
  :deep(.n-gi) {
    width: 100%;
  }
  
  :deep(.n-form-item) {
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
  }
  
  :deep(.n-form-item-label) {
    display: block;
    text-align: left;
    padding-bottom: 8px;
    width: auto !important;
  }
  
  :deep(.n-form-item-blank) {
    min-height: auto;
  }
  
  :deep(.n-input),
  :deep(.n-input-number),
  :deep(.n-input[type="textarea"]) {
    width: 100% !important;
    font-size: 16px; /* 防止 iOS 放大 */
  }
  
  /* 修复 n-input-number 在移动端的布局 */
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
  
  /* 股权扣减分配区域优化 */
  :deep(.n-space--vertical) > div[style*="display: flex"] {
    flex-wrap: wrap !important;
    gap: 8px !important;
  }
  
  /* 滑块行优化 */
  :deep(.n-space--vertical) > div > span[style*="min-width"] {
    min-width: 60px !important;
    font-size: 14px;
  }
  
  :deep(.n-space--vertical) > div > .n-slider {
    flex: 1 !important;
    min-width: 100px !important;
  }
  
  :deep(.n-space--vertical > div > .n-input-number) {
    width: 90px !important;
    flex-shrink: 0 !important;
  }
  
  /* 滑块控件优化 */
  :deep(.n-slider) {
    padding: 10px 0;
  }
  
  :deep(.n-slider-handle) {
    width: 24px !important;
    height: 24px !important;
  }
  
  /* 提交按钮 */
  :deep(.n-button) {
    width: 100%;
    height: 48px;
    font-size: 15px;
  }
  
  /* 表格优化 */
  :deep(.n-data-table) {
    font-size: 13px;
  }
  
  :deep(.n-data-table-th),
  :deep(.n-data-table-td) {
    padding: 10px 8px !important;
  }
  
  /* 卡片间距 */
  :deep(.n-card) {
    margin-bottom: 16px !important;
  }

  /* ===== 支出申请卡片样式 ===== */
  .expense-cards {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .expense-card {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border-radius: 12px;
    padding: 14px;
    border: 1px solid #e2e8f0;
  }

  .expense-card.status-pending {
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    border-color: #fde68a;
  }

  .expense-card.status-approved {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border-color: #86efac;
  }

  .expense-card.status-rejected {
    background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%);
    border-color: #fca5a5;
  }

  .expense-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .expense-title {
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
  }

  .expense-card-body {
    margin-bottom: 12px;
  }

  .expense-amount {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 4px;
  }

  .expense-reason {
    font-size: 13px;
    color: #64748b;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .expense-card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 10px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }

  .expense-meta {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .expense-requester {
    font-size: 13px;
    color: #475569;
  }

  .expense-time {
    font-size: 11px;
    color: #94a3b8;
  }

  .expense-actions {
    display: flex;
    gap: 8px;
  }

  .expense-actions :deep(.n-button) {
    width: auto !important;
    height: 28px !important;
    padding: 0 10px;
  }

  .expense-wait {
    font-size: 12px;
    color: #94a3b8;
  }

  /* ===== 移动端紧凑表单样式 ===== */
  .expense-form-card :deep(.n-card__content) {
    padding: 12px !important;
  }
  
  .mobile-expense-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  
  .mobile-expense-form .form-row {
    display: flex;
    gap: 10px;
  }
  
  .mobile-expense-form .form-col {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .mobile-expense-form .form-col.title-col {
    flex: 1.2;
    min-width: 0;
  }
  
  .mobile-expense-form .form-col.amount-col {
    flex: 0.8;
    min-width: 0;
  }
  
  .mobile-expense-form .form-col.full {
    flex: 1;
  }
  
  .mobile-expense-form label {
    font-size: 12px;
    color: #6b7280;
    font-weight: 500;
  }
  
  /* 统一输入框高度 */
  .mobile-expense-form :deep(.n-input),
  .mobile-expense-form :deep(.n-input-number) {
    font-size: 14px !important;
    height: 32px !important;
  }
  
  .mobile-expense-form :deep(.n-input-number) {
    width: 100% !important;
  }
  
  .mobile-expense-form :deep(.n-input .n-input__input-el),
  .mobile-expense-form :deep(.n-input-number .n-input__input-el) {
    height: 32px !important;
    line-height: 32px !important;
  }
  
  .mobile-expense-form :deep(.n-input-number-button-group) {
    height: 32px !important;
  }
  
  .mobile-expense-form :deep(.n-input-number-button) {
    height: 16px !important;
  }
  
  /* 股权分配区域紧凑样式 */
  .ratio-section {
    background: #f8fafc;
    border-radius: 8px;
    padding: 10px;
  }
  
  .ratio-label {
    font-size: 12px;
    color: #6b7280;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
  }
  
  .ratio-hint {
    color: #22c55e;
    font-weight: 600;
  }
  
  .ratio-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  
  .ratio-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .ratio-name {
    font-size: 13px;
    color: #374151;
    min-width: 60px;
    flex-shrink: 0;
  }
  
  .ratio-slider {
    flex: 1;
    min-width: 0;
  }
  
  .ratio-slider :deep(.n-slider) {
    padding: 6px 0 !important;
  }
  
  .ratio-slider :deep(.n-slider-handle) {
    width: 18px !important;
    height: 18px !important;
  }
  
  .ratio-value {
    font-size: 13px;
    color: #374151;
    font-weight: 600;
    min-width: 36px;
    text-align: right;
  }
  
  /* 提交按钮 */
  .mobile-expense-form .submit-btn {
    margin-top: 4px;
    height: 38px !important;
    font-size: 14px !important;
  }
}
</style>
