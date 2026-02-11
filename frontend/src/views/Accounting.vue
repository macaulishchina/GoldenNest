<template>
  <div class="accounting-container">
    <n-space vertical size="large">
      <!-- 页面头部 -->
      <n-card title="📒 家庭记账" :bordered="false">
        <template #header-extra>
          <n-button type="primary" @click="showCreateModal = true">
            + 新建记账
          </n-button>
        </template>

        <!-- 统计卡片 -->
        <n-grid :cols="isMobile ? 2 : 4" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-statistic label="总支出" :value="stats.total_amount">
              <template #suffix>元</template>
            </n-statistic>
          </n-grid-item>
          <n-grid-item>
            <n-statistic label="已入账" :value="stats.accounted_amount">
              <template #suffix>元</template>
            </n-statistic>
          </n-grid-item>
          <n-grid-item>
            <n-statistic label="未入账" :value="stats.unaccounted_amount">
              <template #suffix>元</template>
            </n-statistic>
          </n-grid-item>
          <n-grid-item>
            <n-statistic label="记录数" :value="stats.total_count" />
          </n-grid-item>
        </n-grid>
      </n-card>

      <!-- 筛选条件 -->
      <n-card :bordered="false">
        <n-space :vertical="isMobile" size="medium">
          <n-select
            v-model:value="filterCategory"
            :options="categoryOptions"
            placeholder="全部分类"
            clearable
            style="min-width: 150px"
            @update:value="fetchEntries"
          />
          <n-select
            v-model:value="filterAccounted"
            :options="accountedOptions"
            placeholder="入账状态"
            clearable
            style="min-width: 150px"
            @update:value="fetchEntries"
          />
          <n-select
            v-model:value="filterConsumer"
            :options="consumerOptions"
            placeholder="消费人"
            clearable
            style="min-width: 150px"
            @update:value="fetchEntries"
          />
          <n-date-picker
            v-model:value="filterDateRange"
            type="daterange"
            clearable
            :style="{ width: isMobile ? '100%' : '300px' }"
            @update:value="fetchEntries"
          />
        </n-space>
      </n-card>

      <!-- 记账列表 -->
      <n-card title="记账记录" :bordered="false">
        <template #header-extra>
          <n-space>
            <n-button
              type="primary"
              :disabled="selectedIds.length === 0"
              @click="handleBatchExpense"
            >
              批量入账 ({{ selectedIds.length }})
            </n-button>
          </n-space>
        </template>

        <n-spin :show="loading">
          <n-space vertical size="medium">
            <n-checkbox-group v-model:value="selectedIds">
              <n-list>
                <n-list-item v-for="entry in entries" :key="entry.id">
                  <template #prefix>
                    <n-checkbox
                      :value="entry.id"
                      :disabled="entry.is_accounted"
                    />
                  </template>
                  <n-thing>
                    <template #header>
                      <n-space align="center">
                        <span class="category-icon">{{ getCategoryIcon(entry.category) }}</span>
                        <span>{{ entry.description }}</span>
                        <n-tag
                          v-if="entry.is_accounted"
                          type="success"
                          size="small"
                        >
                          已入账
                        </n-tag>
                        <n-tag
                          v-else
                          type="warning"
                          size="small"
                        >
                          未入账
                        </n-tag>
                      </n-space>
                    </template>
                    <template #description>
                      <n-space size="small">
                        <n-text depth="3">
                          {{ formatDate(entry.entry_date) }}
                        </n-text>
                        <n-divider vertical />
                        <n-text depth="3">
                          {{ entry.user_nickname }}
                        </n-text>
                        <n-divider vertical />
                        <n-text depth="3">
                          {{ entry.consumer_nickname || '家庭共同' }}
                        </n-text>
                        <n-divider vertical />
                        <n-tag size="small">
                          {{ getSourceLabel(entry.source) }}
                        </n-tag>
                      </n-space>
                    </template>
                    <template #footer>
                      <n-space justify="space-between" align="center">
                        <n-text strong style="font-size: 18px; color: var(--n-color-error)">
                          ¥{{ entry.amount.toFixed(2) }}
                        </n-text>
                        <n-space size="small">
                          <n-button
                            v-if="!entry.is_accounted"
                            size="small"
                            @click="handleEdit(entry)"
                          >
                            编辑
                          </n-button>
                          <n-button
                            v-if="!entry.is_accounted"
                            size="small"
                            type="error"
                            @click="handleDelete(entry.id)"
                          >
                            删除
                          </n-button>
                          <n-button
                            v-if="entry.image_data"
                            size="small"
                            @click="handleViewImage(entry.image_data)"
                          >
                            查看小票
                          </n-button>
                        </n-space>
                      </n-space>
                    </template>
                  </n-thing>
                </n-list-item>
              </n-list>
            </n-checkbox-group>

            <!-- 分页 -->
            <n-pagination
              v-model:page="currentPage"
              :page-count="totalPages"
              :page-size="pageSize"
              show-size-picker
              :page-sizes="[10, 20, 50]"
              @update:page="fetchEntries"
              @update:page-size="handlePageSizeChange"
            />
          </n-space>
        </n-spin>
      </n-card>
    </n-space>

    <!-- 新建记账弹窗 -->
    <n-modal
      v-model:show="showCreateModal"
      preset="card"
      title="新建记账"
      :style="{ width: isMobile ? '95%' : '600px' }"
      :segmented="{ content: true }"
    >
      <n-tabs v-model:value="createMethod" type="segment">
        <n-tab-pane name="manual" tab="手动输入">
          <n-form ref="manualFormRef" :model="manualForm" :rules="manualRules">
            <n-form-item label="金额" path="amount">
              <n-input-number
                v-model:value="manualForm.amount"
                :min="0.01"
                :precision="2"
                placeholder="请输入金额"
                style="width: 100%"
              >
                <template #prefix>¥</template>
              </n-input-number>
            </n-form-item>

            <n-form-item label="分类" path="category">
              <n-select
                v-model:value="manualForm.category"
                :options="categoryOptions"
                placeholder="请选择分类"
              />
            </n-form-item>

            <n-form-item label="描述" path="description">
              <n-input
                v-model:value="manualForm.description"
                type="textarea"
                placeholder="请输入消费描述"
                :autosize="{ minRows: 2, maxRows: 4 }"
              />
            </n-form-item>

            <n-form-item label="消费日期" path="entry_date">
              <n-date-picker
                v-model:value="manualForm.entry_date"
                type="datetime"
                style="width: 100%"
              />
            </n-form-item>

            <n-form-item label="消费人" path="consumer_id">
              <n-select
                v-model:value="manualForm.consumer_id"
                :options="consumerOptionsWithFamily"
                placeholder="请选择消费人（默认家庭共同）"
                clearable
              />
            </n-form-item>
          </n-form>

          <template #footer>
            <n-space justify="end">
              <n-button @click="showCreateModal = false">取消</n-button>
              <n-button type="primary" :loading="creating" @click="handleManualCreate">
                创建
              </n-button>
            </n-space>
          </template>
        </n-tab-pane>

        <n-tab-pane name="photo" tab="拍照识别">
          <n-space vertical size="large">
            <n-upload
              v-model:file-list="photoFileList"
              :max="1"
              accept="image/*"
              list-type="image-card"
              @change="handlePhotoChange"
            >
              <n-button>📷 选择小票照片</n-button>
            </n-upload>

            <n-form-item label="消费日期（可选）">
              <n-date-picker
                v-model:value="photoForm.entry_date"
                type="datetime"
                clearable
                style="width: 100%"
              />
            </n-form-item>

            <n-alert v-if="ocrResult" type="info" title="识别结果">
              <n-space vertical size="small">
                <n-text>金额: ¥{{ ocrResult.amount }}</n-text>
                <n-text>描述: {{ ocrResult.description }}</n-text>
                <n-text>分类: {{ getCategoryLabel(ocrResult.category) }}</n-text>
                <n-text>置信度: {{ (ocrResult.confidence * 100).toFixed(1) }}%</n-text>
              </n-space>
            </n-alert>
          </n-space>

          <template #footer>
            <n-space justify="end">
              <n-button @click="showCreateModal = false">取消</n-button>
              <n-button
                type="primary"
                :loading="creating"
                :disabled="!photoFileList.length"
                @click="handlePhotoCreate"
              >
                识别并创建
              </n-button>
            </n-space>
          </template>
        </n-tab-pane>

        <n-tab-pane name="voice" tab="语音输入">
          <n-space vertical size="large" align="center">
            <n-text depth="3">语音识别功能开发中...</n-text>
            <n-text depth="3">示例："中午吃饭花了38块5"</n-text>
            <n-button size="large" circle type="primary" disabled>
              🎤
            </n-button>
          </n-space>
        </n-tab-pane>

        <n-tab-pane name="import" tab="批量导入">
          <n-space vertical size="large">
            <n-alert type="info" title="导入格式说明">
              请使用以下JSON格式批量导入记账记录：
              <n-code language="json" :code="importTemplate" />
            </n-alert>

            <n-input
              v-model:value="importJson"
              type="textarea"
              placeholder="粘贴JSON数据..."
              :autosize="{ minRows: 8, maxRows: 12 }"
            />
          </n-space>

          <template #footer>
            <n-space justify="end">
              <n-button @click="showCreateModal = false">取消</n-button>
              <n-button
                type="primary"
                :loading="creating"
                :disabled="!importJson.trim()"
                @click="handleImportCreate"
              >
                导入
              </n-button>
            </n-space>
          </template>
        </n-tab-pane>
      </n-tabs>
    </n-modal>

    <!-- 编辑弹窗 -->
    <n-modal
      v-model:show="showEditModal"
      preset="card"
      title="编辑记账"
      :style="{ width: isMobile ? '95%' : '600px' }"
    >
      <n-form ref="editFormRef" :model="editForm">
        <n-form-item label="金额">
          <n-input-number
            v-model:value="editForm.amount"
            :min="0.01"
            :precision="2"
            placeholder="请输入金额"
            style="width: 100%"
          >
            <template #prefix>¥</template>
          </n-input-number>
        </n-form-item>

        <n-form-item label="分类">
          <n-select
            v-model:value="editForm.category"
            :options="categoryOptions"
            placeholder="请选择分类"
          />
        </n-form-item>

        <n-form-item label="描述">
          <n-input
            v-model:value="editForm.description"
            type="textarea"
            placeholder="请输入消费描述"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>

        <n-form-item label="消费日期">
          <n-date-picker
            v-model:value="editForm.entry_date"
            type="datetime"
            style="width: 100%"
          />
        </n-form-item>

        <n-form-item label="消费人">
          <n-select
            v-model:value="editForm.consumer_id"
            :options="consumerOptionsWithFamily"
            placeholder="请选择消费人"
            clearable
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showEditModal = false">取消</n-button>
          <n-button type="primary" :loading="updating" @click="handleUpdate">
            保存
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 批量入账弹窗 -->
    <n-modal
      v-model:show="showBatchExpenseModal"
      preset="card"
      title="批量转为支出申请"
      :style="{ width: isMobile ? '95%' : '500px' }"
    >
      <n-form ref="batchExpenseFormRef" :model="batchExpenseForm">
        <n-form-item label="申请标题">
          <n-input
            v-model:value="batchExpenseForm.title"
            placeholder="请输入支出申请标题"
          />
        </n-form-item>

        <n-form-item label="申请描述（可选）">
          <n-input
            v-model:value="batchExpenseForm.description"
            type="textarea"
            placeholder="请输入支出申请描述"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>

        <n-alert type="info">
          将把 {{ selectedIds.length }} 条记账记录（总计 ¥{{ selectedTotalAmount.toFixed(2) }}）转为支出申请。
        </n-alert>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showBatchExpenseModal = false">取消</n-button>
          <n-button
            type="primary"
            :loading="batchExpenseLoading"
            @click="handleBatchExpenseSubmit"
          >
            提交申请
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 查看小票图片弹窗 -->
    <n-modal
      v-model:show="showImageModal"
      preset="card"
      title="小票照片"
      :style="{ width: isMobile ? '95%' : '600px' }"
    >
      <n-image :src="currentImage" />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { api } from '@/api'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

