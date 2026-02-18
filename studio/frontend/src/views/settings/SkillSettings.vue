<template>
  <div>
    <!-- 顶部操作栏 -->
    <n-space justify="space-between" align="center" style="margin-bottom: 16px">
      <n-text depth="3">管理 AI 工作流技能 — 定义角色、对话策略、阶段流程和产出模板</n-text>
      <n-button type="primary" size="small" @click="openCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        创建新技能
      </n-button>
    </n-space>

    <!-- 技能卡片列表 -->
    <n-spin :show="store.loading">
      <n-grid :cols="1" :y-gap="12" v-if="store.skills.length">
        <n-gi v-for="skill in store.skills" :key="skill.id">
          <n-card size="small" style="background: #1a1a2e" hoverable>
            <n-space justify="space-between" align="center">
              <n-space align="center" :size="12">
                <span style="font-size: 24px">{{ skill.icon }}</span>
                <div>
                  <n-space align="center" :size="6">
                    <n-text strong>{{ skill.name }}</n-text>
                    <n-tag v-if="skill.is_builtin" size="tiny" type="info" round>内置</n-tag>
                    <n-tag v-if="!skill.is_enabled" size="tiny" type="warning" round>已禁用</n-tag>
                  </n-space>
                  <n-text depth="3" style="font-size: 12px; display: block; margin-top: 2px">
                    {{ skill.description }}
                  </n-text>
                </div>
              </n-space>
              <n-space :size="8">
                <n-switch
                  :value="skill.is_enabled"
                  size="small"
                  @update:value="toggleEnabled(skill, $event)"
                />
                <n-button size="tiny" quaternary @click="openEdit(skill)">
                  <template #icon><n-icon :component="CreateOutline" /></template>
                </n-button>
                <n-button size="tiny" quaternary @click="handleDuplicate(skill)">
                  <template #icon><n-icon :component="CopyOutline" /></template>
                </n-button>
                <n-popconfirm
                  v-if="!skill.is_builtin"
                  @positive-click="handleDelete(skill)"
                >
                  <template #trigger>
                    <n-button size="tiny" quaternary type="error">
                      <template #icon><n-icon :component="TrashOutline" /></template>
                    </n-button>
                  </template>
                  确定删除技能「{{ skill.name }}」？
                </n-popconfirm>
                <n-tooltip v-else>
                  <template #trigger>
                    <n-button size="tiny" quaternary disabled>
                      <template #icon><n-icon :component="TrashOutline" /></template>
                    </n-button>
                  </template>
                  内置技能不可删除
                </n-tooltip>
              </n-space>
            </n-space>
            <!-- 阶段预览 -->
            <n-space :size="4" style="margin-top: 8px">
              <n-tag
                v-for="(stage, idx) in skill.stages"
                :key="stage.key"
                size="tiny"
                :bordered="false"
                :type="idx === 0 ? 'default' : 'info'"
              >
                {{ stage.label }}
              </n-tag>
            </n-space>
          </n-card>
        </n-gi>
      </n-grid>
      <n-empty v-else description="暂无技能配置" />
    </n-spin>

    <!-- 编辑 / 创建弹窗 -->
    <n-modal
      v-model:show="showEditor"
      preset="card"
      :title="editingSkill ? `编辑技能 — ${editingSkill.name}` : '创建新技能'"
      style="width: 800px; max-width: 95vw"
      :mask-closable="false"
    >
      <n-tabs type="line" animated :value="editorTab" @update:value="editorTab = $event">
        <!-- 基本信息 -->
        <n-tab-pane name="basic" tab="基本信息">
          <n-form :model="form" label-placement="left" label-width="100">
            <n-form-item label="技能名称">
              <n-input v-model:value="form.name" placeholder="如：需求分析、Bug 问诊" />
            </n-form-item>
            <n-form-item label="图标">
              <n-input v-model:value="form.icon" placeholder="Emoji 图标" style="width: 80px" />
            </n-form-item>
            <n-form-item label="描述">
              <n-input v-model:value="form.description" placeholder="简短描述技能用途" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- AI Prompt 配置 -->
        <n-tab-pane name="prompts" tab="AI 对话配置">
          <n-form label-placement="top">
            <n-form-item label="角色定义 (role_prompt)">
              <n-input
                v-model:value="form.role_prompt"
                type="textarea"
                :rows="4"
                placeholder="定义 AI 的身份和角色..."
              />
            </n-form-item>
            <n-form-item label="对话策略 (strategy_prompt)">
              <n-input
                v-model:value="form.strategy_prompt"
                type="textarea"
                :rows="8"
                placeholder="定义 AI 如何与用户对话..."
              />
            </n-form-item>
            <n-form-item label="工具使用策略 (tool_strategy_prompt)">
              <n-input
                v-model:value="form.tool_strategy_prompt"
                type="textarea"
                :rows="4"
                placeholder="留空则使用系统默认的工具策略"
              />
            </n-form-item>
            <n-form-item label="定稿提示 (finalization_prompt)">
              <n-input
                v-model:value="form.finalization_prompt"
                type="textarea"
                :rows="3"
                placeholder="定义定稿前的提示..."
              />
            </n-form-item>
            <n-form-item label="产出物生成模板 (output_generation_prompt)">
              <n-input
                v-model:value="form.output_generation_prompt"
                type="textarea"
                :rows="8"
                placeholder="模板变量: {discussion_summary}"
              />
              <template #feedback>
                <n-text depth="3" style="font-size: 12px">
                  使用 <code>{discussion_summary}</code> 作为讨论内容的占位符
                </n-text>
              </template>
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- 阶段配置 -->
        <n-tab-pane name="stages" tab="阶段流程">
          <n-text depth="3" style="margin-bottom: 12px; display: block">
            定义项目从创建到完成的阶段流程。key 对应后端 ProjectStatus 枚举值。
          </n-text>
          <n-dynamic-input
            v-model:value="form.stages"
            :on-create="() => ({ key: '', label: '', status: '' })"
          >
            <template #default="{ value: stage }">
              <n-space :size="8" style="width: 100%">
                <n-input v-model:value="stage.key" placeholder="key (如 draft)" style="width: 140px" />
                <n-input v-model:value="stage.label" placeholder="显示标签 (如 草稿)" style="width: 140px" />
                <n-select
                  v-model:value="stage.status"
                  :options="statusOptions"
                  placeholder="映射状态"
                  style="width: 160px"
                />
              </n-space>
            </template>
          </n-dynamic-input>
        </n-tab-pane>

        <!-- UI 文案 -->
        <n-tab-pane name="labels" tab="UI 文案">
          <n-form :model="form.ui_labels" label-placement="left" label-width="140">
            <n-form-item label="项目称呼">
              <n-input v-model:value="form.ui_labels.project_noun" placeholder="需求 / 缺陷 / 审查" />
            </n-form-item>
            <n-form-item label="创建对话框标题">
              <n-input v-model:value="form.ui_labels.create_title" placeholder="🆕 新建需求" />
            </n-form-item>
            <n-form-item label="标题 placeholder">
              <n-input v-model:value="form.ui_labels.create_placeholder" placeholder="简明描述需求目标" />
            </n-form-item>
            <n-form-item label="描述 placeholder">
              <n-input v-model:value="form.ui_labels.description_placeholder" placeholder="详细描述..." />
            </n-form-item>
            <n-form-item label="产出物名称">
              <n-input v-model:value="form.ui_labels.output_noun" placeholder="需求规格书 / 诊断书" />
            </n-form-item>
            <n-form-item label="产出物 Tab 标签">
              <n-input v-model:value="form.ui_labels.output_tab_label" placeholder="📋 设计稿" />
            </n-form-item>
            <n-form-item label="定稿动作名称">
              <n-input v-model:value="form.ui_labels.finalize_action" placeholder="敲定方案 / 生成诊断书" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- System Prompt 预览 -->
        <n-tab-pane name="preview" tab="🔍 预览">
          <n-text depth="3" style="display: block; margin-bottom: 8px; font-size: 12px">
            实时预览 AI 收到的 system prompt 组装顺序（不含项目结构和代码摘要等动态部分）
          </n-text>
          <div class="prompt-preview">
            <div v-for="(section, i) in previewSections" :key="i" class="preview-section">
              <n-text depth="3" style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px">
                {{ section.label }}
              </n-text>
              <n-text v-if="section.content" tag="pre" style="font-size: 12px; white-space: pre-wrap; word-break: break-word; margin: 4px 0 0; line-height: 1.5; color: #ddd">{{ section.content }}</n-text>
              <n-text v-else depth="3" style="font-size: 12px; font-style: italic">（空 — 使用系统默认）</n-text>
            </div>
            <n-divider style="margin: 8px 0" />
            <n-text depth="3" style="font-size: 11px">
              ℹ️ 实际运行时还会插入：项目结构、关键目录、关键文件摘要、{{ form.ui_labels.project_noun || '需求' }}上下文
            </n-text>
          </div>
        </n-tab-pane>
      </n-tabs>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showEditor = false">取消</n-button>
          <n-button type="primary" @click="handleSave" :loading="saving">
            {{ editingSkill ? '保存' : '创建' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { AddOutline, CreateOutline, CopyOutline, TrashOutline } from '@vicons/ionicons5'
import { useSkillStore, type Skill } from '@/stores/skill'

const message = useMessage()
const store = useSkillStore()

const showEditor = ref(false)
const editorTab = ref('basic')
const editingSkill = ref<Skill | null>(null)
const saving = ref(false)

const statusOptions = [
  { label: 'draft', value: 'draft' },
  { label: 'discussing', value: 'discussing' },
  { label: 'planned', value: 'planned' },
  { label: 'implementing', value: 'implementing' },
  { label: 'reviewing', value: 'reviewing' },
  { label: 'deploying', value: 'deploying' },
  { label: 'deployed', value: 'deployed' },
  { label: 'rolled_back', value: 'rolled_back' },
  { label: 'closed', value: 'closed' },
]

const defaultForm = () => ({
  name: '',
  icon: '🎯',
  description: '',
  role_prompt: '',
  strategy_prompt: '',
  tool_strategy_prompt: '',
  finalization_prompt: '',
  output_generation_prompt: '',
  stages: [
    { key: 'draft', label: '草稿', status: 'draft' },
    { key: 'discussing', label: '讨论', status: 'discussing' },
    { key: 'planned', label: '定稿', status: 'planned' },
    { key: 'implementing', label: '实施', status: 'implementing' },
    { key: 'reviewing', label: '审核', status: 'reviewing' },
    { key: 'deploying', label: '部署', status: 'deploying' },
    { key: 'deployed', label: '完成', status: 'deployed' },
  ] as Array<{ key: string; label: string; status: string }>,
  ui_labels: {
    project_noun: '',
    create_title: '',
    create_placeholder: '',
    description_placeholder: '',
    output_noun: '',
    output_tab_label: '',
    finalize_action: '',
  } as Record<string, string>,
})

const form = reactive(defaultForm())

function openCreate() {
  editingSkill.value = null
  Object.assign(form, defaultForm())
  editorTab.value = 'basic'
  showEditor.value = true
}

function openEdit(skill: Skill) {
  editingSkill.value = skill
  Object.assign(form, {
    name: skill.name,
    icon: skill.icon,
    description: skill.description,
    role_prompt: skill.role_prompt,
    strategy_prompt: skill.strategy_prompt,
    tool_strategy_prompt: skill.tool_strategy_prompt,
    finalization_prompt: skill.finalization_prompt,
    output_generation_prompt: skill.output_generation_prompt,
    stages: JSON.parse(JSON.stringify(skill.stages || [])),
    ui_labels: { ...defaultForm().ui_labels, ...(skill.ui_labels || {}) },
  })
  editorTab.value = 'basic'
  showEditor.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    message.warning('请输入技能名称')
    return
  }
  saving.value = true
  try {
    const payload = { ...form }
    if (editingSkill.value) {
      await store.updateSkill(editingSkill.value.id, payload)
      message.success('技能已更新')
    } else {
      await store.createSkill(payload)
      message.success('技能已创建')
    }
    showEditor.value = false
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(skill: Skill, enabled: boolean) {
  try {
    await store.updateSkill(skill.id, { is_enabled: enabled })
    message.success(enabled ? '已启用' : '已禁用')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDuplicate(skill: Skill) {
  try {
    await store.duplicateSkill(skill.id)
    message.success('技能已复制')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '复制失败')
  }
}

async function handleDelete(skill: Skill) {
  try {
    await store.deleteSkill(skill.id)
    message.success('技能已删除')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

const previewSections = computed(() => [
  { label: '🎭 角色设定 (role_prompt)', content: form.role_prompt },
  { label: '📐 策略指引 (strategy_prompt)', content: form.strategy_prompt },
  { label: '🔧 工具使用策略 (tool_strategy_prompt)', content: form.tool_strategy_prompt },
  { label: '✅ 敲定 / 终稿指令 (finalization_prompt)', content: form.finalization_prompt },
  { label: '📄 产出生成模板 (output_generation_prompt)', content: form.output_generation_prompt },
])

onMounted(() => {
  store.fetchSkills()
})
</script>

<style scoped>
.prompt-preview {
  background: #1a1a2e;
  border-radius: 6px;
  padding: 12px 16px;
  max-height: 60vh;
  overflow-y: auto;
}
.preview-section {
  margin-bottom: 12px;
}
.preview-section:last-of-type {
  margin-bottom: 0;
}
</style>
