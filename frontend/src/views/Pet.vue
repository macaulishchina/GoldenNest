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
          <div class="pet-avatar" :class="[pet.pet_type, 'mood-' + (pet.mood?.state || 'happy')]">
            <span class="pet-emoji">{{ getPetEmoji(pet.pet_type) }}</span>
            <!-- 心情特效 -->
            <span v-if="pet.mood?.state === 'ecstatic'" class="mood-sparkles">✨</span>
            <span v-if="pet.mood?.state === 'sad'" class="mood-tear">💧</span>
          </div>
          <div class="pet-particles">
            <span v-for="n in 5" :key="n" class="particle"></span>
          </div>
        </div>

        <h1 class="pet-name">
          {{ pet.name }}
          <span class="rename-icon" @click="showRenameModal = true" title="修改名字">✏️</span>
        </h1>
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
        <div class="stat-card mood-card">
          <span class="stat-icon">{{ pet.mood?.emoji || '❤️' }}</span>
          <div class="stat-info">
            <div class="stat-value-row">
              <span class="stat-value" :style="{ color: pet.mood?.color }">{{ pet.happiness }}</span>
              <span class="multiplier-badge" :class="multiplierClass">
                {{ pet.happiness_multiplier }}x
              </span>
            </div>
            <span class="stat-label">{{ pet.mood?.label || '心情值' }}</span>
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
            <span class="stat-value">{{ pet.pet_age_days || formatAge(pet.created_at) }}天</span>
            <span class="stat-label">陪伴天数</span>
          </div>
        </div>
      </div>

      <!-- 可领取的里程碑 -->
      <div v-if="pet.available_milestones?.length > 0" class="milestones-section">
        <h2>🎯 可领取的里程碑</h2>
        <div class="milestone-list">
          <div
            v-for="ms in pet.available_milestones"
            :key="ms.key"
            class="milestone-card"
          >
            <div class="milestone-icon">{{ ms.type === 'age' ? '📅' : '⭐' }}</div>
            <div class="milestone-info">
              <span class="milestone-name">{{ ms.label }}</span>
              <span class="milestone-reward">
                {{ ms.bonus_exp ? `+${ms.bonus_exp} EXP` : '' }}
                {{ ms.bonus_happiness ? `+${ms.bonus_happiness} 心情` : '' }}
              </span>
            </div>
            <button
              class="milestone-claim-btn"
              @click="claimMilestone(ms.key)"
              :disabled="milestoneLoading"
            >领取</button>
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
          class="btn-action chat"
          @click="showPetChat = true"
        >
          <span class="btn-icon">💬</span>
          <span class="btn-text">聊天</span>
        </button>

        <button
          class="btn-action game"
          @click="showGamePanel = !showGamePanel"
        >
          <span class="btn-icon">🎮</span>
          <span class="btn-text">小游戏</span>
          <span class="btn-badge" v-if="totalGamePlaysLeft > 0">{{ totalGamePlaysLeft }}</span>
        </button>

      </div>

      <!-- Pet AI Chat Dialog -->
      <AIChatDialog
        v-model:show="showPetChat"
        :title="`💬 与${pet.name}对话`"
        :ai-name="pet.name"
        context-type="pet"
        :suggestions="getPetChatSuggestions()"
        :on-chat="handlePetChat"
      />

      <!-- 小游戏面板 -->
      <div v-if="showGamePanel" class="game-panel">
        <h2>🎮 小游戏 <span class="game-total-badge">剩余 {{ totalGamePlaysLeft }}/{{ pet.daily_game_limit || 10 }} 次</span></h2>
        <div class="game-grid">
          <div
            v-for="(game, gameKey) in pet.game_status"
            :key="gameKey"
            class="game-card"
            :class="{
              disabled: !game.can_play || (hasActiveGame && hasActiveGame !== gameKey),
              active: game.has_active_session
            }"
            @click="(game.can_play && (!hasActiveGame || hasActiveGame === gameKey)) && startGame(gameKey)"
          >
            <div class="game-card-top">
              <span class="game-icon">{{ game.icon }}</span>
              <span v-if="game.has_active_session" class="active-badge">进行中</span>
            </div>
            <div class="game-name">{{ game.name }}</div>
            <div class="game-desc">{{ game.description }}</div>
            <div class="game-footer">
              <span class="game-exp">{{ game.exp_range }} EXP</span>
              <span v-if="game.used_today" class="game-played">已玩{{ game.used_today }}次</span>
            </div>
          </div>
        </div>
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

      <!-- 经验获取记录 -->
      <div class="exp-logs-section">
        <div class="exp-logs-header" @click="toggleExpLogs">
          <h3>📊 经验获取记录</h3>
          <span class="toggle-icon" :class="{ expanded: showExpLogs }">▼</span>
        </div>

        <div v-if="showExpLogs" class="exp-logs-content">
          <!-- 经验获取方式说明 -->
          <div class="tips-box">
            <h4>💡 经验获取方式</h4>
            <ul>
              <li>📅 每日签到: +10~45 EXP (连续签到加成)</li>
              <li>🌾 普通饲料: +3 EXP | 🌽 高级饲料: +8 EXP | 🍖 豪华大餐: +20 EXP</li>
              <li>🃏 记忆翻牌: 30~60 EXP | 📈 迷你炒股: 5~80 EXP</li>
              <li>⚔️ 宠物探险: 5~60 EXP | 💣 扫雷: 20~1000 EXP</li>
              <li>💰 存款/投资/投票等操作也可获得EXP</li>
              <li>😊 心情越高EXP倍率越高 (最高1.2x)</li>
            </ul>
          </div>

          <!-- 经验记录列表 -->
          <div class="exp-logs-list">
            <div v-if="expLogsLoading" class="loading-small">
              <span class="spinner-small"></span>
              加载中...
            </div>
            <template v-else-if="expLogs.length > 0">
              <div
                v-for="log in expLogs"
                :key="log.id"
                class="exp-log-item"
              >
                <div class="log-icon">{{ getSourceIcon(log.source) }}</div>
                <div class="log-info">
                  <span class="log-source">
                    {{ log.source_detail || log.source_name }}
                  </span>
                  <span class="log-meta">
                    <span class="log-operator">{{ log.operator_nickname }}</span>
                    <span class="log-separator">·</span>
                    <span class="log-time">{{ formatLogTime(log.created_at) }}</span>
                  </span>
                </div>
                <div class="log-exp">+{{ log.exp_amount }} EXP</div>
              </div>
              <div v-if="expLogsTotal > expLogs.length" class="load-more">
                <button @click="loadMoreExpLogs" :disabled="expLogsLoading">
                  加载更多 ({{ expLogs.length }}/{{ expLogsTotal }})
                </button>
              </div>
            </template>
            <div v-else class="no-logs">
              暂无经验获取记录
            </div>
          </div>
        </div>
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
            v-for="(food, foodKey) in pet?.feed_status"
            :key="foodKey"
            class="food-item"
            :class="{ 'food-disabled': !food.can_feed }"
            @click="food.can_feed && feed(foodKey)"
          >
            <span class="food-icon">{{ food.emoji }}</span>
            <div class="food-detail">
              <span class="food-name">{{ food.name }}</span>
              <span class="food-effects">
                +{{ food.happiness }} 心情 · +{{ food.exp }} EXP
              </span>
              <span v-if="!food.can_feed" class="food-unavailable">
                <template v-if="food.cooldown_remaining > 0">
                  冷却中 {{ formatCooldown(food.cooldown_remaining) }}
                </template>
                <template v-else-if="food.daily_limit && food.used_today >= food.daily_limit">
                  今日已用完
                </template>
              </span>
              <span v-else-if="food.daily_limit" class="food-remaining">
                剩余 {{ food.daily_limit - food.used_today }}/{{ food.daily_limit }} 次
              </span>
            </div>
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

    <!-- 难度选择弹窗（统一） -->
    <div v-if="showDifficultyModal" class="modal-overlay" @click.self="cancelDifficultySelect">
      <div class="modal-content difficulty-modal">
        <h2>🎮 {{ difficultyModalTitle }}</h2>
        <div class="difficulty-cards">
          <div
            v-for="diff in currentGameDifficulties"
            :key="diff.key"
            class="difficulty-card"
            :class="diff.key"
            @click="confirmDifficultySelect(diff.key)"
          >
            <div class="diff-label">{{ diff.label }}</div>
            <div class="diff-desc">{{ diff.desc }}</div>
            <div class="diff-exp">奖励: {{ diff.exp }}</div>
            <div v-if="diff.rules" class="diff-rules">{{ diff.rules }}</div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="cancelDifficultySelect">取消</button>
        </div>
      </div>
    </div>

    <!-- 游戏进行中弹窗 -->
    <div v-if="activeGame" class="modal-overlay game-overlay" :class="{ 'fullscreen-active': gameFullscreen }">
      <div class="modal-content game-modal" :class="{ fullscreen: gameFullscreen }">
        <div class="game-modal-header">
          <h2>{{ activeGameName }}</h2>
          <button
            v-if="activeGameState && !activeGameState.completed && !activeGameState.game_over"
            class="game-abandon-btn"
            @click="showAbandonConfirm = true"
          >🏳️</button>
          <div class="game-header-actions">
            <button
              class="game-mute-btn"
              @click="gameMuted = toggleMute()"
              :title="gameMuted ? '开启音效' : '关闭音效'"
            >{{ gameMuted ? '🔇' : '🔊' }}</button>
            <button
              v-if="(activeGame === 'minesweeper' || activeGame === 'adventure') && activeGameState"
              class="game-fullscreen-btn"
              @click="gameFullscreen = !gameFullscreen"
              :title="gameFullscreen ? '退出全屏' : '全屏模式'"
            >{{ gameFullscreen ? '⬜' : '⛶' }}</button>
            <button class="game-close-btn" @click="closeGame">✕</button>
          </div>
        </div>

        <!-- 确认放弃弹窗 -->
        <div v-if="showAbandonConfirm" class="abandon-confirm-overlay" @click.self="showAbandonConfirm = false">
          <div class="abandon-confirm-dialog">
            <div class="abandon-confirm-title">🏳️ 确认放弃</div>
            <div class="abandon-confirm-message">确定要放弃本局游戏吗？<br>放弃后不会获得任何经验。</div>
            <div class="abandon-confirm-actions">
              <button class="abandon-confirm-btn cancel" @click="showAbandonConfirm = false">取消</button>
              <button class="abandon-confirm-btn confirm" @click="doAbandonGame">确认放弃</button>
            </div>
          </div>
        </div>
        <MemoryGame v-if="activeGame === 'memory'" :state="activeGameState" @action="gameAction" />
        <StockGame v-if="activeGame === 'stock'" :state="activeGameState" @action="gameAction" />
        <AdventureGame v-if="activeGame === 'adventure'" :state="activeGameState" @action="gameAction" />
        <MinesweeperGame v-if="activeGame === 'minesweeper'" :state="activeGameState" @action="gameAction" />
        <div v-if="gameCompleted" class="game-done-actions">
          <button class="btn-submit" @click="closeGame">关闭</button>
        </div>
      </div>
    </div>

    <!-- 升级动画 -->
    <div v-if="showLevelUp && !levelUpInfo.evolved" class="level-up-overlay" @click="showLevelUp = false">
      <div class="level-up-content">
        <div class="level-up-icon">🎉</div>
        <h2>恭喜升级!</h2>
        <p class="new-level">Lv.{{ levelUpInfo.newLevel }}</p>
      </div>
    </div>

    <!-- 进化庆典全屏覆盖 -->
    <div v-if="showEvolution" class="evolution-overlay" @click="showEvolution = false">
      <!-- 烟花粒子 -->
      <div class="fireworks">
        <span v-for="n in 20" :key="n" class="firework-particle" :style="fireworkStyle(n)"></span>
      </div>
      <div class="evolution-celebration">
        <div class="evolution-transform">
          <span class="old-form">{{ getPetEmoji(levelUpInfo.oldType) }}</span>
          <span class="evolution-arrow">➜</span>
          <span class="new-form">{{ getPetEmoji(levelUpInfo.newType) }}</span>
        </div>
        <h2 class="evolution-title">进化成功!</h2>
        <p class="evolution-new-name">{{ getPetTypeName(levelUpInfo.newType) }}</p>
        <p v-if="levelUpInfo.bonusExp" class="evolution-bonus">
          进化奖励 +{{ levelUpInfo.bonusExp }} EXP
        </p>
        <p class="evolution-hint">点击任意处关闭</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { api, petAiApi } from '@/api'
