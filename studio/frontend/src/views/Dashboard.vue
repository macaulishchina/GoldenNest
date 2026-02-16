<template>
  <div>
    <n-space vertical :size="24">
      <!-- 欢迎区 -->
      <n-card style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)">
        <n-space justify="space-between" align="center">
          <div>
            <n-h2 style="margin: 0; color: #e94560">🏗️ 设计院</n-h2>
            <n-text depth="3">AI 驱动的需求迭代平台 — 让想法变成现实</n-text>
          </div>
          <n-button type="primary" @click="showCreate = true" size="large">
            <template #icon><n-icon :component="AddOutline" /></template>
            新建需求
          </n-button>
        </n-space>
      </n-card>

      <!-- 统计卡片 -->
      <n-grid :cols="4" :x-gap="16" :y-gap="16">
        <n-gi>
          <n-card size="small" style="background: #16213e">
            <n-statistic label="进行中" :value="activeCount" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" style="background: #16213e">
            <n-statistic label="已部署" :value="deployedCount" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" style="background: #16213e">
            <n-statistic label="快照数" :value="snapshotCount" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" style="background: #16213e">
            <n-statistic label="总项目" :value="projects.length" />
          </n-card>
        </n-gi>
      </n-grid>

      <!-- 最近项目 -->
      <n-card title="📋 最近项目" size="small" style="background: #16213e">
        <n-list bordered v-if="projects.length">
          <n-list-item v-for="p in projects.slice(0, 8)" :key="p.id">
            <n-thing
              :title="p.title"
              :description="`${p.description.slice(0, 80)}${p.description.length > 80 ? '...' : ''}`"
              style="cursor: pointer"
              @click="$router.push(`/projects/${p.id}`)"
            >
              <template #header-extra>
                <n-space>
                  <n-tag :type="statusType(p.status)" size="small" round>
                    {{ statusLabel(p.status) }}
                  </n-tag>
                  <n-text depth="3" style="font-size: 12px">
                    {{ formatDate(p.updated_at) }}
                  </n-text>
                </n-space>
              </template>
            </n-thing>
          </n-list-item>
        </n-list>
        <n-empty v-else description="还没有项目，点击「新建需求」开始" />
      </n-card>
    </n-space>

    <!-- 新建项目对话框 -->
    <n-modal v-model:show="showCreate" preset="dialog" title="🆕 新建需求" style="width: 600px">
      <n-form :model="newProject" label-placement="left" label-width="80">
        <n-form-item label="需求标题">
          <n-input v-model:value="newProject.title" placeholder="简明描述需求目标" />
        </n-form-item>
        <n-form-item label="需求描述">
          <n-input
            v-model:value="newProject.description"
            type="textarea"
            :rows="4"
            placeholder="详细描述需求背景和期望效果..."
          />
        </n-form-item>
        <n-form-item label="讨论模型">
          <n-space vertical :size="8">
            <n-radio-group v-model:value="discussFilter" size="small">
              <n-radio-button value="all">全部</n-radio-button>
              <n-radio-button value="models">Models</n-radio-button>
              <n-radio-button value="copilot">Copilot ☁️</n-radio-button>
            </n-radio-group>
            <n-tag v-if="studioConfig.docModelsOnly" size="tiny" type="info" :bordered="false">📄 文档模型</n-tag>
            <n-select v-model:value="newProject.discussion_model" :options="modelOptions" filterable :render-label="renderModelLabel" />
          </n-space>
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="showCreate = false">取消</n-button>
        <n-button type="primary" @click="handleCreate" :loading="creating">创建并进入讨论</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { useProjectStore } from '@/stores/project'
import { useStudioConfigStore } from '@/stores/studioConfig'
import { snapshotApi, modelApi } from '@/api'

const router = useRouter()
const message = useMessage()
const store = useProjectStore()
const studioConfig = useStudioConfigStore()

const showCreate = ref(false)
const creating = ref(false)
const snapshotCount = ref(0)
const models = ref<any[]>([])
const discussFilter = ref<'all' | 'models' | 'copilot'>('all')

const newProject = ref({
  title: '',
  description: '',
  discussion_model: 'gpt-4o',
})

const projects = computed(() => store.projects)
const activeCount = computed(() =>
  projects.value.filter(p => !['deployed', 'closed', 'rolled_back'].includes(p.status)).length
)
const deployedCount = computed(() =>
  projects.value.filter(p => p.status === 'deployed').length
)

function filterBySource(list: any[], source: 'all' | 'models' | 'copilot') {
  if (source === 'copilot') return list.filter(m => m.api_backend === 'copilot')
  if (source === 'models') return list.filter(m => m.api_backend !== 'copilot')
  return list
}

function buildGroupedOptions(list: any[]) {
  const modelsApi = list.filter(m => m.api_backend !== 'copilot')
  const copilotApi = list.filter(m => m.api_backend === 'copilot')

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

  const buildGroups = (items: any[], suffix = '') => {
    const groups: Record<string, any[]> = {}
    for (const m of items) {
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
}

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

const modelOptions = computed(() => {
  const byCategory = models.value.filter(m => m.category === 'discussion' || m.category === 'both')
  return buildGroupedOptions(filterBySource(byCategory, discussFilter.value))
})

function statusType(status: string) {
  const map: Record<string, any> = {
    draft: 'default', discussing: 'info', planned: 'warning',
    implementing: 'warning', reviewing: 'info', deploying: 'warning',
    deployed: 'success', rolled_back: 'error', closed: 'default',
  }
  return map[status] || 'default'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    draft: '草稿', discussing: '讨论中', planned: '已定稿',
    implementing: '实施中', reviewing: '审核中', deploying: '部署中',
    deployed: '已部署', rolled_back: '已回滚', closed: '已关闭',
  }
  return map[status] || status
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

async function handleCreate() {
  if (!newProject.value.title.trim()) {
    message.warning('请输入需求标题')
    return
  }
  creating.value = true
  try {
    const project = await store.createProject(newProject.value)
    showCreate.value = false
    message.success('项目已创建')
    router.push(`/projects/${project.id}`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  store.fetchProjects()
  try {
    const { data } = await snapshotApi.list()
    snapshotCount.value = data.length
  } catch {}
  try {
    const { data } = await modelApi.list({ custom_models: studioConfig.customModelsEnabled })
    models.value = data
  } catch {}
})
</script>
