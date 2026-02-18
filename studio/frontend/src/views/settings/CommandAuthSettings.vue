<template>
  <n-space vertical :size="16">

    <!-- 统计 -->
    <n-grid :cols="4" :x-gap="12">
      <n-gi>
        <n-statistic label="授权规则" :value="stats.active_rules" />
      </n-gi>
      <n-gi>
        <n-statistic label="总执行数" :value="stats.total_commands" />
      </n-gi>
      <n-gi>
        <n-statistic label="已批准" :value="stats.approved_count">
          <template #suffix>
            <n-text type="success" style="font-size: 14px">✓</n-text>
          </template>
        </n-statistic>
      </n-gi>
      <n-gi>
        <n-statistic label="已拒绝" :value="stats.rejected_count">
          <template #suffix>
            <n-text type="error" style="font-size: 14px">✗</n-text>
          </template>
        </n-statistic>
      </n-gi>
    </n-grid>

    <!-- 标签页: 规则 / 项目状态 / 审计日志 -->
    <n-tabs type="segment" animated size="small" v-model:value="activeSection">
      <n-tab-pane name="rules" tab="📋 授权规则">
        <!-- 新建规则 -->
        <n-space justify="space-between" align="center" style="margin-bottom: 12px">
          <n-text depth="3" style="font-size: 12px">
            预配置命令授权规则, AI 执行写命令时会先匹配规则, 命中则自动放行或拒绝
          </n-text>
          <n-button type="primary" size="small" @click="showRuleModal('create')">
            ➕ 新建规则
          </n-button>
        </n-space>

        <n-spin :show="rulesLoading">
          <n-empty v-if="!rulesLoading && rules.length === 0" description="暂无授权规则, 在命令审批弹窗选择「永久」也会自动创建">
            <template #extra>
              <n-button size="small" @click="showRuleModal('create')">创建第一条规则</n-button>
            </template>
          </n-empty>

          <div v-else class="rule-list">
            <div
              v-for="rule in rules"
              :key="rule.id"
              class="rule-card"
              :class="{ 'rule-deny': rule.action === 'deny', 'rule-disabled': !rule.is_enabled }"
            >
              <div class="rule-header">
                <div style="display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0">
                  <n-tag :type="rule.action === 'allow' ? 'success' : 'error'" size="small" :bordered="false" round>
                    {{ rule.action === 'allow' ? '✅ 允许' : '🚫 拒绝' }}
                  </n-tag>
                  <code class="rule-pattern">{{ rule.pattern }}</code>
                  <n-tag size="tiny" :bordered="false" round type="default">
                    {{ patternTypeLabel(rule.pattern_type) }}
                  </n-tag>
                  <n-tag size="tiny" :bordered="false" round :type="rule.scope === 'global' ? 'info' : 'warning'">
                    {{ rule.scope === 'global' ? '🌐 全局' : '📁 ' + (rule.project_title || '项目') }}
                  </n-tag>
                </div>
                <n-space :size="4">
                  <n-switch
                    :value="rule.is_enabled"
                    size="small"
                    @update:value="(v: boolean) => toggleRule(rule, v)"
                  />
                  <n-button size="tiny" quaternary @click="showRuleModal('edit', rule)">✏️</n-button>
                  <n-button size="tiny" quaternary type="error" @click="deleteRule(rule)">🗑️</n-button>
                </n-space>
              </div>
              <div v-if="rule.note" class="rule-note">
                <n-text depth="3" style="font-size: 11px">{{ rule.note }}</n-text>
              </div>
              <div class="rule-meta">
                <n-text depth="3" style="font-size: 10px">
                  {{ rule.created_by }} 创建于 {{ formatDt(rule.created_at) }}
                </n-text>
              </div>
            </div>
          </div>
        </n-spin>
      </n-tab-pane>

      <n-tab-pane name="projects" tab="📁 项目授权">
        <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 12px">
          以下项目已开启「写入命令自动批准」— 所有写命令将跳过确认直接执行
        </n-text>
        <n-spin :show="overridesLoading">
          <n-empty v-if="!overridesLoading && overrides.length === 0" description="暂无项目开启写入命令自动批准" />
          <div v-else class="rule-list">
            <div v-for="o in overrides" :key="o.project_id" class="rule-card">
              <div class="rule-header">
                <n-space align="center" :size="8" style="flex: 1">
                  <n-tag type="warning" size="small" :bordered="false" round>🔓 自动批准</n-tag>
                  <n-text strong>{{ o.project_title }}</n-text>
                </n-space>
                <n-button
                  size="small"
                  type="error"
                  secondary
                  @click="revokeOverride(o)"
                >
                  🔒 撤销
                </n-button>
              </div>
            </div>
          </div>
        </n-spin>
      </n-tab-pane>

      <n-tab-pane name="audit" tab="📜 执行记录">
        <n-space justify="space-between" align="center" style="margin-bottom: 12px">
          <n-space :size="8" align="center">
            <n-select
              v-model:value="auditFilter"
              :options="auditFilterOptions"
              size="small"
              style="width: 130px"
              placeholder="全部"
              clearable
            />
            <n-text depth="3" style="font-size: 11px">最近 {{ auditLog.length }} 条</n-text>
          </n-space>
          <n-button size="small" secondary @click="loadAuditLog">🔄 刷新</n-button>
        </n-space>

        <n-spin :show="auditLoading">
          <n-empty v-if="!auditLoading && auditLog.length === 0" description="暂无命令执行记录" />

          <div v-else class="audit-list">
            <div v-for="log in auditLog" :key="log.id" class="audit-item">
              <div class="audit-header">
                <n-tag :type="auditActionType(log.action)" size="tiny" :bordered="false" round>
                  {{ auditActionLabel(log.action) }}
                </n-tag>
                <n-text depth="3" style="font-size: 11px">{{ log.project_title || '-' }}</n-text>
                <n-tag size="tiny" :bordered="false" round type="default">{{ scopeLabel(log.scope) }}</n-tag>
                <n-tag size="tiny" :bordered="false" round type="default">{{ methodLabel(log.method) }}</n-tag>
                <n-text depth="3" style="font-size: 10px; margin-left: auto">{{ formatDt(log.created_at) }}</n-text>
              </div>
              <div class="audit-command">
                <code>$ {{ log.command }}</code>
              </div>
            </div>
          </div>
        </n-spin>
      </n-tab-pane>
    </n-tabs>

    <!-- 规则编辑 Modal -->
    <n-modal v-model:show="ruleModal.show" preset="card" :title="ruleModal.mode === 'create' ? '新建授权规则' : '编辑规则'" style="max-width: 520px" :bordered="false">
      <n-space vertical :size="16">
        <n-form-item label="命令模式" :show-feedback="false">
          <n-input v-model:value="ruleForm.pattern" placeholder="如: npm install, git push, pip, ..." />
        </n-form-item>

        <n-space :size="16">
          <n-form-item label="匹配方式" :show-feedback="false" style="width: 150px">
            <n-select v-model:value="ruleForm.pattern_type" :options="patternTypeOptions" size="small" />
          </n-form-item>
          <n-form-item label="动作" :show-feedback="false" style="width: 130px">
            <n-select v-model:value="ruleForm.action" :options="actionOptions" size="small" />
          </n-form-item>
          <n-form-item label="范围" :show-feedback="false" style="width: 130px">
            <n-select v-model:value="ruleForm.scope" :options="scopeOptions" size="small" />
          </n-form-item>
        </n-space>

        <n-form-item v-if="ruleForm.scope === 'project'" label="项目" :show-feedback="false">
          <n-select
            v-model:value="ruleForm.project_id"
            :options="projectOptions"
            filterable
            placeholder="选择项目"
            size="small"
          />
        </n-form-item>

        <n-form-item label="备注" :show-feedback="false">
          <n-input v-model:value="ruleForm.note" placeholder="可选备注" />
        </n-form-item>

        <!-- 预览 -->
        <n-card size="small" :bordered="false" style="background: #0d1b2a">
          <n-text depth="3" style="font-size: 11px; display: block; margin-bottom: 4px">匹配预览：</n-text>
          <n-text style="font-size: 12px">
            当命令
            <b v-if="ruleForm.pattern_type === 'prefix'">以「{{ ruleForm.pattern }}」开头</b>
            <b v-else-if="ruleForm.pattern_type === 'exact'">完全等于「{{ ruleForm.pattern }}」</b>
            <b v-else-if="ruleForm.pattern_type === 'contains'">包含「{{ ruleForm.pattern }}」</b>
            <b v-else>匹配正则「{{ ruleForm.pattern }}」</b>
            时, 将自动
            <n-text :type="ruleForm.action === 'allow' ? 'success' : 'error'">
              {{ ruleForm.action === 'allow' ? '✅ 允许执行' : '🚫 拒绝执行' }}
            </n-text>
          </n-text>
        </n-card>
      </n-space>

      <template #footer>
        <n-space justify="end">
          <n-button @click="ruleModal.show = false">取消</n-button>
          <n-button type="primary" :loading="ruleModal.saving" @click="saveRule">
            {{ ruleModal.mode === 'create' ? '创建' : '保存' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </n-space>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { commandAuthApi, projectApi } from '@/api'

const message = useMessage()
const dialog = useDialog()

// ---- 统计 ----
const stats = ref({ active_rules: 0, total_commands: 0, approved_count: 0, rejected_count: 0 })

async function loadStats() {
  try {
    const { data } = await commandAuthApi.auditLogStats()
    stats.value = data
  } catch { /* ignore */ }
}

// ---- 规则 ----
const activeSection = ref('rules')
const rulesLoading = ref(false)
const rules = ref<any[]>([])

async function loadRules() {
  rulesLoading.value = true
  try {
    const { data } = await commandAuthApi.listRules()
    rules.value = data
  } catch (e: any) {
    message.error('加载规则失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    rulesLoading.value = false
  }
}

async function toggleRule(rule: any, enabled: boolean) {
  try {
    await commandAuthApi.updateRule(rule.id, { is_enabled: enabled })
    rule.is_enabled = enabled
    loadStats()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

function deleteRule(rule: any) {
  dialog.warning({
    title: '确认删除',
    content: `删除规则「${rule.pattern}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await commandAuthApi.deleteRule(rule.id)
        rules.value = rules.value.filter(r => r.id !== rule.id)
        message.success('已删除')
        loadStats()
      } catch (e: any) {
        message.error(e.response?.data?.detail || '删除失败')
      }
    },
  })
}

// ---- 规则 Modal ----
const ruleModal = ref({ show: false, mode: 'create' as 'create' | 'edit', editId: 0, saving: false })
const ruleForm = ref({
  pattern: '',
  pattern_type: 'prefix',
  scope: 'global',
  project_id: null as number | null,
  action: 'allow',
  note: '',
})

const patternTypeOptions = [
  { label: '前缀匹配', value: 'prefix' },
  { label: '精确匹配', value: 'exact' },
  { label: '包含', value: 'contains' },
  { label: '正则表达式', value: 'regex' },
]
const actionOptions = [
  { label: '✅ 允许', value: 'allow' },
  { label: '🚫 拒绝', value: 'deny' },
]
const scopeOptions = [
  { label: '🌐 全局', value: 'global' },
  { label: '📁 项目', value: 'project' },
]
const projectOptions = ref<any[]>([])

async function loadProjects() {
  try {
    const { data } = await projectApi.list({ page_size: 200 })
    projectOptions.value = data.map((p: any) => ({ label: p.title || `项目 #${p.id}`, value: p.id }))
  } catch { /* ignore */ }
}

function showRuleModal(mode: 'create' | 'edit', rule?: any) {
  ruleModal.value = { show: true, mode, editId: rule?.id || 0, saving: false }
  if (mode === 'edit' && rule) {
    ruleForm.value = {
      pattern: rule.pattern,
      pattern_type: rule.pattern_type,
      scope: rule.scope,
      project_id: rule.project_id,
      action: rule.action,
      note: rule.note || '',
    }
  } else {
    ruleForm.value = { pattern: '', pattern_type: 'prefix', scope: 'global', project_id: null, action: 'allow', note: '' }
  }
  loadProjects()
}

async function saveRule() {
  if (!ruleForm.value.pattern.trim()) {
    message.warning('请填写命令模式')
    return
  }
  ruleModal.value.saving = true
  try {
    if (ruleModal.value.mode === 'create') {
      await commandAuthApi.createRule(ruleForm.value)
      message.success('规则已创建')
    } else {
      await commandAuthApi.updateRule(ruleModal.value.editId, ruleForm.value)
      message.success('规则已更新')
    }
    ruleModal.value.show = false
    loadRules()
    loadStats()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    ruleModal.value.saving = false
  }
}

// ---- 项目覆盖 ----
const overridesLoading = ref(false)
const overrides = ref<any[]>([])

async function loadOverrides() {
  overridesLoading.value = true
  try {
    const { data } = await commandAuthApi.listProjectOverrides()
    overrides.value = data
  } catch (e: any) {
    message.error('加载项目状态失败')
  } finally {
    overridesLoading.value = false
  }
}

function revokeOverride(o: any) {
  dialog.warning({
    title: '撤销自动批准',
    content: `确定撤销项目「${o.project_title}」的命令自动批准？之后写命令将再次需要手动确认。`,
    positiveText: '撤销',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await commandAuthApi.revokeProjectOverride(o.project_id)
        overrides.value = overrides.value.filter(x => x.project_id !== o.project_id)
        message.success('已撤销')
      } catch (e: any) {
        message.error(e.response?.data?.detail || '操作失败')
      }
    },
  })
}

// ---- 审计日志 ----
const auditLoading = ref(false)
const auditLog = ref<any[]>([])
const auditFilter = ref<string | null>(null)
const auditFilterOptions = [
  { label: '✅ 已批准', value: 'approved' },
  { label: '🚫 已拒绝', value: 'rejected' },
  { label: '⏰ 已超时', value: 'timeout' },
]

async function loadAuditLog() {
  auditLoading.value = true
  try {
    const params: any = { limit: 100 }
    if (auditFilter.value) params.action = auditFilter.value
    const { data } = await commandAuthApi.listAuditLog(params)
    auditLog.value = data
  } catch (e: any) {
    message.error('加载日志失败')
  } finally {
    auditLoading.value = false
  }
}

watch(auditFilter, () => loadAuditLog())

// ---- Helpers ----
function patternTypeLabel(t: string) {
  return { prefix: '前缀', exact: '精确', contains: '包含', regex: '正则' }[t] || t
}
function auditActionType(a: string) {
  if (a === 'approved') return 'success'
  if (a === 'rejected') return 'error'
  return 'warning'
}
function auditActionLabel(a: string) {
  return { approved: '✅ 批准', rejected: '🚫 拒绝', timeout: '⏰ 超时' }[a] || a
}
function scopeLabel(s: string) {
  return { once: '仅本次', session: '本会话', project: '本项目', permanent: '永久', rule: '规则' }[s] || s
}
function methodLabel(m: string) {
  if (m === 'manual') return '手动'
  if (m === 'project_auto') return '项目自动'
  if (m === 'session_cache') return '会话缓存'
  if (m?.startsWith('rule:')) return `规则 #${m.split(':')[1]}`
  return m
}
function formatDt(dt?: string) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// ---- Init ----
onMounted(() => {
  loadStats()
  loadRules()
})

watch(activeSection, (val) => {
  if (val === 'projects' && overrides.value.length === 0) loadOverrides()
  if (val === 'audit' && auditLog.value.length === 0) loadAuditLog()
})
</script>

<style scoped>
.rule-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rule-card {
  background: #16213e;
  border-radius: 8px;
  padding: 10px 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: border-color 0.15s;
}
.rule-card:hover {
  border-color: rgba(255, 255, 255, 0.12);
}
.rule-deny {
  border-left: 3px solid #e94560;
}
.rule-disabled {
  opacity: 0.5;
}
.rule-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.rule-pattern {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  color: #70a1ff;
  background: #0d1b2a;
  padding: 2px 8px;
  border-radius: 4px;
}
.rule-note {
  margin-top: 4px;
  padding-left: 4px;
}
.rule-meta {
  margin-top: 4px;
  padding-left: 4px;
}
.audit-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.audit-item {
  background: #16213e;
  border-radius: 6px;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}
.audit-header {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.audit-command {
  margin-top: 4px;
  font-size: 12px;
  color: #a0a0a0;
  font-family: 'Fira Code', 'Consolas', monospace;
  background: #0d1b2a;
  padding: 4px 8px;
  border-radius: 4px;
  word-break: break-all;
  white-space: pre-wrap;
}
</style>