import { useUserStore } from '@/stores/user'
import AIChatDialog from '@/components/AIChatDialog.vue'
import MemoryGame from '@/components/games/MemoryGame.vue'
import StockGame from '@/components/games/StockGame.vue'
import AdventureGame from '@/components/games/AdventureGame.vue'
import MinesweeperGame from '@/components/games/MinesweeperGame.vue'
import { toggleMute, isMuted, warmUp, adventureBGM } from '@/utils/gameSound'

const userStore = useUserStore()
const message = useMessage()

// 状态
const loading = ref(false)
const checkinLoading = ref(false)
const feedLoading = ref(false)
const gameLoading = ref(false)
const milestoneLoading = ref(false)
const pet = ref(null)
const showFeedModal = ref(false)
const showRenameModal = ref(false)
const showLevelUp = ref(false)
const showEvolution = ref(false)
const showGamePanel = ref(false)
const showPetChat = ref(false)
const newName = ref('')
const levelUpInfo = ref({})

// 游戏状态
const activeGame = ref(null)      // 'memory' | 'stock' | 'adventure' | 'minesweeper' | null
const activeGameState = ref({})
const activeGameName = ref('')
const gameCompleted = ref(false)
const showAbandonConfirm = ref(false)

const gameFullscreen = ref(false)

