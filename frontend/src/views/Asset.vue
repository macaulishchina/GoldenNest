<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💎</span> 资产登记</h1>
    
    <n-alert type="info" style="margin-bottom: 16px" :bordered="false">
      💡 <strong>提示：</strong>家庭自由资金通过「资金注入」页面增加，此处仅登记定期、基金、股票等投资型资产。
    </n-alert>
    
    <!-- 发起资产登记按钮 -->
    <div style="margin-bottom: 16px; display: flex; gap: 8px; align-items: center;">
      <n-button type="primary" @click="showCreateModal = true">
        <template #icon><n-icon><SendOutline /></n-icon></template>
        发起资产登记
      </n-button>
      <n-tag type="info" size="small">需全员通过</n-tag>
    </div>
    <!-- 资产登记弹窗 -->
    <n-modal v-model:show="showCreateModal" preset="card" title="发起资产登记申请" style="max-width: 650px; max-height: 90vh; overflow-y: auto">
      <template #header-extra>
        <n-button 
          size="small" 
          :loading="imageParsing" 
          @click="triggerImageUpload"
          :disabled="imageParsing"
        >
          📷 图片识别
        </n-button>
        <input 
          ref="imageInputRef" 
          type="file" 
          accept="image/*" 
          style="display: none" 
          @change="handleImageSelected" 
        />
      </template>
      
      <!-- 图片预览 + 解析状态 -->
      <div v-if="imagePreview || imageParsing" class="image-parse-area">
        <div class="image-preview-wrapper">
          <img v-if="imagePreview" :src="imagePreview" class="image-preview" alt="凭证预览" />
          <n-button v-if="imagePreview && !imageParsing" size="tiny" circle class="image-remove-btn" @click="clearImagePreview">
            ✕
          </n-button>
        </div>
        <div v-if="imageParsing" class="image-parse-status">
          <n-spin size="small" />
          <span style="margin-left: 8px">AI 正在识别图片内容...</span>
        </div>
        <n-alert v-if="imageParseError" type="error" :bordered="false" style="margin-top: 8px" closable @close="imageParseError = ''">
          {{ imageParseError }}
        </n-alert>
        <n-alert v-if="imageParseSuccess" type="success" :bordered="false" style="margin-top: 8px" closable @close="imageParseSuccess = ''">
          ✅ {{ imageParseSuccess }}
        </n-alert>
      </div>
      
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
    </n-modal>

    <!-- 资产编辑弹窗 -->
    <n-modal v-model:show="showEditModal" preset="card" title="编辑资产信息" style="max-width: 500px">
      <n-form v-if="editForm" label-placement="left" label-width="90px">
        <n-form-item label="产品名称">
          <n-input v-model:value="editForm.name" placeholder="产品名称" />
        </n-form-item>
        <n-form-item label="到期日期">
          <n-date-picker v-model:value="editForm.end_date" type="date" style="width: 100%" clearable placeholder="可选" />
        </n-form-item>
        <n-form-item label="银行/机构">
          <n-input v-model:value="editForm.bank_name" placeholder="可选" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="editForm.note" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="可选" />
        </n-form-item>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="showEditModal = false">取消</n-button>
          <n-button type="primary" :loading="editSaving" @click="saveAssetEdit">保存</n-button>
        </div>
      </n-form>
    </n-modal>
    
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
              {{ item.approved_count || 0 }}/{{ item.total_members <= 1 ? 1 : (item.total_members - 1) }} 已审批
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
    <n-card title="家庭投资资产" class="card-hover">
      <div class="asset-filters">
        <n-select 
          v-model:value="listFilter.asset_type" 
          :options="[{ label: '全部类型', value: '' }, ...assetTypeOptions]"
          style="min-width: 110px; flex: 1"
          size="small"
          @update:value="loadAssets"
        />
        <n-select 
          v-model:value="listFilter.currency" 
          :options="[{ label: '全部币种', value: '' }, ...currencyOptions]"
          style="min-width: 110px; flex: 1"
          size="small"
          @update:value="loadAssets"
        />
      </div>
      
      <n-spin :show="assetsLoading">
        <div v-if="assets.length > 0" class="asset-cards">
          <div v-for="asset in assets" :key="asset.id" class="asset-card" style="cursor: pointer" @click="openEditModal(asset)">
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
                <span v-if="asset.bank_name">{{ asset.bank_name }}</span>
                <span v-if="asset.end_date">{{ asset.bank_name ? ' | ' : '' }}到期: {{ formatDate(asset.end_date) }}</span>
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
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { SendOutline, CashOutline, InformationCircleOutline } from '@vicons/ionicons5'
import { approvalApi, assetApi, familyApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useApprovalStore } from '@/stores/approval'

