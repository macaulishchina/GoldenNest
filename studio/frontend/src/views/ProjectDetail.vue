<template>
  <div v-if="project">
    <!-- 顶部: 紧凑信息条 + 内联步骤条 -->
    <div class="project-header-bar">
      <div class="project-header-left">
        <n-button text size="small" @click="$router.push('/projects')" style="padding: 0; font-size: 12px">← 返回</n-button>
        <n-text strong style="font-size: 14px; white-space: nowrap">{{ project.title }}</n-text>
        <n-tag :type="statusType(project.status)" size="tiny" round>{{ statusLabel(project.status) }}</n-tag>
        <n-tag v-if="project.is_archived" type="default" size="tiny" :bordered="false" round>已归档</n-tag>
      </div>
      <div class="project-header-steps">
        <div v-for="(step, i) in stepLabels" :key="i"
             class="step-dot-item"
             :class="{ 'step-done': i + 1 < currentStep || (isAtTerminalStage && i + 1 === currentStep), 'step-current': i + 1 === currentStep && !isAtTerminalStage }">
          <span class="step-dot">{{ (i + 1 < currentStep || (isAtTerminalStage && i + 1 === currentStep)) ? '✓' : i + 1 }}</span>
          <span class="step-text">{{ step }}</span>
        </div>
      </div>
      <div class="project-header-right">
        <n-button
          size="tiny"
          :quaternary="!showPlanPanel"
          :type="showPlanPanel ? 'info' : 'default'"
          @click="showPlanPanel = !showPlanPanel"
          style="font-size: 11px"
        >
          {{ outputTabLabel }}
        </n-button>
        <n-button
          v-if="hasReviewStage && activeTab === 'review'"
          size="tiny"
          :quaternary="!showReviewPanel"
          :type="showReviewPanel ? 'info' : 'default'"
          @click="showReviewPanel = !showReviewPanel"
          style="font-size: 11px"
        >
          {{ reviewOutputNoun }}
        </n-button>
        <n-button size="tiny" quaternary :type="project.is_archived ? 'warning' : 'default'" @click="toggleArchive">
          {{ project.is_archived ? '取消归档' : '归档项目' }}
        </n-button>
        <n-tag v-if="project.github_issue_number" size="tiny" :bordered="false">Issue #{{ project.github_issue_number }}</n-tag>
        <n-tag v-if="project.github_pr_number" size="tiny" :bordered="false" type="info">PR #{{ project.github_pr_number }}</n-tag>
      </div>
    </div>

    <!-- 主内容 Tabs -->
    <n-tabs type="line" animated v-model:value="activeTab" size="small" style="--n-tab-padding: 6px 12px">
      <n-tab-pane name="discuss" :tab="discussTabLabel" :disabled="isTabLocked('discuss')">
        <!-- 工作区信息条 -->
        <div v-if="project.workspace_dir && project.iteration_count > 0" class="workspace-info-bar">
          <n-tag size="small" :bordered="false" type="info">
            🔄 迭代 #{{ project.iteration_count }}
          </n-tag>
          <n-tag size="small" :bordered="false">
            📁 {{ project.workspace_dir }}
          </n-tag>
        </div>
        <!-- 只读提示 -->
        <n-alert v-if="isStageReadonly('discussing')" type="info" style="margin-bottom: 8px" :bordered="false">
          讨论阶段已完成，当前为只读模式。如需修改，请在审查阶段点击「继续迭代」。
        </n-alert>
        <div class="discuss-layout">
          <!-- 左: 聊天区 -->
          <div class="discuss-chat">
            <ChatPanel :project="project" :readonly="isStageReadonly('discussing')" @plan-finalized="onPlanFinalized" />
          </div>
          <!-- 右: 设计稿面板 -->
          <div v-if="showPlanPanel" class="discuss-plan">
            <div class="plan-panel-header">
              <n-button size="tiny" quaternary circle @click="showPlanPanel = false" style="flex-shrink: 0">✕</n-button>
            </div>
            <div class="plan-panel-body">
              <PlanEditor :project="project" :output-noun="outputNoun" :finalize-action="finalizeAction" @updated="refreshProject" />
            </div>
          </div>
        </div>
      </n-tab-pane>

      <n-tab-pane v-if="hasImplementStage" name="implement" tab="🔨 实施" :disabled="isTabLocked('implement')">
        <ImplementPanel :project="project" @status-changed="refreshProject" @go-review="goToReview" />
      </n-tab-pane>

      <n-tab-pane v-if="hasReviewStage" name="review" :tab="reviewDiscussTabLabel" :disabled="isTabLocked('review')">
        <!-- 审查准备 (未准备时显示按钮) -->
        <div v-if="!reviewPrepared" style="padding: 40px 0; text-align: center;">
          <n-result status="info" title="准备审查环境" description="克隆实施分支、获取变更信息、加载需求文档到 AI 上下文">
            <template #footer>
              <n-space vertical align="center" :size="16">
                <n-button type="primary" size="large" @click="handlePrepareReview" :loading="preparingReview">
                  🔍 开始审查
                </n-button>
                <n-text v-if="project.branch_name" depth="3" style="font-size: 12px">
                  将基于分支 <n-tag size="small" :bordered="false">{{ project.branch_name }}</n-tag> 创建审查工作区
                </n-text>
              </n-space>
            </template>
          </n-result>
        </div>
        <!-- 审查已准备: 工作区信息 + 聊天 -->
        <div v-else>
          <!-- 审查工作区信息条 -->
          <div class="workspace-info-bar">
            <n-tag size="small" :bordered="false" type="success">✅ 审查环境就绪</n-tag>
            <n-tag v-if="reviewInfo.branch" size="small" :bordered="false">🌿 {{ reviewInfo.branch }}</n-tag>
            <n-tag v-if="reviewInfo.diff_stat" size="small" :bordered="false">📊 {{ reviewInfo.diff_stat }}</n-tag>
            <n-tag v-if="reviewInfo.changed_files.length" size="small" :bordered="false">
              📝 {{ reviewInfo.changed_files.length }} 个文件变更
            </n-tag>
            <n-button size="tiny" quaternary @click="handleStartIteration" :loading="startingIteration" v-if="project.status === 'reviewing'">
              🔄 继续迭代
            </n-button>
          </div>
          <div class="discuss-layout">
            <div class="discuss-chat">
              <ChatPanel :project="project" @plan-finalized="onReviewFinalized" />
            </div>
            <div v-if="showReviewPanel" class="discuss-plan">
              <div class="plan-panel-header">
                <n-button size="tiny" quaternary circle @click="showReviewPanel = false" style="flex-shrink: 0">✕</n-button>
              </div>
              <div class="plan-panel-body">
                <PlanEditor :project="project" :output-noun="reviewOutputNoun" :finalize-action="reviewFinalizeAction" @updated="refreshProject" />
              </div>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <n-tab-pane v-if="hasDeployStage" name="deploy" tab="🚀 部署" :disabled="isTabLocked('deploy')">
        <DeployPanel :project="project" @deployed="refreshProject" />
      </n-tab-pane>

      <n-tab-pane name="snapshots" tab="📸 快照">
        <SnapshotPanel :project-id="project.id" />
      </n-tab-pane>
    </n-tabs>
  </div>
  <n-spin v-else :show="true" style="margin-top: 100px" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useProjectStore } from '@/stores/project'
