<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💎</span> 资产登记</h1>
    
    <n-alert type="info" style="margin-bottom: 16px" :bordered="false">
      💡 <strong>提示：</strong>家庭自由资金通过「资金注入」页面增加，此处仅登记定期、基金、股票等投资型资产。
    </n-alert>
    
    <!-- 资产登记表单 -->
    <n-card class="card-hover" style="margin-bottom: 24px">
      <template #header>
        <n-space align="center">
          <span>发起资产登记申请</span>
          <n-tag type="info" size="small">需全员通过</n-tag>
        </n-space>
      </template>
      
      <n-form :model="formData" label-placement="left" label-width="100px">
        <!-- 第一行：资产所有者 + 资产类型 -->
        <div class="form-row">
          <n-form-item label="资产所有者" class="form-item-half">
            <n-select 
              v-model:value="formData.user_id" 
              :options="memberOptions" 
              placeholder="选择家庭成员"
            />
          </n-form-item>
          <n-form-item label="资产类型" class="form-item-half">
            <n-select 
              v-model:value="formData.asset_type" 
              :options="assetTypeOptions" 
              placeholder="选择类型"
            />
          </n-form-item>
        </div>
        
        <!-- 第二行：产品名称 + 币种 -->
        <div class="form-row">
          <n-form-item label="产品名称" class="form-item-half">
            <n-input 
              v-model:value="formData.name" 
              placeholder="如：招商银行定期"
            />
          </n-form-item>
          <n-form-item label="币种" class="form-item-half">
            <n-select 
              v-model:value="formData.currency" 
              :options="currencyOptions" 
              placeholder="选择币种"
              @update:value="handleCurrencyChange"
            />
          </n-form-item>
        </div>
        
        <!-- 第三行：金额输入（根据币种动态显示） -->
        <div class="form-row">
          <n-form-item :label="amountLabel" class="form-item-half">
            <n-input-number 
              v-model:value="currentAmount" 
              :min="0.01" 
              :precision="2"
              :placeholder="amountPlaceholder"
              style="width: 100%"
              @update:value="handleAmountChange"
            >
              <template #prefix>{{ currencySymbol }}</template>
            </n-input-number>
          </n-form-item>
          <n-form-item label="预期年化" class="form-item-half">
            <n-input-number 
              v-model:value="formData.expected_rate" 
              :min="0" 
              :max="100"
              :precision="2"
              placeholder="0.00"
              style="width: 100%"
            >
              <template #suffix>%</template>
            </n-input-number>
          </n-form-item>
        </div>
        
        <!-- 汇率信息显示（外币时） -->
        <div v-if="formData.currency !== 'CNY'" class="exchange-rate-info">
          <n-alert type="info" :bordered="false">
            <template #icon>
              <n-icon><CashOutline /></n-icon>
            </template>
            <div v-if="exchangeRateLoading">正在获取实时汇率...</div>
            <div v-else-if="currentExchangeRate">
              <strong>实时汇率：</strong>1 {{ formData.currency }} = ¥{{ currentExchangeRate.toFixed(4) }}
              <span v-if="equivalentCNY" style="margin-left: 12px">
                <strong>等值人民币：</strong>¥{{ equivalentCNY.toLocaleString() }}
              </span>
            </div>
            <div v-else>汇率获取失败，将使用系统默认汇率</div>
          </n-alert>
        </div>
        
        <!-- 第四行：开始日期 + 到期日期 -->
        <div class="form-row">
          <n-form-item label="开始日期" class="form-item-half">
            <n-date-picker 
              v-model:value="formData.start_date" 
              type="date"
              style="width: 100%"
            />
          </n-form-item>
          <n-form-item label="到期日期" class="form-item-half">
            <n-date-picker 
              v-model:value="formData.end_date" 
              type="date"
              style="width: 100%"
              placeholder="可选，开放式产品可不填"
              clearable
            />
          </n-form-item>
        </div>
        
        <!-- 第五行：银行/机构 + 资金来源 -->
        <div class="form-row">
          <n-form-item label="银行/机构" class="form-item-half">
            <n-input 
              v-model:value="formData.bank_name" 
              placeholder="可选，如：招商银行"
            />
          </n-form-item>
          <n-form-item label="资金来源" class="form-item-half">
            <n-radio-group v-model:value="formData.deduct_from_cash">
              <n-radio :value="false">外部注资</n-radio>
              <n-radio :value="true">从自由资金扣除</n-radio>
            </n-radio-group>
          </n-form-item>
        </div>
        
        <!-- 资金来源说明 -->
        <div class="funding-source-tip">
          <n-alert 
            :type="formData.deduct_from_cash ? 'warning' : 'success'" 
            :bordered="false"
            closable
          >
            <template #icon>
              <n-icon><InformationCircleOutline /></n-icon>
            </template>
            <div v-if="formData.deduct_from_cash">
              <strong>从自由资金扣除：</strong>使用家庭现有自由资金购买，不影响股权分配，不改变家庭总资产
            </div>
            <div v-else>
              <strong>外部购买：</strong>从家庭外部账户直接购买，计入{{ selectedMemberName }}的股权，增加家庭总资产
            </div>
          </n-alert>
        </div>
        
        <!-- 第六行：备注 -->
        <n-form-item label="备注">
          <n-input 
            v-model:value="formData.note" 
            type="textarea"
            placeholder="可选，记录额外信息"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
        
        <!-- 提交按钮 -->
        <n-form-item>
          <n-space>
            <n-button 
              type="primary" 
              :loading="submitting" 
              @click="handleSubmit"
              :disabled="!isFormValid"
            >
              <template #icon><n-icon><SendOutline /></n-icon></template>
              发起申请
            </n-button>
            <n-button @click="resetForm">重置</n-button>
          </n-space>
        </n-form-item>
      </n-form>
    </n-card>
    
    <!-- 待审批的资产申请 -->
    <n-card 
      title="待审批申请" 
      class="card-hover" 
      style="margin-bottom: 24px" 
      v-if="pendingApprovals.length > 0"
    >
      <div class="approval-cards">
        <div v-for="item in pendingApprovals" :key="item.id" class="approval-card">
          <div class="approval-card-header">
            <n-tag size="small" type="info">资产登记</n-tag>
            <span class="approval-time">{{ formatDateTime(item.created_at) }}</span>
          </div>
          <div class="approval-card-body">
            <div class="approval-requester">{{ item.requester_nickname }} 发起</div>
            <div class="approval-detail">{{ item.title }}</div>
            <div class="approval-description">{{ item.description }}</div>
          </div>
          <div class="approval-card-footer">
            <span class="approval-progress">
              {{ item.approved_count || 0 }}/{{ item.required_count || 0 }} 已审批
            </span>
            <div class="approval-actions" v-if="item.requester_id !== userStore.user?.id && !item.has_voted">
              <n-button size="small" type="success" @click="handleApprove(item.id, true)">同意</n-button>
              <n-button size="small" type="error" @click="handleApprove(item.id, false)">拒绝</n-button>
            </div>
            <span v-else class="approval-wait">
              {{ item.has_voted ? '已投票' : '等待他人' }}
            </span>
          </div>
        </div>
      </div>
    </n-card>
    
    <!-- 家庭自由资金卡片 -->
    <n-card class="card-hover cash-balance-card" style="margin-bottom: 24px">
      <n-statistic label="家庭自由资金" :value="cashBalance">
        <template #prefix>¥</template>
      </n-statistic>
      <template #footer>
        <n-text depth="3" style="font-size: 12px">
          💰 共享资金池，通过"资金注入"增加，可用于投资或日常支出
        </n-text>
      </template>
    </n-card>
    
    <!-- 资产列表 -->
    <n-card title="我的投资资产" class="card-hover">
      <template #header-extra>
        <n-space>
          <n-select 
            v-model:value="listFilter.asset_type" 
            :options="[{ label: '全部类型', value: '' }, ...assetTypeOptions]"
            style="width: 120px"
            size="small"
            @update:value="loadAssets"
          />
          <n-select 
            v-model:value="listFilter.currency" 
            :options="[{ label: '全部币种', value: '' }, ...currencyOptions]"
            style="width: 100px"
            size="small"
            @update:value="loadAssets"
          />
        </n-space>
      </template>
      
      <n-spin :show="assetsLoading">
        <div v-if="assets.length > 0" class="asset-cards">
          <div v-for="asset in assets" :key="asset.id" class="asset-card">
            <div class="asset-card-header">
              <n-space align="center">
                <span class="asset-name">{{ asset.name }}</span>
                <n-tag 
                  size="small" 
                  :type="asset.is_active ? 'success' : 'default'"
                >
                  {{ asset.is_active ? '持有中' : '已结清' }}
                </n-tag>
                <n-tag size="small" :bordered="false">
                  {{ assetTypeLabels[asset.investment_type] }}
                </n-tag>
              </n-space>
            </div>
            <div class="asset-card-body">
              <div class="asset-amount">
                <span v-if="asset.currency === 'CNY'">
                  ¥{{ asset.principal?.toLocaleString() }}
                </span>
                <span v-else>
                  {{ getCurrencySymbol(asset.currency) }}{{ asset.foreign_amount?.toLocaleString() }}
                  <n-text depth="3" style="font-size: 12px; margin-left: 8px">
                    (≈¥{{ asset.principal?.toLocaleString() }})
                  </n-text>
                </span>
              </div>
              <div class="asset-info">
                <span>年化: {{ asset.expected_rate }}%</span>
                <span v-if="asset.bank_name"> | {{ asset.bank_name }}</span>
                <span v-if="asset.end_date"> | 到期: {{ formatDate(asset.end_date) }}</span>
              </div>
              <div v-if="asset.note" class="asset-note">
                <n-text depth="3">{{ asset.note }}</n-text>
              </div>
            </div>
            <div class="asset-card-footer">
              <n-text depth="3" style="font-size: 12px">
                {{ formatDate(asset.start_date) }} 开始
              </n-text>
              <n-tag 
                size="tiny" 
                :type="asset.deduct_from_cash ? 'warning' : 'success'"
                :bordered="false"
              >
                {{ asset.deduct_from_cash ? '从自由资金扣除' : '外部注资' }}
              </n-tag>
            </div>
          </div>
        </div>
        <n-empty v-else description="暂无资产记录" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { SendOutline, CashOutline, InformationCircleOutline } from '@vicons/ionicons5'