// 响应式状态
const isMobile = ref(window.innerWidth < 768)
window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth < 768
})

// 数据状态
const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const entries = ref<any[]>([])
const stats = ref({
  total_amount: 0,
  total_count: 0,
  accounted_amount: 0,
  accounted_count: 0,
  unaccounted_amount: 0,
  unaccounted_count: 0,
  category_stats: []
})
const familyMembers = ref<any[]>([])

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const totalPages = ref(0)

// 筛选条件
const filterCategory = ref<string | null>(null)
const filterAccounted = ref<boolean | null>(null)
const filterConsumer = ref<number | null>(null)
const filterDateRange = ref<[number, number] | null>(null)

// 选中的记账ID
const selectedIds = ref<number[]>([])

// 弹窗状态
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showBatchExpenseModal = ref(false)
const showImageModal = ref(false)

// 创建方式
const createMethod = ref('manual')

// 手动输入表单
const manualForm = ref({
  amount: null,
  category: 'food',
  description: '',
  entry_date: Date.now(),
  consumer_id: null
})

const manualRules = {
  amount: [{ required: true, type: 'number', message: '请输入金额', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  description: [{ required: true, message: '请输入描述', trigger: 'blur' }],
  entry_date: [{ required: true, type: 'number', message: '请选择日期', trigger: 'change' }]
}

// 拍照识别
const photoFileList = ref<any[]>([])
const photoForm = ref({
  entry_date: null
})
const ocrResult = ref<any>(null)

// 批量导入
const importJson = ref('')
const importTemplate = `[
  {
    "amount": 38.5,
    "category": "food",
    "description": "午餐",
    "entry_date": "2024-01-15T12:30:00",
    "consumer_id": null
  }
]`

// 编辑表单
const editForm = ref({
  id: 0,
  amount: 0,
  category: '',
  description: '',
  entry_date: Date.now(),
  consumer_id: null
})

// 批量入账表单
const batchExpenseForm = ref({
  title: '',
  description: ''
})
const batchExpenseLoading = ref(false)

// 查看图片
const currentImage = ref('')

// 分类选项
const categoryOptions = [
  { label: '餐饮', value: 'food' },
  { label: '交通', value: 'transport' },
  { label: '购物', value: 'shopping' },
  { label: '娱乐', value: 'entertainment' },
  { label: '医疗', value: 'healthcare' },
  { label: '教育', value: 'education' },
  { label: '住房', value: 'housing' },
  { label: '水电煤', value: 'utilities' },
  { label: '其他', value: 'other' }
]

const accountedOptions = [
  { label: '未入账', value: false },
  { label: '已入账', value: true }
]

const consumerOptions = computed(() => {
  return familyMembers.value.map(member => ({
    label: member.nickname,
    value: member.user_id
  }))
})

const consumerOptionsWithFamily = computed(() => {
  return [
    { label: '家庭共同', value: 0 },
    ...consumerOptions.value
  ]
})

const selectedTotalAmount = computed(() => {
  return entries.value
    .filter(e => selectedIds.value.includes(e.id))
    .reduce((sum, e) => sum + e.amount, 0)
})

// 辅助函数
function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    food: '🍽️',
    transport: '🚗',
    shopping: '🛍️',
    entertainment: '🎮',
    healthcare: '💊',
    education: '📚',
    housing: '🏠',
    utilities: '💡',
    other: '📝'
  }
  return icons[category] || '📝'
}