import { implementationApi } from '@/api/index'
import ChatPanel from '@/components/ChatPanel.vue'
import PlanEditor from '@/components/PlanEditor.vue'
import ImplementPanel from '@/components/ImplementPanel.vue'
import DeployPanel from '@/components/DeployPanel.vue'
import SnapshotPanel from '@/components/SnapshotPanel.vue'

const route = useRoute()
const store = useProjectStore()
const message = useMessage()
const activeTab = ref('discuss')
const showPlanPanel = ref(false)
const showReviewPanel = ref(false)

// 审查准备状态
const reviewPrepared = ref(false)
const preparingReview = ref(false)
const startingIteration = ref(false)
const reviewInfo = ref<{
  branch: string
  diff_stat: string
  changed_files: string[]
  workspace_dir: string
}>({ branch: '', diff_stat: '', changed_files: [], workspace_dir: '' })

const project = computed(() => store.currentProject)
const DEFAULT_STEP_LABELS = ['草稿', '讨论', '定稿', '实施', '审核', '部署', '完成']
const DEFAULT_STATUS_ORDER = ['draft', 'discussing', 'planned', 'implementing', 'reviewing', 'deploying', 'deployed']

const outputNoun = computed(() => project.value?.type_info?.ui_labels?.output_noun || '设计稿')
const outputTabLabel = computed(() => project.value?.type_info?.ui_labels?.output_tab_label || `📋 ${outputNoun.value}`)
const finalizeAction = computed(() => project.value?.type_info?.ui_labels?.finalize_action || '敲定方案')
const discussTabLabel = computed(() => project.value?.type_info?.ui_labels?.discuss_tab_label || '💬 讨论 & 设计')
const reviewDiscussTabLabel = computed(() => project.value?.type_info?.ui_labels?.review_discuss_tab_label || '💬 审查/验证')
const reviewOutputNoun = computed(() => project.value?.type_info?.ui_labels?.review_output_noun || '审查报告')
const reviewFinalizeAction = computed(() => project.value?.type_info?.ui_labels?.review_finalize_action || '生成报告')

