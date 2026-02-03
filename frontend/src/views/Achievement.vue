<template>
  <div class="achievement-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>🏆 成就殿堂</h1>
      <p class="subtitle">记录每一个荣耀时刻</p>
    </div>

    <!-- 统计概览 -->
    <div class="stats-overview" v-if="progress">
      <div class="stat-card total">
        <div class="stat-icon">🎯</div>
        <div class="stat-info">
          <span class="stat-value">{{ progress.unlocked_achievements }}</span>
          <span class="stat-label">已解锁</span>
        </div>
        <div class="stat-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: unlockPercentage + '%' }"></div>
          </div>
          <span class="progress-text">{{ unlockPercentage }}%</span>
        </div>
      </div>
      
      <div class="stat-card points">
        <div class="stat-icon">⭐</div>
        <div class="stat-info">
          <span class="stat-value">{{ progress.earned_points }}</span>
          <span class="stat-label">成就点数</span>
        </div>
      </div>
      
      <div class="stat-card rarity">
        <div class="stat-icon">💎</div>
        <div class="stat-info">
          <span class="stat-value">{{ rarityBreakdown }}</span>
          <span class="stat-label">稀有成就</span>
        </div>
      </div>
    </div>

    <!-- 分类筛选 -->
    <div class="category-filter">
      <button
        v-for="cat in categories"
        :key="cat.key"
        :class="['filter-btn', { active: activeCategory === cat.key }]"
        @click="activeCategory = cat.key"
      >
        {{ cat.icon }} {{ cat.name }}
        <span class="count" v-if="getCategoryCount(cat.key) > 0">
          {{ getCategoryUnlocked(cat.key) }}/{{ getCategoryCount(cat.key) }}
        </span>
      </button>
    </div>

    <!-- 成就列表 -->
    <div class="achievements-grid">
      <div
        v-for="achievement in filteredAchievements"
        :key="achievement.code"
        :class="[
          'achievement-card',
          achievement.rarity,
          { unlocked: achievement.is_unlocked, hidden: achievement.is_hidden && !achievement.is_unlocked }
        ]"
      >
        <div class="card-glow"></div>
        <div class="card-content">
          <div class="achievement-icon">
            {{ achievement.is_hidden && !achievement.is_unlocked ? '❓' : achievement.icon }}
          </div>
          <div class="achievement-info">
            <h3 class="achievement-name">
              {{ achievement.is_hidden && !achievement.is_unlocked ? '隐藏成就' : achievement.name }}
            </h3>
            <p class="achievement-desc">
              {{ achievement.is_hidden && !achievement.is_unlocked ? '达成特定条件后解锁' : achievement.description }}
            </p>
          </div>
          <div class="achievement-meta">
            <span :class="['rarity-badge', achievement.rarity]">
              {{ getRarityName(achievement.rarity) }}
            </span>
            <span class="points">+{{ achievement.points }}分</span>
          </div>
          <div class="unlock-time" v-if="achievement.unlocked_at">
            🎉 {{ formatTime(achievement.unlocked_at) }}
          </div>
        </div>
      </div>
    </div>

    <!-- 家庭成就动态 -->
    <div class="family-feed" v-if="recentUnlocks.length > 0">
      <h2>📢 家庭成就动态</h2>
      <div class="feed-list">
        <div v-for="unlock in recentUnlocks" :key="unlock.id" class="feed-item">
          <span class="feed-icon">{{ unlock.icon }}</span>
          <span class="feed-text">
            <strong>{{ unlock.nickname }}</strong> 解锁了 
            <span :class="['achievement-tag', unlock.rarity]">{{ unlock.name }}</span>
          </span>
          <span class="feed-time">{{ formatTime(unlock.unlocked_at) }}</span>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner">🏆</div>
      <p>加载成就中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { achievementApi } from '@/api'
import { useMessage } from 'naive-ui'

const message = useMessage()

