<!--
  Steam 风格成就解锁通知组件
  - 从右下角滑入
  - 支持多个成就堆叠显示
  - 根据稀有度有不同的视觉效果
-->
<template>
  <Teleport to="body">
    <TransitionGroup 
      name="achievement-toast" 
      tag="div" 
      class="achievement-container"
    >
      <div
        v-for="(notification, index) in notifications"
        :key="notification.id"
        :class="['achievement-toast', notification.rarity]"
        :style="{ bottom: `${20 + index * 90}px` }"
        @click="dismiss(notification.id)"
      >
        <!-- 背景光效 -->
        <div class="toast-glow"></div>
        
        <!-- 进度条 -->
        <div class="progress-bar">
          <div class="progress-fill"></div>
        </div>
        
        <!-- 内容区 -->
        <div class="toast-content">
          <!-- 图标 -->
          <div class="achievement-icon">
            <span class="icon-emoji">{{ notification.icon }}</span>
            <div class="icon-ring"></div>
          </div>
          
          <!-- 信息 -->
          <div class="achievement-info">
            <div class="unlock-label">
              <span class="trophy">🏆</span>
              <span>成就已解锁</span>
            </div>
            <div class="achievement-name">{{ notification.name }}</div>
            <div class="achievement-desc">{{ notification.description }}</div>
          </div>
          
          <!-- 积分 -->
          <div class="achievement-points">
            <span class="points-value">+{{ notification.points }}</span>
            <span class="points-label">积分</span>
          </div>
        </div>
        
        <!-- 稀有度标签 -->
        <div :class="['rarity-tag', notification.rarity]">
          {{ getRarityName(notification.rarity) }}
        </div>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAchievementStore } from '@/stores/achievement'

const achievementStore = useAchievementStore()

const notifications = computed(() => achievementStore.notifications)

function dismiss(id: number) {
  achievementStore.dismissNotification(id)
}

function getRarityName(rarity: string): string {
  const names: Record<string, string> = {
    common: '普通',
    rare: '稀有',
    epic: '史诗',
    legendary: '传说',
    mythic: '神话'
  }
  return names[rarity] || rarity
}
</script>

<style scoped>
.achievement-container {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 9999;
  pointer-events: none;
}

.achievement-toast {
  position: fixed;
  right: 20px;
  width: 380px;
  height: 80px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  pointer-events: auto;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.5),
    0 0 40px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: transform 0.2s, opacity 0.2s;
}

.achievement-toast:hover {
  transform: scale(1.02);
}

/* 稀有度边框颜色 */
.achievement-toast.common {
  border-color: rgba(170, 170, 170, 0.5);
}

.achievement-toast.rare {
  border-color: rgba(79, 195, 247, 0.6);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.5),
    0 0 20px rgba(79, 195, 247, 0.3);
}

.achievement-toast.epic {
  border-color: rgba(171, 71, 188, 0.6);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.5),
    0 0 20px rgba(171, 71, 188, 0.4);
}

.achievement-toast.legendary {
  border-color: rgba(255, 215, 0, 0.6);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.5),
    0 0 30px rgba(255, 215, 0, 0.4);
}

.achievement-toast.mythic {
  border-color: rgba(255, 107, 107, 0.7);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.5),
    0 0 40px rgba(255, 107, 107, 0.5);
  animation: mythicPulse 2s ease-in-out infinite;
}

@keyframes mythicPulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5), 0 0 40px rgba(255, 107, 107, 0.5); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5), 0 0 60px rgba(255, 107, 107, 0.8); }
}

/* 背景光效 */
.toast-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0.1;
  pointer-events: none;
}

.common .toast-glow {
  background: radial-gradient(ellipse at 30% 50%, rgba(170, 170, 170, 0.3), transparent 70%);
}

.rare .toast-glow {
  background: radial-gradient(ellipse at 30% 50%, rgba(79, 195, 247, 0.4), transparent 70%);
}

.epic .toast-glow {
  background: radial-gradient(ellipse at 30% 50%, rgba(171, 71, 188, 0.4), transparent 70%);
}

