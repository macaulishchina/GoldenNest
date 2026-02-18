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
            新建项目
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

      <!-- 最近动态：按技能分组双列 -->
      <div v-if="projects.length">
        <n-grid :cols="recentBySkill.length > 1 ? 2 : 1" :x-gap="16" :y-gap="16">
          <n-gi v-for="group in recentBySkill" :key="group.skillId">
            <n-card
              :title="`${group.icon} ${group.name}`"
              size="small"
              style="background: #16213e"
              :header-style="{ borderLeft: `3px solid ${group.color}`, paddingLeft: '12px' }"
            >
              <n-list bordered style="background: transparent">
                <n-list-item
                  v-for="p in group.items"
                  :key="p.id"
                  style="padding: 0"
                >
                  <LogItem :item="p" @click="() => router.push(`/projects/${p.id}`)" />
                </n-list-item>
              </n-list>
            </n-card>
          </n-gi>
        </n-grid>
      </div>
      <n-empty v-else description="还没有项目，点击「新建项目」开始" />
    </n-space>

    <!-- 新建项目对话框 -->
    <n-modal v-model:show="showCreate" preset="dialog" :title="createDialogTitle" style="width: 600px">
      <n-form :model="newProject" label-placement="left" label-width="80">
        <n-form-item label="技能">
          <n-space :size="8">
            <div
              v-for="skill in skillStore.enabledSkills"
              :key="skill.id"
              class="skill-card"
              :class="{ 'skill-card-active': newProject.skill_id === skill.id }"
              @click="newProject.skill_id = skill.id"
            >
              <span class="skill-icon">{{ skill.icon || '🔧' }}</span>
              <span class="skill-name">{{ skill.name }}</span>
            </div>
          </n-space>
        </n-form-item>
        <n-form-item :label="selectedSkillLabels.project_noun + '标题'">
          <n-input v-model:value="newProject.title" :placeholder="selectedSkillUiLabels.create_placeholder || ('简明描述' + selectedSkillLabels.project_noun + '目标')" />
        </n-form-item>
        <n-form-item :label="selectedSkillLabels.project_noun + '描述'">
          <n-input
            v-model:value="newProject.description"
            type="textarea"
            :rows="4"
            :placeholder="selectedSkillUiLabels.description_placeholder || ('详细描述' + selectedSkillLabels.project_noun + '背景和期望效果...')"
          />
        </n-form-item>
        <n-form-item label="讨论模型">
          <n-space vertical :size="8">
            <n-radio-group v-model:value="discussFilter" size="small">
              <n-radio-button v-for="f in providerFilters" :key="f.value" :value="f.value">
                <span style="display:inline-flex;align-items:center;gap:3px">
                  <span v-if="f.icon" v-html="f.icon"></span>
                  <span>{{ f.label }}</span>
                </span>
              </n-radio-button>
            </n-radio-group>
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
import { ref, computed, onMounted, h, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import LogItem from '@/components/LogItem.vue'
import { useProjectStore } from '@/stores/project'
import { useStudioConfigStore } from '@/stores/studioConfig'
import { useSkillStore } from '@/stores/skill'
import { snapshotApi, modelApi } from '@/api'
import { getProviderIcon } from '@/utils/providerIcons'

const router = useRouter()
const message = useMessage()
const store = useProjectStore()
const studioConfig = useStudioConfigStore()
const skillStore = useSkillStore()

const showCreate = ref(false)
const creating = ref(false)
const snapshotCount = ref(0)
const models = ref<any[]>([])
const discussFilter = ref('all')

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

const newProject = ref({
  title: '',
  description: '',
  discussion_model: 'gpt-4o',
  skill_id: null as number | null,
})

const projects = computed(() => store.projects)
const activeCount = computed(() =>
  projects.value.filter(p => !['deployed', 'closed', 'rolled_back'].includes(p.status)).length
)
const deployedCount = computed(() =>
  projects.value.filter(p => p.status === 'deployed').length
)

// ── 按技能分组，每组取最近 5 条，最多 4 组 ────────────────────────
const SKILL_COLORS: Record<string, string> = {
  bug: '#d03050', fix: '#d03050', 缺陷: '#d03050', 问诊: '#d03050',
  需求: '#2080f0', feature: '#2080f0', 分析: '#2080f0',
  任务: '#18a058', task: '#18a058',
  审查: '#f0a020', review: '#f0a020', 评审: '#f0a020',
}
function skillGroupColor(name = '') {
  const n = name.toLowerCase()
  for (const [key, color] of Object.entries(SKILL_COLORS)) {
    if (n.includes(key)) return color
  }
  return '#63e2b7'
}
const recentBySkill = computed(() => {
  const map = new Map<number | string, { skillId: number | string; name: string; icon: string; color: string; items: any[] }>()
  for (const p of projects.value) {
    const sid = p.skill_id ?? 0
    if (!map.has(sid)) {
      const name = p.skill?.name || '项目'
      map.set(sid, { skillId: sid, name, icon: p.skill?.icon || '📋', color: skillGroupColor(name), items: [] })
    }
    const g = map.get(sid)!
    if (g.items.length < 5) g.items.push(p)
  }
  // 按首项更新时间排序，最多展示 4 组
  return [...map.values()]
    .sort((a, b) => (b.items[0]?.updated_at ?? '').localeCompare(a.items[0]?.updated_at ?? ''))
    .slice(0, 4)
})

const selectedSkillLabels = computed(() => {
  const sid = newProject.value.skill_id
  if (sid) {
    const skill = skillStore.getSkillById(sid)
    if (skill?.ui_labels) return { project_noun: skill.ui_labels.project_noun || '需求', output_noun: skill.ui_labels.output_noun || '设计稿' }
  }
  return { project_noun: '需求', output_noun: '设计稿' }
})

const selectedSkillUiLabels = computed(() => {
  const sid = newProject.value.skill_id
  if (sid) {
    const skill = skillStore.getSkillById(sid)
    return skill?.ui_labels || {}
  }
  return {} as Record<string, string>
})

const createDialogTitle = computed(() => {
  const sid = newProject.value.skill_id
  if (sid) {
    const skill = skillStore.getSkillById(sid)
    if (skill?.ui_labels?.create_title) return skill.ui_labels.create_title
  }
  return '🆕 新建项目'
})

// 打开创建弹窗时自动选择第一个技能
watch(showCreate, (show) => {
  if (show && !newProject.value.skill_id && skillStore.enabledSkills.length > 0) {
    newProject.value.skill_id = skillStore.enabledSkills[0].id
  }
})

function filterBySource(list: any[], source: string) {
  if (source === 'all') return list
  if (source === 'custom') return list.filter(m => m.is_custom)
  if (source === 'github') return list.filter(m => m.provider_slug === 'github' || (!m.provider_slug && m.api_backend === 'models'))
  if (source === 'copilot') return list.filter(m => m.provider_slug === 'copilot' || m.api_backend === 'copilot')
  return list.filter(m => m.provider_slug === source)
}

function buildGroupedOptions(list: any[]) {
  // 保留 API 返回顺序, 按 model_family 分组 (后端已提供)
  const mapOpt = (m: any) => ({
    label: m.name, value: m.id,
    supports_vision: m.supports_vision, supports_tools: m.supports_tools,
    is_reasoning: m.is_reasoning, api_backend: m.api_backend,
    is_custom: m.is_custom,
    provider_slug: m.provider_slug || (m.api_backend === 'copilot' ? 'copilot' : 'github'),
    max_input_tokens: studioConfig.getEffectiveMaxInput(m.id, m.max_input_tokens || 0),
    pricing_tier: m.pricing_tier, premium_multiplier: m.premium_multiplier,
    is_deprecated: m.is_deprecated, pricing_note: m.pricing_note,
  })
  // 按 model_family 保序分组
  const groups: Array<{ key: string; label: string; slug: string; items: any[] }> = []
  const groupMap: Record<string, typeof groups[0]> = {}
  for (const m of list) {
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
}

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
  const ctxText = option.max_input_tokens ? formatTokens(option.max_input_tokens) : ''
  const nameStyle = selected ? 'font-weight:600' : ''
  const priceStyle = selected
    ? 'color:#18a058;font-size:11px;flex-shrink:0;margin-left:12px;font-weight:600'
    : 'color:#888;font-size:11px;flex-shrink:0;margin-left:12px'
  return h('div', { style: 'display:flex;justify-content:space-between;align-items:center;width:100%' }, [
    h('span', { style: nameStyle }, [selected ? '● ' : '', option.label as string, ' ', iconVNode, customStr, capStr, depStr]),
    h('span', { style: priceStyle }, [
      ctxText ? h('span', { style: 'color:#666;margin-right:6px' }, ctxText) : null,
      priceText,
    ]),
  ])
}

function formatTokens(n: number): string {
  if (!n) return '0'
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`
  return `${n}`
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
  skillStore.fetchSkills()
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

<style scoped>
.skill-card {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 8px;
  border: 1.5px solid #333; cursor: pointer;
  transition: all .15s; user-select: none;
}
.skill-card:hover { border-color: #63e2b7; }
.skill-card-active { border-color: #63e2b7; background: rgba(99,226,183,.12); }
.skill-icon { font-size: 18px; }
.skill-name { font-size: 13px; }
</style>
