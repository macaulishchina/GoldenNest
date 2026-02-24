<template>
  <n-card title="🎨 AI 技能管理" :bordered="false" style="margin-top: 16px">
    <template #header-extra>
      <n-space :size="8">
        <n-button size="small" quaternary @click="loadSkills" :loading="loading">刷新</n-button>
        <n-button size="small" type="primary" @click="openCreate">添加技能</n-button>
      </n-space>
    </template>

    <n-alert type="info" :bordered="false" style="margin-bottom: 16px">
      每个 AI 功能可配置多个技能实现（提示词），但同一功能仅一个可激活。激活的技能会覆盖代码中的默认提示词。
    </n-alert>

    <n-spin :show="loading">
      <div v-if="groupedSkills.length === 0 && !loading" style="text-align: center; padding: 30px; color: var(--theme-text-tertiary)">
        暂无技能配置，点击「添加技能」或运行 seed 脚本初始化
      </div>

      <div v-for="group in groupedSkills" :key="group.key" class="skill-group">
        <div class="skill-group-title">
          {{ group.label }}
          <n-tag v-if="group.activeSkill" size="tiny" type="success" :bordered="false" style="margin-left: 8px">
            激活: {{ group.activeSkill }}
          </n-tag>
          <n-tag v-else size="tiny" type="warning" :bordered="false" style="margin-left: 8px">
            未激活
          </n-tag>
        </div>

        <div class="skill-list">
          <div v-for="skill in group.skills" :key="skill.id" class="skill-item" :class="{ 'skill-active': skill.is_active }">
            <div class="skill-item-left">
              <div class="skill-name">
                <n-tag :type="skill.is_active ? 'success' : 'default'" size="small" :bordered="false">
                  {{ skill.is_active ? '✅ 激活' : '待机' }}
                </n-tag>
                <span style="margin-left: 6px; font-weight: 500">{{ skill.name }}</span>
              </div>
              <div class="skill-desc">{{ skill.description || '无描述' }}</div>
              <div class="skill-meta">
                <n-tag size="tiny" :bordered="false">{{ skill.function_key }}</n-tag>
                <span v-if="skill.attachments?.length" class="skill-attachment-count">
                  📎 {{ skill.attachments.length }} 个附件
                </span>
              </div>
            </div>
            <div class="skill-item-right">
              <n-button v-if="!skill.is_active" size="small" text type="success" @click="handleActivate(skill)">激活</n-button>
              <n-button v-else size="small" text type="warning" @click="handleDeactivate(skill)">停用</n-button>
              <n-button size="small" text type="primary" @click="openEdit(skill)">编辑</n-button>
              <n-button size="small" text @click="handleDuplicate(skill)">复制</n-button>
              <n-popconfirm @positive-click="handleDelete(skill)">
                <template #trigger>
                  <n-button size="small" text type="error" :disabled="skill.is_active">删除</n-button>
                </template>
                确定删除技能「{{ skill.name }}」？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </div>
    </n-spin>
  </n-card>

  <!-- 编辑/创建 Modal -->
  <n-modal v-model:show="showEditModal" :title="editingSkill ? `编辑技能: ${editingSkill.name}` : '创建新技能'" preset="dialog" style="width: 700px; max-width: 95vw">
    <n-form label-placement="top" :model="editForm">
      <n-grid :cols="2" :x-gap="12">
        <n-gi>
          <n-form-item label="功能标识 (function_key)" required>
            <n-select
              v-model:value="editForm.function_key"
              :options="functionKeyOptions"
              placeholder="选择功能"
              filterable
              :disabled="!!editingSkill"
            />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="技能名称" required>
            <n-input v-model:value="editForm.name" placeholder="如：默认提示词 v1" />
          </n-form-item>
        </n-gi>
      </n-grid>

      <n-form-item label="描述">
        <n-input v-model:value="editForm.description" placeholder="简要说明此技能的特点" />
      </n-form-item>

      <n-form-item label="System Prompt（系统提示词）" required>
        <div style="width: 100%">
          <n-input
            v-model:value="editForm.system_prompt"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 12 }"
            placeholder="使用 $variable 插入动态变量"
            style="font-family: 'Fira Code', 'Cascadia Code', monospace; font-size: 13px"
          />
          <div v-if="currentInputVars.length" class="var-hints">
            <span class="var-hints-label">可用变量：</span>
            <n-tag v-for="v in currentInputVars" :key="v.name" size="tiny" :bordered="false" type="info" class="var-tag" @click="insertVar(v.name, 'system')">
              ${{ v.name }}
              <template #icon><span style="font-size: 10px">{{ v.label }}</span></template>
            </n-tag>
          </div>
        </div>
      </n-form-item>

      <n-form-item label="User Prompt Template（用户提示词模板，可选）">
        <div style="width: 100%">
          <n-input
            v-model:value="editForm.user_prompt_template"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 10 }"
            placeholder="留空则使用代码中的 user_prompt。使用 $variable 插入动态变量"
            style="font-family: 'Fira Code', 'Cascadia Code', monospace; font-size: 13px"
          />
        </div>
      </n-form-item>

      <n-grid :cols="2" :x-gap="12">
        <n-gi>
          <n-form-item label="温度 (temperature)">
            <n-input-number v-model:value="editParams.temperature" :min="0" :max="2" :step="0.1" placeholder="默认" clearable style="width: 100%" />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="最大 Tokens">
            <n-input-number v-model:value="editParams.max_tokens" :min="100" :max="32000" :step="100" placeholder="默认" clearable style="width: 100%" />
          </n-form-item>
        </n-gi>
      </n-grid>

      <n-form-item label="创建后立即激活">
        <n-switch v-model:value="editForm.is_active" v-if="!editingSkill" />
        <span v-else style="color: var(--theme-text-tertiary); font-size: 13px">
          请使用列表中的「激活/停用」按钮
        </span>
      </n-form-item>
    </n-form>

    <template #action>
      <n-button @click="showEditModal = false">取消</n-button>
      <n-button type="primary" :loading="saving" @click="handleSave">
        {{ editingSkill ? '保存' : '创建' }}
      </n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { aiSkillApi, aiConfigApi } from '@/api'

