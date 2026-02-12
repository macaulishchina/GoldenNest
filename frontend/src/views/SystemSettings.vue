<template>
  <div class="system-settings">
    <n-card title="🤖 AI 服务商管理" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="showAddModal = true">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加服务商
        </n-button>
      </template>

      <!-- AI 状态概览 -->
      <n-alert :type="aiStatus.configured ? 'success' : 'warning'" style="margin-bottom: 16px">
        <template #header>
          当前 AI 服务状态
        </template>
        <span v-if="aiStatus.configured">
          ✅ 已配置 — {{ aiStatus.provider_name }} / {{ aiStatus.model }}
          <n-tag :bordered="false" size="small" type="info" style="margin-left: 8px">
            {{ aiStatus.source === 'database' ? '页面配置' : '环境变量' }}
          </n-tag>
        </span>
        <span v-else>⚠️ 未配置 AI 服务，图片识别等功能不可用</span>
      </n-alert>

      <!-- 服务商列表 -->
      <n-spin :show="loading">
        <div v-if="providers.length === 0 && !loading" style="text-align: center; padding: 40px; color: var(--theme-text-tertiary)">
          暂无已配置的 AI 服务商，点击右上角「添加服务商」开始配置
        </div>
        
        <n-space vertical :size="12">
          <n-card
            v-for="p in providers"
            :key="p.id"
            size="small"
            :bordered="true"
            :style="{ borderLeft: p.is_active ? '3px solid #18a058' : '3px solid transparent' }"
          >
            <div class="provider-card">
              <div class="provider-header">
                <div class="provider-title">
                  <n-tag :type="p.is_active ? 'success' : (p.is_enabled ? 'default' : 'error')" size="small" :bordered="false">
                    {{ p.is_active ? '✅ 活跃' : (p.is_enabled ? '待机' : '已禁用') }}
                  </n-tag>
                  <span class="provider-name">{{ p.name }}</span>
                  <n-tag size="tiny" :bordered="false" type="info">{{ p.provider_type }}</n-tag>
                </div>
                <n-space :size="4">
                  <n-button v-if="!p.is_active && p.is_enabled" size="small" type="success" ghost @click="handleActivate(p)">
                    激活
                  </n-button>
                  <n-button v-if="p.is_active" size="small" type="warning" ghost @click="handleDeactivate(p)">
                    取消激活
                  </n-button>
                  <n-button size="small" ghost @click="openEditModal(p)">编辑</n-button>
                  <n-popconfirm @positive-click="handleDelete(p)">
                    <template #trigger>
                      <n-button size="small" type="error" ghost>删除</n-button>
                    </template>
                    确定删除服务商「{{ p.name }}」？
                  </n-popconfirm>
                </n-space>
              </div>
              
              <div class="provider-info">
                <div class="info-row">
                  <span class="info-label">Base URL:</span>
                  <span class="info-value">{{ p.base_url }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">API Key:</span>
                  <span class="info-value">{{ p.api_key_masked || '未配置' }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">当前模型:</span>
                  <n-space align="center" :size="8">
                    <span class="info-value">{{ p.default_model || '未选择' }}</span>
                    <n-button size="tiny" text type="primary" @click="openModelSelector(p)" :loading="modelLoadingId === p.id">
                      选择模型
                    </n-button>
                  </n-space>
                </div>
              </div>
            </div>
          </n-card>
        </n-space>
      </n-spin>
    </n-card>

    <!-- 添加/编辑服务商 Modal -->
    <n-modal v-model:show="showAddModal" :title="editingProvider ? '编辑服务商' : '添加 AI 服务商'" preset="dialog" style="width: 520px">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100px">
        <!-- 模板选择（仅新建时） -->
        <n-form-item v-if="!editingProvider" label="服务商模板">
          <n-select
            v-model:value="selectedTemplate"
            :options="templateOptions"
            placeholder="选择预定义模板快速填充"
            clearable
            @update:value="handleTemplateChange"
          />
        </n-form-item>

        <n-form-item label="名称" path="name">
          <n-input v-model:value="formData.name" placeholder="如：通义千问、OpenAI" />
        </n-form-item>

        <n-form-item label="类型标识" path="provider_type">
          <n-input v-model:value="formData.provider_type" placeholder="如：qwen, openai, deepseek" :disabled="!!editingProvider" />
        </n-form-item>

        <n-form-item label="Base URL" path="base_url">
          <n-input v-model:value="formData.base_url" placeholder="https://api.example.com/v1" />
        </n-form-item>

        <n-form-item label="API Key" path="api_key">
          <n-input
            v-model:value="formData.api_key"
            type="password"
            show-password-on="click"
            :placeholder="editingProvider ? '留空则不修改' : '输入 API Key'"
          />
        </n-form-item>

        <n-form-item label="默认模型" path="default_model">
          <n-input v-model:value="formData.default_model" placeholder="如：qwen-vl-plus, gpt-4o-mini" />
        </n-form-item>
      </n-form>

      <template #action>
        <n-space>
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSaveProvider">
            {{ editingProvider ? '保存' : '添加' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 模型选择 Modal -->
    <n-modal v-model:show="showModelModal" title="选择模型" preset="dialog" style="width: 600px">
      <n-spin :show="modelsLoading">
        <div v-if="modelList.length === 0 && !modelsLoading" style="text-align: center; padding: 20px; color: var(--theme-text-tertiary)">
          无法获取模型列表，请检查 API Key 和 Base URL 是否正确
        </div>

        <!-- 搜索 -->
        <n-input
          v-if="modelList.length > 0"
          v-model:value="modelSearch"
          placeholder="搜索模型..."
          clearable
          style="margin-bottom: 12px"
        />

        <div class="model-list" v-if="modelList.length > 0">
          <div
            v-for="m in filteredModels"
            :key="m.id"
            class="model-item"
            :class="{ active: m.id === modelSelectingProvider?.default_model }"
            @click="handleSelectModel(m.id)"
          >
            <div class="model-name">{{ m.id }}</div>
            <div class="model-owner" v-if="m.owned_by">{{ m.owned_by }}</div>
          </div>
        </div>
      </n-spin>
    </n-modal>

    <!-- ==================== 功能级模型配置 ==================== -->
    <n-card title="🎯 功能级模型配置" :bordered="false" style="margin-top: 16px">
      <template #header-extra>
        <n-button size="small" quaternary @click="loadFunctionConfigs" :loading="fnLoading">
          刷新
        </n-button>
      </template>

      <n-alert type="info" :bordered="false" style="margin-bottom: 16px">
        可为每个 AI 功能单独指定服务商和模型。未配置的功能将使用上方全局活跃服务商的默认模型。
      </n-alert>

      <n-spin :show="fnLoading">
        <div v-if="fnGroups.length === 0 && !fnLoading" style="text-align: center; padding: 30px; color: var(--theme-text-tertiary)">
          暂无功能注册信息
        </div>

        <div v-for="group in fnGroups" :key="group.key" class="fn-group">
          <div class="fn-group-title">{{ group.icon }} {{ group.name }}</div>
          <div class="fn-list">
            <div v-for="fn in group.functions" :key="fn.key" class="fn-item">
              <div class="fn-item-left">
                <div class="fn-name">
                  {{ fn.name }}
                  <n-tag v-if="!fn.is_enabled" size="tiny" type="error" :bordered="false" style="margin-left: 6px">已禁用</n-tag>
                  <n-tag v-else-if="fn.source === 'function'" size="tiny" type="success" :bordered="false" style="margin-left: 6px">自定义</n-tag>
                </div>
                <div class="fn-desc">{{ fn.description }}</div>
                <div class="fn-model-info">
                  <n-tag size="tiny" :bordered="false" :type="fn.is_enabled ? 'info' : 'default'">
                    {{ fn.resolved_model || '未配置' }}
                  </n-tag>
                  <span class="fn-capability">{{ capabilityLabel(fn.capability) }}</span>
                </div>
              </div>
              <div class="fn-item-right">
                <n-button size="small" text type="primary" @click="openFnConfigModal(fn)">
                  配置
                </n-button>
                <n-button v-if="fn.source === 'function'" size="small" text type="warning" @click="handleResetFnConfig(fn)">
                  重置
                </n-button>
              </div>
            </div>
          </div>
        </div>
      </n-spin>
    </n-card>

    <!-- 功能模型配置 Modal -->
    <n-modal v-model:show="showFnConfigModal" :title="`配置: ${fnConfigTarget?.name || ''}`" preset="dialog" style="width: 500px">
      <n-form label-placement="left" label-width="90px">
        <n-form-item label="服务商">
          <n-select
            v-model:value="fnConfigForm.provider_id"
            :options="providerOptionsForFn"
            placeholder="使用全局默认"
            clearable
          />
        </n-form-item>

        <n-form-item label="模型名称">
          <n-input-group>
            <n-input v-model:value="fnConfigForm.model_name" placeholder="填写模型名称" style="flex: 1" />
            <n-button @click="openFnModelPicker" :loading="fnModelPickerLoading" :disabled="!fnConfigForm.provider_id && providers.length === 0">
              选择
            </n-button>
          </n-input-group>
        </n-form-item>

        <n-form-item label="启用状态">
          <n-switch v-model:value="fnConfigForm.is_enabled" />
          <span style="margin-left: 8px; font-size: 12px; color: var(--theme-text-tertiary)">
            禁用后该功能将不可用
          </span>
        </n-form-item>

        <div v-if="fnConfigTarget" style="margin-top: 8px; font-size: 12px; color: var(--theme-text-tertiary)">
          <div>默认模型：{{ fnConfigTarget.default_model || '跟随全局' }}</div>
          <div v-if="fnConfigTarget.alternative_models?.length">
            推荐模型：{{ fnConfigTarget.alternative_models.join('、') }}
          </div>
        </div>
      </n-form>

      <template #action>
        <n-space>
          <n-button @click="showFnConfigModal = false">取消</n-button>
          <n-button type="primary" :loading="fnConfigSaving" @click="handleSaveFnConfig">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 功能模型选择 Modal -->
    <n-modal v-model:show="showFnModelPicker" title="选择模型" preset="dialog" style="width: 600px">
      <n-spin :show="fnModelPickerLoading">
        <n-input
          v-if="fnPickerModels.length > 0"
          v-model:value="fnModelSearchText"
          placeholder="搜索模型..."
          clearable
          style="margin-bottom: 12px"
        />
        <div v-if="fnPickerModels.length === 0 && !fnModelPickerLoading" style="text-align: center; padding: 20px; color: var(--theme-text-tertiary)">
          无法获取模型列表
        </div>
        <div class="model-list" v-if="fnPickerModels.length > 0">
          <div
            v-for="m in fnFilteredPickerModels"
            :key="m.id"
            class="model-item"
            :class="{ active: m.id === fnConfigForm.model_name }"
            @click="fnConfigForm.model_name = m.id; showFnModelPicker = false"
          >
            <div class="model-name">{{ m.id }}</div>
            <div class="model-owner" v-if="m.owned_by">{{ m.owned_by }}</div>
          </div>
        </div>
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { aiConfigApi } from '@/api'

const message = useMessage()

// 状态
const loading = ref(false)
const saving = ref(false)
const providers = ref<any[]>([])
const templates = ref<any[]>([])
const aiStatus = ref<any>({ configured: false })
const showAddModal = ref(false)
const editingProvider = ref<any>(null)
const selectedTemplate = ref<string | null>(null)

// 模型选择
const showModelModal = ref(false)
const modelList = ref<any[]>([])
const modelsLoading = ref(false)
const modelSearch = ref('')
const modelSelectingProvider = ref<any>(null)
const modelLoadingId = ref<number | null>(null)

// 表单
const formRef = ref()
const formData = ref({
  name: '',
  provider_type: '',
  api_key: '',
  base_url: '',
  default_model: ''
})
const formRules = {
  name: { required: true, message: '请输入服务商名称', trigger: 'blur' },
  provider_type: { required: true, message: '请输入类型标识', trigger: 'blur' },
  base_url: { required: true, message: '请输入 Base URL', trigger: 'blur' }
}

// 模板选项
const templateOptions = computed(() =>
  templates.value.map(t => ({
    label: `${t.name} (${t.provider_type})`,
    value: t.provider_type
  }))
)

// 过滤模型
const filteredModels = computed(() => {
  if (!modelSearch.value) return modelList.value
  const q = modelSearch.value.toLowerCase()
  return modelList.value.filter(m => m.id.toLowerCase().includes(q))
})

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const [providersRes, statusRes] = await Promise.all([
      aiConfigApi.listProviders(),
      aiConfigApi.getStatus()
    ])
    providers.value = providersRes.data
    aiStatus.value = statusRes.data
  } catch (e: any) {
    if (e.response?.status !== 403) {
      message.error('加载配置失败')
    }
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const res = await aiConfigApi.getTemplates()
    templates.value = res.data
  } catch (e) {
    console.error('加载模板失败', e)
  }
}

// 模板切换
function handleTemplateChange(type: string | null) {
  if (!type) return
  const tpl = templates.value.find(t => t.provider_type === type)
  if (tpl) {
    formData.value.name = tpl.name
    formData.value.provider_type = tpl.provider_type
    formData.value.base_url = tpl.base_url
    formData.value.default_model = tpl.default_model
  }
}

// 打开编辑
function openEditModal(p: any) {
  editingProvider.value = p
  formData.value = {
    name: p.name,
    provider_type: p.provider_type,
    api_key: '',
    base_url: p.base_url,
    default_model: p.default_model
  }
  showAddModal.value = true
}

// 保存
async function handleSaveProvider() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  
  saving.value = true
  try {
    if (editingProvider.value) {
      // 编辑
      const payload: any = {
        name: formData.value.name,
        base_url: formData.value.base_url,
        default_model: formData.value.default_model
      }
      if (formData.value.api_key) {
        payload.api_key = formData.value.api_key
      }
      await aiConfigApi.updateProvider(editingProvider.value.id, payload)
      message.success('已更新')
    } else {
      // 新建
      await aiConfigApi.createProvider(formData.value)
      message.success('已添加')
    }
    showAddModal.value = false
    editingProvider.value = null
    resetForm()
    await loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

function resetForm() {
  formData.value = { name: '', provider_type: '', api_key: '', base_url: '', default_model: '' }
  selectedTemplate.value = null
}

// 激活
async function handleActivate(p: any) {
  try {
    await aiConfigApi.activateProvider(p.id)
    message.success(`已激活: ${p.name}`)
    await loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '激活失败')
  }
}

// 取消激活
async function handleDeactivate(p: any) {
  try {
    await aiConfigApi.deactivateProvider(p.id)
    message.success('已取消激活，将使用环境变量配置')
    await loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

// 删除
async function handleDelete(p: any) {
  try {
    await aiConfigApi.deleteProvider(p.id)
    message.success('已删除')
    await loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

// 模型选择
async function openModelSelector(p: any) {
  modelSelectingProvider.value = p
  modelSearch.value = ''
  modelList.value = []
  showModelModal.value = true
  modelsLoading.value = true
  modelLoadingId.value = p.id
  try {
    const res = await aiConfigApi.fetchModels(p.id)
    modelList.value = res.data
  } catch (e: any) {
    message.error(e.response?.data?.detail || '获取模型列表失败')
  } finally {
    modelsLoading.value = false
    modelLoadingId.value = null
  }
}

async function handleSelectModel(modelId: string) {
  if (!modelSelectingProvider.value) return
  try {
    await aiConfigApi.setModel(modelSelectingProvider.value.id, modelId)
    message.success(`已切换模型: ${modelId}`)
    showModelModal.value = false
    await loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '切换模型失败')
  }
}

// Modal 关闭时重置
function onModalClose() {
  editingProvider.value = null
  resetForm()
}

// 监听 modal 关闭
watch(showAddModal, (val) => {
  if (!val) onModalClose()
})

onMounted(() => {
  loadData()
  loadTemplates()
  loadFunctionConfigs()
})

// ==================== 功能级模型配置 ====================
const fnLoading = ref(false)
const fnConfigs = ref<any[]>([])
const fnGroups = ref<any[]>([])
const showFnConfigModal = ref(false)
const fnConfigTarget = ref<any>(null)
const fnConfigSaving = ref(false)
const fnConfigForm = ref({
  provider_id: null as number | null,
  model_name: '',
  is_enabled: true
})

// 功能模型选择器
const showFnModelPicker = ref(false)
const fnModelPickerLoading = ref(false)
const fnPickerModels = ref<any[]>([])
const fnModelSearchText = ref('')

const fnFilteredPickerModels = computed(() => {
  if (!fnModelSearchText.value) return fnPickerModels.value
  const q = fnModelSearchText.value.toLowerCase()
  return fnPickerModels.value.filter((m: any) => m.id.toLowerCase().includes(q))
})

const providerOptionsForFn = computed(() =>
  providers.value
    .filter((p: any) => p.is_enabled)
    .map((p: any) => ({ label: `${p.name} (${p.provider_type})`, value: p.id }))
)

function capabilityLabel(cap: string) {
  const map: Record<string, string> = {
    text_chat: '💬 文本',
    text_to_json: '📋 JSON',
    vision: '👁 视觉',
    audio_transcription: '🎤 语音',
    model_listing: '📡 列表'
  }
  return map[cap] || cap
}

async function loadFunctionConfigs() {
  fnLoading.value = true
  try {
    const res = await aiConfigApi.getFunctionConfigs()
    fnConfigs.value = res.data.functions || []

    // 按组分类
    const groupMap: Record<string, any> = {}
    for (const fn of fnConfigs.value) {
      const gKey = fn.group || 'other'
      if (!groupMap[gKey]) {
        groupMap[gKey] = {
          key: gKey,
          name: fn.group_name || gKey,
          icon: fn.group_icon || '📦',
          order: fn.group_order ?? 99,
          functions: []
        }
      }
      groupMap[gKey].functions.push(fn)
    }

    fnGroups.value = Object.values(groupMap).sort((a: any, b: any) => a.order - b.order)
  } catch (e: any) {
    if (e.response?.status !== 403) {
      console.error('加载功能配置失败', e)
    }
  } finally {
    fnLoading.value = false
  }
}

function openFnConfigModal(fn: any) {
  fnConfigTarget.value = fn
  fnConfigForm.value = {
    provider_id: fn.config_provider_id || null,
    model_name: fn.config_model_name || fn.default_model || '',
    is_enabled: fn.is_enabled !== false
  }
  showFnConfigModal.value = true
}

async function handleSaveFnConfig() {
  if (!fnConfigTarget.value) return
  fnConfigSaving.value = true
  try {
    await aiConfigApi.updateFunctionConfig(fnConfigTarget.value.key, {
      provider_id: fnConfigForm.value.provider_id,
      model_name: fnConfigForm.value.model_name,
      is_enabled: fnConfigForm.value.is_enabled
    })
    message.success('已保存功能配置')
    showFnConfigModal.value = false
    await loadFunctionConfigs()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    fnConfigSaving.value = false
  }
}

async function handleResetFnConfig(fn: any) {
  try {
    await aiConfigApi.resetFunctionConfig(fn.key)
    message.success(`已重置「${fn.name}」为全局默认`)
    await loadFunctionConfigs()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '重置失败')
  }
}

async function openFnModelPicker() {
  fnModelSearchText.value = ''
  fnPickerModels.value = []
  fnModelPickerLoading.value = true
  showFnModelPicker.value = true

  // 确定使用哪个 provider 的模型列表
  const pid = fnConfigForm.value.provider_id
  const targetProvider = pid
    ? providers.value.find((p: any) => p.id === pid)
    : providers.value.find((p: any) => p.is_active)

  if (!targetProvider) {
    fnModelPickerLoading.value = false
    message.warning('请先选择服务商或确保有活跃的全局服务商')
    return
  }

  try {
    const res = await aiConfigApi.fetchModels(targetProvider.id)
    fnPickerModels.value = res.data
  } catch (e: any) {
    message.error('获取模型列表失败')
  } finally {
    fnModelPickerLoading.value = false
  }
}
</script>

<style scoped>
.system-settings {
  max-width: 900px;
  margin: 0 auto;
  padding: 16px;
}

.provider-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.provider-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.provider-name {
  font-weight: 600;
  font-size: 15px;
}

.provider-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--theme-text-secondary, #666);
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-label {
  color: var(--theme-text-tertiary, #999);
  min-width: 70px;
  flex-shrink: 0;
}

.info-value {
  word-break: break-all;
}

.model-list {
  max-height: 400px;
  overflow-y: auto;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.model-item:hover {
  background: rgba(24, 160, 88, 0.08);
}

.model-item.active {
  background: rgba(24, 160, 88, 0.12);
  font-weight: 600;
}

.model-name {
  font-size: 13px;
}

.model-owner {
  font-size: 12px;
  color: var(--theme-text-tertiary, #999);
}

@media (max-width: 768px) {
  .system-settings {
    padding: 8px;
  }
  
  .provider-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }

  .fn-item {
    flex-direction: column;
    align-items: flex-start !important;
  }

  .fn-item-right {
    margin-top: 6px;
    align-self: flex-end;
  }
}

/* ========== 功能级模型配置 ========== */
.fn-group {
  margin-bottom: 20px;
}

.fn-group-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--theme-border, #e8e8e8);
  color: var(--theme-text-primary, #333);
}

.fn-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fn-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--theme-card-bg, rgba(0, 0, 0, 0.02));
  transition: background 0.2s;
}

.fn-item:hover {
  background: var(--theme-hover-bg, rgba(24, 160, 88, 0.06));
}

.fn-item-left {
  flex: 1;
  min-width: 0;
}

.fn-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--theme-text-primary, #333);
  display: flex;
  align-items: center;
}

.fn-desc {
  font-size: 12px;
  color: var(--theme-text-tertiary, #999);
  margin-top: 2px;
}

.fn-model-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.fn-capability {
  font-size: 11px;
  color: var(--theme-text-tertiary, #aaa);
}

.fn-item-right {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
</style>