interface Achievement {
  code: string
  name: string
  description: string
  category: string
  icon: string
  rarity: string
  points: number
  is_hidden: boolean
  is_unlocked: boolean
  unlocked_at?: string
}

interface Progress {
  total_achievements: number
  unlocked_achievements: number
  total_points: number
  earned_points: number
  percentage: number
  categories: Array<{
    category: string
    category_name: string
    total: number
    unlocked: number
    percentage: number
  }>
  recent_unlocks: Array<any>
}

interface RecentUnlock {
  id: number
  code: string
  name: string
  icon: string
  rarity: string
  nickname: string
  unlocked_at: string
}

const loading = ref(true)
const achievements = ref<Achievement[]>([])
const progress = ref<Progress | null>(null)
const recentUnlocks = ref<RecentUnlock[]>([])
const activeCategory = ref('all')

const categories = [
  { key: 'all', name: '全部', icon: '🌟' },
  { key: 'deposit', name: '存款达人', icon: '💰' },
  { key: 'streak', name: '坚持不懈', icon: '🔥' },
  { key: 'family', name: '家庭协作', icon: '👨‍👩‍👧‍👦' },
  { key: 'equity', name: '股权大师', icon: '📊' },
  { key: 'investment', name: '理财先锋', icon: '📈' },
  { key: 'expense', name: '审批专家', icon: '✅' },
  { key: 'hidden', name: '隐藏彩蛋', icon: '🎁' },
  { key: 'special', name: '特殊成就', icon: '🌈' }
]

const filteredAchievements = computed(() => {
  if (activeCategory.value === 'all') {
    return achievements.value
  }
  return achievements.value.filter(a => a.category === activeCategory.value)
})

const unlockPercentage = computed(() => {
  if (!progress.value || progress.value.total_achievements === 0) return 0
  return progress.value.percentage || Math.round((progress.value.unlocked_achievements / progress.value.total_achievements) * 100)
})

const rarityBreakdown = computed(() => {
  if (!progress.value || !progress.value.categories) return '0'
  // 从成就列表中统计稀有成就数量
  const epicCount = achievements.value.filter(a => 
    a.is_unlocked && ['epic', 'legendary', 'mythic'].includes(a.rarity)
  ).length
  return epicCount.toString()
})

function getCategoryCount(category: string): number {
  if (category === 'all') return achievements.value.length
  return achievements.value.filter(a => a.category === category).length
}