const message = useMessage()

const loading = ref(false)
const saving = ref(false)
const skills = ref<any[]>([])
const functionRegistry = ref<any[]>([])
const showEditModal = ref(false)
const editingSkill = ref<any>(null)

// 编辑表单
const editForm = ref({
  function_key: '',
  name: '',
  description: '',
  system_prompt: '',
  user_prompt_template: '' as string | null,
  is_active: true,
  sort_order: 0,
})
const editParams = ref<{ temperature?: number | null; max_tokens?: number | null }>({
  temperature: null,
  max_tokens: null,
})

// function_key 选项
const functionKeyOptions = computed(() =>
  functionRegistry.value.map((fn: any) => ({
    label: `${fn.name} (${fn.key})`,
    value: fn.key,
  }))
)

// 当前选中功能的输入变量
const currentInputVars = computed(() => {
  const fn = functionRegistry.value.find((f: any) => f.key === editForm.value.function_key)
  return fn?.input_variables || []
})

// 按 function_key 分组
const groupedSkills = computed(() => {
  const groups: Record<string, { key: string; label: string; activeSkill: string | null; skills: any[] }> = {}

  for (const skill of skills.value) {
    if (!groups[skill.function_key]) {
      const fn = functionRegistry.value.find((f: any) => f.key === skill.function_key)
      groups[skill.function_key] = {
        key: skill.function_key,
        label: fn ? `${fn.name} (${skill.function_key})` : skill.function_key,
        activeSkill: null,
        skills: [],
      }
    }
    groups[skill.function_key].skills.push(skill)
    if (skill.is_active) {
      groups[skill.function_key].activeSkill = skill.name
    }
  }

  return Object.values(groups).sort((a, b) => a.key.localeCompare(b.key))
})

function insertVar(name: string, _target: string) {
  // Simple: just copy to clipboard
  navigator.clipboard?.writeText(`$${name}`)
  message.info(`已复制 $${name} 到剪贴板`)
}

