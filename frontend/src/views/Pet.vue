<template>
  <div class="pet-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span>
      <p>加载中...</p>
    </div>

    <template v-else-if="pet">
      <!-- 宠物展示区 -->
      <div class="pet-display">
        <div class="pet-stage">
          <div class="pet-avatar" :class="pet.pet_type">
            <span class="pet-emoji">{{ getPetEmoji(pet.pet_type) }}</span>
          </div>
          <div class="pet-particles">
            <span v-for="n in 5" :key="n" class="particle"></span>
          </div>
        </div>
        
        <h1 class="pet-name">{{ pet.name }}</h1>
        <p class="pet-type-label">{{ getPetTypeName(pet.pet_type) }}</p>
        
        <!-- 等级和经验 -->
        <div class="level-info">
          <span class="level">Lv.{{ pet.level }}</span>
          <div class="exp-bar">
            <div class="exp-fill" :style="{ width: expProgress + '%' }"></div>
          </div>
          <span class="exp-text">{{ pet.current_exp }}/{{ pet.exp_to_next }} EXP</span>
        </div>
      </div>

      <!-- 属性卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-icon">⭐</span>
          <div class="stat-info">
            <span class="stat-value">{{ pet.total_exp }}</span>
            <span class="stat-label">总经验</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">❤️</span>
          <div class="stat-info">
            <span class="stat-value">{{ pet.happiness }}</span>
            <span class="stat-label">心情值</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">🔥</span>
          <div class="stat-info">
            <span class="stat-value">{{ pet.checkin_streak }}天</span>
            <span class="stat-label">连续签到</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">🎂</span>
          <div class="stat-info">
            <span class="stat-value">{{ formatAge(pet.created_at) }}</span>
            <span class="stat-label">陪伴天数</span>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button 
          class="btn-action checkin" 
          @click="checkin" 
          :disabled="checkinLoading || pet.checked_in_today"
        >
          <span class="btn-icon">📅</span>
          <span class="btn-text">{{ pet.checked_in_today ? '今日已签到' : '每日签到' }}</span>
          <span class="btn-reward" v-if="!pet.checked_in_today">+{{ getCheckinExp() }} EXP</span>
        </button>

        <button 
          class="btn-action feed" 
          @click="showFeedModal = true"
          :disabled="feedLoading"
        >
          <span class="btn-icon">🍖</span>
          <span class="btn-text">投喂食物</span>
        </button>

        <button 
          class="btn-action rename" 
          @click="showRenameModal = true"
        >
          <span class="btn-icon">✏️</span>
          <span class="btn-text">修改名字</span>
        </button>
      </div>

      <!-- 进化路线 -->
      <div class="evolution-section">
        <h2>🌟 进化之路</h2>
        <div class="evolution-path">
          <div 
            v-for="(stage, key) in evolutionStages" 
            :key="key"
            class="evolution-stage"
            :class="{ active: pet.pet_type === key, unlocked: isStageUnlocked(key) }"
          >
            <span class="stage-emoji">{{ stage.emoji }}</span>
            <span class="stage-name">{{ stage.name }}</span>
            <span class="stage-level">Lv.{{ stage.minLevel }}+</span>
          </div>
        </div>
      </div>

      <!-- 喂养提示 -->
      <div class="tips-section">
        <h3>💡 经验获取方式</h3>
        <ul>
          <li>📅 每日签到: +10~60 EXP (连续签到加成)</li>
          <li>💰 存款操作: 每100元 +1 EXP</li>
          <li>📈 投资收益: 每10元收益 +1 EXP</li>
          <li>🗳️ 参与投票: +20 EXP</li>
          <li>🎁 赠送股权: +30 EXP</li>
        </ul>
      </div>
    </template>

    <!-- 没有宠物时显示创建提示 -->
    <div v-else class="no-pet">
      <div class="no-pet-icon">🥚</div>
      <h2>家庭还没有吉祥物</h2>
      <p>请先加入或创建一个家庭</p>
    </div>

    <!-- 喂食弹窗 -->
    <div v-if="showFeedModal" class="modal-overlay" @click.self="showFeedModal = false">
      <div class="modal-content">
        <h2>🍖 选择食物</h2>
        <div class="food-list">
          <div 
            v-for="food in foods" 
            :key="food.type"
            class="food-item"
            @click="feed(food.type)"
          >
            <span class="food-icon">{{ food.icon }}</span>
            <span class="food-name">{{ food.name }}</span>
            <span class="food-effect">+{{ food.happiness }} 心情</span>
          </div>
        </div>
        <button class="btn-cancel" @click="showFeedModal = false">取消</button>
      </div>
    </div>

    <!-- 改名弹窗 -->
    <div v-if="showRenameModal" class="modal-overlay" @click.self="showRenameModal = false">
      <div class="modal-content">
        <h2>✏️ 修改名字</h2>
        <div class="form-group">
          <input v-model="newName" placeholder="请输入新名字" maxlength="20" />
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showRenameModal = false">取消</button>
          <button class="btn-submit" @click="rename" :disabled="!newName.trim()">确认</button>
        </div>
      </div>
    </div>

    <!-- 升级动画 -->
    <div v-if="showLevelUp" class="level-up-overlay" @click="showLevelUp = false">
      <div class="level-up-content">
        <div class="level-up-icon">🎉</div>
        <h2>恭喜升级!</h2>
        <p class="new-level">Lv.{{ levelUpInfo.newLevel }}</p>
        <p v-if="levelUpInfo.evolved" class="evolution-msg">
          {{ getPetEmoji(levelUpInfo.newType) }} 进化为 {{ getPetTypeName(levelUpInfo.newType) }}!
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 状态
const loading = ref(false)
const hasFamily = computed(() => !!userStore.user?.family_id)
const checkinLoading = ref(false)
const feedLoading = ref(false)
const pet = ref(null)
const showFeedModal = ref(false)
const showRenameModal = ref(false)
const showLevelUp = ref(false)
const newName = ref('')
const levelUpInfo = ref({})

