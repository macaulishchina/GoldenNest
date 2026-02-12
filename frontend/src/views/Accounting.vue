<template>
  <div class="accounting-container">
    <n-space vertical :size="8">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-top">
          <h3 class="page-title">📒 家庭记账</h3>
          <n-button type="primary" size="small" @click="showCreateModal = true">+ 新建记账</n-button>
        </div>
        <div class="stats-box">
          <div class="stats-box-top">
            <span class="stats-box-title">概览</span>
            <n-select
              v-model:value="statsRange"
              :options="statsRangeOptions"
              size="tiny"
              style="width: 100px"
              @update:value="handleStatsRangeChange"
            />
          </div>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-label">总支出</span>
              <span class="stat-value">¥{{ stats.total_amount.toFixed(2) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">已入账</span>
              <span class="stat-value accent">¥{{ stats.accounted_amount.toFixed(2) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">未入账</span>
              <span class="stat-value warn">¥{{ stats.unaccounted_amount.toFixed(2) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">记录数</span>
              <span class="stat-value">{{ stats.total_count }} 笔</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 筛选条件 -->
      <div class="filter-bar">
        <n-select
          v-model:value="filterCategory"
          :options="categoryOptions"
          placeholder="全部分类"
          clearable
          size="small"
          style="min-width: 110px; flex: 1"
          @update:value="fetchEntries"
        />
        <n-select
          v-model:value="filterAccounted"
          :options="accountedOptions"
          placeholder="入账状态"
          clearable
          size="small"
          style="min-width: 110px; flex: 1"
          @update:value="fetchEntries"
        />
        <n-select
          v-model:value="filterConsumer"
          :options="consumerOptions"
          placeholder="消费人"
          clearable
          size="small"
          style="min-width: 110px; flex: 1"
          @update:value="fetchEntries"
        />
        <n-date-picker
          v-model:value="filterDateRange"
          type="daterange"
          clearable
          size="small"
          style="flex: 2; min-width: 180px"
          @update:value="fetchEntries"
        />
      </div>

      <!-- 记账列表 -->
      <n-card title="记账记录" :bordered="false" class="entry-list-card">
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
              <div class="entry-list">
                <div class="entry-card" v-for="entry in entries" :key="entry.id" @click="handleEdit(entry)">
                  <div class="entry-check" :class="{ 'hidden-checkbox': entry.is_accounted }" @click.stop>
                    <n-checkbox :value="entry.id" :disabled="entry.is_accounted" />
                  </div>
                  <div class="entry-body">
                    <!-- 第一行：图标 + 描述 + 标签 … 金额 -->
                    <div class="entry-row1">
                      <span class="category-icon">{{ getCategoryIcon(entry.category) }}</span>
                      <span class="entry-desc">{{ entry.description }}</span>
                      <n-tag :type="entry.is_accounted ? 'success' : 'warning'" size="small">
                        {{ entry.is_accounted ? '已入账' : '未入账' }}
                      </n-tag>
                      <span class="entry-amount">¥{{ entry.amount.toFixed(2) }}</span>
                    </div>
                    <!-- 第二行：分类 · 消费人 · 记账人 · 记账方式 -->
                    <div class="entry-row2">
                      {{ getCategoryLabel(entry.category) }}
                      <span class="dot">·</span>
                      {{ entry.consumer_nickname || '家庭共同' }}
                      <span class="dot">·</span>
                      {{ entry.user_nickname }}
                      <span class="dot">·</span>
                      {{ getSourceLabel(entry.source) }}
                    </div>
                    <!-- 第三行：时间左下 + 操作按钮右下 -->
                    <div class="entry-row3">
                      <span class="entry-date">{{ formatDate(entry.entry_date) }}</span>
                      <span class="entry-actions">
                        <n-button v-if="!entry.is_accounted" size="tiny" quaternary type="error" @click.stop="handleDelete(entry.id)">删除</n-button>
                        <n-button v-if="entry.has_image || entry.image_data" size="tiny" quaternary @click.stop="handleViewImage(entry)">查看小票</n-button>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
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

          <n-space justify="end" style="margin-top: 16px">
            <n-button @click="showCreateModal = false">取消</n-button>
            <n-button type="primary" :loading="creating" @click="handleManualCreateWithDuplicateCheck">
              创建
            </n-button>
          </n-space>
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

          <n-space justify="end" style="margin-top: 16px">
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

          <n-space justify="end" style="margin-top: 16px">
            <n-button @click="showCreateModal = false">取消</n-button>
            <n-button
              type="primary"
              :loading="creating"
              :disabled="!importJson.trim()"
              @click="handleImportCreateWithDuplicateCheck"
            >
              导入
            </n-button>
          </n-space>
        </n-tab-pane>
      </n-tabs>
    </n-modal>

    <!-- 编辑弹窗 -->
    <n-modal
      v-model:show="showEditModal"
      preset="card"
      :title="editForm.is_accounted ? '查看记账（已入账）' : '编辑记账'"
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
            :disabled="editForm.is_accounted"
          >
            <template #prefix>¥</template>
          </n-input-number>
        </n-form-item>

        <n-form-item label="分类">
          <n-select
            v-model:value="editForm.category"
            :options="categoryOptions"
            placeholder="请选择分类"
            :disabled="editForm.is_accounted"
          />
        </n-form-item>

        <n-form-item label="描述">
          <n-input
            v-model:value="editForm.description"
            type="textarea"
            placeholder="请输入消费描述"
            :autosize="{ minRows: 2, maxRows: 4 }"
            :disabled="editForm.is_accounted"
          />
        </n-form-item>

        <n-form-item label="消费日期">
          <n-date-picker
            v-model:value="editForm.entry_date"
            type="datetime"
            style="width: 100%"
            :disabled="editForm.is_accounted"
          />
        </n-form-item>

        <n-form-item label="消费人">
          <n-select
            v-model:value="editForm.consumer_id"
            :options="consumerOptionsWithFamily"
            placeholder="请选择消费人"
            clearable
            :disabled="editForm.is_accounted"
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showEditModal = false">{{ editForm.is_accounted ? '关闭' : '取消' }}</n-button>
          <n-button v-if="!editForm.is_accounted" type="primary" :loading="updating" @click="handleUpdate">
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
            确认入账
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 重复检测确认弹窗 -->
    <n-modal
      v-model:show="showDuplicateModal"
      preset="card"
      title="⚠️ 检测到可能重复的记账"
      :style="{ width: isMobile ? '95%' : '700px' }"
      :segmented="{ content: true }"
    >
      <n-space vertical size="large">
        <n-alert type="warning">
          检测到 {{ duplicateCheckResults.exact_duplicates_count }} 条完全重复，
          {{ duplicateCheckResults.likely_duplicates_count }} 条很可能重复，
          {{ duplicateCheckResults.possible_duplicates_count }} 条可能重复。
          请确认如何处理这些记录。
        </n-alert>

        <n-space vertical size="medium">
          <div v-for="result in duplicateCheckResults.results" :key="result.index">
            <n-card
              v-if="result.is_duplicate"
              :title="`记账 #${result.index + 1}`"
              size="small"
              :bordered="true"
            >
              <!-- 新记账信息 -->
              <n-descriptions :column="isMobile ? 1 : 2" size="small">
                <n-descriptions-item label="金额">
                  ¥{{ result.entry_data.amount.toFixed(2) }}
                </n-descriptions-item>
                <n-descriptions-item label="描述">
                  {{ result.entry_data.description }}
                </n-descriptions-item>
                <n-descriptions-item label="分类">
                  {{ getCategoryLabel(result.entry_data.category) }}
                </n-descriptions-item>
                <n-descriptions-item label="日期">
                  {{ formatDate(result.entry_data.entry_date) }}
                </n-descriptions-item>
              </n-descriptions>

              <!-- 重复匹配信息 -->
              <n-divider style="margin: 12px 0" />
              <n-text strong>匹配到 {{ result.duplicates.length }} 条已有记录：</n-text>

              <n-space vertical size="small" style="margin-top: 8px">
                <n-card
                  v-for="(dup, dupIndex) in result.duplicates"
                  :key="dupIndex"
                  size="small"
                  embedded
                >
                  <template #header>
                    <n-space align="center">
                      <n-tag
                        v-if="dup.match_level === 'exact'"
                        type="error"
                        size="small"
                      >
                        完全重复
                      </n-tag>
                      <n-tag
                        v-else-if="dup.match_level === 'likely'"
                        type="warning"
                        size="small"
                      >
                        很可能重复
                      </n-tag>
                      <n-tag
                        v-else
                        type="info"
                        size="small"
                      >
                        可能重复
                      </n-tag>
                      <n-text>相似度: {{ (dup.similarity_score * 100).toFixed(0) }}%</n-text>
                    </n-space>
                  </template>

                  <n-space vertical size="small">
                    <n-text>¥{{ dup.existing_entry.amount.toFixed(2) }} - {{ dup.existing_entry.description }}</n-text>
                    <n-text depth="3" style="font-size: 12px">
                      {{ formatDate(dup.existing_entry.entry_date) }} · {{ dup.existing_entry.user_nickname }}
                    </n-text>
                    <n-divider style="margin: 4px 0" />
                    <n-text depth="3" style="font-size: 12px">
                      匹配原因：{{ dup.match_reasons.join('；') }}
                    </n-text>
                  </n-space>
                </n-card>
              </n-space>

              <!-- 操作按钮 -->
              <template #footer>
                <n-space justify="end">
                  <n-button
                    size="small"
                    @click="handleDuplicateAction(result.index, 'ignore')"
                  >
                    忽略重复，仍然记账
                  </n-button>
                  <n-button
                    size="small"
                    type="error"
                    @click="handleDuplicateAction(result.index, 'skip')"
                  >
                    跳过此条
                  </n-button>
                  <n-button
                    v-if="result.match_level === 'possible'"
                    size="small"
                    type="primary"
                    @click="handleDuplicateAction(result.index, 'ai')"
                  >
                    让AI再次判断
                  </n-button>
                </n-space>
              </template>
            </n-card>
          </div>
        </n-space>
      </n-space>

      <template #footer>
        <n-space justify="space-between">
          <n-button @click="handleBatchDuplicateAction('skip-all')">
            全部跳过重复
          </n-button>
          <n-space>
            <n-button @click="handleBatchDuplicateAction('ignore-all')">
              全部忽略，继续记账
            </n-button>
            <n-button
              type="primary"
              @click="handleBatchDuplicateAction('smart')"
            >
              智能处理（跳过完全重复，保留其他）
            </n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>

    <!-- 查看小票图片弹窗 -->
    <n-modal
      v-model:show="showImageModal"
      :style="{ width: isMobile ? '95vw' : '80vw', maxWidth: '800px' }"
    >
      <div class="receipt-viewer" @click="showImageModal = false">
        <img :src="currentImage" class="receipt-img" @click.stop />
        <n-button class="receipt-close" circle size="small" @click="showImageModal = false">✕</n-button>
      </div>
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
const filterAccounted = ref<string | null>('false')
const filterConsumer = ref<number | null>(null)
const filterDateRange = ref<[number, number] | null>(null)

// 统计时间范围
const statsRange = ref('month')
const statsRangeOptions = [
  { label: '今天', value: 'today' },
  { label: '近一周', value: 'week' },
  { label: '近一月', value: 'month' },
  { label: '近一年', value: 'year' },
  { label: '全部', value: 'all' }
]

// 选中的记账ID
const selectedIds = ref<number[]>([])

// 弹窗状态
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showBatchExpenseModal = ref(false)
const showImageModal = ref(false)
const showDuplicateModal = ref(false)

// 重复检测相关
const duplicateCheckResults = ref({
  results: [],
  exact_duplicates_count: 0,
  likely_duplicates_count: 0,
  possible_duplicates_count: 0,
  unique_count: 0
})
const pendingEntries = ref<any[]>([])  // 待创建的记账条目
const duplicateActions = ref<Map<number, string>>(new Map())  // 每条记录的处理决定

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
  consumer_id: null,
  is_accounted: false
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
  { label: '未入账', value: 'false' },
  { label: '已入账', value: 'true' }
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
    if (filterAccounted.value !== null) params.is_accounted = filterAccounted.value === 'true'
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
    // 根据统计时间范围计算日期
    if (statsRange.value !== 'all') {
      const now = dayjs()
      const rangeMap: Record<string, number> = {
        year: 365, month: 30, week: 7, today: 0
      }
      const days = rangeMap[statsRange.value] ?? 30
      params.start_date = now.subtract(days, 'day').startOf('day').toISOString()
      params.end_date = now.endOf('day').toISOString()
    }
    const { data } = await api.get('/accounting/stats/summary', { params })
    stats.value = data
  } catch (error: any) {
    message.error(error.response?.data?.detail || '获取统计数据失败')
  }
}

function handleStatsRangeChange(val: string) {
  statsRange.value = val
  fetchStats()
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
    const file = photoFileList.value[0].file!
    const formData = new FormData()
    formData.append('file', file)
    if (photoForm.value.entry_date) {
      formData.append('entry_date', dayjs(photoForm.value.entry_date).toISOString())
    }

    const { data } = await api.post('/accounting/photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
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
    consumer_id: entry.consumer_id || 0,
    is_accounted: entry.is_accounted || false
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

    message.success('入账成功，已记录到资金流水')
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

async function handleViewImage(entry: any) {
  if (entry.image_data) {
    currentImage.value = entry.image_data
    showImageModal.value = true
    return
  }
  try {
    const { data } = await api.get(`/accounting/${entry.id}`)
    currentImage.value = data.image_data || ''
    showImageModal.value = true
  } catch {
    message.error('加载小票图片失败')
  }
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

// ==================== 重复检测功能 ====================

async function checkDuplicates(entries: any[]) {
  /**
   * 检查一组记账条目是否重复
   * @param entries 待检查的记账条目数组
   * @returns 重复检测结果
   */
  try {
    const { data } = await api.post('/accounting/check-duplicates', { entries })
    return data
  } catch (error: any) {
    console.error('重复检测失败:', error)
    message.error(error.response?.data?.detail || '重复检测失败')
    return null
  }
}

async function handleManualCreateWithDuplicateCheck() {
  /**
   * 手动创建记账（带重复检测）
   */
  if (!manualForm.value.amount || !manualForm.value.description) {
    message.warning('请填写完整信息')
    return
  }

  const entryData = {
    amount: manualForm.value.amount,
    category: manualForm.value.category,
    description: manualForm.value.description,
    entry_date: dayjs(manualForm.value.entry_date).toISOString(),
    consumer_id: manualForm.value.consumer_id || null
  }

  // 先检查重复
  const checkResult = await checkDuplicates([entryData])

  if (!checkResult) {
    // 检测失败，直接创建
    await createEntryDirect(entryData)
    return
  }

  // 如果有重复，显示确认弹窗
  if (checkResult.exact_duplicates_count > 0 ||
      checkResult.likely_duplicates_count > 0 ||
      checkResult.possible_duplicates_count > 0) {
    pendingEntries.value = [entryData]
    duplicateCheckResults.value = checkResult
    duplicateActions.value.clear()
    showDuplicateModal.value = true
  } else {
    // 没有重复，直接创建
    await createEntryDirect(entryData)
  }
}

async function createEntryDirect(entryData: any) {
  /**
   * 直接创建记账条目（不检查重复）
   */
  creating.value = true
  try {
    await api.post('/accounting/entry', entryData)
    message.success('记账成功')
    showCreateModal.value = false
    showDuplicateModal.value = false
    resetManualForm()
    await fetchEntries()
    await fetchStats()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '记账失败')
  } finally {
    creating.value = false
  }
}

function handleDuplicateAction(index: number, action: 'ignore' | 'skip' | 'ai') {
  /**
   * 处理单条记账的重复决定
   * @param index 记账条目索引
   * @param action 'ignore'=忽略重复继续记账, 'skip'=跳过此条, 'ai'=让AI再次判断
   */
  duplicateActions.value.set(index, action)

  if (action === 'ignore') {
    // 立即创建这条记账
    const entryData = pendingEntries.value[index]
    if (entryData) {
      createEntryDirect(entryData)
    }
  } else if (action === 'skip') {
    message.info(`已跳过第 ${index + 1} 条记账`)
  } else if (action === 'ai') {
    message.info('AI再次判断功能开发中...')
    // TODO: 调用AI进行更详细的判断
  }
}

async function handleBatchDuplicateAction(action: 'skip-all' | 'ignore-all' | 'smart') {
  /**
   * 批量处理重复记账
   * @param action
   *   - 'skip-all': 全部跳过
   *   - 'ignore-all': 全部忽略，继续记账
   *   - 'smart': 智能处理（跳过完全重复，保留其他）
   */
  if (action === 'skip-all') {
    showDuplicateModal.value = false
    message.info('已跳过所有重复记账')
  } else if (action === 'ignore-all') {
    // 全部创建
    creating.value = true
    try {
      for (const entryData of pendingEntries.value) {
        await api.post('/accounting/entry', entryData)
      }
      message.success(`成功创建 ${pendingEntries.value.length} 条记账`)
      showDuplicateModal.value = false
      showCreateModal.value = false
      resetManualForm()
      await fetchEntries()
      await fetchStats()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '批量记账失败')
    } finally {
      creating.value = false
    }
  } else if (action === 'smart') {
    // 智能处理：跳过完全重复，创建其他
    creating.value = true
    try {
      let createdCount = 0
      let skippedCount = 0

      for (let i = 0; i < duplicateCheckResults.value.results.length; i++) {
        const result = duplicateCheckResults.value.results[i]

        if (result.match_level === 'exact') {
          // 完全重复，跳过
          skippedCount++
        } else {
          // 其他情况，创建
          const entryData = pendingEntries.value[i]
          if (entryData) {
            await api.post('/accounting/entry', entryData)
            createdCount++
          }
        }
      }

      message.success(`智能处理完成：创建 ${createdCount} 条，跳过 ${skippedCount} 条重复`)
      showDuplicateModal.value = false
      showCreateModal.value = false
      resetManualForm()
      await fetchEntries()
      await fetchStats()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '智能处理失败')
    } finally {
      creating.value = false
    }
  }
}

async function handleImportCreateWithDuplicateCheck() {
  /**
   * 批量导入记账（带重复检测）
   */
  if (!importJson.value.trim()) {
    message.warning('请输入JSON数据')
    return
  }

  try {
    const entries = JSON.parse(importJson.value)

    // 先检查重复
    const checkResult = await checkDuplicates(entries)

    if (!checkResult) {
      // 检测失败，直接导入
      await importEntriesDirect(entries)
      return
    }

    // 如果有重复，显示确认弹窗
    if (checkResult.exact_duplicates_count > 0 ||
        checkResult.likely_duplicates_count > 0 ||
        checkResult.possible_duplicates_count > 0) {
      pendingEntries.value = entries
      duplicateCheckResults.value = checkResult
      duplicateActions.value.clear()
      showDuplicateModal.value = true
    } else {
      // 没有重复，直接导入
      await importEntriesDirect(entries)
    }
  } catch (error: any) {
    if (error instanceof SyntaxError) {
      message.error('JSON格式错误')
    } else {
      message.error('解析失败')
    }
  }
}

async function importEntriesDirect(entries: any[]) {
  /**
   * 直接导入记账条目（不检查重复）
   */
  creating.value = true
  try {
    await api.post('/accounting/import', { entries })
    message.success(`成功导入 ${entries.length} 条记账记录`)
    showCreateModal.value = false
    showDuplicateModal.value = false
    importJson.value = ''
    await fetchEntries()
    await fetchStats()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '导入失败')
  } finally {
    creating.value = false
  }
}

// ==================== 原有函数（保留向后兼容） ====================

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

/* ===== 记账列表卡片 ===== */
.entry-list-card :deep(.n-card__content) {
  padding-left: 8px !important;
  padding-right: 8px !important;
}

/* ===== 页面头部 ===== */
.page-header {
  background: var(--theme-bg-card, #ffffff);
  border-radius: 16px;
  padding: 16px 20px;
  border: 1px solid var(--theme-border, #e5e7eb);
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--theme-text-primary, #1f2937);
}

.stats-box {
  padding-top: 2px;
}

.stats-box-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--theme-border, #e5e7eb);
}

.stats-box-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--theme-text-primary, #1f2937);
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
  flex: 1;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-label {
  font-size: 13px;
  color: var(--theme-text-secondary, #6b7280);
  line-height: 1.3;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--theme-text-primary, #1f2937);
  line-height: 1.4;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.stat-value.accent {
  color: var(--theme-success, #18a058);
}

.stat-value.warn {
  color: var(--theme-warning, #f0a020);
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 2px;
}

.receipt-viewer {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.6);
  border-radius: 8px;
  padding: 16px;
}

.receipt-img {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 4px;
}

.receipt-close {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0.8;
}

/* ===== 记账列表卡片 ===== */
.entry-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.entry-card {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 4px 10px 0;
  margin: 0 -8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.entry-card:hover {
  background: rgba(128, 128, 128, 0.08);
}

.entry-check {
  padding-top: 6px;
  padding-left: 8px;
  flex-shrink: 0;
}

.entry-check.hidden-checkbox {
  visibility: hidden;
}

.entry-body {
  flex: 1;
  min-width: 0;
}

/* 第一行：图标 描述 标签 ... 金额 */
.entry-row1 {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.entry-desc {
  font-weight: 500;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entry-amount {
  margin-left: auto;
  font-weight: 600;
  font-size: 17px;
  color: #e88080;
  white-space: nowrap;
  flex-shrink: 0;
}

/* 第二行：分类 · 消费人 · 记账人 · 记账方式 */
.entry-row2 {
  font-size: 12px;
  color: var(--n-text-color-3, #999);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

.entry-row2 .dot {
  margin: 0 4px;
  opacity: 0.45;
}

/* 第三行：时间(左) + 操作按钮(右) */
.entry-row3 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 2px;
}

.entry-date {
  font-size: 12px;
  color: var(--n-text-color-3, #999);
}

.entry-actions {
  display: flex;
  gap: 0;
}

@media (max-width: 767px) {
  .accounting-container {
    padding: 12px;
  }

  .stats-section {
    flex-direction: column;
    align-items: stretch;
  }

  .stats-grid {
    gap: 10px 16px;
  }

  .stat-value {
    font-size: 18px;
  }

  .page-header {
    padding: 14px 16px;
    border-radius: 12px;
  }

  .entry-card {
    padding: 8px 10px;
  }

  .entry-desc {
    font-size: 14px;
  }

  .entry-amount {
    font-size: 15px;
  }

  .entry-row2 {
    white-space: normal;
  }
}
</style>