// 根据项目类型定义的阶段决定是否显示对应 Tab
const hasImplementStage = computed(() => {
  const stages = project.value?.type_info?.stages
  if (!stages || stages.length === 0) return true  // 无类型信息时显示所有 tab
  return stages.some((s: any) => s.status === 'implementing')
})

const hasReviewStage = computed(() => {
  const stages = project.value?.type_info?.stages
  if (!stages || stages.length === 0) return false  // 没有类型信息时不显示审查 tab
  return stages.some((s: any) => s.status === 'reviewing')
})

const hasDeployStage = computed(() => {
  const stages = project.value?.type_info?.stages
  if (!stages || stages.length === 0) return true
  return stages.some((s: any) => ['deploying', 'deployed'].includes(s.status))
})

const stepLabels = computed(() => {
  const stages = project.value?.type_info?.stages
  if (stages && stages.length > 0) return stages.map(s => s.label)
  return DEFAULT_STEP_LABELS
})

const stageStatusOrder = computed(() => {
  const stages = project.value?.type_info?.stages
  if (stages && stages.length > 0) return stages.map(s => s.status)
  return DEFAULT_STATUS_ORDER
})


const currentStep = computed(() => {
  const status = project.value?.status || 'draft'
  const order = stageStatusOrder.value
  const idx = order.indexOf(status)
  // 如果找到了, step = idx + 1; 末尾状态（closed/rolled_back）= 最后一步
  if (idx >= 0) return idx + 1
  return order.length
})

// 项目是否已到达类型定义的最终阶段
const isAtTerminalStage = computed(() => {
  const stages = project.value?.type_info?.stages
  const status = project.value?.status
  if (!stages || stages.length === 0 || !status) return false
  return stages[stages.length - 1].status === status
})

function statusType(s: string) {
  // 如果当前状态是类型配置的最终阶段, 显示 success
  const stages = project.value?.type_info?.stages
  if (stages && stages.length > 0 && stages[stages.length - 1].status === s) return 'success'
  const m: Record<string, any> = {
    draft:'default', discussing:'info', planned:'warning', implementing:'warning',
    reviewing:'info', deploying:'warning', deployed:'success', rolled_back:'error',
  }
  return m[s] || 'default'
}

function statusLabel(s: string) {
  // 优先从类型定义的 stages 获取标签
  const stages = project.value?.type_info?.stages
  if (stages) {
    const stage = stages.find(st => st.status === s)
    if (stage) return stage.label
  }
  const m: Record<string, string> = {
    draft:'草稿', discussing:'讨论中', planned:'已定稿', implementing:'实施中',
    reviewing:'审核中', deploying:'部署中', deployed:'已部署', rolled_back:'已回滚',
  }
  return m[s] || s
}

