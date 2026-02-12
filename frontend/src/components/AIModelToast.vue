<template>
  <Teleport to="body">
    <TransitionGroup name="ai-toast" tag="div" class="ai-toast-container">
      <div
        v-for="toast in visibleToasts"
        :key="toast.id"
        class="ai-toast"
      >
        <span class="ai-toast-icon">✦</span>
        <span class="ai-toast-text">
          <span class="ai-toast-fn">{{ toast.functionName }}</span>
          <span class="ai-toast-sep">·</span>
          <span class="ai-toast-model">{{ toast.model }}</span>
        </span>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface ToastItem {
  id: number
  functionName: string
  model: string
  timer?: ReturnType<typeof setTimeout>
}

const toasts = ref<ToastItem[]>([])
let nextId = 0

// 最多同时显示 3 条，多了自动移除旧的
const visibleToasts = computed(() => toasts.value.slice(-3))

function show(functionName: string, model: string) {
  const id = nextId++
  const item: ToastItem = { id, functionName, model }

  toasts.value.push(item)

  // 2.5 秒后自动消失
  item.timer = setTimeout(() => {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }, 2500)

  // 防止堆积过多
  if (toasts.value.length > 5) {
    const old = toasts.value.shift()
    if (old?.timer) clearTimeout(old.timer)
  }
}

// 暴露给外部调用
defineExpose({ show })
</script>

<style scoped>
.ai-toast-container {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  pointer-events: none;
}

.ai-toast {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(24, 160, 88, 0.12) 0%, rgba(59, 130, 246, 0.10) 100%);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(24, 160, 88, 0.18);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
  pointer-events: none;
  user-select: none;
}

.ai-toast-icon {
  font-size: 11px;
  background: linear-gradient(135deg, #18a058, #3b82f6);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: sparkle 2s ease-in-out infinite;
}

@keyframes sparkle {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

.ai-toast-fn {
  color: var(--theme-text-primary, #1f2937);
  font-weight: 500;
}

.ai-toast-sep {
  color: var(--theme-text-tertiary, #aaa);
  font-size: 10px;
}

.ai-toast-model {
  color: var(--theme-primary, #18a058);
  font-weight: 600;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11px;
}

/* 深色主题适配 */
body.theme-dark .ai-toast {
  background: linear-gradient(135deg, rgba(24, 160, 88, 0.18) 0%, rgba(59, 130, 246, 0.15) 100%);
  border-color: rgba(24, 160, 88, 0.25);
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.25);
}

/* 动画 */
.ai-toast-enter-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.ai-toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 1, 1);
}

.ai-toast-enter-from {
  opacity: 0;
  transform: translateY(16px) scale(0.9);
}

.ai-toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
}

.ai-toast-move {
  transition: transform 0.3s ease;
}

@media (max-width: 768px) {
  .ai-toast-container {
    bottom: 100px;
  }
  .ai-toast {
    font-size: 11px;
    padding: 5px 12px;
  }
}
</style>
