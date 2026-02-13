<!--
  成就解锁通知组件
  桌面端: Steam 风格右下角滑入
  移动端: 顶部紧凑横幅，从顶部滑入，不干扰操作
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
        :style="posStyle(index)"
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
          
          <!-- 积分 + 稀有度合并 -->
          <div class="achievement-badge">
            <span :class="['rarity-dot', notification.rarity]"></span>
            <span class="points-value">+{{ notification.points }}</span>
          </div>
        </div>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useAchievementStore } from '@/stores/achievement'

const achievementStore = useAchievementStore()
const isMobile = ref(window.innerWidth < 768)

function onResize() { isMobile.value = window.innerWidth < 768 }
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

const notifications = computed(() => achievementStore.notifications)

function posStyle(index: number) {
  if (isMobile.value) {
    // 移动端：从顶部向下堆叠，留出安全区域
    return { top: `calc(env(safe-area-inset-top, 8px) + ${index * 56}px)` }
  }
  // 桌面端：从底部向上堆叠
  return { bottom: `${20 + index * 76}px` }
}

function dismiss(id: number) {
  achievementStore.dismissNotification(id)
}
</script>

<style scoped>
.achievement-container {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
}

/* ===== 桌面端：右下角卡片 ===== */
.achievement-toast {
  position: fixed;
  right: 20px;
  width: 360px;
  height: 68px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  pointer-events: auto;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.5),
    0 0 30px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: transform 0.2s, opacity 0.2s;
}

.achievement-toast:hover {
  transform: scale(1.02);
}

/* 稀有度边框颜色 */
.achievement-toast.common { border-color: rgba(170, 170, 170, 0.5); }
.achievement-toast.rare {
  border-color: rgba(79, 195, 247, 0.6);
  box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 15px rgba(79,195,247,0.3);
}
.achievement-toast.epic {
  border-color: rgba(171, 71, 188, 0.6);
  box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 15px rgba(171,71,188,0.4);
}
.achievement-toast.legendary {
  border-color: rgba(255, 215, 0, 0.6);
  box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 20px rgba(255,215,0,0.4);
}
.achievement-toast.mythic {
  border-color: rgba(255, 107, 107, 0.7);
  box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 30px rgba(255,107,107,0.5);
  animation: mythicPulse 2s ease-in-out infinite;
}

@keyframes mythicPulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 30px rgba(255,107,107,0.5); }
  50% { box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 50px rgba(255,107,107,0.8); }
}

/* 背景光效 */
.toast-glow {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  opacity: 0.1;
  pointer-events: none;
}
.common .toast-glow { background: radial-gradient(ellipse at 20% 50%, rgba(170,170,170,0.3), transparent 70%); }
.rare .toast-glow { background: radial-gradient(ellipse at 20% 50%, rgba(79,195,247,0.4), transparent 70%); }
.epic .toast-glow { background: radial-gradient(ellipse at 20% 50%, rgba(171,71,188,0.4), transparent 70%); }
.legendary .toast-glow { background: radial-gradient(ellipse at 20% 50%, rgba(255,215,0,0.4), transparent 70%); }
.mythic .toast-glow {
  background: radial-gradient(ellipse at 20% 50%, rgba(255,107,107,0.5), transparent 70%);
  animation: glowPulse 1.5s ease-in-out infinite;
}
@keyframes glowPulse { 0%,100% { opacity: 0.1; } 50% { opacity: 0.3; } }