import { approvalApi, assetApi, familyApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useApprovalStore } from '@/stores/approval'

const message = useMessage()
const userStore = useUserStore()
const approvalStore = useApprovalStore()

// 表单数据
const formData = ref({
  user_id: 0,
  name: '',
  asset_type: 'time_deposit' as 'time_deposit' | 'fund' | 'stock' | 'bond' | 'other',
  currency: 'CNY' as 'CNY' | 'USD' | 'HKD' | 'JPY' | 'EUR' | 'GBP' | 'AUD' | 'CAD' | 'SGD' | 'KRW',
  amount: null as number | null,
  foreign_amount: null as number | null,
  expected_rate: 0,
  start_date: Date.now(),
  end_date: null as number | null,
  bank_name: '',
  deduct_from_cash: false,
  note: ''
})

// 家庭成员选项
const memberOptions = ref<Array<{ label: string; value: number }>>([])
const members = ref<Array<{ id: number; nickname: string }>>([])

// 资产类型选项（不包括家庭自由资金，自由资金通过资金注入增加）
const assetTypeOptions = [
  { label: '定期存款', value: 'time_deposit' },
  { label: '基金', value: 'fund' },
  { label: '股票', value: 'stock' },
  { label: '债券', value: 'bond' },
  { label: '其他', value: 'other' }
]