async function refreshProject() {
  const id = Number(route.params.id)
  if (id) await store.fetchProject(id)
}

// ---- 状态 → 默认 Tab 映射 ----
const STATUS_TAB_MAP: Record<string, string> = {
  draft: 'discuss',
  discussing: 'discuss',
  planned: 'discuss',
  implementing: 'implement',
  reviewing: 'review',
  deploying: 'deploy',
  deployed: 'deploy',
  rolled_back: 'deploy',
}

function getDefaultTab(status: string): string {
  return STATUS_TAB_MAP[status] || 'discuss'
}

function syncActiveTab() {
  if (!project.value) return
  const targetTab = getDefaultTab(project.value.status)
  // 检查目标 tab 是否存在
  if (targetTab === 'implement' && !hasImplementStage.value) return
  if (targetTab === 'review' && !hasReviewStage.value) return
  if (targetTab === 'deploy' && !hasDeployStage.value) return
  activeTab.value = targetTab
}

// ---- 阶段只读管理 ----
function isStageReadonly(stageStatus: string): boolean {
  if (!project.value) return false
  const order = stageStatusOrder.value
  const currentIdx = order.indexOf(project.value.status)
  const stageIdx = order.indexOf(stageStatus)
  if (currentIdx < 0 || stageIdx < 0) return false
  // 当前状态之前的阶段都是只读
  return stageIdx < currentIdx
}

function isTabLocked(tabName: string): boolean {
  if (!project.value) return false
  const order = stageStatusOrder.value
  const currentStatus = project.value.status
  const currentIdx = order.indexOf(currentStatus)
  if (currentIdx < 0) return false

  // 每个 tab 对应的最早阶段状态
  const TAB_FIRST_STATUS: Record<string, string> = {
    discuss: 'discussing',
    implement: 'implementing',
    review: 'reviewing',
    deploy: 'deploying',
  }
  const firstStatus = TAB_FIRST_STATUS[tabName]
  if (!firstStatus) return false

  const tabIdx = order.indexOf(firstStatus)
  if (tabIdx < 0) return false

  // 允许当前阶段和下一阶段，其余锁定
  // discuss (idx 1) 对应 draft (0) + discussing (1)，所以 discuss tab 用 tabIdx - 1
  // draft 可以进 discuss，所以 discuss 永不锁
  if (tabName === 'discuss') return false

  return tabIdx > currentIdx + 1
}

// ---- 审查准备 ----
async function handlePrepareReview() {
  if (!project.value) return
  preparingReview.value = true
  try {
    const res = await implementationApi.prepareReview(project.value.id)
    if (res.data.success) {
      reviewPrepared.value = true
      reviewInfo.value = {
        branch: res.data.branch || '',
        diff_stat: res.data.diff_stat || '',
        changed_files: res.data.changed_files || [],
        workspace_dir: res.data.workspace_dir || '',
      }
      await refreshProject()
      message.success('审查环境准备完成')
    } else {
      message.error(res.data.message || '审查环境准备失败')
    }
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '审查环境准备失败')
  } finally {
    preparingReview.value = false
  }
}

// ---- 继续迭代 ----
async function handleStartIteration() {
  if (!project.value) return
  startingIteration.value = true
  try {
    const res = await implementationApi.startIteration(project.value.id)
    if (res.data.success) {
      message.success(`已开始第 ${res.data.iteration} 次迭代`)
      reviewPrepared.value = false
      reviewInfo.value = { branch: '', diff_stat: '', changed_files: [], workspace_dir: '' }
      await refreshProject()
      syncActiveTab()  // 切换到讨论 tab
    } else {
      message.error(res.data.message || '迭代启动失败')
    }
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '迭代启动失败')
  } finally {
    startingIteration.value = false
  }
}

function onPlanFinalized() {
  refreshProject()
  showPlanPanel.value = true
}

