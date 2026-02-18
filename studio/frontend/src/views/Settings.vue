<template>
  <div>
    <n-h3>⚙️ 设置</n-h3>

    <n-tabs type="line" animated :value="activeTab" @update:value="activeTab = $event">
      <n-tab-pane name="ai" tab="🤖 AI 配置">
        <n-tabs
          type="segment"
          animated
          size="small"
          :value="aiSubTab"
          @update:value="aiSubTab = $event"
          style="margin-bottom: 16px"
        >
          <n-tab-pane name="providers" tab="🔌 服务提供商">
            <AIServiceSettings />
          </n-tab-pane>
          <n-tab-pane name="preferences" tab="⚙️ 使用偏好">
            <AIPreferences />
          </n-tab-pane>
          <n-tab-pane name="models" tab="📊 模型管理">
            <ModelSettings />
          </n-tab-pane>
        </n-tabs>
      </n-tab-pane>
      <n-tab-pane name="system" tab="🖥️ 系统与接口">
        <SystemSettings />
      </n-tab-pane>
      <n-tab-pane name="skills" tab="🎯 技能管理">
        <SkillSettings />
      </n-tab-pane>
      <n-tab-pane name="tools" tab="🔧 工具管理">
        <ToolSettings />
      </n-tab-pane>
      <n-tab-pane name="command-auth" tab="🔒 命令授权">
        <CommandAuthSettings />
      </n-tab-pane>
      <n-tab-pane name="workflows" tab="🔄 工作流">
        <WorkflowSettings />
      </n-tab-pane>
      <n-tab-pane v-if="authStore.isAdmin" name="users" tab="👥 用户管理">
        <UserManagement />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AIServiceSettings from './settings/AIServiceSettings.vue'
import AIPreferences from './settings/AIPreferences.vue'
import ModelSettings from './settings/ModelSettings.vue'
import SystemSettings from './settings/SystemSettings.vue'
import SkillSettings from './settings/SkillSettings.vue'
import ToolSettings from './settings/ToolSettings.vue'
import WorkflowSettings from './settings/WorkflowSettings.vue'
import CommandAuthSettings from './settings/CommandAuthSettings.vue'
import UserManagement from './settings/UserManagement.vue'

const authStore = useAuthStore()
const activeTab = ref('ai')
const aiSubTab = ref('providers')
</script>

<style>
.cap-row-override td {
  background: rgba(64, 152, 252, 0.08) !important;
}
</style>
