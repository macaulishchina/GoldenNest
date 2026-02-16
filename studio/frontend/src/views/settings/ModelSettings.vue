<template>
  <n-space vertical :size="16">
    <!-- 模型配置 -->
    <n-card size="small" style="background: #16213e">
      <template #header>
        <n-space align="center" :size="8" @click="toggleSection('config')" style="cursor: pointer; user-select: none">
          <n-icon :component="sectionOpen.config ? ChevronDown : ChevronForward" :size="16" />
          <span>🧠 模型配置</span>
        </n-space>
      </template>
      <div v-show="sectionOpen.config">
      <n-space vertical :size="12">
        <n-space align="center">
          <n-switch v-model:value="studioConfig.freeModelsOnly" />
          <n-text>仅使用免费模型</n-text>
          <n-text depth="3" style="font-size: 11px">开启后只显示 x0 的免费模型，不消耗高级请求额度</n-text>
        </n-space>

        <n-descriptions :column="2" label-placement="left" bordered size="small">
          <n-descriptions-item label="免费模型工具轮次">
            <n-input-number
              v-model:value="studioConfig.freeToolRounds"
              :min="1" :max="100" size="small" style="width: 100px"
            />
          </n-descriptions-item>
          <n-descriptions-item label="付费模型工具轮次">
            <n-input-number
              v-model:value="studioConfig.paidToolRounds"
              :min="1" :max="50" size="small" style="width: 100px"
            />
          </n-descriptions-item>
        </n-descriptions>
        <n-text depth="3" style="font-size: 11px">工具轮次 = AI 可查看代码的次数。免费模型多次调用不影响额度，付费模型每次都消耗高级请求。</n-text>

        <!-- 模型黑名单 -->
        <n-divider style="margin: 8px 0" />
        <n-text strong style="font-size: 13px">  模型黑名单</n-text>
        <n-text depth="3" style="font-size: 11px">匹配到关键词的模型不会出现在选择列表中 (模糊匹配，不区分大小写)</n-text>
        <n-space :size="4" :wrap="true">
          <n-tag
            v-for="item in studioConfig.modelBlacklist" :key="item"
            closable size="small" type="error"
            @close="studioConfig.removeFromBlacklist(item)"
          >
            {{ item }}
          </n-tag>
        </n-space>
        <n-space>
          <n-input
            v-model:value="blacklistInput"
            placeholder="输入模型名关键词..."
            size="small" style="width: 200px"
            @keydown.enter="addBlacklist"
          />
          <n-button size="small" @click="addBlacklist">添加</n-button>
        </n-space>
      </n-space>
      </div>
    </n-card>

    <!-- 补充模型配置 (DB 管理) -->
    <n-card size="small" style="background: #16213e">
      <template #header>
        <n-space align="center" :size="8" @click="toggleSection('custom')" style="cursor: pointer; user-select: none">
          <n-icon :component="sectionOpen.custom ? ChevronDown : ChevronForward" :size="16" />
          <span>📦 补充模型列表</span>
        </n-space>
      </template>
      <template #header-extra>
        <n-space :size="4" align="center">
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-switch
                v-model:value="studioConfig.customModelsEnabled"
                size="small"
                :rail-style="({ checked }: { checked: boolean }) => checked ? { background: '#18a058' } : { background: '#d03050' }"
              />
            </template>
            {{ studioConfig.customModelsEnabled ? '补充模型已启用 (点击全局禁用)' : '补充模型已全局禁用 (点击启用)' }}
          </n-tooltip>
          <n-button size="tiny" @click.stop="showAddModelModal = true" type="primary">+ 添加模型</n-button>
          <n-popconfirm @positive-click="resetCustomModels">
            <template #trigger>
              <n-button size="tiny" type="warning" ghost>🔄 重置为默认</n-button>
            </template>
            确定要清空所有自定义模型并恢复默认列表吗？
          </n-popconfirm>
        </n-space>
      </template>

      <div v-show="sectionOpen.custom">
      <n-alert v-if="!studioConfig.customModelsEnabled" type="warning" :bordered="false" style="margin-bottom: 8px; font-size: 12px">
        ⚠️ 补充模型已全局禁用。开启右上角总开关后，下方已启用的模型才会出现在模型选择列表中。
      </n-alert>
      <n-text depth="3" style="font-size: 11px; display: block; margin-bottom: 8px">
        补充 GitHub Models API 不返回但实际可用的模型, 以及 Copilot 专属模型的回退列表。
      </n-text>

      <n-space align="center" style="margin-bottom: 8px" :size="8">
        <n-input
          v-model:value="customModelSearch"
          placeholder="搜索模型名..."
          size="small" style="width: 180px" clearable
        />
        <n-select
          v-model:value="customModelBackendFilter"
          :options="[{label:'全部', value:''}, {label:'Models API', value:'models'}, {label:'Copilot API', value:'copilot'}]"
          size="small" style="width: 130px" placeholder="后端"
        />
      </n-space>

      <n-spin :show="loadingCustomModels">
        <n-data-table
          v-if="filteredCustomModels.length"
          :columns="customModelColumns"
          :data="filteredCustomModels"
          size="small"
          :max-height="350"
          :scroll-x="800"
          :row-class-name="(row: any) => !studioConfig.customModelsEnabled ? 'custom-model-disabled' : ''"
        />
        <n-empty v-else description="暂无自定义模型" />
      </n-spin>
      </div>
    </n-card>

    <!-- 模型能力管理 -->
    <n-card size="small" style="background: #16213e">
      <template #header>
        <n-space align="center" :size="8" @click="toggleSection('caps')" style="cursor: pointer; user-select: none">
          <n-icon :component="sectionOpen.caps ? ChevronDown : ChevronForward" :size="16" />
          <span>📊 模型能力管理</span>
        </n-space>
      </template>
      <template #header-extra>
        <n-space :size="4">
          <n-popconfirm @positive-click="resetAllCapabilities">
            <template #trigger>
              <n-button size="tiny" type="warning" ghost>🔄 清除所有覆盖</n-button>
            </template>
            确定要清除所有手动覆盖的能力设置吗？将恢复为自动检测值。
          </n-popconfirm>
        </n-space>
      </template>
      <div v-show="sectionOpen.caps">
      <n-text depth="3" style="font-size: 11px; display: block; margin-bottom: 8px">
        模型的上下文窗口和能力数据。蓝色背景表示有手动覆盖。
        点击数值可编辑, 点击能力图标可切换。修改会即时持久化到数据库。
      </n-text>
      <n-alert type="info" :bordered="false" style="margin-bottom: 8px; font-size: 12px">
        <n-space align="center" :size="4" :wrap="false">
          <span>💡 定价倍率 (x0 / x1 / x10 等) 来自
          <n-button text tag="a" href="https://docs.github.com/en/copilot/concepts/billing/copilot-requests#model-multipliers" target="_blank" size="tiny" type="info">
            GitHub 官方文档
          </n-button>
          的硬编码映射表，非 API 实时获取。</span>
          <n-button size="tiny" type="primary" ghost @click="handleRefreshPricing" :loading="loadingPricing">
            🔄 刷新定价
          </n-button>
        </n-space>
      </n-alert>

      <n-space align="center" style="margin-bottom: 8px" :size="8" :wrap="true">
        <n-input
          v-model:value="capSearch"
          placeholder="搜索模型名..."
          size="small" style="width: 160px" clearable
        />
        <n-select
          v-model:value="capSourceFilter"
          :options="sourceFilterOptions"
          size="small" style="width: 130px" placeholder="来源"
        />
        <n-select
          v-model:value="capCompanyFilter"
          :options="companyFilterOptions"
          size="small" style="width: 130px" placeholder="厂商"
        />
        <n-select
          v-model:value="capPricingFilter"
          :options="pricingFilterOptions"
          size="small" style="width: 130px" placeholder="定价"
        />
        <n-button size="small" @click="fetchMergedCapabilities" :loading="loadingMerged">
          🔄 刷新
        </n-button>
        <n-button size="small" type="info" :ghost="!studioConfig.docModelsOnly" @click="studioConfig.docModelsOnly = !studioConfig.docModelsOnly">
          {{ studioConfig.docModelsOnly ? '✅ 只用官方推荐模型' : '只用官方推荐模型' }}
        </n-button>
      </n-space>

      <n-spin :show="loadingMerged">
        <n-data-table
          v-if="filteredMerged.length"
          :columns="mergedColumns"
          :data="filteredMerged"
          size="small"
          :max-height="500"
          :scroll-x="900"
          :row-class-name="mergedRowClass"
        />
        <n-empty v-else description="加载中..." />
      </n-spin>
      </div>
    </n-card>

    <!-- 添加模型对话框 -->
    <n-modal v-model:show="showAddModelModal" preset="card" title="添加补充模型" style="width: 500px">
      <n-space vertical :size="12">
        <n-input v-model:value="newModel.name" placeholder="模型名 (用于 API 调用, 如 gpt-5)" size="small" />
        <n-input v-model:value="newModel.friendly_name" placeholder="显示名 (如 GPT-5)" size="small" />
        <n-space :size="8">
          <n-select
            v-model:value="newModel.model_family"
            :options="[
              {label:'openai', value:'openai'}, {label:'anthropic', value:'anthropic'},
              {label:'google', value:'google'}, {label:'deepseek', value:'deepseek'},
              {label:'mistralai', value:'mistralai'}, {label:'meta', value:'meta'},
              {label:'microsoft', value:'microsoft'}, {label:'xai', value:'xai'},
              {label:'cohere', value:'cohere'},
            ]"
            size="small" style="width: 150px" placeholder="厂商"
          />
          <n-select
            v-model:value="newModel.api_backend"
            :options="[{label:'Models API', value:'models'}, {label:'Copilot API', value:'copilot'}]"
            size="small" style="width: 150px" placeholder="API 后端"
          />
        </n-space>
        <n-select
          v-model:value="newModel.tags" multiple
          :options="[
            {label:'reasoning', value:'reasoning'}, {label:'agents', value:'agents'},
            {label:'multimodal', value:'multimodal'}, {label:'multipurpose', value:'multipurpose'},
            {label:'vision', value:'vision'}, {label:'conversation', value:'conversation'},
          ]"
          size="small" placeholder="能力标签"
        />
        <n-input v-model:value="newModel.summary" placeholder="简介" size="small" type="textarea" :rows="2" />
        <n-button type="primary" size="small" @click="addCustomModel" block>确认添加</n-button>
      </n-space>
    </n-modal>

    <!-- 定价变化确认对话框 -->
    <n-modal v-model:show="showPricingDiffModal" preset="card" title="📊 定价变化确认" style="width: 850px">
      <n-alert v-if="pricingDiff.length === 0" type="success" :bordered="false">
        ✅ 定价已是最新，与 GitHub 官方文档一致，无需更新。
      </n-alert>
      <template v-else>
        <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 12px">
          从 GitHub 官方文档检测到以下定价变化，确认后将更新运行时定价表 (重启后恢复为代码默认值)：
        </n-text>
        <n-data-table
          :columns="pricingDiffColumns"
          :data="pricingDiff"
          size="small"
          :max-height="400"
        />
        <n-space justify="end" style="margin-top: 12px">
          <n-button size="small" @click="showPricingDiffModal = false">取消</n-button>
          <n-button size="small" type="primary" @click="applyPricingChanges" :loading="applyingPricing">
            确认应用 ({{ pricingDiff.length }} 项变更)
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </n-space>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted } from 'vue'
import { useMessage, NInputNumber, NTag, NSpace, NText, NButton, NSwitch, NPopconfirm, NIcon } from 'naive-ui'
import { ChevronDown, ChevronForward } from '@vicons/ionicons5'
import { modelApi, modelConfigApi } from '@/api'
import { useStudioConfigStore } from '@/stores/studioConfig'

