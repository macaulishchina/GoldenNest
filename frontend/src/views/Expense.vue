<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💸</span> 支出申请</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <n-form :model="formData" label-placement="left" label-width="100px">
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
      </n-form>
    </n-card>

    <n-card title="申请记录" class="card-hover">
      <n-data-table :columns="columns" :data="expenses" :loading="loading" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NSpace, NTooltip, NProgress } from 'naive-ui'
import { approvalApi, familyApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { formatShortDateTime } from '@/utils/date'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const expenses = ref<any[]>([])
const familyMembers = ref<any[]>([])

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
    const res = await approvalApi.list({ request_type: 'expense' })
    expenses.value = res.data.items || []
  } finally {
    loading.value = false
  }
}

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