function onReviewFinalized() {
  refreshProject()
  showReviewPanel.value = true
}

function goToReview() {
  activeTab.value = 'review'
  refreshProject()
}

async function toggleArchive() {
  if (!project.value) return
  const nextArchived = !project.value.is_archived
  try {
    await store.updateProject(project.value.id, { is_archived: nextArchived })
    message.success(nextArchived ? '已归档' : '已取消归档')
    await refreshProject()
  } catch {
    message.error('操作失败')
  }
}

// ---- 初次加载后检查状态，可能需要自动恢复审查准备状态 ----
async function initAfterLoad() {
  if (!project.value) return
  syncActiveTab()
  // 如果处于 reviewing 状态且有 workspace_dir，认为审查已准备
  if (project.value.status === 'reviewing' && project.value.workspace_dir) {
    reviewPrepared.value = true
    // 获取工作区信息
    try {
      const res = await implementationApi.getWorkspaceInfo(project.value.id)
      reviewInfo.value = {
        branch: res.data.branch || '',
        diff_stat: '',
        changed_files: [],
        workspace_dir: res.data.workspace_dir || '',
      }
    } catch {
      // 忽略错误，用户可重新准备
    }
  }
}

onMounted(async () => {
  await refreshProject()
  initAfterLoad()
})
watch(() => route.params.id, async () => {
  reviewPrepared.value = false
  reviewInfo.value = { branch: '', diff_stat: '', changed_files: [], workspace_dir: '' }
  await refreshProject()
  initAfterLoad()
})
</script>

<style scoped>
/* ============ 紧凑顶部信息条 ============ */
.project-header-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  margin-bottom: 6px;
  background: #16213e;
  border-radius: 8px;

/* 工作区信息条 */
.workspace-info-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  margin-bottom: 8px;
  background: rgba(14, 165, 233, 0.06);
  border: 1px solid rgba(14, 165, 233, 0.15);
  border-radius: 6px;
  flex-wrap: wrap;
}
  flex-wrap: nowrap;
  min-height: 36px;
}
.project-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.project-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  margin-left: auto;
}

/* 内联迷你步骤条 */
.project-header-steps {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  justify-content: center;
  overflow: hidden;
}
.step-dot-item {
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0.35;
  transition: opacity 0.15s;
  white-space: nowrap;
}
.step-dot-item.step-done {
  opacity: 0.55;
}
.step-dot-item.step-current {
  opacity: 1;
}
.step-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 9px;
  font-weight: 600;
  background: rgba(255,255,255,0.08);
  color: #aaa;
  flex-shrink: 0;
}
.step-done .step-dot {
  background: #18a058;
  color: #fff;
  font-size: 10px;
}
.step-current .step-dot {
  background: #0ea5e9;
  color: #fff;
  box-shadow: 0 0 6px rgba(14, 165, 233, 0.4);
}
.step-text {
  font-size: 10px;
  color: #888;
}
.step-current .step-text {
  color: #e0e0e0;
  font-weight: 500;
}
/* 设计稿面板布局 */
.discuss-layout {
  display: flex;
  height: calc(100vh - 200px);
  min-height: 400px;
  overflow: hidden;
}
.discuss-chat {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
.discuss-plan {
  position: relative;
  width: 42%;
  min-width: 340px;
  max-width: 560px;
  flex-shrink: 0;
  border-left: 1px solid #2a2a3e;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.plan-panel-header {
  display: flex;
  justify-content: flex-end;
  padding: 4px 6px 0;
  flex-shrink: 0;
}
.plan-panel-body {
  flex: 1;
  overflow: hidden;
  padding: 0 10px 8px;
  display: flex;
  flex-direction: column;
}

/* 步骤之间的连线 */
.step-dot-item + .step-dot-item::before {
  content: '';
  display: inline-block;
  width: 16px;
  height: 1px;
  background: rgba(255,255,255,0.12);
  margin-right: 2px;
  flex-shrink: 0;
}
.step-dot-item.step-done + .step-dot-item::before {
  background: #18a058;
}
</style>