function getCategoryLabel(category: string): string {
  const option = categoryOptions.find(opt => opt.value === category)
  return option?.label || category
}

function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    manual: '手动',
    photo: '拍照',
    voice: '语音',
    import: '导入',
    auto: '自动'
  }
  return labels[source] || source
}

function formatDate(dateStr: string): string {
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

// API调用
async function fetchEntries() {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value
    }

    if (filterCategory.value) params.category = filterCategory.value
    if (filterAccounted.value !== null) params.is_accounted = filterAccounted.value
    if (filterConsumer.value !== null) params.consumer_id = filterConsumer.value
    if (filterDateRange.value) {
      params.start_date = dayjs(filterDateRange.value[0]).toISOString()
      params.end_date = dayjs(filterDateRange.value[1]).toISOString()
    }

    const { data } = await api.get('/accounting/list', { params })
    entries.value = data.entries
    totalPages.value = Math.ceil(data.total / pageSize.value)
  } catch (error: any) {
    message.error(error.response?.data?.detail || '获取记账列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const params: any = {}
    if (filterDateRange.value) {
      params.start_date = dayjs(filterDateRange.value[0]).toISOString()
      params.end_date = dayjs(filterDateRange.value[1]).toISOString()
    }
    const { data } = await api.get('/accounting/stats/summary', { params })
    stats.value = data
  } catch (error: any) {
    message.error(error.response?.data?.detail || '获取统计数据失败')
  }
}

