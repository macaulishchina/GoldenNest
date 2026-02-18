<template>
  <div>
    <n-space justify="space-between" align="center" style="margin-bottom: 16px">
      <n-h3 style="margin: 0">📋 项目</n-h3>
      <n-button type="primary" @click="$router.push('/')">
        <template #icon><n-icon :component="AddOutline" /></template>
        新建项目
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
      <n-select
        v-model:value="skillFilter"
        :options="skillFilterOptions"
        placeholder="按技能筛选"
        clearable
        style="width: 180px"
      />
      <n-switch v-model:value="showArchived" />
      <n-text depth="3" style="font-size: 12px">显示已归档</n-text>
    </n-space>

    <n-spin :show="store.loading">
      <n-list v-if="filteredProjects.length" bordered style="background: #16213e">
        <n-list-item
          v-for="p in filteredProjects"
          :key="p.id"
          style="padding: 0; position: relative"
        >
          <LogItem :item="p" @click="$router.push(`/projects/${p.id}`)" />
          <!-- 归档 / PR 角标区 -->
          <div class="item-actions">
            <n-tag v-if="p.github_pr_number" size="small" :bordered="false" type="info" style="cursor:default">
              PR #{{ p.github_pr_number }}
            </n-tag>
            <n-button
              size="tiny"
              :type="p.is_archived ? 'warning' : 'default'"
              @click.stop="toggleArchive(p)"
            >
              {{ p.is_archived ? '取消归档' : '归档' }}
            </n-button>
          </div>
        </n-list-item>
      </n-list>
      <n-empty v-else description="暂无项目" />
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { AddOutline } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'
import { useProjectStore } from '@/stores/project'
import { useSkillStore } from '@/stores/skill'
import LogItem from '@/components/LogItem.vue'

const store = useProjectStore()
const skillStore = useSkillStore()
const message = useMessage()
const statusFilter = ref<string | null>(null)
const skillFilter = ref<number | null>(null)
const showArchived = ref(false)

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

const skillFilterOptions = computed(() =>
  skillStore.skills.map(s => ({ label: `${s.icon} ${s.name}`, value: s.id }))
)

const filteredProjects = computed(() => {
  let list = store.projects
  if (statusFilter.value) list = list.filter(p => p.status === statusFilter.value)
  if (skillFilter.value) list = list.filter(p => p.skill_id === skillFilter.value)
  return list
})

function formatDate(d: string) {
  return new Date(d).toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' })
}

async function toggleArchive(p: any) {
  const nextArchived = !p.is_archived
  try {
    await store.updateProject(p.id, { is_archived: nextArchived })
    message.success(nextArchived ? '已归档' : '已取消归档')
    await store.fetchProjects({ include_archived: showArchived.value })
  } catch {
    message.error('操作失败')
  }
}

onMounted(() => {
  store.fetchProjects()
  skillStore.fetchSkills()
})
watch(showArchived, (val) => {
  store.fetchProjects({ include_archived: val })
})
</script>

<style scoped>
/* 使 LogItem 撑满 n-list-item，并把 action 按钮绝对定位在右下 */
:deep(.n-list-item) {
  padding: 0 !important;
}
.item-actions {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  gap: 8px;
  align-items: center;
  pointer-events: auto;
  z-index: 1;
}
</style>