// 全屏时隐藏导航栏
watch(gameFullscreen, (fs) => {
  document.body.classList.toggle('game-fullscreen', fs)
}, { immediate: false })
const gameMuted = ref(false)

// 移动端检测 - 用于扫雷自动全屏
const isMobile = computed(() => window.innerWidth <= 768 || 'ontouchstart' in window)

// 难度选择状态
const showDifficultyModal = ref(false)
const pendingGameType = ref(null)  // 待开始的游戏类型

// 各游戏的难度配置
const GAME_DIFFICULTIES = {
  memory: {
    name: '记忆翻牌',
    difficulties: [
      { key: 'easy', label: '入门', desc: '3×4 (6对) | 初始20秒', exp: '15~30 EXP' },
      { key: 'medium', label: '普通', desc: '4×4 (8对) | 初始15秒', exp: '30~60 EXP' },
      { key: 'hard', label: '困难', desc: '4×5 (10对) | 初始10秒', exp: '60~120 EXP' },
      { key: 'expert', label: '地狱', desc: '6×6 (18对) | 初始10秒 | 连续失败扣时', exp: '300~1000 EXP' },
    ]
  },
  stock: {
    name: '迷你炒股',
    difficulties: [
      { key: 'easy', label: '入门', desc: '5回合 低波动', exp: '10~50 EXP' },
      { key: 'medium', label: '普通', desc: '10回合 中波动', exp: '20~100 EXP' },
      { key: 'hard', label: '困难', desc: '15回合 高波动 | 支持做空', exp: '50~200 EXP', rules: '可卖空股票获利于下跌行情，做空保证金基于现金' },
      { key: 'expert', label: '地狱', desc: '25回合 极端波动 | 支持做空', exp: '200~1000 EXP', rules: '可卖空股票获利于下跌行情，做空保证金基于现金' },
    ]
  },
  adventure: {
    name: '宠物探险',
    difficulties: [
      { key: 'easy', label: '入门', desc: '5层 低难度', exp: '25~50 EXP' },
      { key: 'medium', label: '普通', desc: '8层 中难度', exp: '50~100 EXP' },
      { key: 'hard', label: '困难', desc: '12层 高难度', exp: '115~250 EXP' },
      { key: 'expert', label: '地狱', desc: '18层 极高难度', exp: '500~1000 EXP' },
      { key: 'endless', label: '无尽', desc: '无限层 难度递增', exp: '无上限', rules: '层数越高怪物越强，偶有难度波动。可随时撤退保留经验，死亡也保留经验。每10层有Boss' },
    ]
  },
  minesweeper: {
    name: '扫雷',
    difficulties: [
      { key: 'easy', label: '入门', desc: '6×6 (5雷)', exp: '20 EXP' },
      { key: 'medium', label: '普通', desc: '9×9 (12雷)', exp: '60 EXP' },
      { key: 'hard', label: '困难', desc: '12×12 (30雷)', exp: '200 EXP' },
      { key: 'expert', label: '地狱', desc: '16×16 (55雷)', exp: '1000 EXP' },
    ]
  }
}

// 计算当前游戏的难度列表
const currentGameDifficulties = computed(() => {
  if (!pendingGameType.value) return []
  return GAME_DIFFICULTIES[pendingGameType.value]?.difficulties || []
})

// 难度选择弹窗标题
const difficultyModalTitle = computed(() => {
  if (!pendingGameType.value) return '选择难度'
  return GAME_DIFFICULTIES[pendingGameType.value]?.name || '选择难度'
})

// 经验记录相关状态
const showExpLogs = ref(false)
const expLogs = ref([])
const expLogsTotal = ref(0)
const expLogsLoading = ref(false)
const expLogsOffset = ref(0)
const EXP_LOGS_LIMIT = 20

// 进化阶段（已修复阈值）
const evolutionStages = {
  golden_egg: { name: '金蛋', emoji: '🥚', minLevel: 1 },
  golden_chick: { name: '金雏鸡', emoji: '🐣', minLevel: 10 },
  golden_bird: { name: '金凤雏', emoji: '🐤', minLevel: 30 },
  golden_phoenix: { name: '金凤凰', emoji: '🦅', minLevel: 60 },
  golden_dragon: { name: '金龙', emoji: '🐉', minLevel: 100 }
}

// 计算经验进度
const expProgress = computed(() => {
  if (!pet.value) return 0
  return Math.min(100, (pet.value.current_exp / pet.value.exp_to_next) * 100)
})

// 心情倍率样式
const multiplierClass = computed(() => {
  const m = pet.value?.happiness_multiplier || 1.0
  if (m >= 1.2) return 'multiplier-high'
  if (m >= 1.0) return 'multiplier-normal'
  if (m >= 0.8) return 'multiplier-low'
  return 'multiplier-bad'
})

// 剩余游戏总次数
const totalGamePlaysLeft = computed(() => {
  if (!pet.value) return 0
  const limit = pet.value.daily_game_limit || 10
  const used = pet.value.total_games_used || 0
  return Math.max(0, limit - used)
})

// 当前有进行中的游戏类型（null表示没有）
const hasActiveGame = computed(() => {
  if (!pet.value?.game_status) return null
  for (const [key, game] of Object.entries(pet.value.game_status)) {
    if (game && game.has_active_session) return key
  }
  return null
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
    pet.value = null
  } finally {
    loading.value = false
  }
}

