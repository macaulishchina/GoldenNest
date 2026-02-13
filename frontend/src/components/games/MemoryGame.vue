<template>
  <div class="memory-game">
    <div class="game-header">
      <div class="stat">翻牌: <strong>{{ state.flips }}</strong></div>
      <div class="stat">配对: <strong>{{ state.matched_pairs }}/{{ state.total_pairs }}</strong></div>
      <div class="stat timer" :class="{ warning: timeLeft <= 5, danger: timeLeft <= 3 }">
        ⏱️ <strong>{{ timeLeft }}s</strong>
      </div>
    </div>

    <div class="diff-badge" :class="state.difficulty">
      {{ diffLabel }}
    </div>

    <div 
      class="board"
      :style="{ gridTemplateColumns: `repeat(${state.cols || 4}, minmax(${(state.cols || 4) > 5 ? '36px' : '44px'}, 1fr))` }"
    >
      <div
        v-for="(card, idx) in displayBoard"
        :key="idx"
        class="card-slot"
        :class="{
          flipped: card.revealed || card.active,
          matched: card.revealed,
          active: card.active
        }"
        @click="flipCard(idx)"
      >
        <div class="card-inner">
          <div class="card-front">?</div>
          <div class="card-back">{{ card.symbol || '?' }}</div>
        </div>
      </div>
    </div>

    <!-- 游戏结果 -->
    <div v-if="state.completed || timeUp || state.abandoned" class="game-result" :class="resultClass">
      <div class="result-title">{{ resultTitle }}</div>
      <div v-if="state.exp_earned > 0" class="result-exp">获得 {{ state.exp_earned }} EXP</div>
      <div v-else class="result-exp lost">未获得经验</div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { memorySound } from '../../utils/gameSound'

const props = defineProps<{
  state: any
}>()

const emit = defineEmits<{
  (e: 'action', action: any): void
}>()

// 难度标签
const difficulties: Record<string, string> = {
  easy: '入门',
  medium: '普通',
  hard: '困难',
  expert: '地狱'
}

const diffLabel = computed(() => difficulties[props.state?.difficulty] || '')

// 倒计时（按难度设置初始时间）
const TIMER_BY_DIFFICULTY: Record<string, number> = {
  easy: 20,
  medium: 15,
  hard: 10,
  expert: 10
}
const timeLeft = ref(TIMER_BY_DIFFICULTY[props.state?.difficulty] || 10)
const timeUp = ref(false)
const showAbandonConfirm = ref(false)
const consecutiveFails = ref(0) // 连续失败计数（地狱难度惩罚用）
let timer: ReturnType<typeof setInterval> | null = null
let noMatchTimeout: ReturnType<typeof setTimeout> | null = null // 不匹配翻回定时器

onMounted(() => {
  startTimer()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (noMatchTimeout) clearTimeout(noMatchTimeout)
})

function startTimer() {
  timer = setInterval(() => {
    if (props.state?.completed || timeUp.value) {
      if (timer) clearInterval(timer)
      return
    }
    timeLeft.value--
    if (timeLeft.value <= 0) {
      timeUp.value = true
      if (timer) clearInterval(timer)
      emit('action', { timeout: true })
    }
  }, 1000)
}

// 监听配对成功，加时间 + 重置连续失败
watch(() => props.state?.matched_pairs, (newVal, oldVal) => {
  if (newVal && oldVal !== undefined && newVal > oldVal) {
    timeLeft.value = Math.min(30, timeLeft.value + 10)
    consecutiveFails.value = 0 // 配对成功重置连续失败计数
  }
})

// 结果展示
const resultClass = computed(() => {
  if (props.state?.abandoned || timeUp.value) return 'lose'
  return props.state?.exp_earned > 0 ? 'win' : 'lose'
})

const resultTitle = computed(() => {
  if (props.state?.abandoned) return '🏳️ 已放弃'
  if (timeUp.value) return '⏰ 时间到！'
  const pairs = props.state?.total_pairs || 6
  const flips = props.state?.flips || 0
  if (flips <= pairs) return '🎉 完美通关！'
  if (flips <= pairs * 1.5) return '👍 优秀！'
  return '✅ 游戏完成！'
})

// 临时翻开的卡牌
const tempFlipped = ref<number[]>([])
const isProcessing = ref(false)

const displayBoard = computed(() => {
  return (props.state.board || []).map((symbol: string | null, idx: number) => {
    const isRevealed = symbol !== null
    const isActive = tempFlipped.value.includes(idx)
    return {
      symbol: isRevealed ? symbol : (isActive ? getActiveSymbol(idx) : null),
      revealed: isRevealed,
      active: isActive,
    }
  })
})

const activeSymbols = ref<Record<number, string>>({})

function getActiveSymbol(idx: number): string | null {
  return activeSymbols.value[idx] || null
}