function getCategoryUnlocked(category: string): number {
  if (category === 'all') return achievements.value.filter(a => a.is_unlocked).length
  return achievements.value.filter(a => a.category === category && a.is_unlocked).length
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

function formatTime(timeStr: string): string {
  // 后端返回的是 UTC 时间，需要添加 'Z' 后缀确保正确解析
  const utcTimeStr = timeStr.endsWith('Z') ? timeStr : timeStr + 'Z'
  const date = new Date(utcTimeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  
  return date.toLocaleDateString('zh-CN')
}

async function loadData() {
  loading.value = true
  try {
    const [defRes, progressRes, recentRes] = await Promise.all([
      achievementApi.getDefinitions(true),
      achievementApi.getProgress(),
      achievementApi.getRecent(10)
    ])
    
    achievements.value = defRes.data
    progress.value = progressRes.data
    recentUnlocks.value = recentRes.data
  } catch (error: any) {
    message.error('加载成就数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.achievement-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 2.5rem;
  background: linear-gradient(135deg, #ffd700, #ff8c00);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}

.subtitle {
  color: #888;
  font-size: 1.1rem;
}

/* 统计概览 */
.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(255, 215, 0, 0.2);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.stat-icon {
  font-size: 2.5rem;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #ffd700;
}

.stat-label {
  color: #aaa;
  font-size: 0.9rem;
}

.stat-progress {
  margin-left: auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.progress-bar {
  width: 100px;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #ff8c00);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.progress-text {
  font-size: 0.85rem;
  color: #ffd700;
}

/* 分类筛选 */
.category-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 28px;
  justify-content: center;
}

.filter-btn {
  padding: 10px 20px;
  border: 1px solid rgba(255, 215, 0, 0.3);
  background: rgba(26, 26, 46, 0.8);
  color: #ddd;
  border-radius: 25px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-btn:hover {
  background: rgba(255, 215, 0, 0.1);
  border-color: #ffd700;
}

.filter-btn.active {
  background: linear-gradient(135deg, #ffd700, #ff8c00);
  color: #1a1a2e;
  border-color: transparent;
  font-weight: bold;
}

.filter-btn .count {
  font-size: 0.8rem;
  background: rgba(0, 0, 0, 0.2);
  padding: 2px 8px;
  border-radius: 10px;
}

/* 成就网格 */
.achievements-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.achievement-card {
  position: relative;
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.achievement-card:hover {
  transform: translateY(-4px);
}

.achievement-card.unlocked {
  border-color: rgba(255, 215, 0, 0.5);
}

.achievement-card.hidden:not(.unlocked) {
  opacity: 0.5;
  filter: grayscale(0.5);
}

/* 稀有度边框颜色 */
.achievement-card.common.unlocked {
  border-color: #aaa;
}

.achievement-card.rare.unlocked {
  border-color: #4fc3f7;
}

.achievement-card.epic.unlocked {
  border-color: #ab47bc;
}

.achievement-card.legendary.unlocked {
  border-color: #ffd700;
}

.achievement-card.mythic.unlocked {
  border-color: #ff6b6b;
  animation: mythicGlow 2s ease-in-out infinite;
}

@keyframes mythicGlow {
  0%, 100% { box-shadow: 0 0 20px rgba(255, 107, 107, 0.5); }
  50% { box-shadow: 0 0 40px rgba(255, 107, 107, 0.8); }
}

.card-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  opacity: 0;
  transition: opacity 0.3s;
}

.achievement-card.unlocked .card-glow {
  opacity: 1;
}

.achievement-card.common .card-glow {
  background: linear-gradient(90deg, #aaa, #888);
}

.achievement-card.rare .card-glow {
  background: linear-gradient(90deg, #4fc3f7, #29b6f6);
}

.achievement-card.epic .card-glow {
  background: linear-gradient(90deg, #ab47bc, #8e24aa);
}

.achievement-card.legendary .card-glow {
  background: linear-gradient(90deg, #ffd700, #ff8c00);
}

.achievement-card.mythic .card-glow {
  background: linear-gradient(90deg, #ff6b6b, #ff8e8e, #ff6b6b);
  animation: mythicShine 2s linear infinite;
}

@keyframes mythicShine {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.card-content {
  padding: 20px;
}

.achievement-icon {
  font-size: 3rem;
  margin-bottom: 12px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.achievement-card:not(.unlocked) .achievement-icon {
  filter: grayscale(1) opacity(0.5);
}

.achievement-name {
  font-size: 1.2rem;
  color: #fff;
  margin-bottom: 8px;
}

.achievement-desc {
  color: #aaa;
  font-size: 0.9rem;
  margin-bottom: 12px;
  min-height: 40px;
}

.achievement-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rarity-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: bold;
}

.rarity-badge.common {
  background: rgba(170, 170, 170, 0.2);
  color: #aaa;
}

.rarity-badge.rare {
  background: rgba(79, 195, 247, 0.2);
  color: #4fc3f7;
}

.rarity-badge.epic {
  background: rgba(171, 71, 188, 0.2);
  color: #ab47bc;
}

.rarity-badge.legendary {
  background: rgba(255, 215, 0, 0.2);
  color: #ffd700;
}

.rarity-badge.mythic {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
}

.points {
  color: #ffd700;
  font-weight: bold;
}

.unlock-time {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  color: #4caf50;
  font-size: 0.85rem;
}

/* 家庭动态 */
.family-feed {
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 215, 0, 0.2);
}

.family-feed h2 {
  color: #ffd700;
  margin-bottom: 20px;
  font-size: 1.3rem;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feed-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.feed-icon {
  font-size: 1.5rem;
}

.feed-text {
  flex: 1;
  color: #ddd;
}

.feed-text strong {
  color: #ffd700;
}

.achievement-tag {
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 0.85rem;
}

.achievement-tag.common {
  background: rgba(170, 170, 170, 0.2);
  color: #ccc;
}

.achievement-tag.rare {
  background: rgba(79, 195, 247, 0.2);
  color: #4fc3f7;
}

.achievement-tag.epic {
  background: rgba(171, 71, 188, 0.2);
  color: #ab47bc;
}

.achievement-tag.legendary {
  background: rgba(255, 215, 0, 0.2);
  color: #ffd700;
}

.achievement-tag.mythic {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
}

.feed-time {
  color: #888;
  font-size: 0.85rem;
}

/* 加载状态 */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.loading-spinner {
  font-size: 4rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-overlay p {
  color: #ffd700;
  margin-top: 16px;
  font-size: 1.2rem;
}

/* ===== 移动端响应式优化 ===== */
@media (max-width: 768px) {
  .achievement-page {
    padding: 12px;
    padding-bottom: 80px;
    background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
    min-height: 100vh;
  }
  
  .page-header h1 {
    font-size: 1.4rem;
  }
  
  .page-header {
    margin-bottom: 16px;
  }
  
  .subtitle {
    font-size: 0.8rem;
    color: #888;
  }
  
  /* ===== 统计概览：改为紧凑单行 ===== */
  .stats-overview {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 16px;
  }
  
  .stat-card {
    padding: 12px 8px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    text-align: center;
    background: linear-gradient(145deg, #252540, #1e1e35);
    border-radius: 12px;
    border: 1px solid rgba(255, 215, 0, 0.15);
  }
  
  .stat-icon {
    font-size: 1.4rem;
    margin-bottom: 2px;
  }
  
  .stat-info {
    align-items: center;
  }
  
  .stat-value {
    font-size: 1.2rem;
    line-height: 1.2;
  }
  
  .stat-label {
    font-size: 0.65rem;
    color: #999;
  }
  
  .stat-progress {
    display: none; /* 移动端隐藏进度条，只显示百分比 */
  }
  
  /* 在已解锁卡片显示百分比 */
  .stat-card.total .stat-value::after {
    content: '';
  }
  
  /* ===== 分类筛选：更紧凑、更统一 ===== */
  .category-filter {
    display: flex;
    justify-content: flex-start;
    overflow-x: auto;
    flex-wrap: nowrap;
    padding: 4px;
    gap: 6px;
    margin-bottom: 14px;
    background: rgba(30, 30, 50, 0.6);
    border-radius: 20px;
    -webkit-overflow-scrolling: touch;
  }
  
  .category-filter::-webkit-scrollbar {
    display: none;
  }
  
  .filter-btn {
    white-space: nowrap;
    flex-shrink: 0;
    padding: 8px 14px;
    min-height: 32px;
    font-size: 12px;
    border-radius: 16px;
    border: none;
    background: transparent;
    color: #aaa;
    transition: all 0.2s ease;
  }
  
  .filter-btn:hover {
    background: rgba(255, 255, 255, 0.05);
  }
  
  .filter-btn.active {
    background: rgba(255, 215, 0, 0.15);
    color: #ffd700;
    font-weight: 500;
  }
  
  .filter-btn .count {
    font-size: 0.65rem;
    padding: 2px 5px;
    margin-left: 4px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    color: inherit;
  }
  
  /* ===== 成就网格：2列紧凑布局 ===== */
  .achievements-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 20px;
  }
  
  .achievement-card {
    border-radius: 14px;
    background: linear-gradient(145deg, #1f1f35, #181828);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }
  
  .achievement-card.unlocked {
    background: linear-gradient(145deg, #252545, #1e1e38);
    border-color: rgba(255, 215, 0, 0.3);
    box-shadow: 0 4px 16px rgba(255, 215, 0, 0.1);
  }
  
  .achievement-card:not(.unlocked) {
    opacity: 0.6;
  }
  
  .card-glow {
    height: 3px;
  }
  
  .card-content {
    padding: 12px;
    display: flex;
    flex-direction: column;
    min-height: 140px;
  }
  
  /* 紧凑卡片布局 */
  .achievement-icon {
    font-size: 2rem;
    margin-bottom: 8px;
    text-align: center;
  }
  
  .achievement-info {
    flex: 1;
    text-align: center;
  }
  
  .achievement-name {
    font-size: 0.85rem;
    margin-bottom: 4px;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: #eee;
  }
  
  .achievement-desc {
    font-size: 0.7rem;
    min-height: auto;
    margin-bottom: 10px;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: #888;
    text-align: center;
  }
  
  .achievement-meta {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    gap: 4px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .rarity-badge {
    padding: 3px 8px;
    font-size: 0.6rem;
    border-radius: 10px;
    font-weight: 600;
  }
  
  .points {
    font-size: 0.7rem;
    color: #ffd700;
  }
  
  .unlock-time {
    margin-top: 8px;
    padding-top: 8px;
    font-size: 0.65rem;
    text-align: center;
    border-top-color: rgba(255, 255, 255, 0.05);
  }
  
  /* ===== 稀有度颜色加强 ===== */
  .achievement-card.common.unlocked {
    border-color: rgba(170, 170, 170, 0.4);
  }
  
  .achievement-card.rare.unlocked {
    border-color: rgba(79, 195, 247, 0.5);
    box-shadow: 0 4px 16px rgba(79, 195, 247, 0.15);
  }
  
  .achievement-card.epic.unlocked {
    border-color: rgba(171, 71, 188, 0.5);
    box-shadow: 0 4px 16px rgba(171, 71, 188, 0.15);
  }
  
  .achievement-card.legendary.unlocked {
    border-color: rgba(255, 215, 0, 0.5);
    box-shadow: 0 4px 16px rgba(255, 215, 0, 0.2);
  }
  
  .achievement-card.mythic.unlocked {
    border-color: rgba(255, 107, 107, 0.5);
    box-shadow: 0 4px 16px rgba(255, 107, 107, 0.2);
  }
  
  /* 家庭动态优化 */
  .family-feed {
    padding: 14px;
    margin-bottom: 20px;
    border-radius: 14px;
    background: linear-gradient(145deg, #1f1f35, #181828);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }
  
  .family-feed h2 {
    font-size: 1rem;
    margin-bottom: 12px;
  }
  
  .feed-list {
    gap: 8px;
  }
  
  .feed-item {
    padding: 10px 12px;
    font-size: 0.8rem;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.03);
    flex-wrap: wrap;
  }
  
  .feed-icon {
    font-size: 1.1rem;
  }
  
  .feed-text {
    font-size: 0.8rem;
    flex: 1;
  }
  
  .feed-time {
    font-size: 0.7rem;
    color: #666;
    width: 100%;
    margin-top: 4px;
    padding-left: calc(1.1rem + 12px);
  }
  
  .achievement-tag {
    font-size: 0.75rem;
    padding: 2px 6px;
  }
}

/* ===== 超小屏幕 (< 375px) ===== */
@media (max-width: 374px) {
  .stats-overview {
    gap: 6px;
  }
  
  .stat-card {
    padding: 10px 6px;
  }
  
  .stat-icon {
    font-size: 1.2rem;
  }
  
  .stat-value {
    font-size: 1rem;
  }
  
  .achievements-grid {
    gap: 8px;
  }
  
  .card-content {
    padding: 10px;
    min-height: 130px;
  }
  
  .achievement-icon {
    font-size: 1.6rem;
  }
  
  .achievement-name {
    font-size: 0.8rem;
  }
  
  .achievement-desc {
    font-size: 0.65rem;
  }
  
  .filter-btn {
    padding: 6px 10px;
    font-size: 11px;
  }
}
</style>