// 处理升级/进化结果
const handleExpResult = (res, oldLevel) => {
  if (res.data.evolved) {
    levelUpInfo.value = {
      newLevel: pet.value.level,
      evolved: true,
      oldType: res.data.old_type,
      newType: res.data.new_type,
      bonusExp: res.data.evolution_bonus_exp || 0
    }
    showEvolution.value = true
  } else if (pet.value.level > oldLevel) {
    levelUpInfo.value = {
      newLevel: pet.value.level,
      evolved: false
    }
    showLevelUp.value = true
  }
}

// 签到
const checkin = async () => {
  checkinLoading.value = true
  try {
    const oldLevel = pet.value.level
    const res = await api.post('/pet/checkin')
    await loadPet()
    handleExpResult(res, oldLevel)
    message.success(`签到成功! +${res.data.exp_gained} EXP`)
  } catch (err) {
    message.error(err.response?.data?.detail || '签到失败')
  } finally {
    checkinLoading.value = false
  }
}

// AI Pet Chat
const handlePetChat = async (messageText, history = []) => {
  const response = await petAiApi.chat({
    message: messageText,
    history: history
  })
  return {
    reply: response.data.reply,
    suggestions: []
  }
}

const getPetChatSuggestions = () => {
  if (!pet.value) return []
  
  const suggestions = ['你好', '今天心情怎么样']
  
  if (pet.value.happiness < 50) {
    suggestions.push('怎么不开心了')
  }
  
  if (!pet.value.checked_in_today) {
    suggestions.push('一起签到吧')
  }
  
  return suggestions
}

// 喂食
const feed = async (foodType) => {
  feedLoading.value = true
  showFeedModal.value = false
  try {
    const oldLevel = pet.value.level
    const res = await api.post('/pet/feed', { food_type: foodType })
    await loadPet()
    handleExpResult(res, oldLevel)
    message.success(`喂食成功! 心情+${res.data.happiness_gained}, +${res.data.exp_gained} EXP`)
  } catch (err) {
    message.error(err.response?.data?.detail || '喂食失败')
  } finally {
    feedLoading.value = false
  }
}

// 开始游戏
const startGame = async (gameType, difficulty = null) => {
  const gameStatus = pet.value?.game_status?.[gameType]

  // 有进行中的游戏 → 直接恢复，不需要选难度
  if (gameStatus?.has_active_session) {
    gameLoading.value = true
    gameCompleted.value = false
    try {
      const res = await api.post('/pet/game/start', { game_type: gameType })
      activeGame.value = gameType
      activeGameState.value = res.data.state
      activeGameName.value = res.data.game_name
      showGamePanel.value = false
      // 扫雷在移动端自动全屏
      if (gameType === 'minesweeper' && isMobile.value) {
        gameFullscreen.value = true
      }
    } catch (err) {
      message.error(err.response?.data?.detail || '启动游戏失败')
    } finally {
      gameLoading.value = false
    }
    return
  }

  // 所有游戏都需要选难度（如果没有传入难度）
  if (!difficulty) {
    pendingGameType.value = gameType
    showDifficultyModal.value = true
    showGamePanel.value = false
    return
  }

  // 有难度参数，直接开始游戏
  gameLoading.value = true
  gameCompleted.value = false
  try {
    const payload = { game_type: gameType, difficulty }
    const res = await api.post('/pet/game/start', payload)
    activeGame.value = gameType
    activeGameState.value = res.data.state
    activeGameName.value = res.data.game_name
    showGamePanel.value = false
    showDifficultyModal.value = false
    // 扫雷在移动端自动全屏
    if (gameType === 'minesweeper' && isMobile.value) {
      gameFullscreen.value = true
    }
  } catch (err) {
    message.error(err.response?.data?.detail || '启动游戏失败')
  } finally {
    gameLoading.value = false
  }
}

// 确认选择难度
const confirmDifficultySelect = (difficulty) => {
  if (!pendingGameType.value) return
  warmUp() // 预热音频上下文，确保第一个音效不会被截断
  startGame(pendingGameType.value, difficulty)
}

// 取消难度选择
const cancelDifficultySelect = () => {
  showDifficultyModal.value = false
  pendingGameType.value = null
}

// 游戏操作
const gameAction = async (action) => {
  if (gameLoading.value) return
  gameLoading.value = true
  try {
    const oldLevel = pet.value.level
    const res = await api.post('/pet/game/action', {
      game_type: activeGame.value,
      action
    })
    activeGameState.value = res.data.state
    if (res.data.result?.completed) {
      gameCompleted.value = true
      if (res.data.pet) {
        pet.value = res.data.pet
      }
      if (res.data.exp_gained > 0) {
        message.success(`游戏完成！+${res.data.exp_gained} EXP`)
      }
      handleExpResult(res, oldLevel)
    }
  } catch (err) {
    const detail = err.response?.data?.detail || '操作失败'
    // 扫雷和弦失败由组件内部 toast 处理，不在此重复弹出
    if (activeGame.value === 'minesweeper' && detail.includes('和弦')) {
      // 静默处理，MinesweeperGame 组件已本地拦截
    } else {
      message.error(detail)
    }
  } finally {
    gameLoading.value = false
  }
}

// 放弃游戏
const doAbandonGame = async () => {
  showAbandonConfirm.value = false
  await gameAction({ action: 'abandon' })
}

// 关闭游戏
const closeGame = () => {
  adventureBGM.stop()
  gameFullscreen.value = false
  activeGame.value = null
  activeGameState.value = {}
  if (gameCompleted.value) {
    gameCompleted.value = false
  }
  // 刷新宠物数据，更新 game_status 中的 has_active_session 状态
  loadPet()
}

// 领取里程碑
const claimMilestone = async (milestoneKey) => {
  milestoneLoading.value = true
  try {
    const oldLevel = pet.value.level
    const res = await api.post('/pet/milestone/claim', { milestone_key: milestoneKey })
    await loadPet()
    handleExpResult(res, oldLevel)
    message.success(res.data.message || '里程碑领取成功!')
  } catch (err) {
    message.error(err.response?.data?.detail || '领取失败')
  } finally {
    milestoneLoading.value = false
  }
}