const assetTypeLabels: Record<string, string> = {
  cash: '家庭自由资金',
  time_deposit: '定期存款',
  fund: '基金',
  stock: '股票',
  bond: '债券',
  other: '其他'
}

// 币种选项
const currencyOptions = [
  { label: '人民币 CNY', value: 'CNY' },
  { label: '美元 USD', value: 'USD' },
  { label: '港币 HKD', value: 'HKD' },
  { label: '日元 JPY', value: 'JPY' },
  { label: '欧元 EUR', value: 'EUR' },
  { label: '英镑 GBP', value: 'GBP' },
  { label: '澳元 AUD', value: 'AUD' },
  { label: '加元 CAD', value: 'CAD' },
  { label: '新币 SGD', value: 'SGD' },
  { label: '韩元 KRW', value: 'KRW' }
]

const currencySymbols: Record<string, string> = {
  CNY: '¥',
  USD: '$',
  HKD: 'HK$',
  JPY: '¥',
  EUR: '€',
  GBP: '£',
  AUD: 'A$',
  CAD: 'C$',
  SGD: 'S$',
  KRW: '₩'
}

// 汇率相关
const currentExchangeRate = ref<number | null>(null)
const exchangeRateLoading = ref(false)

// 当前金额（根据币种动态绑定）
const currentAmount = computed({
  get: () => formData.value.currency === 'CNY' ? formData.value.amount : formData.value.foreign_amount,
  set: (val) => {
    if (formData.value.currency === 'CNY') {
      formData.value.amount = val
      formData.value.foreign_amount = null
    } else {
      formData.value.foreign_amount = val
      formData.value.amount = null
    }
  }
})

