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
          <n-space vertical size="large" align="center" style="padding: 20px 0">
            <n-text depth="3">点击麦克风按钮开始录音，说出消费内容</n-text>
            <n-text depth="3">示例："中午吃饭花了38块5"</n-text>

            <!-- 录音按钮 -->
            <n-button
              size="large"
              circle
              :type="voiceRecording ? 'error' : 'primary'"
              :loading="voiceProcessing"
              @click="toggleVoiceRecording"
              style="width: 80px; height: 80px; font-size: 32px"
            >
              {{ voiceRecording ? '⏹' : '🎤' }}
            </n-button>

            <n-text v-if="voiceRecording" type="error">
              🔴 录音中... {{ voiceSeconds }}s（点击停止）
            </n-text>
            <n-text v-if="voiceProcessing" depth="3">
              正在识别语音...
            </n-text>

            <!-- 识别结果 -->
            <template v-if="voiceResult">
              <n-divider />
              <n-alert type="success" title="语音识别结果">
                <n-space vertical size="small">
                  <n-text v-if="voiceResult.transcript">原文: {{ voiceResult.transcript }}</n-text>
                  <n-text>金额: ¥{{ voiceResult.amount?.toFixed(2) || '未识别' }}</n-text>
                  <n-text>描述: {{ voiceResult.description || '未识别' }}</n-text>
                  <n-text>分类: {{ getCategoryLabel(voiceResult.category || 'other') }}</n-text>
                </n-space>
              </n-alert>
              <n-space justify="end" style="width: 100%">
                <n-button @click="voiceResult = null">清除</n-button>
                <n-button type="primary" :loading="creating" @click="handleVoiceCreate">
                  确认记账
                </n-button>
              </n-space>
            </template>

            <!-- 不支持提示 -->
            <n-alert v-if="!voiceSupported" type="warning" title="浏览器不支持">
              您的浏览器不支持语音录制功能，请使用 Chrome、Edge 等现代浏览器。
            </n-alert>
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

// 语音录入
const voiceRecording = ref(false)
const voiceProcessing = ref(false)
const voiceSeconds = ref(0)
const voiceResult = ref<any>(null)
const voiceSupported = ref(!!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia))
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let voiceTimer: ReturnType<typeof setInterval> | null = null

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

// ==================== 语音录入功能 ====================

async function toggleVoiceRecording() {
  if (voiceRecording.value) {
    stopVoiceRecording()
  } else {
    await startVoiceRecording()
  }
}

async function startVoiceRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []
    voiceSeconds.value = 0
    voiceResult.value = null

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      // 停止所有音轨
      stream.getTracks().forEach(track => track.stop())

      // 合并音频数据
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })

      // 转换为 base64
      const reader = new FileReader()
      reader.onloadend = async () => {
        const base64Audio = reader.result as string
        await sendVoiceToBackend(base64Audio)
      }
      reader.readAsDataURL(audioBlob)
    }

    mediaRecorder.start()
    voiceRecording.value = true

    // 计时器
    voiceTimer = setInterval(() => {
      voiceSeconds.value++
      // 最长录制60秒
      if (voiceSeconds.value >= 60) {
        stopVoiceRecording()
      }
    }, 1000)

  } catch (error: any) {
    if (error.name === 'NotAllowedError') {
      message.error('请允许麦克风权限以使用语音输入')
    } else {
      message.error('无法启动录音: ' + error.message)
    }
  }
}

function stopVoiceRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  voiceRecording.value = false
  if (voiceTimer) {
    clearInterval(voiceTimer)
    voiceTimer = null
  }
}

async function sendVoiceToBackend(base64Audio: string) {
  voiceProcessing.value = true
  try {
    const { data } = await api.post('/accounting/voice', {
      audio_data: base64Audio
    })
    voiceResult.value = data
    message.success('语音识别成功')
  } catch (error: any) {
    message.error(error.response?.data?.detail || '语音识别失败')
  } finally {
    voiceProcessing.value = false
  }
}

async function handleVoiceCreate() {
  if (!voiceResult.value || !voiceResult.value.amount) {
    message.warning('未识别到有效金额')
    return
  }

  creating.value = true
  try {
    await api.post('/accounting/entry', {
      amount: voiceResult.value.amount,
      category: voiceResult.value.category || 'other',
      description: voiceResult.value.description || voiceResult.value.transcript || '语音记账',
      entry_date: dayjs().toISOString(),
      consumer_id: null
    })

    message.success('语音记账成功')
    voiceResult.value = null
    showCreateModal.value = false
    await fetchEntries()
    await fetchStats()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '记账失败')
  } finally {
    creating.value = false
  }
}

// ==================== 手动记账功能 ====================

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

.category-icon {
  font-size: 20px;
}

@media (max-width: 767px) {
  .accounting-container {
    padding: 12px;
  }
}
</style>
