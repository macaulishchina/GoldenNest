<template>
  <div class="time-range-selector">
    <div class="selector-wrapper">
      <button
        v-for="option in options"
        :key="option.value"
        class="range-btn"
        :class="{ active: modelValue === option.value }"
        @click="selectRange(option.value)"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    default: 'month'
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const options = [
  { value: 'day', label: '最近一天' },
  { value: 'week', label: '最近一周' },
  { value: 'month', label: '最近一月' },
  { value: 'year', label: '最近一年' },
  { value: 'all', label: '全部' }
]

function selectRange(value) {
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<style scoped>
.time-range-selector {
  margin-bottom: 16px;
}

.selector-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
}

.range-btn {
  padding: 6px 14px;
  border: 1px solid var(--theme-border);
  background: var(--theme-bg-card);
  color: var(--theme-text-secondary);
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.range-btn:hover {
  border-color: var(--theme-primary, #667eea);
  color: var(--theme-primary, #667eea);
}

.range-btn.active {
  background: var(--theme-gradient-primary, linear-gradient(135deg, #667eea 0%, #764ba2 100%));
  border-color: transparent;
  color: #fff;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

/* 移动端样式 */
@media (max-width: 768px) {
  .selector-wrapper {
    gap: 6px;
  }
  
  .range-btn {
    padding: 5px 10px;
    font-size: 12px;
  }
}
</style>