// 改名
const rename = async () => {
  if (!newName.value.trim()) return
  try {
    await api.put('/pet', { name: newName.value.trim() })
    pet.value.name = newName.value.trim()
    showRenameModal.value = false
    message.success('改名成功')
  } catch (err) {
    message.error(err.response?.data?.detail || '改名失败')
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
  const streakBonus = Math.min(7, pet.value.checkin_streak) * 5
  return baseExp + streakBonus
}

const formatAge = (dateStr) => {
  if (!dateStr) return '0'
  const created = new Date(dateStr)
  const now = new Date()
  const days = Math.floor((now - created) / (1000 * 60 * 60 * 24))
  return days
}

const formatCooldown = (seconds) => {
  if (seconds <= 0) return ''
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}时${m}分`
  return `${m}分钟`
}

const fireworkStyle = (n) => {
  const angle = (n / 20) * 2 * Math.PI
  const distance = 100 + Math.random() * 150
  const delay = Math.random() * 1.5
  const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#FF9A3C', '#A855F7', '#FF69B4']
  const color = colors[n % colors.length]
  const tx = Math.cos(angle) * distance
  const ty = Math.sin(angle) * distance
  return {
    '--tx': tx + 'px',
    '--ty': ty + 'px',
    '--delay': delay + 's',
    '--color': color
  }
}

// 经验记录相关方法
const toggleExpLogs = async () => {
  showExpLogs.value = !showExpLogs.value
  if (showExpLogs.value && expLogs.value.length === 0) {
    await loadExpLogs()
  }
}

const loadExpLogs = async () => {
  expLogsLoading.value = true
  try {
    const res = await api.get('/pet/exp-logs', {
      params: { limit: EXP_LOGS_LIMIT, offset: 0, time_range: 'day' }
    })
    expLogs.value = res.data.logs
    expLogsTotal.value = res.data.total
    expLogsOffset.value = res.data.logs.length
  } catch (err) {
    console.error('获取经验记录失败:', err)
    message.error('获取经验记录失败')
  } finally {
    expLogsLoading.value = false
  }
}

const loadMoreExpLogs = async () => {
  if (expLogsLoading.value) return
  expLogsLoading.value = true
  try {
    const res = await api.get('/pet/exp-logs', {
      params: { limit: EXP_LOGS_LIMIT, offset: expLogsOffset.value, time_range: 'day' }
    })
    expLogs.value.push(...res.data.logs)
    expLogsOffset.value += res.data.logs.length
  } catch (err) {
    console.error('加载更多记录失败:', err)
  } finally {
    expLogsLoading.value = false
  }
}

const getSourceIcon = (source) => {
  const icons = {
    'daily_checkin': '📅',
    'feed': '🍖',
    'feed_basic': '🌾',
    'feed_premium': '🌽',
    'feed_luxury': '🍖',
    'deposit': '💰',
    'investment': '📈',
    'vote': '🗳️',
    'proposal_passed': '✅',
    'expense_approved': '💳',
    'gift': '🎁',
    'gift_sent': '🎁',
    'achievement_unlock': '🏆',
    'game_memory': '🃏',
    'game_stock': '📈',
    'game_adventure': '⚔️',
    'game_minesweeper': '💣',
    'milestone_age': '📅',
    'milestone_exp': '⭐',
    'evolution_bonus': '🎊'
  }
  return icons[source] || '⭐'
}

const formatLogTime = (dateStr) => {
  if (!dateStr) return ''
  // 后端返回的是 UTC 时间，如果没有 Z 后缀需要添加
  let normalizedStr = dateStr
  if (!dateStr.endsWith('Z') && !dateStr.includes('+')) {
    normalizedStr = dateStr + 'Z'
  }
  const date = new Date(normalizedStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  return `${date.getMonth() + 1}/${date.getDate()}`
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
  background: var(--theme-bg-primary);
}

.loading {
  text-align: center;
  padding: 60px;
  color: var(--theme-text-secondary);
}

.spinner {
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 4px solid var(--theme-border-light, #f3f3f3);
  border-top: 4px solid #ffc107;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* ==================== 宠物展示区 ==================== */
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
  position: relative;
  overflow: visible;
}

/* ==================== 进化形态动画 ==================== */
.pet-avatar.golden_egg {
  animation: egg-wobble 2.5s ease-in-out infinite;
}

.pet-avatar.golden_chick {
  animation: chick-peck 2s ease-in-out infinite;
}

.pet-avatar.golden_bird {
  animation: bird-flap 2.5s ease-in-out infinite;
}

.pet-avatar.golden_phoenix {
  background: linear-gradient(135deg, #ff9a3c 0%, #ffce00 50%, #ff6f61 100%);
  animation: phoenix-glow 3s ease-in-out infinite;
}

.pet-avatar.golden_dragon {
  background: linear-gradient(135deg, #ff6b6b 0%, #ffd93d 50%, #6bcb77 100%);
  animation: dragon-breathe 4s ease-in-out infinite;
}

@keyframes egg-wobble {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(5deg); }
  75% { transform: rotate(-5deg); }
}

@keyframes chick-peck {
  0%, 100% { transform: translateY(0); }
  30% { transform: translateY(0); }
  35% { transform: translateY(6px); }
  40% { transform: translateY(0); }
  45% { transform: translateY(6px); }
  50% { transform: translateY(0); }
}

@keyframes bird-flap {
  0%, 100% { transform: translateY(0) scaleX(1); }
  25% { transform: translateY(-8px) scaleX(1.05); }
  50% { transform: translateY(0) scaleX(1); }
  75% { transform: translateY(-4px) scaleX(0.97); }
}

@keyframes phoenix-glow {
  0%, 100% {
    box-shadow: 0 10px 30px rgba(255, 154, 60, 0.4), 0 0 20px rgba(255, 206, 0, 0.2);
  }
  50% {
    box-shadow: 0 10px 40px rgba(255, 154, 60, 0.7), 0 0 40px rgba(255, 206, 0, 0.5);
  }
}

@keyframes dragon-breathe {
  0%, 100% {
    transform: scale(1);
    filter: hue-rotate(0deg);
  }
  50% {
    transform: scale(1.05);
    filter: hue-rotate(30deg);
  }
}

/* ==================== 心情状态动画（优先级高） ==================== */
.pet-avatar.mood-ecstatic {
  animation: mood-ecstatic 1.5s ease-in-out infinite !important;
}

.pet-avatar.mood-happy {
  /* 使用进化动画即可，不覆盖 */
}

.pet-avatar.mood-neutral {
  animation: mood-neutral 4s ease-in-out infinite !important;
}

.pet-avatar.mood-sad {
  animation: mood-sad 3s ease-in-out infinite !important;
  filter: saturate(0.6) brightness(0.85);
}

@keyframes mood-ecstatic {
  0%, 100% { transform: translateY(0) scale(1); }
  25% { transform: translateY(-12px) scale(1.05); }
  50% { transform: translateY(0) scale(1); }
  75% { transform: translateY(-8px) scale(1.02); }
}

@keyframes mood-neutral {
  0%, 100% { transform: scale(1); opacity: 0.95; }
  50% { transform: scale(0.98); opacity: 0.85; }
}

@keyframes mood-sad {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(5px); }
}

/* 心情特效 */
.mood-sparkles {
  position: absolute;
  top: -5px;
  right: -5px;
  font-size: 24px;
  animation: sparkle-float 1.5s ease-in-out infinite;
  pointer-events: none;
}

@keyframes sparkle-float {
  0%, 100% { transform: translateY(0) scale(1); opacity: 1; }
  50% { transform: translateY(-8px) scale(1.2); opacity: 0.7; }
}

.mood-tear {
  position: absolute;
  bottom: 10px;
  right: 20px;
  font-size: 18px;
  animation: tear-drop 2s ease-in infinite;
  pointer-events: none;
}

@keyframes tear-drop {
  0% { transform: translateY(0); opacity: 0; }
  30% { opacity: 1; }
  100% { transform: translateY(30px); opacity: 0; }
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
  color: var(--theme-text-primary);
}

.rename-icon {
  font-size: 12px;
  cursor: pointer;
  opacity: 0.35;
  transition: opacity 0.2s;
  vertical-align: super;
  margin-left: 2px;
}

.rename-icon:hover {
  opacity: 0.8;
}

.pet-type-label {
  color: var(--theme-text-secondary);
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
  background: var(--theme-bg-secondary);
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
  color: var(--theme-text-secondary);
}

/* ==================== 属性卡片 ==================== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--theme-bg-card);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
}

.stat-icon {
  font-size: 28px;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: var(--theme-text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--theme-text-secondary);
}

.multiplier-badge {
  font-size: 11px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 8px;
  line-height: 1;
}

.multiplier-high {
  background: var(--theme-success-bg, #e8f5e9);
  color: var(--theme-success, #2e7d32);
}

.multiplier-normal {
  background: var(--theme-bg-secondary);
  color: var(--theme-text-secondary);
}

.multiplier-low {
  background: var(--theme-warning-bg);
  color: #e65100;
}

.multiplier-bad {
  background: var(--theme-error-bg);
  color: var(--theme-error);
}

/* ==================== 里程碑区域 ==================== */
.milestones-section {
  background: var(--theme-warning-bg);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
  border: 1px solid var(--theme-warning-light);
}

.milestones-section h2 {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: var(--theme-text-primary);
}

.milestone-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.milestone-card {
  display: flex;
  align-items: center;
  background: var(--theme-bg-card);
  padding: 14px 16px;
  border-radius: 12px;
  gap: 12px;
  box-shadow: 0 1px 4px var(--theme-shadow-sm);
}

.milestone-icon {
  font-size: 28px;
}

.milestone-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.milestone-name {
  font-weight: 600;
  color: var(--theme-text-primary);
  font-size: 15px;
}

.milestone-reward {
  font-size: 13px;
  color: #4caf50;
  font-weight: 500;
}

.milestone-claim-btn {
  background: linear-gradient(135deg, #ffc107, #ffca28);
  border: none;
  border-radius: 20px;
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 600;
  color: var(--theme-text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.milestone-claim-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(255, 193, 7, 0.5);
}

.milestone-claim-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ==================== 操作按钮 ==================== */
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

.btn-action.chat {
  background: linear-gradient(135deg, #00bcd4 0%, #03a9f4 100%);
  color: white;
}

.btn-action.game {
  background: linear-gradient(135deg, #9c27b0 0%, #e040fb 100%);
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

.btn-badge {
  background: rgba(255,255,255,0.3);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

/* ==================== 小游戏面板 ==================== */
.game-panel {
  background: var(--theme-bg-card);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
  animation: slideDown 0.3s ease-out;
}

.game-panel h2 {
  margin: 0 0 16px 0;
  font-size: 18px;
}

.game-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.game-card {
  background: var(--theme-bg-card);
  border-radius: 12px;
  padding: 14px;
  border: 1px solid var(--theme-border-light);
  cursor: pointer;
  transition: all 0.2s;
}

.game-card:hover:not(.disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  border-color: #c0c0ff;
}

.game-card.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.game-card.active {
  border-color: var(--theme-purple);
  background: var(--theme-purple-bg);
}

.game-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.game-icon {
  font-size: 28px;
}

.active-badge {
  font-size: 10px;
  background: #9c27b0;
  color: white;
  padding: 2px 6px;
  border-radius: 8px;
  font-weight: bold;
}

.game-name {
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 4px;
  color: var(--theme-text-primary);
}

.game-desc {
  font-size: 12px;
  color: var(--theme-text-tertiary);
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.game-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.game-exp {
  font-size: 11px;
  color: #4caf50;
  font-weight: 600;
}

.game-played {
  font-size: 11px;
  color: var(--theme-text-secondary);
  background: var(--theme-bg-secondary);
  padding: 2px 6px;
  border-radius: 8px;
}

.game-total-badge {
  font-size: 13px;
  font-weight: normal;
  color: var(--theme-text-secondary);
  margin-left: 8px;
}

/* ==================== 游戏弹窗 ==================== */
.game-overlay {
  z-index: 1500;
}

.game-overlay.fullscreen-active {
  padding: 0;
}

.game-modal {
  max-width: 420px;
  max-height: 85vh;
  height: 85vh;
  overflow: hidden;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.game-modal.fullscreen {
  max-width: 100vw;
  max-height: 100vh;
  width: 100vw;
  height: 100vh;
  border-radius: 0;
  margin: 0;
  padding: 12px;
  padding-bottom: env(safe-area-inset-bottom, 8px);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.game-modal.fullscreen .minesweeper-game {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.game-modal.fullscreen .board-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
}

.game-modal.fullscreen .board {
  max-width: none;
  width: auto;
  height: auto;
  max-height: 100%;
}

.game-modal.fullscreen .cell {
  min-width: 36px;
  min-height: 36px;
  font-size: clamp(12px, 3vw, 18px);
}

/* 大屏全屏时格子可以更大 */
@media (min-width: 500px) {
  .game-modal.fullscreen .cell {
    min-width: 40px;
    min-height: 40px;
  }
}

.game-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.game-modal-header h2 {
  margin: 0;
  font-size: 18px;
}

.game-abandon-btn {
  padding: 6px 12px;
  border: 1px solid var(--theme-border);
  border-radius: 6px;
  background: var(--theme-bg-card);
  color: var(--theme-text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 12px;
}
.game-abandon-btn:hover {
  background: var(--theme-error-bg);
  border-color: var(--theme-error-light);
}

/* 确认放弃弹窗 */
.abandon-confirm-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  z-index: 100;
}
.abandon-confirm-dialog {
  background: var(--theme-bg-card);
  border-radius: 12px;
  padding: 20px;
  max-width: 280px;
  text-align: center;
  box-shadow: 0 4px 20px var(--theme-shadow);
}
.abandon-confirm-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 12px;
}
.abandon-confirm-message {
  font-size: 14px;
  color: var(--theme-text-secondary);
  margin-bottom: 20px;
  line-height: 1.5;
}
.abandon-confirm-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.abandon-confirm-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}
.abandon-confirm-btn.cancel {
  background: var(--theme-bg-secondary);
  color: var(--theme-text-secondary);
}
.abandon-confirm-btn.cancel:hover {
  background: var(--theme-card-hover);
}
.abandon-confirm-btn.confirm {
  background: #ef5350;
  color: white;
}
.abandon-confirm-btn.confirm:hover {
  background: #e53935;
}

.game-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.game-mute-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: var(--theme-bg-secondary);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.game-mute-btn:hover {
  background: var(--theme-card-hover);
}

.game-fullscreen-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: var(--theme-bg-secondary);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.game-fullscreen-btn:hover {
  background: var(--theme-card-hover);
}

.game-close-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: var(--theme-bg-secondary);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.game-close-btn:hover {
  background: var(--theme-card-hover);
}

.game-done-actions {
  margin-top: 12px;
}

/* ==================== 进化路线 ==================== */
.evolution-section {
  background: var(--theme-bg-card);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
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
  background: var(--theme-border);
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
  background: var(--theme-bg-card);
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
  color: var(--theme-text-secondary);
}

.stage-level {
  font-size: 10px;
  color: var(--theme-text-tertiary);
}

/* ==================== 经验获取记录 ==================== */
.exp-logs-section {
  background: var(--theme-bg-card);
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
  overflow: hidden;
}

.exp-logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.exp-logs-header:hover {
  background: var(--theme-card-hover);
}

.exp-logs-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--theme-text-primary);
}

.toggle-icon {
  font-size: 12px;
  color: var(--theme-text-tertiary);
  transition: transform 0.3s;
}

.toggle-icon.expanded {
  transform: rotate(180deg);
}

.exp-logs-content {
  padding: 0 20px 20px;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tips-box {
  background: var(--theme-warning-bg);
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 16px;
  border: 1px solid var(--theme-warning-light);
}

.tips-box h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: var(--theme-warning, #856404);
}

.tips-box ul {
  margin: 0;
  padding-left: 18px;
}

.tips-box li {
  color: var(--theme-text-secondary);
  font-size: 13px;
  margin: 4px 0;
}

.exp-logs-list {
  max-height: 400px;
  overflow-y: auto;
}

.loading-small {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  color: var(--theme-text-secondary);
  font-size: 14px;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid var(--theme-border-light, #f3f3f3);
  border-top: 2px solid #ffc107;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.exp-log-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: var(--theme-bg-secondary);
  border-radius: 10px;
  margin-bottom: 8px;
  transition: background 0.2s;
}

.exp-log-item:hover {
  background: var(--theme-card-hover);
}

.log-icon {
  font-size: 24px;
  margin-right: 12px;
  width: 32px;
  text-align: center;
}

.log-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.log-source {
  font-size: 14px;
  color: var(--theme-text-primary);
  font-weight: 500;
}

.log-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.log-operator {
  color: var(--theme-text-secondary);
  font-weight: 500;
}

.log-separator {
  color: var(--theme-border, #ccc);
}

.log-time {
  color: var(--theme-text-tertiary);
}

.log-exp {
  font-size: 14px;
  font-weight: bold;
  color: #ffc107;
  background: var(--theme-warning-bg);
  padding: 4px 10px;
  border-radius: 12px;
}

.load-more {
  text-align: center;
  padding: 12px 0;
}

.load-more button {
  background: none;
  border: 1px solid var(--theme-border, #ddd);
  padding: 8px 20px;
  border-radius: 20px;
  color: var(--theme-text-secondary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.load-more button:hover:not(:disabled) {
  background: var(--theme-card-hover);
  border-color: var(--theme-border);
}

.load-more button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-logs {
  text-align: center;
  padding: 30px;
  color: var(--theme-text-tertiary);
  font-size: 14px;
}

/* ==================== 无宠物状态 ==================== */
.no-pet {
  text-align: center;
  padding: 80px 20px;
}

.no-pet-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.no-pet h2 {
  color: var(--theme-text-secondary);
  margin-bottom: 8px;
}

.no-pet p {
  color: var(--theme-text-tertiary);
}

/* ==================== Modal 通用 ==================== */
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
  background: var(--theme-bg-card);
  border-radius: 16px;
  padding: 24px;
  max-width: 400px;
  width: 100%;
  animation: modalIn 0.25s ease-out;
}

@keyframes modalIn {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.modal-content h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  text-align: center;
}

/* ==================== 喂食弹窗 ==================== */
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
  background: var(--theme-bg-secondary);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  gap: 14px;
}

.food-item:hover:not(.food-disabled) {
  background: var(--theme-warning-bg);
  transform: translateX(4px);
}

.food-item.food-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.food-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.food-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.food-name {
  font-weight: 600;
  font-size: 15px;
  color: var(--theme-text-primary);
}

.food-effects {
  font-size: 13px;
  color: #4caf50;
}

.food-unavailable {
  font-size: 12px;
  color: #f44336;
}

.food-remaining {
  font-size: 12px;
  color: var(--theme-text-secondary);
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--theme-border, #e0e0e0);
  border-radius: 8px;
  font-size: 16px;
  box-sizing: border-box;
  background: var(--theme-bg-secondary);
  color: var(--theme-text-primary);
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.btn-cancel {
  flex: 1;
  padding: 12px;
  border: 1px solid var(--theme-border);
  background: var(--theme-bg-secondary);
  color: var(--theme-text-primary);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.btn-cancel:hover {
  background: var(--theme-bg-elevated, var(--theme-bg-secondary));
  border-color: var(--theme-text-tertiary);
}

.btn-submit {
  flex: 1;
  padding: 12px;
  background: #ffc107;
  color: var(--theme-text-primary);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ==================== 升级动画 ==================== */
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

/* ==================== 进化庆典全屏 ==================== */
.evolution-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(ellipse at center, #1a0533 0%, #0d0015 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 3000;
  overflow: hidden;
}

.fireworks {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.firework-particle {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color);
  animation: firework 2s var(--delay) ease-out infinite;
}

@keyframes firework {
  0% {
    transform: translate(0, 0) scale(1);
    opacity: 1;
  }
  100% {
    transform: translate(var(--tx), var(--ty)) scale(0);
    opacity: 0;
  }
}

.evolution-celebration {
  text-align: center;
  z-index: 1;
  animation: celebrationIn 0.8s ease-out;
}

@keyframes celebrationIn {
  0% { transform: scale(0); opacity: 0; }
  60% { transform: scale(1.1); }
  100% { transform: scale(1); opacity: 1; }
}

.evolution-transform {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 24px;
}

.old-form {
  font-size: 60px;
  opacity: 0.6;
  animation: fadeOld 2s ease-in-out infinite;
}

@keyframes fadeOld {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 0.3; }
}

.evolution-arrow {
  font-size: 36px;
  color: #ffd700;
  animation: arrowPulse 1s ease-in-out infinite;
}

@keyframes arrowPulse {
  0%, 100% { transform: translateX(0); opacity: 0.7; }
  50% { transform: translateX(8px); opacity: 1; }
}

.new-form {
  font-size: 80px;
  animation: newFormGlow 1.5s ease-in-out infinite;
}

@keyframes newFormGlow {
  0%, 100% {
    transform: scale(1);
    filter: drop-shadow(0 0 10px rgba(255, 215, 0, 0.5));
  }
  50% {
    transform: scale(1.1);
    filter: drop-shadow(0 0 25px rgba(255, 215, 0, 0.9));
  }
}

.evolution-title {
  color: #ffd700;
  font-size: 36px;
  margin: 0 0 8px 0;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
}

.evolution-new-name {
  color: white;
  font-size: 24px;
  margin: 0 0 16px 0;
}

.evolution-bonus {
  color: #4caf50;
  font-size: 20px;
  font-weight: bold;
  margin: 0 0 24px 0;
  animation: bonusPop 0.5s ease-out 0.5s both;
}

@keyframes bonusPop {
  0% { transform: scale(0); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.evolution-hint {
  color: rgba(255,255,255,0.4);
  font-size: 14px;
  margin: 0;
}

/* ==================== 移动端响应式 ==================== */
@media (max-width: 767px) {
  .pet-page {
    padding: 16px;
    padding-bottom: 80px;
  }

  .pet-avatar {
    width: 120px;
    height: 120px;
  }

  .pet-emoji {
    font-size: 55px;
  }

  .pet-name {
    font-size: 24px;
  }

  .stats-grid {
    gap: 10px;
  }

  .stat-card {
    padding: 12px;
  }

  .stat-icon {
    font-size: 24px;
  }

  .stat-value {
    font-size: 16px;
  }

  .stat-label {
    font-size: 11px;
  }

  .btn-action {
    min-height: 52px;
    padding: 14px 16px;
    font-size: 15px;
  }

  .btn-icon {
    font-size: 20px;
    margin-right: 10px;
  }

  .evolution-section {
    padding: 16px;
    overflow-x: auto;
  }

  .evolution-path {
    min-width: max-content;
    padding: 0 10px;
  }

  .stage-emoji {
    font-size: 28px;
    width: 44px;
    height: 44px;
  }

  .stage-name {
    font-size: 10px;
  }

  .stage-level {
    font-size: 9px;
  }

  .modal-content {
    margin: 16px;
    padding: 20px;
    max-height: 80vh;
    overflow-y: auto;
  }

  .food-item {
    min-height: 48px;
  }

  .food-icon {
    font-size: 28px;
  }

  .form-group input {
    font-size: 16px;
    padding: 14px;
  }

  .btn-cancel,
  .btn-submit {
    padding: 14px;
    font-size: 15px;
  }

  /* 游戏面板移动端适配 */
  .game-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .game-card {
    padding: 12px;
  }

  .game-icon {
    font-size: 24px;
  }

  .game-name {
    font-size: 14px;
  }

  .game-modal {
    max-height: 90vh;
    margin: 8px;
    padding: 12px;
  }

  /* 进化庆典移动端 */
  .old-form {
    font-size: 44px;
  }

  .new-form {
    font-size: 60px;
  }

  .evolution-title {
    font-size: 28px;
  }

  .evolution-arrow {
    font-size: 28px;
  }
}

/* ==================== 难度选择弹窗 ==================== */
.difficulty-modal {
  max-width: 400px;
}

.difficulty-modal h2 {
  text-align: center;
  margin-bottom: 20px;
}

.difficulty-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.difficulty-card {
  padding: 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  background: var(--theme-bg-card);
  color: var(--theme-text-primary);
}

.difficulty-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--theme-shadow);
}

.difficulty-card.easy {
  background: var(--theme-success-bg);
  border-color: var(--theme-success);
}

.difficulty-card.medium {
  background: var(--theme-warning-bg);
  border-color: var(--theme-warning);
}

.difficulty-card.hard {
  background: var(--theme-error-bg);
  border-color: var(--theme-error);
}

.difficulty-card.expert {
  background: var(--theme-bg-elevated);
  border-color: var(--theme-primary);
  box-shadow: 0 0 20px var(--theme-primary-shadow);
}

.diff-label {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.diff-desc {
  font-size: 13px;
  color: var(--theme-text-secondary);
  margin-bottom: 4px;
}

.diff-exp {
  font-size: 12px;
  color: var(--theme-text-secondary);
  font-weight: 500;
}

.difficulty-card.expert .diff-exp {
  color: var(--theme-primary);
  font-weight: 600;
}

.diff-rules {
  font-size: 11px;
  color: var(--theme-text-tertiary, #999);
  margin-top: 4px;
  line-height: 1.4;
}

.difficulty-card.endless {
  border-color: var(--theme-purple, #9c7cf4);
  background: var(--theme-purple-bg, linear-gradient(135deg, #f3edff, #f5f0ff));
}

.difficulty-card.endless .diff-label {
  color: var(--theme-purple, #7c4dff);
}

.difficulty-card.endless .diff-desc {
  color: var(--theme-text-secondary);
}

.difficulty-card.endless .diff-exp {
  color: var(--theme-purple, #7c4dff);
  font-weight: 600;
}

.difficulty-card.endless .diff-rules {
  color: var(--theme-text-tertiary, #999);
}

@media (max-width: 480px) {
  .difficulty-modal {
    margin: 12px;
  }
  
  .difficulty-card {
    padding: 14px;
  }
  
  .diff-label {
    font-size: 16px;
  }
}
</style>