const message = useMessage()
const studioConfig = useStudioConfigStore()

// ==================== 折叠/展开 ====================
const sectionOpen = reactive({
  config: true,
  custom: true,
  caps: true,
})

function toggleSection(key: keyof typeof sectionOpen) {
  sectionOpen[key] = !sectionOpen[key]
}

const blacklistInput = ref('')
function addBlacklist() {
  if (blacklistInput.value.trim()) {
    studioConfig.addToBlacklist(blacklistInput.value)
    blacklistInput.value = ''
  }
}

// ==================== 补充模型管理 ====================
const customModels = ref<any[]>([])
const loadingCustomModels = ref(false)
const customModelSearch = ref('')
const customModelBackendFilter = ref('')
const showAddModelModal = ref(false)

const filteredCustomModels = computed(() => {
  let list = customModels.value
  if (customModelBackendFilter.value) {
    list = list.filter((m: any) => m.api_backend === customModelBackendFilter.value)
  }
  if (customModelSearch.value) {
    const q = customModelSearch.value.toLowerCase()
    list = list.filter((m: any) =>
      m.name.toLowerCase().includes(q) ||
      m.friendly_name.toLowerCase().includes(q) ||
      m.model_family.toLowerCase().includes(q)
    )
  }
  return list
})

async function fetchCustomModels() {
  loadingCustomModels.value = true
  try {
    const { data } = await modelConfigApi.listModels()
    customModels.value = data
  } catch {}
  finally { loadingCustomModels.value = false }
}