// 等值人民币
const equivalentCNY = computed(() => {
  if (formData.value.currency === 'CNY') return formData.value.amount
  if (!formData.value.foreign_amount || !currentExchangeRate.value) return null
  return (formData.value.foreign_amount * currentExchangeRate.value).toFixed(2)
})

// 金额标签和占位符
const amountLabel = computed(() => formData.value.currency === 'CNY' ? '金额' : '外币金额')
const amountPlaceholder = computed(() => formData.value.currency === 'CNY' ? '输入人民币金额' : `输入${formData.value.currency}金额`)
const currencySymbol = computed(() => currencySymbols[formData.value.currency] || '')

// 选中成员名称
const selectedMemberName = computed(() => {
  const member = members.value.find(m => m.id === formData.value.user_id)
  return member?.nickname || '该成员'
})

// 表单验证
const isFormValid = computed(() => {
  return formData.value.user_id > 0 && 
         formData.value.name.trim() !== '' &&
         currentAmount.value !== null &&
         currentAmount.value > 0
})

// 提交状态
const submitting = ref(false)

// 待审批申请
const pendingApprovals = ref<any[]>([])

// 家庭自由资金余额
const cashBalance = ref(0)

// 资产列表
const assets = ref<any[]>([])
const assetsLoading = ref(false)
const listFilter = ref({
  asset_type: '',
  currency: ''
})

// 币种切换处理
const handleCurrencyChange = async (currency: string) => {
  if (currency !== 'CNY') {
    await fetchExchangeRate(currency)
  } else {
    currentExchangeRate.value = null
  }
}

// 金额变化处理
const handleAmountChange = () => {
  // 触发等值人民币计算
}

// 获取汇率
const fetchExchangeRate = async (currency: string) => {
  if (currency === 'CNY') return
  
  exchangeRateLoading.value = true
  try {
    const { data } = await assetApi.getExchangeRate(currency)
    currentExchangeRate.value = data.rate
  } catch (error) {
    console.error('Failed to fetch exchange rate:', error)
    message.warning('汇率获取失败，将使用系统默认汇率')
    currentExchangeRate.value = null
  } finally {
    exchangeRateLoading.value = false
  }
}

// 获取币种符号
const getCurrencySymbol = (currency: string) => {
  return currencySymbols[currency] || currency
}

// 加载家庭成员
const loadFamilyMembers = async () => {
  try {
    const { data } = await familyApi.getMy()
    members.value = data.members || []
    memberOptions.value = members.value.map(m => ({
      label: m.nickname,
      value: m.id
    }))
    // 默认选择当前用户
    if (userStore.user?.id) {
      formData.value.user_id = userStore.user.id
    }
  } catch (error) {
    console.error('Failed to load family members:', error)
    message.error('加载家庭成员失败')
  }
}

// 加载待审批申请
const loadPendingApprovals = async () => {
  try {
    const { data } = await approvalApi.list({ 
      request_type: 'asset_create',
      status: 'pending'
    })
    pendingApprovals.value = data.items || []
  } catch (error) {
    console.error('Failed to load pending approvals:', error)
  }
}

// 加载家庭自由资金余额
const loadCashBalance = async () => {
  try {
    const { data } = await assetApi.getCashBalance()
    cashBalance.value = data.balance || 0
  } catch (error) {
    console.error('Failed to load cash balance:', error)
  }
}