async function loadSkills() {
  loading.value = true
  try {
    const [skillRes, registryRes] = await Promise.all([
      aiSkillApi.list(),
      aiConfigApi.getFunctionRegistry(),
    ])
    skills.value = skillRes.data
    functionRegistry.value = registryRes.data
  } catch (e: any) {
    message.error('加载技能列表失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingSkill.value = null
  editForm.value = {
    function_key: '',
    name: '',
    description: '',
    system_prompt: '',
    user_prompt_template: null,
    is_active: true,
    sort_order: 0,
  }
  editParams.value = { temperature: null, max_tokens: null }
  showEditModal.value = true
}

function openEdit(skill: any) {
  editingSkill.value = skill
  editForm.value = {
    function_key: skill.function_key,
    name: skill.name,
    description: skill.description || '',
    system_prompt: skill.system_prompt || '',
    user_prompt_template: skill.user_prompt_template || null,
    is_active: skill.is_active,
    sort_order: skill.sort_order || 0,
  }
  // 解析 parameters JSON
  let params: any = {}
  if (skill.parameters) {
    try {
      params = typeof skill.parameters === 'string' ? JSON.parse(skill.parameters) : skill.parameters
    } catch { /* ignore */ }
  }
  editParams.value = {
    temperature: params.temperature ?? null,
    max_tokens: params.max_tokens ?? null,
  }
  showEditModal.value = true
}

async function handleSave() {
  if (!editForm.value.function_key || !editForm.value.name || !editForm.value.system_prompt) {
    message.warning('请填写必要字段')
    return
  }

  saving.value = true
  try {
    // 构建 parameters JSON
    const params: Record<string, any> = {}
    if (editParams.value.temperature != null) params.temperature = editParams.value.temperature
    if (editParams.value.max_tokens != null) params.max_tokens = editParams.value.max_tokens

    const payload: any = {
      ...editForm.value,
      user_prompt_template: editForm.value.user_prompt_template || null,
      parameters: Object.keys(params).length > 0 ? JSON.stringify(params) : null,
    }

    if (editingSkill.value) {
      await aiSkillApi.update(editingSkill.value.id, payload)
      message.success('技能已更新')
    } else {
      await aiSkillApi.create(payload)
      message.success('技能已创建')
    }

    showEditModal.value = false
    await loadSkills()
  } catch (e: any) {
    message.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function handleActivate(skill: any) {
  try {
    await aiSkillApi.activate(skill.id)
    message.success(`已激活「${skill.name}」`)
    await loadSkills()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '激活失败')
  }
}

async function handleDeactivate(skill: any) {
  try {
    await aiSkillApi.deactivate(skill.id)
    message.success(`已停用「${skill.name}」`)
    await loadSkills()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '停用失败')
  }
}

async function handleDuplicate(skill: any) {
  try {
    await aiSkillApi.duplicate(skill.id)
    message.success('技能已复制')
    await loadSkills()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '复制失败')
  }
}

async function handleDelete(skill: any) {
  try {
    await aiSkillApi.remove(skill.id)
    message.success('技能已删除')
    await loadSkills()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(loadSkills)
</script>

<style scoped>
.skill-group {
  margin-bottom: 20px;
}

.skill-group-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--theme-border, #e8e8e8);
  color: var(--theme-text-primary, #333);
  display: flex;
  align-items: center;
}

.skill-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skill-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--theme-card-bg, rgba(0, 0, 0, 0.02));
  transition: background 0.2s;
}

.skill-item:hover {
  background: var(--theme-hover-bg, rgba(24, 160, 88, 0.06));
}

.skill-active {
  border-left: 3px solid #18a058;
}

.skill-item-left {
  flex: 1;
  min-width: 0;
}

.skill-name {
  font-size: 14px;
  display: flex;
  align-items: center;
}

.skill-desc {
  font-size: 12px;
  color: var(--theme-text-tertiary, #999);
  margin-top: 2px;
}

.skill-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.skill-attachment-count {
  font-size: 11px;
  color: var(--theme-text-tertiary, #aaa);
}

.skill-item-right {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.var-hints {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.var-hints-label {
  font-size: 12px;
  color: var(--theme-text-tertiary, #999);
}

.var-tag {
  cursor: pointer;
}

.var-tag:hover {
  opacity: 0.8;
}
</style>
