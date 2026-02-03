import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePrivacyStore = defineStore('privacy', () => {
  // 隐私模式状态 - 默认开启（隐藏金额）
  const privacyMode = ref(localStorage.getItem('privacy_mode') !== 'false')

  // 切换隐私模式
  function togglePrivacy() {
    privacyMode.value = !privacyMode.value
    localStorage.setItem('privacy_mode', privacyMode.value.toString())
  }

  // 设置隐私模式
  function setPrivacyMode(value: boolean) {
    privacyMode.value = value
    localStorage.setItem('privacy_mode', value.toString())
  }

  // 格式化金额（支持隐私模式）
  function formatMoney(num: number, options?: { showSign?: boolean, decimals?: number }) {
    if (privacyMode.value) {
      return '****'
    }
    const { showSign = false, decimals = 2 } = options || {}
    const formatted = Math.abs(num).toLocaleString('zh-CN', { 
      minimumFractionDigits: decimals, 
      maximumFractionDigits: decimals 
    })
    if (showSign && num > 0) {
      return '+' + formatted
    }
    if (num < 0) {
      return '-' + formatted
    }
    return formatted
  }

  // 格式化百分比（通常不需要隐藏，但提供选项）
  function formatPercent(num: number, hideInPrivacy: boolean = false) {
    if (hideInPrivacy && privacyMode.value) {
      return '**%'
    }
    return num.toFixed(2) + '%'
  }

  return {
    privacyMode,
    togglePrivacy,
    setPrivacyMode,
    formatMoney,
    formatPercent
  }
})
