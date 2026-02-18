<template>
  <div>
    <!-- 模型选择与控制 -->
    <n-space align="center" style="margin-bottom: 16px" :wrap="true">
      <n-radio-group v-model:value="modelSourceFilter" size="small">
        <n-radio-button v-for="f in providerFilters" :key="f.value" :value="f.value">
          <span style="display:inline-flex;align-items:center;gap:3px">
            <span v-if="f.icon" v-html="f.icon"></span>
            <span>{{ f.label }}</span>
          </span>
        </n-radio-button>
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
import { getProviderIcon } from '@/utils/providerIcons'
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
const modelSourceFilter = ref('all')

const providerFilters = computed(() => {
  const filters: Array<{value: string; label: string; icon: string}> = [
    { value: 'all', label: '全部', icon: '' },
    { value: 'github', label: 'GitHub', icon: getProviderIcon('github', 'G', 12) },
  ]
  if (models.value.some(m => m.api_backend === 'copilot')) {
    filters.push({ value: 'copilot', label: 'Copilot', icon: getProviderIcon('copilot', 'C', 12) })
  }
  const seen = new Set<string>()
  for (const m of models.value) {
    const slug = m.provider_slug || ''
    if (slug && slug !== 'github' && slug !== 'copilot' && !seen.has(slug)) {
      seen.add(slug)
      filters.push({ value: slug, label: m.publisher || slug, icon: getProviderIcon(slug, m.publisher || slug, 12) })
    }
  }
  if (studioConfig.customModelsEnabled) {
    filters.push({ value: 'custom', label: '补充', icon: '' })
  }
  return filters
})

const repoName = 'macaulishchina/GoldenNest'

const modelOptions = computed(() => {
  const byCategory = models.value.filter(m => m.category === 'implementation' || m.category === 'both')
  const filtered = modelSourceFilter.value === 'all'
    ? byCategory
    : modelSourceFilter.value === 'custom'
      ? byCategory.filter(m => m.is_custom)
      : modelSourceFilter.value === 'github'
        ? byCategory.filter(m => m.provider_slug === 'github' || (!m.provider_slug && m.api_backend === 'models'))
        : modelSourceFilter.value === 'copilot'
          ? byCategory.filter(m => m.provider_slug === 'copilot' || m.api_backend === 'copilot')
          : byCategory.filter(m => m.provider_slug === modelSourceFilter.value)

  // 保留 API 返回顺序, 按 model_family 分组
  const mapOpt = (m: any) => ({
    label: m.name, value: m.id,
    supports_vision: m.supports_vision, supports_tools: m.supports_tools,
    is_reasoning: m.is_reasoning, api_backend: m.api_backend,
    is_custom: m.is_custom,
    provider_slug: m.provider_slug || (m.api_backend === 'copilot' ? 'copilot' : 'github'),
    pricing_tier: m.pricing_tier, premium_multiplier: m.premium_multiplier,
    is_deprecated: m.is_deprecated, pricing_note: m.pricing_note,
  })
  const groups: Array<{ key: string; label: string; slug: string; items: any[] }> = []
  const groupMap: Record<string, typeof groups[0]> = {}
  for (const m of filtered) {
    const family = m.model_family || m.publisher || m.provider_slug || 'Other'
    const slug = m.provider_slug || (m.api_backend === 'copilot' ? 'copilot' : 'github')
    const gKey = slug + ':' + family
    if (!groupMap[gKey]) {
      const g = { key: gKey, label: family, slug, items: [] as any[] }
      groups.push(g)
      groupMap[gKey] = g
    }
    groupMap[gKey].items.push(m)
  }
  return groups.map(g => ({
    type: 'group', label: g.label, key: g.key, provider_slug: g.slug,
    children: g.items.map(mapOpt),
  }))
})

function renderModelLabel(option: any, selected: boolean) {
  if (option.type === 'group') {
    const iconHtml = getProviderIcon(option.provider_slug || 'github', option.label, 14)
    return h('span', { style: 'display:inline-flex;align-items:center;gap:4px' }, [
      h('span', { innerHTML: iconHtml, style: 'display:inline-flex' }),
      option.label,
    ])
  }
  const caps: string[] = []
  if (option.is_reasoning) caps.push('🧠')
  if (option.supports_vision) caps.push('👁️')
  if (option.supports_tools) caps.push('🔧')
  const depStr = option.is_deprecated ? ' ⚠️' : ''
  const capStr = caps.length ? ` ${caps.join('')}` : ''
  const iconHtml = getProviderIcon(option.provider_slug || 'github', '', 12)
  const iconVNode = h('span', { innerHTML: iconHtml, style: 'display:inline-flex;vertical-align:middle;margin:0 2px' })
  const customStr = option.is_custom ? ' 🧩' : ''
  const priceText = option.pricing_note || 'x0'
  const nameStyle = selected ? 'font-weight:600' : ''
  const priceStyle = selected
    ? 'color:#18a058;font-size:11px;flex-shrink:0;margin-left:12px;font-weight:600'
    : 'color:#888;font-size:11px;flex-shrink:0;margin-left:12px'
  return h('div', { style: 'display:flex;justify-content:space-between;align-items:center;width:100%' }, [
    h('span', { style: nameStyle }, [selected ? '● ' : '', option.label as string, ' ', iconVNode, customStr, capStr, depStr]),
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
