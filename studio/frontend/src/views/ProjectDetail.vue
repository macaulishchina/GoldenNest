<template>
  <div v-if="project">
    <!-- 顶部信息区 -->
    <n-card size="small" style="background: #16213e; margin-bottom: 16px">
      <n-space justify="space-between" align="center">
        <n-space align="center">
          <n-button text @click="$router.push('/projects')">← 返回</n-button>
          <n-h3 style="margin: 0">{{ project.title }}</n-h3>
          <n-tag :type="statusType(project.status)" size="small" round>
            {{ statusLabel(project.status) }}
          </n-tag>
        </n-space>
        <n-space>
          <n-tag v-if="project.github_issue_number" size="small" :bordered="false">
            Issue #{{ project.github_issue_number }}
          </n-tag>
          <n-tag v-if="project.github_pr_number" size="small" :bordered="false" type="info">
            PR #{{ project.github_pr_number }}
          </n-tag>
        </n-space>
      </n-space>
      <!-- 状态流水线 -->
      <n-steps :current="currentStep" size="small" style="margin-top: 12px">
        <n-step title="草稿" />
        <n-step title="讨论" />
        <n-step title="定稿" />
        <n-step title="实施" />
        <n-step title="审核" />
        <n-step title="部署" />
        <n-step title="完成" />
      </n-steps>
    </n-card>

    <!-- 主内容 Tabs -->
    <n-tabs type="line" animated v-model:value="activeTab">
      <n-tab-pane name="discuss" tab="💬 讨论 & 设计">
        <div :style="splitLayoutStyle">
          <!-- 左侧: 聊天面板 -->
          <div :style="chatPanelStyle">
            <ChatPanel :project="project" @plan-finalized="onPlanFinalized" />
          </div>
          <!-- 右侧: Plan 面板 (可收起) -->
          <div v-if="showPlanPanel" style="flex: 0 0 40%; min-width: 320px; max-width: 50%; border-left: 1px solid #333; padding-left: 16px; display: flex; flex-direction: column; overflow: hidden;">
            <n-space justify="space-between" align="center" style="margin-bottom: 8px; flex-shrink: 0;">
              <n-text strong style="font-size: 14px">📋 设计稿</n-text>
              <n-button size="tiny" quaternary @click="showPlanPanel = false">✕ 收起</n-button>
            </n-space>
            <div style="flex: 1; overflow-y: auto;">
              <PlanEditor :project="project" @updated="refreshProject" />
            </div>
          </div>
          <!-- Plan 展开按钮 (收起时显示) -->
          <div v-else style="flex: 0 0 32px; display: flex; align-items: flex-start; padding-top: 12px;">
            <n-tooltip placement="left">
              <template #trigger>
                <n-button size="small" quaternary @click="showPlanPanel = true" style="writing-mode: vertical-lr;">
                  📋 设计稿 {{ project.plan_version ? `v${project.plan_version}` : '' }}
                </n-button>
              </template>
              展开设计稿面板
            </n-tooltip>
          </div>
        </div>
      </n-tab-pane>

      <n-tab-pane name="implement" tab="🔨 实施">
        <ImplementPanel :project="project" @status-changed="refreshProject" />
      </n-tab-pane>

      <n-tab-pane name="deploy" tab="🚀 部署">
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
import { useProjectStore } from '@/stores/project'
import ChatPanel from '@/components/ChatPanel.vue'
import PlanEditor from '@/components/PlanEditor.vue'
import ImplementPanel from '@/components/ImplementPanel.vue'
import DeployPanel from '@/components/DeployPanel.vue'
import SnapshotPanel from '@/components/SnapshotPanel.vue'

const route = useRoute()
const store = useProjectStore()
const activeTab = ref('discuss')
const showPlanPanel = ref(false)

const project = computed(() => store.currentProject)

// 动态布局: 讨论 & Plan 分栏
const splitLayoutStyle = computed(() => ({
  display: 'flex',
  gap: '16px',
  height: 'calc(100vh - 280px)',
  minHeight: '500px',
}))

const chatPanelStyle = computed(() => ({
  flex: showPlanPanel.value ? '1 1 60%' : '1',
  minWidth: '0',
  overflow: 'hidden',
}))

const currentStep = computed(() => {
  const map: Record<string, number> = {
    draft: 1, discussing: 2, planned: 3, implementing: 4,
    reviewing: 5, deploying: 6, deployed: 7, rolled_back: 7, closed: 7,
  }
  return map[project.value?.status || 'draft'] || 1
})

function statusType(s: string) {
  const m: Record<string, any> = {
    draft:'default', discussing:'info', planned:'warning', implementing:'warning',
    reviewing:'info', deploying:'warning', deployed:'success', rolled_back:'error',
  }
  return m[s] || 'default'
}

function statusLabel(s: string) {
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

onMounted(() => refreshProject())
watch(() => route.params.id, () => refreshProject())
</script>
