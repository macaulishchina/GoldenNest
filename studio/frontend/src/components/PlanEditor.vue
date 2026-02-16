<template>
  <div style="display: flex; flex-direction: column; height: 100%;">
    <!-- 工具栏 -->
    <n-space justify="space-between" align="center" style="margin-bottom: 8px; flex-shrink: 0;">
      <n-space align="center" :size="8">
        <n-text strong>设计稿 Plan</n-text>
        <n-tag v-if="project.plan_version" size="small" type="info">v{{ project.plan_version }}</n-tag>
        <!-- 版本历史 -->
        <n-select
          v-if="versions.length > 1"
          v-model:value="selectedVersion"
          :options="versionOptions"
          size="small"
          style="width: 140px"
          placeholder="版本历史"
          @update:value="loadVersion"
        />
        <n-tag v-if="viewingOldVersion" size="small" type="warning">
          查看 v{{ selectedVersion }} (只读)
        </n-tag>
      </n-space>
      <n-space :size="6">
        <n-button v-if="viewingOldVersion" size="small" @click="restoreCurrentVersion">
          ↩ 返回当前版本
        </n-button>
        <n-button v-if="viewingOldVersion" size="small" type="warning" @click="applyOldVersion">
          📥 恢复此版本
        </n-button>
        <n-button v-if="!viewingOldVersion && !editing" size="small" @click="startEditing">
          ✏️ 编辑
        </n-button>
        <n-button v-if="editing && !viewingOldVersion" size="small" @click="editing = false">
          ✖ 取消
        </n-button>
        <n-button size="small" type="primary" @click="handleSave" :loading="saving" v-if="editing && !viewingOldVersion">
          💾 保存
        </n-button>
      </n-space>
    </n-space>

    <!-- 内容区 -->
    <div style="flex: 1; overflow-y: auto;">
      <n-card v-if="!displayContent && !editing" style="background: #16213e">
        <n-empty description="还没有设计稿，请在讨论区完成讨论后点击「敲定方案」" />
      </n-card>

      <!-- 编辑模式: 左右分栏 (编辑 + 实时预览) -->
      <div v-else-if="editing" style="display: flex; gap: 12px; height: 100%;">
        <div style="flex: 1; min-width: 0;">
          <n-input
            v-model:value="editContent"
            type="textarea"
            :autosize="{ minRows: 20, maxRows: 60 }"
            placeholder="Markdown 格式的设计稿..."
            style="font-family: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace; font-size: 13px;"
          />
        </div>
        <div style="flex: 1; min-width: 0; overflow-y: auto; background: #16213e; border-radius: 6px; padding: 12px;">
          <n-text depth="3" style="font-size: 11px; display: block; margin-bottom: 8px">📖 实时预览</n-text>
          <div class="plan-markdown-body" v-html="editPreview" />
        </div>
      </div>

      <!-- 预览模式 (默认: 渲染 Markdown) -->
      <n-card v-else-if="displayContent" style="background: #16213e">
        <div class="plan-markdown-body" v-html="renderedPlan" />
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { projectApi, discussionApi } from '@/api'
import type { Project } from '@/stores/project'
import { marked } from 'marked'

const props = defineProps<{ project: Project }>()
const emit = defineEmits(['updated'])
const message = useMessage()

const editing = ref(false)
const saving = ref(false)
const editContent = ref('')
const versions = ref<any[]>([])
const selectedVersion = ref<number | null>(null)
const oldVersionContent = ref<string>('')

const viewingOldVersion = computed(() =>
  selectedVersion.value !== null && selectedVersion.value !== props.project.plan_version
)

const displayContent = computed(() =>
  viewingOldVersion.value ? oldVersionContent.value : props.project.plan_content
)

const renderedPlan = computed(() => {
  const content = displayContent.value
  if (!content) return ''
  try {
    return marked.parse(content, { async: false }) as string
  } catch {
    return content.replace(/\n/g, '<br>')
  }
})

const editPreview = computed(() => {
  if (!editContent.value) return '<span style="color:#666">输入 Markdown 内容后这里会实时预览...</span>'
  try {
    return marked.parse(editContent.value, { async: false }) as string
  } catch {
    return editContent.value.replace(/\n/g, '<br>')
  }
})

const versionOptions = computed(() =>
  versions.value.map(v => ({
    label: `v${v.version}${v.is_current ? ' (当前)' : ''} - ${new Date(v.created_at).toLocaleDateString('zh-CN')}`,
    value: v.version,
  }))
)

function startEditing() {
  editing.value = true
  editContent.value = props.project.plan_content || ''
}

function restoreCurrentVersion() {
  selectedVersion.value = props.project.plan_version || null
  oldVersionContent.value = ''
}

async function loadVersion(version: number) {
  if (version === props.project.plan_version) {
    oldVersionContent.value = ''
    return
  }
  try {
    const { data } = await discussionApi.getPlanVersion(props.project.id, version)
    oldVersionContent.value = data.content
  } catch (e: any) {
    message.error('加载版本失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function applyOldVersion() {
  if (!oldVersionContent.value) return
  saving.value = true
  try {
    await projectApi.update(props.project.id, { plan_content: oldVersionContent.value })
    message.success(`已恢复到 v${selectedVersion.value}`)
    selectedVersion.value = null
    oldVersionContent.value = ''
    emit('updated')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '恢复失败')
  } finally {
    saving.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await projectApi.update(props.project.id, { plan_content: editContent.value })
    message.success('设计稿已保存')
    editing.value = false
    emit('updated')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function loadVersions() {
  try {
    const { data } = await discussionApi.getPlanVersions(props.project.id)
    versions.value = data
    if (props.project.plan_version) {
      selectedVersion.value = props.project.plan_version
    }
  } catch {
    // Versions not available yet
  }
}

onMounted(() => loadVersions())

watch(() => props.project.plan_version, () => {
  loadVersions()
  selectedVersion.value = props.project.plan_version || null
  oldVersionContent.value = ''
})
</script>

<style>
/* PlanEditor 自带的 Markdown 渲染样式 */
.plan-markdown-body {
  color: #e0e0e0;
  line-height: 1.6;
  font-size: 14px;
}
.plan-markdown-body pre {
  background: #0d1b2a;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}
.plan-markdown-body code {
  background: #0d1b2a;
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 13px;
}
.plan-markdown-body pre code {
  background: none;
  padding: 0;
}
.plan-markdown-body p { margin: 0.5em 0; }
.plan-markdown-body h1, .plan-markdown-body h2, .plan-markdown-body h3 {
  color: #e94560;
  margin: 0.7em 0 0.3em;
}
.plan-markdown-body ul, .plan-markdown-body ol { padding-left: 1.5em; }
.plan-markdown-body blockquote {
  border-left: 3px solid #e94560;
  margin: 0.5em 0;
  padding: 0.4em 1em;
  background: rgba(233, 69, 96, 0.1);
}
.plan-markdown-body table { border-collapse: collapse; width: 100%; }
.plan-markdown-body th, .plan-markdown-body td { border: 1px solid #333; padding: 6px 12px; }
.plan-markdown-body th { background: #0d1b2a; }
.plan-markdown-body img { max-width: 100%; border-radius: 6px; }
</style>