// 进化阶段
const evolutionStages = {
  golden_egg: { name: '金蛋', emoji: '🥚', minLevel: 1 },
  golden_chick: { name: '金雏鸡', emoji: '🐣', minLevel: 10 },
  golden_bird: { name: '金凤雏', emoji: '🐤', minLevel: 30 },
  golden_phoenix: { name: '金凤凰', emoji: '🦅', minLevel: 50 },
  golden_dragon: { name: '金龙', emoji: '🐉', minLevel: 80 }
}

// 食物列表
const foods = [
  { type: 'normal', name: '普通饲料', icon: '🌾', happiness: 5 },
  { type: 'premium', name: '高级饲料', icon: '🌽', happiness: 15 },
  { type: 'luxury', name: '豪华大餐', icon: '🍖', happiness: 30 }
]

// 计算经验进度
const expProgress = computed(() => {
  if (!pet.value) return 0
  return Math.min(100, (pet.value.current_exp / pet.value.exp_to_next) * 100)
})

// 加载宠物信息
const loadPet = async () => {
  loading.value = true
  try {
    const res = await api.get('/pet')
    pet.value = res.data
    newName.value = res.data?.name || ''
  } catch (err) {
    console.error('获取宠物信息失败:', err)
    // 任何错误都显示没有宠物状态
    pet.value = null
  } finally {
    loading.value = false
  }
}

// 签到
const checkin = async () => {
  checkinLoading.value = true
  try {
    const res = await api.post('/pet/checkin')
    const oldLevel = pet.value.level
    await loadPet()
    
    // 检查是否升级
    if (pet.value.level > oldLevel) {
      levelUpInfo.value = {
        newLevel: pet.value.level,
        evolved: res.data.evolved,
        newType: pet.value.pet_type
      }
      showLevelUp.value = true
    }
    
    alert(`签到成功! +${res.data.exp_gained} EXP`)
  } catch (err) {
    alert(err.response?.data?.detail || '签到失败')
  } finally {
    checkinLoading.value = false
  }
}