async function fetchFamilyMembers() {
  try {
    const { data } = await api.get('/family/my')
    familyMembers.value = data.members || []
  } catch (error: any) {
    console.error('获取家庭成员失败:', error)
  }
}

async function handleManualCreate() {
  if (!manualForm.value.amount || !manualForm.value.description) {
    message.warning('请填写完整信息')
    return
  }

  creating.value = true
  try {
    await api.post('/accounting/entry', {
      amount: manualForm.value.amount,
      category: manualForm.value.category,
      description: manualForm.value.description,
      entry_date: dayjs(manualForm.value.entry_date).toISOString(),
      consumer_id: manualForm.value.consumer_id || null
    })

    message.success('记账成功')
    showCreateModal.value = false
    resetManualForm()
    await fetchEntries()
    await fetchStats()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '记账失败')
  } finally {
    creating.value = false
  }
}

async function handlePhotoChange() {
  // 自动开始识别
  if (photoFileList.value.length > 0) {
    ocrResult.value = null
  }
}

async function handlePhotoCreate() {
  if (photoFileList.value.length === 0) {
    message.warning('请选择小票照片')
    return
  }

  creating.value = true
  try {
    const file = photoFileList.value[0].file
    const reader = new FileReader()

    reader.onload = async (e) => {
      const imageData = e.target?.result as string

      const payload: any = {
        image_data: imageData
      }

      if (photoForm.value.entry_date) {
        payload.entry_date = dayjs(photoForm.value.entry_date).toISOString()
      }

      try {
        const { data } = await api.post('/accounting/photo', payload)
        message.success('小票识别成功')
        ocrResult.value = data
        showCreateModal.value = false
        photoFileList.value = []
        photoForm.value.entry_date = null
        await fetchEntries()
        await fetchStats()
      } catch (error: any) {
        message.error(error.response?.data?.detail || 'OCR识别失败')
      } finally {
        creating.value = false
      }
    }

    reader.readAsDataURL(file)
  } catch (error: any) {
    message.error('读取图片失败')
    creating.value = false
  }
}

