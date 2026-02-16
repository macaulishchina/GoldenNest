<template>
  <div>
    <n-h3>⚙️ 设置</n-h3>

    <n-tabs type="line" animated :value="activeTab" @update:value="activeTab = $event">
      <n-tab-pane name="copilot" tab="🤖 Copilot">
        <CopilotSettings />
      </n-tab-pane>
      <n-tab-pane name="system" tab="🖥️ 系统与接口">
        <SystemSettings />
      </n-tab-pane>
      <n-tab-pane name="models" tab="🧠 模型配置">
        <ModelSettings />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import CopilotSettings from './settings/CopilotSettings.vue'
import SystemSettings from './settings/SystemSettings.vue'
import ModelSettings from './settings/ModelSettings.vue'

const activeTab = ref('copilot')
</script>

<style>
.cap-row-override td {
  background: rgba(64, 152, 252, 0.08) !important;
}
</style>