.legendary .toast-glow {
  background: radial-gradient(ellipse at 30% 50%, rgba(255, 215, 0, 0.4), transparent 70%);
}

.mythic .toast-glow {
  background: radial-gradient(ellipse at 30% 50%, rgba(255, 107, 107, 0.5), transparent 70%);
  animation: glowPulse 1.5s ease-in-out infinite;
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.1; }
  50% { opacity: 0.3; }
}

/* 进度条 */
.progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #8bc34a);
  animation: progressShrink 5s linear forwards;
}

.rare .progress-fill {
  background: linear-gradient(90deg, #4fc3f7, #29b6f6);
}

.epic .progress-fill {
  background: linear-gradient(90deg, #ab47bc, #8e24aa);
}

.legendary .progress-fill {
  background: linear-gradient(90deg, #ffd700, #ff8c00);
}

.mythic .progress-fill {
  background: linear-gradient(90deg, #ff6b6b, #ff8e8e);
}

@keyframes progressShrink {
  from { width: 100%; }
  to { width: 0%; }
}

/* 内容区 */
.toast-content {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  height: 100%;
  gap: 14px;
}

/* 图标 */
.achievement-icon {
  position: relative;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-emoji {
  font-size: 32px;
  z-index: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  animation: iconBounce 0.5s ease-out;
}

@keyframes iconBounce {
  0% { transform: scale(0) rotate(-20deg); }
  50% { transform: scale(1.3) rotate(10deg); }
  100% { transform: scale(1) rotate(0); }
}

.icon-ring {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  animation: ringExpand 0.6s ease-out;
}

@keyframes ringExpand {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; }
}

/* 信息区 */
.achievement-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.unlock-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #4caf50;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 2px;
}

.trophy {
  animation: trophyShine 1s ease-in-out infinite;
}

@keyframes trophyShine {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.5); }
}

.achievement-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--theme-text-primary, #fff);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.achievement-desc {
  font-size: 12px;
  color: var(--theme-text-tertiary, #aaa);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 积分 */
.achievement-points {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 10px;
  background: rgba(255, 215, 0, 0.15);
  border-radius: 6px;
  flex-shrink: 0;
}

.points-value {
  font-size: 18px;
  font-weight: bold;
  color: #ffd700;
  animation: pointsPop 0.4s ease-out 0.3s both;
}

@keyframes pointsPop {
  0% { transform: scale(0); }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); }
}

.points-label {
  font-size: 10px;
  color: var(--theme-text-tertiary, #888);
}

/* 稀有度标签 */
.rarity-tag {
  position: absolute;
  top: 8px;
  right: 12px;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.rarity-tag.common {
  background: rgba(170, 170, 170, 0.2);
  color: #aaa;
}

.rarity-tag.rare {
  background: rgba(79, 195, 247, 0.2);
  color: #4fc3f7;
}

.rarity-tag.epic {
  background: rgba(171, 71, 188, 0.2);
  color: #ab47bc;
}

.rarity-tag.legendary {
  background: rgba(255, 215, 0, 0.2);
  color: #ffd700;
}

.rarity-tag.mythic {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
  animation: tagGlow 1s ease-in-out infinite;
}

@keyframes tagGlow {
  0%, 100% { box-shadow: 0 0 5px rgba(255, 107, 107, 0.5); }
  50% { box-shadow: 0 0 15px rgba(255, 107, 107, 0.8); }
}

/* 进入/离开动画 */
.achievement-toast-enter-active {
  animation: slideIn 0.4s ease-out;
}

.achievement-toast-leave-active {
  animation: slideOut 0.3s ease-in forwards;
}

@keyframes slideIn {
  0% {
    transform: translateX(120%);
    opacity: 0;
  }
  100% {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOut {
  0% {
    transform: translateX(0);
    opacity: 1;
  }
  100% {
    transform: translateX(120%);
    opacity: 0;
  }
}

/* 移动端适配 */
@media (max-width: 440px) {
  .achievement-toast {
    width: calc(100vw - 40px);
    right: 20px;
  }
}
</style>