async function handleImportCreate() {
  if (!importJson.value.trim()) {
    message.warning('请输入JSON数据')
    return
  }

  creating.value = true
  try {
    const entries = JSON.parse(importJson.value)

    await api.post('/accounting/import', { entries })

    message.success(`成功导入 ${entries.length} 条记账记录`)
    showCreateModal.value = false
    importJson.value = ''
    await fetchEntries()
    await fetchStats()
  } catch (error: any) {
    if (error instanceof SyntaxError) {
      message.error('JSON格式错误')
    } else {
      message.error(error.response?.data?.detail || '导入失败')
    }
  } finally {
    creating.value = false
  }
}

function handleEdit(entry: any) {
  editForm.value = {
    id: entry.id,
    amount: entry.amount,
    category: entry.category,
    description: entry.description,
    entry_date: new Date(entry.entry_date).getTime(),
    consumer_id: entry.consumer_id || 0
  }
  showEditModal.value = true
}

async function handleUpdate() {
  updating.value = true
  try {
    const payload: any = {
      amount: editForm.value.amount,
      category: editForm.value.category,
      description: editForm.value.description,
      entry_date: dayjs(editForm.value.entry_date).toISOString(),
      consumer_id: editForm.value.consumer_id || null
    }

    await api.put(`/accounting/${editForm.value.id}`, payload)

    message.success('更新成功')
    showEditModal.value = false
    await fetchEntries()
    await fetchStats()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '更新失败')
  } finally {
    updating.value = false
  }
}

function handleDelete(id: number) {
  dialog.warning({
    title: '确认删除',
    content: '确定要删除这条记账记录吗？',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.delete(`/accounting/${id}`)
        message.success('删除成功')
        await fetchEntries()
        await fetchStats()
      } catch (error: any) {
        message.error(error.response?.data?.detail || '删除失败')
      }
    }
  })
}

function handleBatchExpense() {
  if (selectedIds.value.length === 0) {
    message.warning('请先选择要入账的记录')
    return
  }

  batchExpenseForm.value.title = `记账批量入账 ${dayjs().format('YYYY-MM-DD')}`
  batchExpenseForm.value.description = ''
  showBatchExpenseModal.value = true
}

async function handleBatchExpenseSubmit() {
  if (!batchExpenseForm.value.title) {
    message.warning('请输入申请标题')
    return
  }

  batchExpenseLoading.value = true
  try {
    await api.post('/accounting/batch-expense', {
      entry_ids: selectedIds.value,
      title: batchExpenseForm.value.title,
      description: batchExpenseForm.value.description || null
    })

    message.success('已提交支出申请')
    showBatchExpenseModal.value = false
    selectedIds.value = []
    await fetchEntries()
    await fetchStats()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '提交失败')
  } finally {
    batchExpenseLoading.value = false
  }
}

function handleViewImage(imageData: string) {
  currentImage.value = imageData
  showImageModal.value = true
}

function handlePageSizeChange(newPageSize: number) {
  pageSize.value = newPageSize
  currentPage.value = 1
  fetchEntries()
}

function resetManualForm() {
  manualForm.value = {
    amount: null,
    category: 'food',
    description: '',
    entry_date: Date.now(),
    consumer_id: null
  }
}

// 初始化
onMounted(() => {
  fetchFamilyMembers()
  fetchEntries()
  fetchStats()
})
</script>

<style scoped>
.accounting-container {
  padding: 20px;
}

.category-icon {
  font-size: 20px;
}

@media (max-width: 767px) {
  .accounting-container {
    padding: 12px;
  }
}
</style>