// 喂食
const feed = async (foodType) => {
  feedLoading.value = true
  showFeedModal.value = false
  try {
    const oldLevel = pet.value.level
    const res = await api.post('/pet/feed', { food_type: foodType })
    await loadPet()
    
    if (pet.value.level > oldLevel) {
      levelUpInfo.value = {
        newLevel: pet.value.level,
        evolved: res.data.evolved,
        newType: pet.value.pet_type
      }
      showLevelUp.value = true
    }
    
    alert(`喂食成功! 心情+${res.data.happiness_gained}`)
  } catch (err) {
    alert(err.response?.data?.detail || '喂食失败')
  } finally {
    feedLoading.value = false
  }
}

// 改名
const rename = async () => {
  if (!newName.value.trim()) return
  try {
    await api.put('/pet', { name: newName.value.trim() })
    pet.value.name = newName.value.trim()
    showRenameModal.value = false
  } catch (err) {
    alert(err.response?.data?.detail || '改名失败')
  }
}

// 工具函数
const getPetEmoji = (type) => {
  return evolutionStages[type]?.emoji || '🥚'
}

const getPetTypeName = (type) => {
  return evolutionStages[type]?.name || '神秘生物'
}

const isStageUnlocked = (stageKey) => {
  if (!pet.value) return false
  const stages = Object.keys(evolutionStages)
  const currentIdx = stages.indexOf(pet.value.pet_type)
  const stageIdx = stages.indexOf(stageKey)
  return stageIdx <= currentIdx
}

const getCheckinExp = () => {
  if (!pet.value) return 10
  const baseExp = 10
  const streakBonus = Math.min(50, pet.value.checkin_streak * 5)
  return baseExp + streakBonus
}

const formatAge = (dateStr) => {
  if (!dateStr) return '0'
  const created = new Date(dateStr)
  const now = new Date()
  const days = Math.floor((now - created) / (1000 * 60 * 60 * 24))
  return days + '天'
}

onMounted(() => {
  loadPet()
})
</script>