/* 进度条 */
.progress-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 2px;
  background: rgba(255,255,255,0.1);
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #8bc34a);
  animation: progressShrink 5s linear forwards;
}
.rare .progress-fill { background: linear-gradient(90deg, #4fc3f7, #29b6f6); }
.epic .progress-fill { background: linear-gradient(90deg, #ab47bc, #8e24aa); }
.legendary .progress-fill { background: linear-gradient(90deg, #ffd700, #ff8c00); }
.mythic .progress-fill { background: linear-gradient(90deg, #ff6b6b, #ff8e8e); }
@keyframes progressShrink { from { width: 100%; } to { width: 0%; } }

/* 内容区 */
.toast-content {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  height: 100%;
  gap: 10px;
}

/* 图标 */
.achievement-icon {
  position: relative;
  width: 42px; height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.icon-emoji {
  font-size: 28px;
  z-index: 1;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
  animation: iconBounce 0.5s ease-out;
}
@keyframes iconBounce {
  0% { transform: scale(0) rotate(-20deg); }
  50% { transform: scale(1.3) rotate(10deg); }
  100% { transform: scale(1) rotate(0); }
}
.icon-ring {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(255,255,255,0.2);
  border-radius: 50%;
  animation: ringExpand 0.6s ease-out;
}
@keyframes ringExpand { 0% { transform: scale(0.5); opacity: 1; } 100% { transform: scale(1.5); opacity: 0; } }

/* 信息区 */
.achievement-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
.unlock-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #4caf50;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 1px;
}
.trophy { animation: trophyShine 1s ease-in-out infinite; }
@keyframes trophyShine { 0%,100% { filter: brightness(1); } 50% { filter: brightness(1.5); } }

.achievement-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}
.achievement-desc {
  font-size: 11px;
  color: #aaa;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 积分+稀有度合并徽章 */
.achievement-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(255,215,0,0.12);
  border-radius: 20px;
  flex-shrink: 0;
}
.rarity-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.rarity-dot.common { background: #aaa; }
.rarity-dot.rare { background: #4fc3f7; box-shadow: 0 0 4px #4fc3f7; }
.rarity-dot.epic { background: #ab47bc; box-shadow: 0 0 4px #ab47bc; }
.rarity-dot.legendary { background: #ffd700; box-shadow: 0 0 6px #ffd700; }
.rarity-dot.mythic { background: #ff6b6b; box-shadow: 0 0 6px #ff6b6b; animation: dotPulse 1s ease-in-out infinite; }
@keyframes dotPulse { 0%,100% { box-shadow: 0 0 4px #ff6b6b; } 50% { box-shadow: 0 0 12px #ff6b6b; } }

.points-value {
  font-size: 14px;
  font-weight: bold;
  color: #ffd700;
  animation: pointsPop 0.4s ease-out 0.3s both;
  white-space: nowrap;
}
@keyframes pointsPop { 0% { transform: scale(0); } 50% { transform: scale(1.3); } 100% { transform: scale(1); } }

/* ===== 桌面端动画: 右侧滑入 ===== */
.achievement-toast-enter-active {
  animation: slideIn 0.4s ease-out;
}
.achievement-toast-leave-active {
  animation: slideOut 0.3s ease-in forwards;
}
@keyframes slideIn {
  0% { transform: translateX(120%); opacity: 0; }
  100% { transform: translateX(0); opacity: 1; }
}
@keyframes slideOut {
  0% { transform: translateX(0); opacity: 1; }
  100% { transform: translateX(120%); opacity: 0; }
}

/* ===== 移动端重写：顶部紧凑横幅 ===== */
@media (max-width: 767px) {
  .achievement-toast {
    position: fixed;
    left: 8px;
    right: 8px;
    width: auto;
    height: 48px;
    border-radius: 12px;
    bottom: auto !important;
  }

  .toast-content {
    padding: 4px 10px;
    gap: 8px;
  }

  .achievement-icon {
    width: 32px; height: 32px;
  }
  .icon-emoji { font-size: 22px; }

  .unlock-label { display: none; }
  .achievement-name { font-size: 13px; }
  .achievement-desc { font-size: 10px; }

  .achievement-badge {
    padding: 2px 8px;
  }
  .points-value { font-size: 12px; }
  .rarity-dot { width: 6px; height: 6px; }

  /* 动画从顶部滑入 */
  .achievement-toast-enter-active {
    animation: slideDown 0.35s ease-out;
  }
  .achievement-toast-leave-active {
    animation: slideUp 0.25s ease-in forwards;
  }
}

@keyframes slideDown {
  0% { transform: translateY(-120%); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}
@keyframes slideUp {
  0% { transform: translateY(0); opacity: 1; }
  100% { transform: translateY(-120%); opacity: 0; }
}
</style>