const message = useMessage()
const userStore = useUserStore()
const approvalStore = useApprovalStore()

// 弹窗控制
const showCreateModal = ref(false)

// 资产编辑弹窗
const showEditModal = ref(false)
const editSaving = ref(false)
const selectedEditAsset = ref<any>(null)
const editForm = ref({
  name: '',
  end_date: null as number | null,
  bank_name: '',
  note: ''
})

const openEditModal = (asset: any) => {
  selectedEditAsset.value = asset
  editForm.value = {
    name: asset.name || '',
    end_date: asset.end_date ? new Date(asset.end_date).getTime() : null,
    bank_name: asset.bank_name || '',
    note: asset.note || ''
  }
  showEditModal.value = true
}

const saveAssetEdit = async () => {
  if (!selectedEditAsset.value) return
  if (!editForm.value.name?.trim()) {
    message.warning('产品名称不能为空')
    return
  }
  editSaving.value = true
  try {
    await assetApi.updateInfo(selectedEditAsset.value.id, {
      name: editForm.value.name.trim(),
      end_date: editForm.value.end_date ? new Date(editForm.value.end_date).toISOString() : '',
      bank_name: editForm.value.bank_name || '',
      note: editForm.value.note || '',
    })
    message.success('资产信息已更新')
    showEditModal.value = false
    await loadAssets()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    editSaving.value = false
  }
}

// 表单数据
const formData = ref({
  user_id: 0,
  name: '',
  asset_type: 'time_deposit' as 'time_deposit' | 'fund' | 'stock' | 'bond' | 'other',
  currency: 'CNY' as 'CNY' | 'USD' | 'HKD' | 'JPY' | 'EUR' | 'GBP' | 'AUD' | 'CAD' | 'SGD' | 'KRW',
  amount: null as number | null,
  foreign_amount: null as number | null,
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

// ========== 图片导入识别 ==========
const imageInputRef = ref<HTMLInputElement | null>(null)
const imageParsing = ref(false)
const imagePreview = ref('')
const imageParseError = ref('')
const imageParseSuccess = ref('')

const triggerImageUpload = () => {
  imageInputRef.value?.click()
}

const clearImagePreview = () => {
  imagePreview.value = ''
  imageParseError.value = ''
  imageParseSuccess.value = ''
  if (imageInputRef.value) imageInputRef.value.value = ''
}

const handleImageSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件')
    return
  }

  if (file.size > 20 * 1024 * 1024) {
    message.error('图片大小不能超过 20MB')
    return
  }

  // 显示预览
  const reader = new FileReader()
  reader.onload = async (e) => {
    const base64 = e.target?.result as string
    imagePreview.value = base64
    imageParseError.value = ''
    imageParseSuccess.value = ''

    // 调用 AI 解析
    imageParsing.value = true
    try {
      const { data } = await assetApi.parseImage(base64)
      if (data.success && data.data) {
        applyParsedData(data.data)
        const fields = Object.keys(data.data).filter(k => data.data[k] != null)
        imageParseSuccess.value = `成功识别 ${fields.length} 个字段：${fields.map(f => fieldLabels[f] || f).join('、')}`
      } else {
        imageParseError.value = data.error || '未能从图片中识别出有效信息'
      }
    } catch (error: any) {
      console.error('Image parse failed:', error)
      imageParseError.value = error.response?.data?.detail || '图片识别失败，请检查 AI 服务配置'
    } finally {
      imageParsing.value = false
    }
  }
  reader.readAsDataURL(file)
}