watch(() => props.state.last_flip_result, (result) => {
  if (!result) return
  if (result.action === 'first_flip') {
    memorySound.flip()
    tempFlipped.value = [result.position]
    activeSymbols.value = { [result.position]: result.symbol }
  } else if (result.action === 'match') {
    memorySound.match()
    // 立即清理，不需要等待动画
    if (noMatchTimeout) { clearTimeout(noMatchTimeout); noMatchTimeout = null }
    tempFlipped.value = []
    activeSymbols.value = {}
    isProcessing.value = false
    consecutiveFails.value = 0
    // 检查是否全部匹配完 → 胜利
    if (props.state.matched_pairs >= props.state.total_pairs) {
      memorySound.win()
    }
  } else if (result.action === 'no_match') {
    memorySound.mismatch()
    tempFlipped.value = result.positions
    activeSymbols.value = {
      [result.positions[0]]: result.symbols[0],
      [result.positions[1]]: result.symbols[1],
    }
    isProcessing.value = true
    // 地狱难度：连续失败惩罚
    if (props.state?.difficulty === 'expert') {
      consecutiveFails.value++
      if (consecutiveFails.value >= 2) {
        const penalty = consecutiveFails.value // 第2次连续失败扣 2s，第3次扣 3s...
        timeLeft.value = Math.max(0, timeLeft.value - penalty)
      }
    } else {
      consecutiveFails.value++
    }
    // 加快翻回动画（从800ms降为400ms）
    if (noMatchTimeout) clearTimeout(noMatchTimeout)
    noMatchTimeout = setTimeout(() => {
      tempFlipped.value = []
      activeSymbols.value = {}
      isProcessing.value = false
      noMatchTimeout = null
    }, 400)
  }
}, { deep: true })

function flipCard(idx: number) {
  // 如果正在处理不匹配动画，强制结束当前动画，允许丝滑连续操作
  if (isProcessing.value) {
    if (noMatchTimeout) {
      clearTimeout(noMatchTimeout)
      noMatchTimeout = null
    }
    tempFlipped.value = []
    activeSymbols.value = {}
    isProcessing.value = false
  }
  if (props.state.completed) return
  if (timeUp.value) return
  if (props.state.board[idx] !== null) return
  if (tempFlipped.value.includes(idx)) return
  emit('action', { position: idx })
}

function doAbandon() {
  showAbandonConfirm.value = false
  if (timer) clearInterval(timer)
  emit('action', { action: 'abandon' })
}
</script>

<style scoped>
.memory-game {
  padding: 8px;
  position: relative;
}
.game-header {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--theme-text-secondary, #666);
}
.timer {
  transition: color 0.3s;
}
.timer.warning {
  color: #ff9800;
}
.timer.danger {
  color: #f44336;
  animation: pulse 0.5s ease infinite;
}
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.abandon-btn-inline {
  padding: 4px 8px;
  border: 1px solid var(--theme-border, #ddd);
  border-radius: 6px;
  background: var(--theme-bg-card, #fff);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 4px;
}
.abandon-btn-inline:hover {
  background: var(--theme-error-bg, #ffebee);
  border-color: var(--theme-error-light, #ef9a9a);
}

.diff-badge {
  text-align: center;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  color: white;
  margin: 0 auto 12px;
  width: fit-content;
}
.diff-badge.easy { background: #4caf50; }
.diff-badge.medium { background: #2196f3; }
.diff-badge.hard { background: #ff9800; }
.diff-badge.expert { background: #e91e63; }

.board {
  display: grid;
  gap: 4px;
  margin: 0 auto;
  max-width: 100%;
  max-height: calc(100vh - 200px);
}
.card-slot {
  aspect-ratio: 1;
  perspective: 600px;
  cursor: pointer;
  min-width: 32px;
  max-width: 70px;
}
.card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.25s;
  transform-style: preserve-3d;
}
.card-slot.flipped .card-inner,
.card-slot.matched .card-inner {
  transform: rotateY(180deg);
}
.card-front, .card-back {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: clamp(14px, 3.5vw, 28px);
}
.card-front {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  font-weight: bold;
}
.card-back {
  background: var(--theme-bg-card, #fff);
  border: 2px solid var(--theme-border, #e0e0e0);
  transform: rotateY(180deg);
}
.card-slot.matched .card-back {
  background: var(--theme-success-bg, #e8f5e9);
  border-color: #4caf50;
}
.card-slot.active .card-back {
  background: var(--theme-warning-bg, #fff8e1);
  border-color: #ffc107;
}

/* 结果 */
.game-result {
  text-align: center;
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
}
.game-result.win {
  background: var(--theme-success-bg, linear-gradient(135deg, #e8f5e9, #c8e6c9));
}
.game-result.lose {
  background: var(--theme-error-bg, linear-gradient(135deg, #ffebee, #ffcdd2));
}
.result-title {
  font-size: 18px;
  font-weight: bold;
}
.win .result-title { color: var(--theme-success, #2e7d32); }
.lose .result-title { color: var(--theme-error, #c62828); }
.result-exp {
  font-size: 14px;
  color: var(--theme-success, #388e3c);
  margin-top: 4px;
}
.result-exp.lost {
  color: var(--theme-text-tertiary, #999);
}

/* 确认弹窗 */
.confirm-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  z-index: 100;
}
.confirm-dialog {
  background: var(--theme-bg-card, white);
  border-radius: 12px;
  padding: 20px;
  max-width: 280px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}
.confirm-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 12px;
}
.confirm-message {
  font-size: 14px;
  color: var(--theme-text-secondary, #666);
  margin-bottom: 20px;
  line-height: 1.5;
}
.confirm-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.confirm-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}
.confirm-btn.cancel {
  background: var(--theme-bg-secondary, #f5f5f5);
  color: var(--theme-text-secondary, #666);
}
.confirm-btn.cancel:hover {
  background: var(--theme-border, #e0e0e0);
}
.confirm-btn.confirm {
  background: #ef5350;
  color: white;
}
.confirm-btn.confirm:hover {
  background: #e53935;
}
</style>