<style scoped>
.pet-page {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
  min-height: 100vh;
  background: linear-gradient(180deg, #fff9e6 0%, #fff 30%);
}

.loading {
  text-align: center;
  padding: 60px;
  color: #666;
}

.spinner {
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #ffc107;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 宠物展示区 */
.pet-display {
  text-align: center;
  padding: 30px 20px;
}

.pet-stage {
  position: relative;
  display: inline-block;
}

.pet-avatar {
  width: 150px;
  height: 150px;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 50%, #ffc107 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 30px rgba(255, 193, 7, 0.4);
  animation: float 3s ease-in-out infinite;
}

.pet-avatar.golden_dragon {
  background: linear-gradient(135deg, #ff6b6b 0%, #ffd93d 50%, #6bcb77 100%);
}

.pet-avatar.golden_phoenix {
  background: linear-gradient(135deg, #ff9a3c 0%, #ffce00 50%, #ff6f61 100%);
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.pet-emoji {
  font-size: 70px;
}

.pet-particles {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.particle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: #ffd700;
  border-radius: 50%;
  animation: particle 2s ease-in-out infinite;
}

.particle:nth-child(1) { animation-delay: 0s; top: -80px; left: 0; }
.particle:nth-child(2) { animation-delay: 0.4s; top: -60px; left: 60px; }
.particle:nth-child(3) { animation-delay: 0.8s; top: 0; left: 80px; }
.particle:nth-child(4) { animation-delay: 1.2s; top: 60px; left: 40px; }
.particle:nth-child(5) { animation-delay: 1.6s; top: 40px; left: -60px; }

@keyframes particle {
  0%, 100% { opacity: 0; transform: scale(0.5); }
  50% { opacity: 1; transform: scale(1); }
}

.pet-name {
  font-size: 28px;
  margin: 20px 0 8px 0;
  color: #333;
}

.pet-type-label {
  color: #888;
  font-size: 16px;
  margin: 0 0 20px 0;
}

.level-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.level {
  font-size: 20px;
  font-weight: bold;
  color: #ffc107;
  text-shadow: 1px 1px 0 #fff;
}

.exp-bar {
  width: 150px;
  height: 10px;
  background: #e0e0e0;
  border-radius: 5px;
  overflow: hidden;
}

.exp-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffc107, #ffeb3b);
  border-radius: 5px;
  transition: width 0.3s;
}

.exp-text {
  font-size: 12px;
  color: #888;
}

/* 属性卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.stat-icon {
  font-size: 28px;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #888;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.btn-action {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-action.checkin {
  background: linear-gradient(135deg, #4caf50 0%, #8bc34a 100%);
  color: white;
}

.btn-action.feed {
  background: linear-gradient(135deg, #ff9800 0%, #ffc107 100%);
  color: white;
}

.btn-action.rename {
  background: linear-gradient(135deg, #2196f3 0%, #03a9f4 100%);
  color: white;
}

.btn-icon {
  font-size: 24px;
  margin-right: 12px;
}

.btn-text {
  flex: 1;
  text-align: left;
}

.btn-reward {
  background: rgba(255,255,255,0.2);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
}

/* 进化路线 */
.evolution-section {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.evolution-section h2 {
  margin: 0 0 16px 0;
  font-size: 18px;
}

.evolution-path {
  display: flex;
  justify-content: space-between;
  position: relative;
}

.evolution-path::before {
  content: '';
  position: absolute;
  top: 25px;
  left: 30px;
  right: 30px;
  height: 3px;
  background: #e0e0e0;
}

.evolution-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
  opacity: 0.4;
}

.evolution-stage.unlocked {
  opacity: 1;
}

.evolution-stage.active .stage-emoji {
  transform: scale(1.3);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1.3); }
  50% { transform: scale(1.5); }
}

.stage-emoji {
  font-size: 32px;
  background: white;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 8px;
  transition: transform 0.3s;
}

.stage-name {
  font-size: 11px;
  color: #666;
}

.stage-level {
  font-size: 10px;
  color: #999;
}

/* 提示区域 */
.tips-section {
  background: #f9f9f9;
  border-radius: 12px;
  padding: 16px;
}

.tips-section h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
}

.tips-section ul {
  margin: 0;
  padding-left: 20px;
}

.tips-section li {
  color: #666;
  font-size: 14px;
  margin: 6px 0;
}

/* 无宠物状态 */
.no-pet {
  text-align: center;
  padding: 80px 20px;
}

.no-pet-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.no-pet h2 {
  color: #666;
  margin-bottom: 8px;
}

.no-pet p {
  color: #999;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  padding: 24px;
  max-width: 400px;
  width: 100%;
}

.modal-content h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  text-align: center;
}

.food-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.food-item {
  display: flex;
  align-items: center;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.food-item:hover {
  background: #fff3e0;
  transform: translateX(4px);
}

.food-icon {
  font-size: 32px;
  margin-right: 16px;
}

.food-name {
  flex: 1;
  font-weight: 500;
}

.food-effect {
  color: #4caf50;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.btn-cancel {
  flex: 1;
  padding: 12px;
  border: 1px solid #e0e0e0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
}

.btn-submit {
  flex: 1;
  padding: 12px;
  background: #ffc107;
  color: #333;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 升级动画 */
.level-up-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.level-up-content {
  text-align: center;
  animation: levelUp 0.5s ease-out;
}

@keyframes levelUp {
  0% { transform: scale(0.5); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.level-up-icon {
  font-size: 80px;
  animation: bounce 0.5s ease infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

.level-up-content h2 {
  color: #ffd700;
  font-size: 32px;
  margin: 20px 0 10px 0;
  text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

.new-level {
  color: white;
  font-size: 48px;
  font-weight: bold;
  margin: 0;
}

.evolution-msg {
  color: #ffd700;
  font-size: 24px;
  margin-top: 16px;
}
</style>