// 字段中文标签
const fieldLabels: Record<string, string> = {
  name: '产品名称',
  asset_type: '资产类型',
  currency: '币种',
  amount: '金额',
  start_date: '开始日期',
  end_date: '到期日期',
  bank_name: '银行/机构',
  note: '备注'
}

// 将解析结果应用到表单
const applyParsedData = async (data: Record<string, any>) => {
  // 产品名称
  if (data.name) {
    formData.value.name = data.name
  }

  // 资产类型
  const validAssetTypes = ['time_deposit', 'fund', 'stock', 'bond', 'other']
  if (data.asset_type && validAssetTypes.includes(data.asset_type)) {
    formData.value.asset_type = data.asset_type
  }

  // 币种
  const validCurrencies = ['CNY', 'USD', 'HKD', 'JPY', 'EUR', 'GBP', 'AUD', 'CAD', 'SGD', 'KRW']
  if (data.currency && validCurrencies.includes(data.currency)) {
    formData.value.currency = data.currency
    // 如果是外币，获取汇率
    if (data.currency !== 'CNY') {
      await fetchExchangeRate(data.currency)
    } else {
      currentExchangeRate.value = null
    }
  }

  // 金额
  if (data.amount && data.amount > 0) {
    if (formData.value.currency === 'CNY') {
      formData.value.amount = data.amount
      formData.value.foreign_amount = null
    } else {
      formData.value.foreign_amount = data.amount
      formData.value.amount = null
    }
  }

  // 开始日期
  if (data.start_date) {
    const d = new Date(data.start_date)
    if (!isNaN(d.getTime())) {
      formData.value.start_date = d.getTime()
    }
  }

  // 到期日期
  if (data.end_date) {
    const d = new Date(data.end_date)
    if (!isNaN(d.getTime())) {
      formData.value.end_date = d.getTime()
    }
  }

  // 银行名称
  if (data.bank_name) {
    formData.value.bank_name = data.bank_name
  }

  // 备注
  if (data.note) {
    formData.value.note = formData.value.note 
      ? `${formData.value.note}\n${data.note}` 
      : data.note
  }

  message.success('图片识别完成，已自动填充表单')
}

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
    
    const { data } = await assetApi.myAssets(params)
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
    showCreateModal.value = false
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

.image-parse-area {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--theme-bg-secondary);
  border-radius: 8px;
  border: 1px dashed var(--theme-border);
}

.image-preview-wrapper {
  position: relative;
  display: inline-block;
}

.image-preview {
  max-width: 200px;
  max-height: 150px;
  border-radius: 6px;
  object-fit: contain;
  border: 1px solid var(--theme-border-light);
}

.image-remove-btn {
  position: absolute;
  top: -6px;
  right: -6px;
  font-size: 10px;
  background: var(--theme-error) !important;
  color: white !important;
}

.image-parse-status {
  display: flex;
  align-items: center;
  margin-top: 8px;
  font-size: 13px;
  color: var(--theme-text-secondary);
}

.exchange-rate-info {
  margin-bottom: 16px;
}

.funding-source-tip {
  margin-bottom: 16px;
}

.cash-balance-card {
  background: var(--theme-gradient-primary);
  color: var(--theme-gradient-text);
}

.cash-balance-card :deep(.n-statistic) {
  color: var(--theme-gradient-text);
}

.cash-balance-card :deep(.n-statistic-value__prefix),
.cash-balance-card :deep(.n-statistic-value__content) {
  color: var(--theme-gradient-text) !important;
}

.asset-filters {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
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
  background: var(--theme-bg-card);
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
