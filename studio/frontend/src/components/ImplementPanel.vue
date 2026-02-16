<template>
  <div>
    <!-- 模型选择与控制 -->
    <n-space align="center" style="margin-bottom: 16px" :wrap="true">
      <n-radio-group v-model:value="modelSourceFilter" size="small">
        <n-radio-button value="all">全部</n-radio-button>
        <n-radio-button value="models">Models</n-radio-button>
        <n-radio-button value="copilot">Copilot ☁️</n-radio-button>
      </n-radio-group>
      <n-select
        v-model:value="implModel"
        :options="modelOptions"
        :render-label="renderModelLabel"
        size="small"
        style="width: 260px"
        filterable
        @update:value="handleModelChange"
      />
      <n-tag v-if="studioConfig.docModelsOnly" size="tiny" type="info" :bordered="false">📄 文档模型</n-tag>
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary @click="refreshModels" :loading="loadingModels">
            🔄
          </n-button>
        </template>
        刷新模型列表
      </n-tooltip>
      <n-button
        type="primary"
        @click="handleStartImplementation"
        :loading="starting"
        :disabled="!project.plan_content || project.status === 'implementing'"
      >
        🚀 发起实施
      </n-button>
      <n-button @click="refreshStatus" :loading="polling" size="small">
        🔄 刷新状态
      </n-button>
    </n-space>

    <!-- 进度面板 -->
    <n-card style="background: #16213e; margin-bottom: 16px">
      <n-steps :current="implStep" size="small">
        <n-step title="创建 Issue" :status="stepStatus(1)" />
        <n-step title="Agent 编码" :status="stepStatus(2)" />
        <n-step title="PR 创建" :status="stepStatus(3)" />
        <n-step title="Review" :status="stepStatus(4)" />
      </n-steps>
    </n-card>

    <!-- 状态详情 -->
    <n-card v-if="implStatus" style="background: #16213e; margin-bottom: 16px">
      <n-descriptions :column="2" label-placement="left" bordered size="small">
        <n-descriptions-item label="状态">
          <n-tag :type="implStatusType" size="small">{{ implStatusText }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="Issue" v-if="implStatus.github_issue_number">
          <n-button text tag="a" :href="`https://github.com/${repoName}/issues/${implStatus.github_issue_number}`" target="_blank">
            #{{ implStatus.github_issue_number }}
          </n-button>
        </n-descriptions-item>
        <n-descriptions-item label="PR" v-if="implStatus.github_pr_number">
          <n-button text tag="a" :href="implStatus.pr_url" target="_blank">
            #{{ implStatus.github_pr_number }} - {{ implStatus.pr_title }}
          </n-button>
        </n-descriptions-item>
        <n-descriptions-item label="分支" v-if="implStatus.branch_name">
          <n-tag size="small" :bordered="false">{{ implStatus.branch_name }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="变更文件" v-if="implStatus.pr_files_changed">
          {{ implStatus.pr_files_changed }} 个文件
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <!-- PR Diff 查看 -->
    <n-card v-if="implStatus?.github_pr_number" title="📝 PR Diff" style="background: #16213e">
      <template #header-extra>
        <n-button size="small" @click="loadDiff" :loading="loadingDiff">查看 Diff</n-button>
      </template>

      <div v-if="diffData">
        <n-collapse>
          <n-collapse-item
            v-for="f in diffData.files"
            :key="f.filename"
            :title="`${f.status === 'added' ? '🟢' : f.status === 'removed' ? '🔴' : '🟡'} ${f.filename}`"
            :name="f.filename"
          >
            <template #header-extra>
              <n-text depth="3" style="font-size: 12px">
                +{{ f.additions }} -{{ f.deletions }}
              </n-text>
            </template>
            <pre style="background: #0d1b2a; padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 12px; white-space: pre-wrap">{{ f.patch }}</pre>
          </n-collapse-item>
        </n-collapse>
      </div>

      <n-empty v-else-if="!loadingDiff" description="点击「查看 Diff」加载变更" />
    </n-card>

    <!-- 操作按钮 -->
    <n-space v-if="implStatus?.github_pr_number && implStatus.pr_state === 'open'" style="margin-top: 16px">
      <n-button type="success" @click="handleApprovePR" :loading="approving">
        ✅ 通过并合并 PR
      </n-button>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import { implementationApi, modelApi, projectApi } from '@/api'
import { useStudioConfigStore } from '@/stores/studioConfig'
import type { Project } from '@/stores/project'

const props = defineProps<{ project: Project }>()
const emit = defineEmits(['status-changed'])
const message = useMessage()
const studioConfig = useStudioConfigStore()

const implStatus = ref<any>(null)
const implModel = ref(props.project.implementation_model || 'claude-sonnet-4-20250514')
const starting = ref(false)
const polling = ref(false)
const loadingDiff = ref(false)
const approving = ref(false)
const diffData = ref<any>(null)
const models = ref<any[]>([])
let pollTimer: any = null
const loadingModels = ref(false)
const modelSourceFilter = ref<'all' | 'models' | 'copilot'>('all')

const repoName = 'macaulishchina/GoldenNest'

const modelOptions = computed(() => {
  const byCategory = models.value.filter(m => m.category === 'implementation' || m.category === 'both')
  const filtered = modelSourceFilter.value === 'all'
    ? byCategory
    : modelSourceFilter.value === 'copilot'
      ? byCategory.filter(m => m.api_backend === 'copilot')
      : byCategory.filter(m => m.api_backend !== 'copilot')

  const modelsApi = filtered.filter(m => m.api_backend !== 'copilot')
  const copilotApi = filtered.filter(m => m.api_backend === 'copilot')

  const classifyFamily = (m: any): string => {
    const n = String(m.id || m.name || '').replace(/^copilot:/, '').toLowerCase()
    if (n.includes('claude') || n.includes('anthropic')) return 'Anthropic'
    if (n.includes('gpt') || n.startsWith('o1') || n.startsWith('o3') || n.startsWith('o4')) return 'OpenAI'
    if (n.includes('gemini') || n.includes('google')) return 'Google'
    if (n.includes('deepseek')) return 'DeepSeek'
    if (n.includes('mistral')) return 'Mistral AI'
    if (n.includes('meta')) return 'Meta'
    if (n.includes('microsoft')) return 'Microsoft'
    if (n.includes('cohere')) return 'Cohere'
    if (n.includes('xai')) return 'xAI'
    return m.publisher || '其他'
  }

  const buildGroups = (list: any[], suffix: string = '') => {
    const groups: Record<string, any[]> = {}
    for (const m of list) {
      const pub = classifyFamily(m) + suffix
      if (!groups[pub]) groups[pub] = []
      groups[pub].push(m)
    }
    return groups
  }

  const mapOpt = (m: any) => ({
    label: m.name, value: m.id,
    supports_vision: m.supports_vision, supports_tools: m.supports_tools,
    is_reasoning: m.is_reasoning, api_backend: m.api_backend,
    pricing_tier: m.pricing_tier, premium_multiplier: m.premium_multiplier,
    is_deprecated: m.is_deprecated, pricing_note: m.pricing_note,
  })
  const options: any[] = []
  for (const [pub, items] of Object.entries(buildGroups(modelsApi))) {
    options.push({ type: 'group', label: pub, key: pub, children: items.map(mapOpt) })
  }
  if (copilotApi.length) {
    for (const [pub, items] of Object.entries(buildGroups(copilotApi, ' ☁️'))) {
      options.push({ type: 'group', label: pub, key: 'copilot-' + pub, children: items.map(mapOpt) })
    }
  }
  return options
})

function renderModelLabel(option: any, selected: boolean) {
  if (option.type === 'group') return option.label
  const caps: string[] = []
  if (option.is_reasoning) caps.push('🧠')
  if (option.supports_vision) caps.push('👁️')
  if (option.supports_tools) caps.push('🔧')
  const depStr = option.is_deprecated ? ' ⚠️' : ''
  const capStr = caps.length ? ` ${caps.join('')}` : ''
  const priceText = option.pricing_note || 'x0'
  const nameStyle = selected ? 'font-weight:600' : ''
  const priceStyle = selected
    ? 'color:#18a058;font-size:11px;flex-shrink:0;margin-left:12px;font-weight:600'
    : 'color:#888;font-size:11px;flex-shrink:0;margin-left:12px'
  return h('div', { style: 'display:flex;justify-content:space-between;align-items:center;width:100%' }, [
    h('span', { style: nameStyle }, [selected ? '● ' : '', option.label as string, capStr, depStr]),
    h('span', { style: priceStyle }, priceText),
  ])
}

async function refreshModels() {
  loadingModels.value = true
  try {
    await modelApi.refresh()
    const { data } = await modelApi.list({ category: 'implementation', custom_models: studioConfig.customModelsEnabled })
    models.value = data
    message.success(`已刷新，共 ${data.length} 个可用模型`)
  } catch (e: any) {
    message.error('刷新失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loadingModels.value = false
  }
}

const implStep = computed(() => {
  if (!implStatus.value) return 0
  const s = implStatus.value.status
  if (s === 'pr_merged') return 5
  if (s === 'pr_created') return 3
  if (s === 'agent_working') return 2
  if (s === 'issue_created') return 1
  return 0
})

const implStatusType = computed(() => {
  const m: Record<string, any> = {
    not_started: 'default', issue_created: 'info', agent_working: 'warning',
    pr_created: 'success', pr_merged: 'success',
  }
  return m[implStatus.value?.status] || 'default'
})

const implStatusText = computed(() => {
  const m: Record<string, string> = {
    not_started: '未开始', issue_created: 'Issue 已创建', agent_working: 'Agent 编码中...',
    pr_created: 'PR 已创建', pr_merged: 'PR 已合并',
  }
  return m[implStatus.value?.status] || ''
})

function stepStatus(step: number) {
  if (implStep.value > step) return 'finish'
  if (implStep.value === step) return 'process'
  return 'wait'
}

async function refreshStatus() {
  polling.value = true
  try {
    const { data } = await implementationApi.getStatus(props.project.id)
    implStatus.value = data
  } catch {}
  finally { polling.value = false }
}

async function handleStartImplementation() {
  starting.value = true
  try {
    const { data } = await implementationApi.start(props.project.id, {
      use_copilot_agent: true,
    })
    message.success(data.message)
    emit('status-changed')
    // 开始轮询
    startPolling()
    refreshStatus()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '发起实施失败')
  } finally {
    starting.value = false
  }
}

async function loadDiff() {
  loadingDiff.value = true
  try {
    const { data } = await implementationApi.getDiff(props.project.id)
    diffData.value = data
  } catch (e: any) {
    message.error(e.response?.data?.detail || '加载 Diff 失败')
  } finally {
    loadingDiff.value = false
  }
}

async function handleApprovePR() {
  approving.value = true
  try {
    const { data } = await implementationApi.approvePR(props.project.id)
    if (data.merged) {
      message.success('PR 已合并')
      emit('status-changed')
      refreshStatus()
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '合并失败')
  } finally {
    approving.value = false
  }
}

async function handleModelChange(val: string) {
  try { await projectApi.update(props.project.id, { implementation_model: val }) } catch {}
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    if (implStatus.value?.status === 'agent_working' || implStatus.value?.status === 'issue_created') {
      refreshStatus()
    } else {
      stopPolling()
    }
  }, 30000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(async () => {
  refreshStatus()
  // 加载模型列表 (使用后端缓存，不阻塞页面; 手动点击刷新按钮强制刷新)
  modelApi.list({ category: 'implementation', custom_models: studioConfig.customModelsEnabled }).then(({ data }) => {
    models.value = data
    if (data.length && !data.find((m: any) => m.id === implModel.value)) {
      implModel.value = data[0].id
    }
  }).catch(() => {})
  // 自动轮询
  if (['implementing', 'reviewing'].includes(props.project.status)) {
    startPolling()
  }
})

onUnmounted(() => stopPolling())
</script>
