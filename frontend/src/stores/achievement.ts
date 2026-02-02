/**
 * 成就通知 Store - 管理 Steam 风格的成就解锁弹窗
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface AchievementNotification {
  id: number
  code: string
  name: string
  description: string
  icon: string
  rarity: string
  points: number
  timestamp: number
}

let notificationId = 0

export const useAchievementStore = defineStore('achievement', () => {
  const notifications = ref<AchievementNotification[]>([])
  const audioEnabled = ref(true)

  // 添加成就通知
  function addNotification(achievement: {
    code: string
    name: string
    description: string
    icon: string
    rarity: string
    points: number
  }) {
    const notification: AchievementNotification = {
      ...achievement,
      id: ++notificationId,
      timestamp: Date.now()
    }
    
    notifications.value.push(notification)
    
    // 播放音效
    if (audioEnabled.value) {
      playUnlockSound(achievement.rarity)
    }
    
    // 5秒后自动移除
    setTimeout(() => {
      removeNotification(notification.id)
    }, 5000)
  }

  // 批量添加成就通知
  function addNotifications(achievements: Array<{
    code: string
    name: string
    description: string
    icon: string
    rarity: string
    points: number
  }>) {
    achievements.forEach((ach, index) => {
      // 错开显示时间，避免同时弹出
      setTimeout(() => {
        addNotification(ach)
      }, index * 300)
    })
  }

  // 移除通知
  function removeNotification(id: number) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  // 手动关闭通知
  function dismissNotification(id: number) {
    removeNotification(id)
  }

  // 播放解锁音效
  function playUnlockSound(rarity: string) {
    try {
      // 使用 Web Audio API 生成简单的解锁音效
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      
      // 根据稀有度调整音效
      const baseFreq = {
        common: 523.25,    // C5
        rare: 659.25,      // E5
        epic: 783.99,      // G5
        legendary: 880,    // A5
        mythic: 1046.5     // C6
      }[rarity] || 523.25

      // 创建振荡器
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      
      oscillator.type = 'sine'
      oscillator.frequency.setValueAtTime(baseFreq, audioContext.currentTime)
      oscillator.frequency.exponentialRampToValueAtTime(baseFreq * 1.5, audioContext.currentTime + 0.1)
      oscillator.frequency.exponentialRampToValueAtTime(baseFreq * 2, audioContext.currentTime + 0.2)
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)
      
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.5)
    } catch (e) {
      // 音频播放失败时静默处理
      console.log('Audio playback not available')
    }
  }

  // 切换音效
  function toggleAudio() {
    audioEnabled.value = !audioEnabled.value
  }

  return {
    notifications,
    audioEnabled,
    addNotification,
    addNotifications,
    removeNotification,
    dismissNotification,
    toggleAudio
  }
})