async function toggleCustomModelEnabled(row: any) {
  try {
    await modelConfigApi.updateModel(row.id, { enabled: !row.enabled })
    row.enabled = !row.enabled
    await modelApi.refresh()
  } catch (e: any) {
    message.error('更新失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteCustomModel(row: any) {
  try {
    await modelConfigApi.deleteModel(row.id)
    await fetchCustomModels()
    await modelApi.refresh()
    message.success(`已删除 ${row.name}`)
  } catch (e: any) {
    message.error('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function resetCustomModels() {
  try {
    await modelConfigApi.resetModels()
    await fetchCustomModels()
    await modelApi.refresh()
    message.success('已重置为默认模型列表')
  } catch (e: any) {
    message.error('重置失败: ' + (e.response?.data?.detail || e.message))
  }
}

const newModel = ref({
  name: '', friendly_name: '', model_family: 'openai',
  tags: [] as string[], summary: '', api_backend: 'models',
})
async function addCustomModel() {
  if (!newModel.value.name.trim()) { message.warning('请输入模型名'); return }
  try {
    await modelConfigApi.createModel(newModel.value)
    newModel.value = { name: '', friendly_name: '', model_family: 'openai', tags: [], summary: '', api_backend: 'models' }
    showAddModelModal.value = false
    await fetchCustomModels()
    await modelApi.refresh()
    message.success('模型已添加')
  } catch (e: any) {
    message.error('添加失败: ' + (e.response?.data?.detail || e.message))
  }
}

const customModelColumns = [
  {
    title: '模型名',
    key: 'name',
    width: 200,
    ellipsis: { tooltip: true },
    render(row: any) {
      return h(NText, { style: 'font-size:12px;font-family:monospace' }, () => row.name)
    },
  },
  {
    title: '显示名',
    key: 'friendly_name',
    width: 150,
    ellipsis: { tooltip: true },
  },
  {
    title: '厂商',
    key: 'model_family',
    width: 80,
    render(row: any) {
      return h(NText, { depth: 3, style: 'font-size:11px' }, () => row.model_family)
    },
  },
  {
    title: '后端',
    key: 'api_backend',
    width: 70,
    render(row: any) {
      const icon = row.api_backend === 'copilot' ? '☁️' : '🔗'
      return h(NTag, { size: 'tiny', bordered: false }, () => icon + ' ' + row.api_backend)
    },
  },
  {
    title: 'Tags',
    key: 'tags',
    width: 140,
    render(row: any) {
      return h(NSpace, { size: 2 }, () =>
        (row.tags || []).map((t: string) =>
          h(NTag, { size: 'tiny', bordered: false, type: tagColor(t) as any }, () => t)
        )
      )
    },
  },
  {
    title: '启用',
    key: 'enabled',
    width: 60,
    render(row: any) {
      return h(NSwitch, {
        size: 'small',
        value: row.enabled,
        'onUpdate:value': () => toggleCustomModelEnabled(row),
      })
    },
  },
  {
    title: '来源',
    key: 'is_seed',
    width: 60,
    render(row: any) {
      return h(NTag, { size: 'tiny', bordered: false, type: row.is_seed ? 'default' : 'info' },
        () => row.is_seed ? '内置' : '自建')
    },
  },
  {
    title: '',
    key: 'actions',
    width: 50,
    render(row: any) {
      return h(NPopconfirm, {
        onPositiveClick: () => deleteCustomModel(row),
      }, {
        trigger: () => h(NButton, { size: 'tiny', type: 'error', quaternary: true }, () => '🗑'),
        default: () => `确定删除 ${row.name}？`,
      })
    },
  },
]

function tagColor(tag: string): string {
  if (tag === 'reasoning') return 'warning'
  if (tag === 'agents' || tag === 'tools') return 'success'
  if (tag === 'multimodal' || tag === 'vision') return 'info'
  return 'default'
}


// ==================== 模型能力管理 ====================
const mergedData = ref<any[]>([])
const loadingMerged = ref(false)
const capSearch = ref('')
const capSourceFilter = ref('')
const capCompanyFilter = ref('')
const capPricingFilter = ref('')
const docModelSet = ref<Set<string>>(new Set())

function classifyFamily(model: any): string {
  const n = String(model.id || model.name || '').replace(/^copilot:/, '').toLowerCase()
  if (n.includes('claude') || n.includes('anthropic')) return 'Anthropic'
  if (n.includes('gpt') || n.startsWith('o1') || n.startsWith('o3') || n.startsWith('o4')) return 'OpenAI'
  if (n.includes('gemini') || n.includes('google')) return 'Google'
  if (n.includes('deepseek')) return 'DeepSeek'
  if (n.includes('mistral')) return 'Mistral AI'
  if (n.includes('meta')) return 'Meta'
  if (n.includes('microsoft')) return 'Microsoft'
  if (n.includes('cohere')) return 'Cohere'
  if (n.includes('xai')) return 'xAI'
  return model.publisher || '其它'
}

const sourceFilterOptions = [
  { label: '全部来源', value: '' },
  { label: '☁️ Copilot', value: 'copilot' },
  { label: '🔗 GitHub Models', value: 'models' },
  { label: '📦 补充', value: 'custom' },
]

const companyFilterOptions = computed(() => {
  const companies = new Set(mergedData.value.map((m: any) => classifyFamily(m)).filter(Boolean))
  const opts: { label: string; value: string }[] = [{ label: '全部厂商', value: '' }]
  for (const c of [...companies].sort()) {
    opts.push({ label: c, value: c })
  }
  return opts
})

const pricingFilterOptions = [
  { label: '全部定价', value: '' },
  { label: '🆓 免费 (x0)', value: 'free' },
  { label: '💰 收费 (x>0)', value: 'premium' },
]

const filteredMerged = computed(() => {
  let list = mergedData.value
  if (studioConfig.docModelsOnly && docModelSet.value.size > 0) {
    list = list.filter((m: any) =>
      m.api_backend !== 'copilot' ||
      docModelSet.value.has(String(m.id || m.name).replace(/^copilot:/, '').toLowerCase())
    )
  }
  if (capSourceFilter.value) {
    if (capSourceFilter.value === 'custom') {
      list = list.filter((m: any) => m.is_custom)
    } else {
      list = list.filter((m: any) => m.api_backend === capSourceFilter.value && !m.is_custom)
    }
  }
  if (capCompanyFilter.value) {
    list = list.filter((m: any) => classifyFamily(m) === capCompanyFilter.value)
  }
  if (capPricingFilter.value) {
    const pf = capPricingFilter.value
    if (pf === 'free') {
      list = list.filter((m: any) => m.premium_multiplier === 0)
    } else if (pf === 'premium') {
      list = list.filter((m: any) => m.premium_multiplier > 0)
    }
  }
  if (capSearch.value) {
    const q = capSearch.value.toLowerCase()
    list = list.filter((m: any) =>
      m.name.toLowerCase().includes(q) ||
      m.id.toLowerCase().includes(q) ||
      classifyFamily(m).toLowerCase().includes(q)
    )
  }
  return list
})

async function fetchMergedCapabilities() {
  loadingMerged.value = true
  try {
    const { data } = await modelConfigApi.getMerged()
    mergedData.value = data
  } catch {}
  finally { loadingMerged.value = false }
}

function fmtTokens(n: number): string {
  if (!n) return '-'
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`
  return `${n}`
}

async function updateCapOverride(row: any, field: string, val: any) {
  try {
    await modelConfigApi.upsertCapability(row.id, { [field]: val })
    await fetchMergedCapabilities()
  } catch (e: any) {
    message.error('更新失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function resetSingleCapability(row: any) {
  const clean = row.id.replace(/^copilot:/, '').toLowerCase()
  try {
    await modelConfigApi.deleteCapability(clean)
    await fetchMergedCapabilities()
    message.success(`已重置 ${row.name}`)
  } catch (e: any) {
    if (e.response?.status === 404) {
      message.info('该模型没有覆盖记录')
    } else {
      message.error('重置失败')
    }
  }
}

async function resetAllCapabilities() {
  try {
    await modelConfigApi.resetAllCapabilities()
    await fetchMergedCapabilities()
    message.success('所有能力覆盖已清除')
  } catch (e: any) {
    message.error('重置失败')
  }
}

function mergedRowClass(row: any) {
  return row.has_override ? 'cap-row-override' : ''
}

// ==================== 定价刷新 ====================
const loadingPricing = ref(false)
const applyingPricing = ref(false)
const showPricingDiffModal = ref(false)
const pricingDiff = ref<any[]>([])
const scrapedPricing = ref<Record<string, any>>({})

async function handleRefreshPricing() {
  loadingPricing.value = true
  try {
    const { data } = await modelApi.refreshPricing()
    pricingDiff.value = data.changes || []
    scrapedPricing.value = data.scraped || {}
    const docIds = Object.keys(scrapedPricing.value || {}).map((k: string) => k.toLowerCase())
    docModelSet.value = new Set(docIds)
    studioConfig.setDocModels(docIds)
    showPricingDiffModal.value = true
    if (pricingDiff.value.length === 0) {
      message.success(`定价已是最新 (共 ${data.scraped_count} 个模型)`)
    } else {
      message.info(`检测到 ${pricingDiff.value.length} 项定价变化`)
    }
  } catch (e: any) {
    message.error('刷新定价失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loadingPricing.value = false
  }
}

async function applyPricingChanges() {
  applyingPricing.value = true
  try {
    await modelApi.applyPricing(scrapedPricing.value)
    showPricingDiffModal.value = false
    message.success('定价表已更新，正在刷新模型数据...')
    await fetchMergedCapabilities()
  } catch (e: any) {
    message.error('应用定价失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    applyingPricing.value = false
  }
}

const pricingDiffColumns = [
  {
    title: '模型',
    key: 'model',
    width: 180,
    ellipsis: { tooltip: true },
    render(row: any) {
      return h(NText, { style: 'font-size:12px;font-family:monospace' }, () => row.model)
    },
  },
  {
    title: '类型',
    key: 'type',
    width: 70,
    render(row: any) {
      const map: Record<string, { type: string; label: string }> = {
        changed: { type: 'warning', label: '变更' },
        added: { type: 'success', label: '新增' },
        removed: { type: 'error', label: '移除' },
      }
      const m = map[row.type] || { type: 'default', label: row.type }
      return h(NTag, { size: 'tiny', type: m.type as any, bordered: false }, () => m.label)
    },
  },
  {
    title: '付费(旧)',
    key: 'old_paid',
    width: 75,
    render(row: any) {
      if (row.old_paid == null) return h(NText, { depth: 3 }, () => '-')
      const color = row.old_paid === 0 ? '#18a058' : '#f0a020'
      return h(NText, { style: `color:${color};font-weight:bold` }, () => `x${row.old_paid}`)
    },
  },
  {
    title: '→',
    key: 'arrow1',
    width: 25,
    render() { return h(NText, { depth: 3 }, () => '→') },
  },
  {
    title: '付费(新)',
    key: 'new_paid',
    width: 75,
    render(row: any) {
      if (row.new_paid == null) return h(NText, { depth: 3 }, () => '-')
      const color = row.new_paid === 0 ? '#18a058' : '#f0a020'
      return h(NText, { style: `color:${color};font-weight:bold` }, () => `x${row.new_paid}`)
    },
  },
  {
    title: '免费(旧)',
    key: 'old_free',
    width: 75,
    render(row: any) {
      if (row.old_free == null) return h(NTag, { size: 'tiny', type: 'error', bordered: false }, () => '需订阅')
      return h(NTag, { size: 'tiny', type: 'success', bordered: false }, () => `x${row.old_free}`)
    },
  },
  {
    title: '→',
    key: 'arrow2',
    width: 25,
    render() { return h(NText, { depth: 3 }, () => '→') },
  },
  {
    title: '免费(新)',
    key: 'new_free',
    width: 75,
    render(row: any) {
      if (row.new_free == null) return h(NTag, { size: 'tiny', type: 'error', bordered: false }, () => '需订阅')
      return h(NTag, { size: 'tiny', type: 'success', bordered: false }, () => `x${row.new_free}`)
    },
  },
  {
    title: '说明',
    key: 'note',
    ellipsis: { tooltip: true },
    render(row: any) {
      return h(NText, { depth: 3, style: 'font-size:11px' }, () => row.note)
    },
  },
]

const mergedColumns = [
  {
    title: '模型',
    key: 'name',
    width: 180,
    fixed: 'left' as const,
    ellipsis: { tooltip: true },
    render(row: any) {
      const backend = row.api_backend === 'copilot' ? ' ☁️' : ''
      return h(NText, { style: 'font-size:12px' }, () => row.name + backend)
    },
  },
  {
    title: '输入窗口',
    key: 'eff_max_input',
    width: 120,
    render(row: any) {
      return h(NInputNumber, {
        value: row.eff_max_input,
        size: 'tiny',
        min: 0,
        step: 1000,
        style: 'width:100px',
        'onUpdate:value': (val: number | null) => {
          if (val != null) {
            updateCapOverride(row, 'max_input_tokens', val)
          }
        },
      })
    },
  },
  {
    title: '输出',
    key: 'eff_max_output',
    width: 120,
    render(row: any) {
      return h(NInputNumber, {
        value: row.eff_max_output,
        size: 'tiny',
        min: 0,
        step: 100,
        style: 'width:100px',
        'onUpdate:value': (val: number | null) => {
          if (val != null) {
            updateCapOverride(row, 'max_output_tokens', val)
          }
        },
      })
    },
  },
  {
    title: '定价',
    key: 'pricing_note',
    width: 80,
    render(row: any) {
      const color = row.premium_multiplier === 0 ? '#18a058' : '#f0a020'
      const text = row.premium_multiplier === 0 ? 'x0' : `x${row.premium_multiplier}`
      return h(NTag, { size: 'tiny', bordered: false, style: `color:${color}` }, () => text)
    },
  },
  {
    title: '👁️ 视觉',
    key: 'eff_supports_vision',
    width: 65,
    render(row: any) {
      return h(NSwitch, {
        size: 'small',
        value: row.eff_supports_vision,
        'onUpdate:value': (val: boolean) => updateCapOverride(row, 'supports_vision', val),
      })
    },
  },
  {
    title: '🔧 工具',
    key: 'eff_supports_tools',
    width: 65,
    render(row: any) {
      return h(NSwitch, {
        size: 'small',
        value: row.eff_supports_tools,
        'onUpdate:value': (val: boolean) => updateCapOverride(row, 'supports_tools', val),
      })
    },
  },
  {
    title: '🧠 推理',
    key: 'eff_is_reasoning',
    width: 65,
    render(row: any) {
      return h(NSwitch, {
        size: 'small',
        value: row.eff_is_reasoning,
        'onUpdate:value': (val: boolean) => updateCapOverride(row, 'is_reasoning', val),
      })
    },
  },
  {
    title: '',
    key: 'actions',
    width: 50,
    render(row: any) {
      if (!row.has_override) return null
      return h(NButton, {
        size: 'tiny',
        quaternary: true,
        onClick: () => resetSingleCapability(row),
      }, () => '↩️')
    },
  },
]

onMounted(() => {
  docModelSet.value = new Set((studioConfig.docModelIds || []).map((k: string) => k.toLowerCase()))
  fetchCustomModels()
  fetchMergedCapabilities()
})
</script>

<style>
.cap-row-override td {
  background: rgba(64, 152, 252, 0.08) !important;
}
.custom-model-disabled td {
  opacity: 0.45;
}
</style>
