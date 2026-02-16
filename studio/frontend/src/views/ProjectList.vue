<template>
  <div>
    <n-space justify="space-between" align="center" style="margin-bottom: 16px">
      <n-h3 style="margin: 0">📋 需求项目</n-h3>
      <n-button type="primary" @click="$router.push('/')">
        <template #icon><n-icon :component="AddOutline" /></template>
        新建需求
      </n-button>
    </n-space>

    <n-space style="margin-bottom: 16px">
      <n-select
        v-model:value="statusFilter"
        :options="filterOptions"
        placeholder="按状态筛选"
        clearable
        style="width: 180px"
      />
    </n-space>

    <n-spin :show="store.loading">
      <n-grid :cols="1" :y-gap="12" v-if="filteredProjects.length">
        <n-gi v-for="p in filteredProjects" :key="p.id">
          <n-card
            hoverable
            size="small"
            style="background: #16213e; cursor: pointer"
            @click="$router.push(`/projects/${p.id}`)"
          >
            <n-space justify="space-between" align="center">
              <n-space vertical :size="4">
                <n-space align="center">
                  <n-text strong style="font-size: 16px">{{ p.title }}</n-text>
                  <n-tag :type="statusType(p.status)" size="small" round>
                    {{ statusLabel(p.status) }}
                  </n-tag>
                </n-space>
                <n-text depth="3" style="font-size: 13px">
                  {{ p.description.slice(0, 120) }}{{ p.description.length > 120 ? '...' : '' }}
                </n-text>
              </n-space>
              <n-space align="center">
                <n-tag v-if="p.github_pr_number" size="small" :bordered="false" type="info">
                  PR #{{ p.github_pr_number }}
                </n-tag>
                <n-text depth="3" style="font-size: 12px">
                  💬 {{ p.message_count }} · {{ formatDate(p.updated_at) }}
                </n-text>
              </n-space>
            </n-space>
          </n-card>
        </n-gi>
      </n-grid>
      <n-empty v-else description="暂无项目" />
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { AddOutline } from '@vicons/ionicons5'
import { useProjectStore } from '@/stores/project'

const store = useProjectStore()
const statusFilter = ref<string | null>(null)

const filterOptions = [
  { label: '草稿', value: 'draft' },
  { label: '讨论中', value: 'discussing' },
  { label: '已定稿', value: 'planned' },
  { label: '实施中', value: 'implementing' },
  { label: '审核中', value: 'reviewing' },
  { label: '部署中', value: 'deploying' },
  { label: '已部署', value: 'deployed' },
  { label: '已回滚', value: 'rolled_back' },
]

const filteredProjects = computed(() => {
  if (!statusFilter.value) return store.projects
  return store.projects.filter(p => p.status === statusFilter.value)
})

function statusType(s: string) {
  const m: Record<string, any> = {
    draft:'default', discussing:'info', planned:'warning', implementing:'warning',
    reviewing:'info', deploying:'warning', deployed:'success', rolled_back:'error', closed:'default',
  }
  return m[s] || 'default'
}

function statusLabel(s: string) {
  const m: Record<string, string> = {
    draft:'草稿', discussing:'讨论中', planned:'已定稿', implementing:'实施中',
    reviewing:'审核中', deploying:'部署中', deployed:'已部署', rolled_back:'已回滚', closed:'已关闭',
  }
  return m[s] || s
}

function formatDate(d: string) {
  return new Date(d).toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' })
}

onMounted(() => store.fetchProjects())
</script>
