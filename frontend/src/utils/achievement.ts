/**
 * 成就检查工具函数
 * 在关键操作后调用，检查并显示新解锁的成就
 */
import { achievementApi } from '@/api'
import { useAchievementStore } from '@/stores/achievement'

// 防抖标记，避免短时间内重复调用
let isChecking = false
let lastCheckTime = 0
const CHECK_INTERVAL = 3000 // 最小检查间隔 3 秒

/**
 * 获取未展示的成就并显示弹窗
 * 用于路由切换和轮询时调用
 * @returns 新展示的成就数量
 */
export async function fetchUnshownAchievements(): Promise<number> {
  // 防抖：避免短时间内重复调用
  const now = Date.now()
  if (isChecking || now - lastCheckTime < CHECK_INTERVAL) {
    return 0
  }
  
  try {
    isChecking = true
    lastCheckTime = now
    
    const achievementStore = useAchievementStore()
    const res = await achievementApi.getUnshown()
    
    if (res.data.new_unlocks && res.data.new_unlocks.length > 0) {
      // 将未展示的成就添加到通知队列
      const achievements = res.data.new_unlocks.map((unlock: any) => ({
        code: unlock.achievement.code,
        name: unlock.achievement.name,
        description: unlock.achievement.description,
        icon: unlock.achievement.icon,
        rarity: unlock.achievement.rarity,
        points: unlock.achievement.points
      }))
      
      achievementStore.addNotifications(achievements)
      return achievements.length
    }
    
    return 0
  } catch (error) {
    console.error('获取未展示成就失败:', error)
    return 0
  } finally {
    isChecking = false
  }
}

/**
 * 检查成就并显示弹窗（主动触发检查）
 * 用于用户操作后立即检查
 * @returns 新解锁的成就数量
 */
export async function checkAndShowAchievements(): Promise<number> {
  try {
    const achievementStore = useAchievementStore()
    const res = await achievementApi.check()
    
    if (res.data.new_unlocks && res.data.new_unlocks.length > 0) {
      // 将新解锁的成就添加到通知队列
      const achievements = res.data.new_unlocks.map((unlock: any) => ({
        code: unlock.achievement.code,
        name: unlock.achievement.name,
        description: unlock.achievement.description,
        icon: unlock.achievement.icon,
        rarity: unlock.achievement.rarity,
        points: unlock.achievement.points
      }))
      
      achievementStore.addNotifications(achievements)
      return achievements.length
    }
    
    return 0
  } catch (error) {
    console.error('成就检查失败:', error)
    return 0
  }
}

/**
 * 包装异步函数，在执行后自动检查成就
 * @param asyncFn 要执行的异步函数
 * @returns 包装后的函数
 */
export function withAchievementCheck<T extends (...args: any[]) => Promise<any>>(
  asyncFn: T
): T {
  return (async (...args: Parameters<T>) => {
    const result = await asyncFn(...args)
    // 延迟一下再检查，确保后端已处理完成就
    setTimeout(() => {
      checkAndShowAchievements()
    }, 500)
    return result
  }) as T
}