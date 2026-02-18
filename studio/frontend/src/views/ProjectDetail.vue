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
        <n-button size="tiny" quaternary :type="project.is_archived ? 'warning' : 'default'" @click="toggleArchive">
          {{ project.is_archived ? '取消归档' : '归档项目' }}
        </n-button>
        <n-tag v-if="project.github_issue_number" size="tiny" :bordered="false">Issue #{{ project.github_issue_number }}</n-tag>
        <n-tag v-if="project.github_pr_number" size="tiny" :bordered="false" type="info">PR #{{ project.github_pr_number }}</n-tag>
      </div>
    </div>

    <!-- 主内容 Tabs -->
    <n-tabs type="line" animated v-model:value="activeTab" size="small" style="--n-tab-padding: 6px 12px">
      <n-tab-pane name="discuss" :tab="discussTabLabel">
        <div class="discuss-layout">
          <!-- 左: 聊天区 -->
          <div class="discuss-chat">
            <ChatPanel :project="project" @plan-finalized="onPlanFinalized" />
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

      <n-tab-pane v-if="hasImplementStage" name="implement" tab="🔨 实施">
        <ImplementPanel :project="project" @status-changed="refreshProject" />
      </n-tab-pane>

      <n-tab-pane v-if="hasDeployStage" name="deploy" tab="🚀 部署">
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

const project = computed(() => store.currentProject)
const DEFAULT_STEP_LABELS = ['草稿', '讨论', '定稿', '实施', '审核', '部署', '完成']
const DEFAULT_STATUS_ORDER = ['draft', 'discussing', 'planned', 'implementing', 'reviewing', 'deploying', 'deployed']

const outputNoun = computed(() => project.value?.skill?.ui_labels?.output_noun || '设计稿')
const outputTabLabel = computed(() => project.value?.skill?.ui_labels?.output_tab_label || `📋 ${outputNoun.value}`)
const finalizeAction = computed(() => project.value?.skill?.ui_labels?.finalize_action || '敲定方案')
const discussTabLabel = computed(() => project.value?.skill?.ui_labels?.discuss_tab_label || '💬 讨论 & 设计')

// 根据 skill 定义的阶段决定是否显示对应 Tab
const hasImplementStage = computed(() => {
  const stages = project.value?.skill?.stages
  if (!stages || stages.length === 0) return true  // 无 skill 时显示所有 tab
  return stages.some((s: any) => s.status === 'implementing')
})

const hasDeployStage = computed(() => {
  const stages = project.value?.skill?.stages
  if (!stages || stages.length === 0) return true
  return stages.some((s: any) => ['deploying', 'deployed'].includes(s.status))
})

const stepLabels = computed(() => {
  const stages = project.value?.skill?.stages
  if (stages && stages.length > 0) return stages.map(s => s.label)
  return DEFAULT_STEP_LABELS
})

const stageStatusOrder = computed(() => {
  const stages = project.value?.skill?.stages
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

// 项目是否已到达 skill 定义的最终阶段
const isAtTerminalStage = computed(() => {
  const stages = project.value?.skill?.stages
  const status = project.value?.status
  if (!stages || stages.length === 0 || !status) return false
  return stages[stages.length - 1].status === status
})

function statusType(s: string) {
  // 如果当前状态是 skill 的最终阶段, 显示 success
  const stages = project.value?.skill?.stages
  if (stages && stages.length > 0 && stages[stages.length - 1].status === s) return 'success'
  const m: Record<string, any> = {
    draft:'default', discussing:'info', planned:'warning', implementing:'warning',
    reviewing:'info', deploying:'warning', deployed:'success', rolled_back:'error',
  }
  return m[s] || 'default'
}

function statusLabel(s: string) {
  // 优先从 skill.stages 获取标签
  const stages = project.value?.skill?.stages
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

function onPlanFinalized() {
  refreshProject()
  showPlanPanel.value = true
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

onMounted(() => refreshProject())
watch(() => route.params.id, () => refreshProject())
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