// 加载资产列表
const loadAssets = async () => {
  assetsLoading.value = true
  try {
    const params: any = {}
    if (listFilter.value.asset_type) params.asset_type = listFilter.value.asset_type
    if (listFilter.value.currency) params.currency = listFilter.value.currency
    
    const { data } = await assetApi.myAssets()
    assets.value = data.assets || []
  } catch (error) {
    console.error('Failed to load assets:', error)
    message.error('加载资产列表失败')
  } finally {
    assetsLoading.value = false
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!isFormValid.value) {
    message.warning('请填写必填项')
    return
  }
  
  submitting.value = true
  try {
    const submitData: any = {
      user_id: formData.value.user_id,
      name: formData.value.name,
      asset_type: formData.value.asset_type,
      currency: formData.value.currency,
      expected_rate: formData.value.expected_rate,
      start_date: new Date(formData.value.start_date).toISOString(),
      deduct_from_cash: formData.value.deduct_from_cash
    }
    
    if (formData.value.currency === 'CNY') {
      submitData.amount = formData.value.amount
    } else {
      submitData.foreign_amount = formData.value.foreign_amount
    }
    
    if (formData.value.end_date) {
      submitData.end_date = new Date(formData.value.end_date).toISOString()
    }
    
    if (formData.value.bank_name) {
      submitData.bank_name = formData.value.bank_name
    }
    
    if (formData.value.note) {
      submitData.note = formData.value.note
    }
    
    await approvalApi.createAsset(submitData)
    message.success('资产登记申请已提交')
    resetForm()
    loadPendingApprovals()
    loadCashBalance()
  } catch (error: any) {
    console.error('Failed to submit asset:', error)
    message.error(error.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  formData.value = {
    user_id: userStore.user?.id || 0,
    name: '',
    asset_type: 'time_deposit',
    currency: 'CNY',
    amount: null,
    foreign_amount: null,
    expected_rate: 0,
    start_date: Date.now(),
    end_date: null,
    bank_name: '',
    deduct_from_cash: false,
    note: ''
  }
  currentExchangeRate.value = null
}

// 审批操作
const handleApprove = async (id: number, approved: boolean) => {
  try {
    if (approved) {
      await approvalApi.approve(id)
      message.success('已同意申请')
    } else {
      await approvalApi.reject(id)
      message.success('已拒绝申请')
    }
    loadPendingApprovals()
    loadCashBalance()
    loadAssets()
    
    // 立即刷新审批红点
    await approvalStore.refreshNow()
  } catch (error: any) {
    console.error('Failed to approve:', error)
    message.error(error.response?.data?.detail || '操作失败')
  }
}

// 日期格式化
const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 页面加载
onMounted(() => {
  loadFamilyMembers()
  loadPendingApprovals()
  loadCashBalance()
  loadAssets()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  margin-bottom: 24px;
  font-size: 24px;
  font-weight: 600;
}

.icon {
  font-size: 28px;
  margin-right: 8px;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 0;
}

.form-item-half {
  flex: 1;
}

.form-item-flex {
  flex: 1;
}

.exchange-rate-info {
  margin-bottom: 16px;
}

.funding-source-tip {
  margin-bottom: 16px;
}

.cash-balance-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.cash-balance-card :deep(.n-statistic) {
  color: white;
}

.approval-cards,
.asset-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.approval-card,
.asset-card {
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  padding: 16px;
  background: white;
  transition: all 0.3s;
}

.approval-card:hover,
.asset-card:hover {
  box-shadow: 0 4px 12px var(--theme-shadow-sm);
  transform: translateY(-2px);
}

.approval-card-header,
.asset-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.approval-card-body,
.asset-card-body {
  margin-bottom: 12px;
}

.approval-requester {
  font-weight: 500;
  margin-bottom: 4px;
}

.approval-detail {
  font-size: 14px;
  color: var(--theme-text-primary);
  margin-bottom: 4px;
}

.approval-description {
  font-size: 12px;
  color: var(--theme-text-tertiary);
}

.approval-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--theme-border-light);
}

.approval-progress {
  font-size: 12px;
  color: var(--theme-text-secondary);
}

.approval-actions {
  display: flex;
  gap: 8px;
}

.approval-wait {
  font-size: 12px;
  color: var(--theme-text-tertiary);
}

.approval-time {
  font-size: 12px;
  color: var(--theme-text-tertiary);
}

.asset-name {
  font-weight: 500;
  font-size: 16px;
}

.asset-amount {
  font-size: 24px;
  font-weight: 600;
  color: var(--theme-text-primary);
  margin-bottom: 8px;
}

.asset-info {
  font-size: 14px;
  color: var(--theme-text-secondary);
  margin-bottom: 8px;
}

.asset-note {
  font-size: 12px;
  margin-top: 8px;
}

.asset-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--theme-border-light);
}

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }
  
  .approval-cards,
  .asset-cards {
    grid-template-columns: 1fr;
  }
}
</style>
