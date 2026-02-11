<template>
  <div class="minesweeper-game">
    <!-- 游戏面板 -->
    <template v-if="state">
      <!-- 状态栏 - 固定顶部 -->
      <div class="status-bar">
        <div class="stat">
          <span class="stat-icon">💣</span>
          <span>{{ remainingMines }}</span>
        </div>
        <div class="stat diff-badge" :class="state.difficulty">
          {{ diffLabel }}
        </div>
        <div class="stat">
          <span class="stat-icon">⏱️</span>
          <span>{{ elapsedTime }}s</span>
        </div>
      </div>

      <!-- 雷区 - 独立滚动区域 -->
      <div class="board-scroll-container" ref="boardScrollRef">
        <div class="board-wrapper">
          <div
            class="board"
            :style="{
              gridTemplateColumns: `repeat(${state.cols}, minmax(${state.cols > 12 ? '28px' : '36px'}, 1fr))`,
            }"
          >
            <div
              v-for="(_, idx) in state.rows * state.cols"
              :key="idx"
              class="cell"
              :class="cellClass(Math.floor(idx / state.cols), idx % state.cols)"
              @click.prevent="cellClick(Math.floor(idx / state.cols), idx % state.cols)"
              @mousedown="cellMouseDown(Math.floor(idx / state.cols), idx % state.cols, $event)"
              @mouseup="cellMouseUp"
              @contextmenu.prevent="cellRightClick(Math.floor(idx / state.cols), idx % state.cols)"
              @touchstart="cellTouchStart(Math.floor(idx / state.cols), idx % state.cols, $event)"
              @touchend="cellTouchEnd(Math.floor(idx / state.cols), idx % state.cols, $event)"
              @touchmove="cellTouchMove($event)"
            >
              <span v-if="cellContent(Math.floor(idx / state.cols), idx % state.cols)" :class="'n' + state.board[Math.floor(idx / state.cols)][idx % state.cols]">
                {{ cellContent(Math.floor(idx / state.cols), idx % state.cols) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 和弦提示 - 仅显示最新一条，新的覆盖旧的 -->
      <transition name="chord-toast">
        <div v-if="chordToast" class="chord-toast" :class="chordToast.type" @click="chordToast = null">
          {{ chordToast.text }}
        </div>
      </transition>

      <!-- 操作提示 - 固定底部 -->
      <div v-if="!state.completed" class="hints-bar">
        <div class="hint-item">
          <span class="hint-icon">👆</span>
          <span class="hint-text">点击翻开</span>
        </div>
        <div class="hint-item">
          <span class="hint-icon">🚩</span>
          <span class="hint-text">长按标记</span>
        </div>
        <div class="hint-item">
          <span class="hint-icon">⚡</span>
          <span class="hint-text">数字和弦</span>
        </div>
      </div>

      <!-- 结果 - 固定底部 -->
      <div v-if="state.completed" class="game-result" :class="resultClass">
        <div class="result-title">{{ resultTitle }}</div>
        <div v-if="state.won && !state.abandoned" class="result-exp">获得 {{ state.exp_earned }} EXP</div>
        <div v-else class="result-exp lost">未获得经验</div>
      </div>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { mineSound } from '../../utils/gameSound'

const props = defineProps<{ state: any }>()
const emit = defineEmits<{
  (e: 'action', action: any): void
  (e: 'chord-error', msg: string): void
}>()

const startTime = ref(Date.now())
const elapsedTime = ref(0)
const showAbandonConfirm = ref(false)
const boardScrollRef = ref<HTMLElement | null>(null)
const mouseDownCell = ref<{ r: number; c: number } | null>(null)
const isLeftMouseDown = ref(false)
const isRightMouseDown = ref(false)

// ===== 触摸支持（优化版）=====
const touchStartTime = ref(0)
const touchMoved = ref(false)
const longPressTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const longPressFired = ref(false)      // 本次触摸周期内长按是否已触发
const touchLocked = ref(false)         // 触摸锁定，防止长按后浏览器合成click
const LONG_PRESS_DURATION = 400        // 400ms触发，比之前更灵敏

// ===== 和弦动画 =====
const chordAnimCells = ref<Set<string>>(new Set())
const chordToast = ref<{ text: string; type: string } | null>(null)
let chordToastTimer: ReturnType<typeof setTimeout> | null = null

let timer: ReturnType<typeof setInterval> | null = null

const difficulties = [
  { key: 'easy', label: '入门', rows: 6, cols: 6, mines: 5, exp: 20 },
  { key: 'medium', label: '进阶', rows: 9, cols: 9, mines: 12, exp: 50 },
  { key: 'hard', label: '困难', rows: 12, cols: 12, mines: 30, exp: 120 },
  { key: 'expert', label: '地狱', rows: 16, cols: 16, mines: 55, exp: 1000 },
]

const diffLabel = computed(() => {
  const d = difficulties.find(d => d.key === props.state?.difficulty)
  return d ? d.label : ''
})

const remainingMines = computed(() => {
  if (!props.state) return 0
  let flags = 0
  for (const row of props.state.flagged) {
    for (const f of row) {
      if (f) flags++
    }
  }
  return props.state.mine_count - flags
})

// 结果展示
const resultClass = computed(() => {
  if (props.state?.abandoned) return 'lose'
  return props.state?.won ? 'win' : 'lose'
})

const resultTitle = computed(() => {
  if (props.state?.abandoned) return '🏳️ 已放弃'
  return props.state?.won ? '🎉 扫雷成功！' : '💥 踩到地雷！'
})

onMounted(() => {
  startTime.value = Date.now()
  timer = setInterval(() => {
    if (props.state?.completed) {
      if (timer) clearInterval(timer)
      return
    }
    elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
  }, 1000)
  
  // 全局监听鼠标松开事件，确保和弦检测正确
  window.addEventListener('mouseup', cellMouseUp)
  
  // 处理触摸滚动
  const el = boardScrollRef.value
  if (el) {
    el.addEventListener('touchmove', (e: TouchEvent) => {
      const { scrollHeight, clientHeight, scrollWidth, clientWidth } = el
      if (scrollHeight > clientHeight || scrollWidth > clientWidth) {
        e.stopPropagation()
      }
    }, { passive: true })
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (longPressTimer.value) clearTimeout(longPressTimer.value)
  if (chordToastTimer) clearTimeout(chordToastTimer)
  window.removeEventListener('mouseup', cellMouseUp)
})

// 监听游戏完成 → 播放胜利/失败音效
watch(() => props.state?.completed, (newVal, oldVal) => {
  if (newVal && !oldVal) {
    if (props.state?.won && !props.state?.abandoned) {
      mineSound.win()
    } else {
      mineSound.explode()
    }
  }
})

function cellClass(r: number, c: number) {
  if (!props.state) return ''
  const revealed = props.state.revealed[r][c]
  const flagged = props.state.flagged[r][c]
  const questioned = props.state.questioned?.[r]?.[c] || false
  const val = props.state.board[r][c]
  const classes: string[] = []
  if (revealed) {
    classes.push('revealed')
    if (val === -1) classes.push('mine')
  } else {
    classes.push('hidden')
    if (flagged) classes.push('flagged')
    else if (questioned) classes.push('questioned')
  }
  
  // 和弦动画效果：格子在和弦范围内时闪烁
  const key = `${r},${c}`
  if (chordAnimCells.value.has(key)) {
    classes.push('chord-anim')
  }
  
  // 和弦预览：鼠标按下数字格时高亮自身
  if (revealed && val > 0 && (isLeftMouseDown.value || isRightMouseDown.value)) {
    if (mouseDownCell.value && mouseDownCell.value.r === r && mouseDownCell.value.c === c) {
      classes.push('chord-hover')
    }
  }
  
  return classes.join(' ')
}

function cellContent(r: number, c: number): string {
  if (!props.state) return ''
  const revealed = props.state.revealed[r][c]
  const flagged = props.state.flagged[r][c]
  const questioned = props.state.questioned?.[r]?.[c] || false
  const val = props.state.board[r][c]
  if (!revealed && flagged) return '🚩'
  if (!revealed && questioned) return '❓'
  if (!revealed) return ''
  if (val === -1) return '💣'
  if (val === 0) return ''
  return String(val)
}

// ========== 和弦动画 ==========
function getNeighborKeys(r: number, c: number): string[] {
  const keys: string[] = []
  for (let dr = -1; dr <= 1; dr++) {
    for (let dc = -1; dc <= 1; dc++) {
      if (dr === 0 && dc === 0) continue
      const nr = r + dr
      const nc = c + dc
      if (nr >= 0 && nr < props.state.rows && nc >= 0 && nc < props.state.cols) {
        keys.push(`${nr},${nc}`)
      }
    }
  }
  return keys
}

function playChordAnimation(r: number, c: number) {
  const neighbors = getNeighborKeys(r, c)
  chordAnimCells.value = new Set([`${r},${c}`, ...neighbors])
  // 动画结束后清除
  setTimeout(() => {
    chordAnimCells.value = new Set()
  }, 550)
}

function showChordToast(text: string, type: 'error' | 'info' = 'error') {
  // 清除旧的 timer
  if (chordToastTimer) {
    clearTimeout(chordToastTimer)
  }
  // 新提示覆盖旧提示，不会累积
  chordToast.value = { text, type }
  chordToastTimer = setTimeout(() => {
    chordToast.value = null
    chordToastTimer = null
  }, 2000)
}

// ========== 和弦操作（前置本地检查 + 动画）==========
function doChord(r: number, c: number) {
  if (!props.state) return
  const val = props.state.board[r][c]
  if (val <= 0) return
  
  // 本地计算周围旗数与未翻开数
  let flagCount = 0
  let unrevealed = 0
  for (let dr = -1; dr <= 1; dr++) {
    for (let dc = -1; dc <= 1; dc++) {
      if (dr === 0 && dc === 0) continue
      const nr = r + dr
      const nc = c + dc
      if (nr >= 0 && nr < props.state.rows && nc >= 0 && nc < props.state.cols) {
        if (props.state.flagged[nr][nc]) {
          flagCount++
        } else if (!props.state.revealed[nr][nc]) {
          unrevealed++
        }
      }
    }
  }
  
  // 本地前置检查：两种和弦条件都不满足时，显示内置 toast 而非 message.error
  if (flagCount !== val && flagCount + unrevealed !== val) {
    showChordToast(`🚩${flagCount} + 未翻开${unrevealed} ≠ 数字${val}`, 'error')
    return
  }
  
  // 播放和弦动画
  playChordAnimation(r, c)
  mineSound.chord()
  
  // 发送和弦操作到后端
  emit('action', { action: 'chord', row: r, col: c })
}

// ========== 点击事件 ==========
function cellClick(r: number, c: number) {
  if (!props.state || props.state.completed) return
  
  // 触摸锁定中（长按后），不处理 click
  if (touchLocked.value) return
  
  const revealed = props.state.revealed[r][c]
  const flagged = props.state.flagged[r][c]
  const questioned = props.state.questioned?.[r]?.[c] || false

  // 对已翻开的数字格子进行和弦操作
  if (revealed) {
    const val = props.state.board[r][c]
    if (val > 0) {
      doChord(r, c)
    }
    return
  }

  // 对未翻开的格子：如果有标记不做任何操作
  if (flagged || questioned) return
  
  mineSound.reveal()
  emit('action', { action: 'reveal', row: r, col: c })
}

function cellRightClick(r: number, c: number) {
  if (!props.state || props.state.completed) return
  if (!props.state.revealed[r][c]) {
    const isFlagged = props.state.flagged[r][c]
    if (isFlagged) mineSound.unflag()
    else mineSound.flag()
    emit('action', { action: 'flag', row: r, col: c })
  }
}

function cellMouseDown(r: number, c: number, e: MouseEvent) {
  if (!props.state || props.state.completed) return
  
  if (e.button === 0) {
    isLeftMouseDown.value = true
  } else if (e.button === 2) {
    isRightMouseDown.value = true
  }
  
  mouseDownCell.value = { r, c }
  
  // 检测双键和弦
  if (isLeftMouseDown.value && isRightMouseDown.value) {
    const revealed = props.state.revealed[r][c]
    if (revealed) {
      const val = props.state.board[r][c]
      if (val > 0) {
        doChord(r, c)
      }
    }
  }
}

function cellMouseUp(e: MouseEvent) {
  if (e instanceof MouseEvent) {
    if (e.button === 0) {
      isLeftMouseDown.value = false
    } else if (e.button === 2) {
      isRightMouseDown.value = false
    }
  }
  mouseDownCell.value = null
}

// ========== 触摸事件（优化版：解决长按插旗误触问题）==========
const touchStartPos = ref<{ x: number; y: number } | null>(null)
const TOUCH_MOVE_THRESHOLD = 10 // 移动超过10px判定为滑动

function cellTouchStart(r: number, c: number, e: TouchEvent) {
  if (!props.state || props.state.completed) return
  
  touchStartTime.value = Date.now()
  touchMoved.value = false
  longPressFired.value = false
  touchLocked.value = false
  
  // 记录触摸起始位置，用于判断是否为滑动
  const touch = e.touches[0]
  touchStartPos.value = touch ? { x: touch.clientX, y: touch.clientY } : null
  
  // 设置长按定时器
  longPressTimer.value = setTimeout(() => {
    if (!touchMoved.value) {
      // 标记本次触摸已触发长按操作
      longPressFired.value = true
      // 立即锁定，阻止后续一切 click 行为
      touchLocked.value = true
      
      if (!props.state.revealed[r][c]) {
        // 长按未翻开格子 → 插旗/取消旗
        const isFlagged = props.state.flagged[r][c]
        if (isFlagged) mineSound.unflag()
        else mineSound.flag()
        emit('action', { action: 'flag', row: r, col: c })
        if (navigator.vibrate) {
          navigator.vibrate(50)
        }
      } else {
        // 长按已翻开的数字格子 → 和弦
        const val = props.state.board[r][c]
        if (val > 0) {
          doChord(r, c)
          if (navigator.vibrate) {
            navigator.vibrate(30)
          }
        }
      }
    }
  }, LONG_PRESS_DURATION)
}

function cellTouchMove(e: TouchEvent) {
  // 用位置偏移判断是否为滑动，而非简单的 touchmove 触发
  if (!touchMoved.value && touchStartPos.value) {
    const touch = e.touches[0]
    if (touch) {
      const dx = Math.abs(touch.clientX - touchStartPos.value.x)
      const dy = Math.abs(touch.clientY - touchStartPos.value.y)
      if (dx > TOUCH_MOVE_THRESHOLD || dy > TOUCH_MOVE_THRESHOLD) {
        touchMoved.value = true
      }
    }
  }
  if (touchMoved.value && longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }
}

function cellTouchEnd(r: number, c: number, e: TouchEvent) {
  if (!props.state || props.state.completed) return
  
  // 清除长按定时器
  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }
  
  // ★ 核心修复：长按已触发过操作 → 完全阻止后续行为
  if (longPressFired.value) {
    e.preventDefault()
    // 延迟解锁，确保浏览器合成的 click 事件也被拦截
    setTimeout(() => {
      touchLocked.value = false
    }, 300)
    return
  }
  
  // 手指移动过 → 取消
  if (touchMoved.value) return
  
  // 快速点击（< 400ms）→ 翻开/和弦
  const touchDuration = Date.now() - touchStartTime.value
  if (touchDuration < LONG_PRESS_DURATION) {
    e.preventDefault()
    cellClick(r, c)
  }
}

function doAbandon() {
  showAbandonConfirm.value = false
  if (timer) clearInterval(timer)
  emit('action', { action: 'abandon' })
}
</script>

<style scoped>
.minesweeper-game {
  padding: 8px;
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 状态栏 - 固定高度 */
.status-bar {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: var(--theme-bg-secondary, #f5f5f5);
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: bold;
  color: var(--theme-text-primary, #333);
}
.stat {
  display: flex;
  align-items: center;
  gap: 4px;
}
.stat-icon { font-size: 16px; }
.diff-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  color: white;
}
.diff-badge.easy { background: #4caf50; }
.diff-badge.medium { background: #2196f3; }
.diff-badge.hard { background: #ff9800; }
.diff-badge.expert { background: #e91e63; }

.abandon-btn-inline {
  padding: 4px 8px;
  border: 1px solid var(--theme-border, #ddd);
  border-radius: 6px;
  background: var(--theme-bg-card, #fff);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.abandon-btn-inline:hover {
  background: var(--theme-error-bg, #ffebee);
  border-color: var(--theme-error-light, #ef9a9a);
}

/* 雷区滚动容器 */
.board-scroll-container {
  flex: 1;
  min-height: 0;
  overflow: auto;
  overflow: scroll;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  touch-action: pan-x pan-y;
  border-radius: 8px;
  background: var(--theme-bg-secondary, #fafafa);
  margin-bottom: 8px;
}

/* 网格 */
.board-wrapper {
  display: flex;
  justify-content: center;
  padding: 4px;
  min-width: fit-content;
}
.board {
  display: grid;
  gap: 2px;
  width: max-content;
  min-width: 100%;
}
.cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  font-size: clamp(10px, 2.5vw, 16px);
  font-weight: bold;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  transition: background 0.15s, transform 0.1s, box-shadow 0.15s;
  min-width: 24px;
  min-height: 24px;
  position: relative;
}

/* 未翻开格子 */
.cell.hidden {
  background: linear-gradient(135deg, #90a4ae, #78909c);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.15);
}
.cell.hidden:active {
  transform: scale(0.92);
  filter: brightness(0.9);
}

/* 标旗格子 - 与 hidden 有微妙区分 */
.cell.flagged {
  background: linear-gradient(135deg, #7e97a0, #6b8290);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), inset 0 -1px 0 rgba(0,0,0,0.2);
}

/* 问号格子 */
.cell.questioned {
  background: linear-gradient(135deg, #ffb74d, #ffa726);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.15);
}

/* 已翻开格子 */
.cell.revealed {
  background: var(--theme-bg-card, #e8e8e8);
}

/* 地雷格子 */
.cell.mine {
  background: #ef5350;
  animation: mine-reveal 0.3s ease;
}
@keyframes mine-reveal {
  0% { transform: scale(1); }
  50% { transform: scale(1.15); }
  100% { transform: scale(1); }
}

/* 和弦悬停 - 中心格子 */
.cell.chord-hover {
  background: #c5e1a5 !important;
  box-shadow: 0 0 8px rgba(76, 175, 80, 0.5);
}

/* ===== 和弦动画 - 周围格子脉冲闪烁 ===== */
.cell.chord-anim {
  animation: chord-pulse 0.5s ease-out;
  z-index: 2;
}

.cell.chord-anim.revealed {
  animation: chord-pulse-revealed 0.5s ease-out;
}

@keyframes chord-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
    transform: scale(1);
  }
  30% {
    box-shadow: 0 0 12px 4px rgba(76, 175, 80, 0.5);
    transform: scale(1.08);
    background: #a5d6a7;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
    transform: scale(1);
  }
}

@keyframes chord-pulse-revealed {
  0% {
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
  }
  30% {
    box-shadow: 0 0 10px 3px rgba(76, 175, 80, 0.4);
    background: #dcedc8;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}

/* 数字颜色 */
.n1 { color: #1976d2; }
.n2 { color: #388e3c; }
.n3 { color: #d32f2f; }
.n4 { color: #1a237e; }
.n5 { color: #795548; }
.n6 { color: #00897b; }
.n7 { color: var(--theme-text-primary, #212121); }
.n8 { color: #9e9e9e; }

/* ===== 和弦提示 Toast（组件内部，新覆盖旧）===== */
.chord-toast {
  position: absolute;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  z-index: 50;
  white-space: nowrap;
  pointer-events: auto;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}
.chord-toast.error {
  background: rgba(244, 67, 54, 0.92);
  color: white;
}
.chord-toast.info {
  background: rgba(33, 150, 243, 0.92);
  color: white;
}

.chord-toast-enter-active {
  transition: all 0.25s ease-out;
}
.chord-toast-leave-active {
  transition: all 0.2s ease-in;
}
.chord-toast-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}
.chord-toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

/* 操作提示栏 - 固定底部 */
.hints-bar {
  flex-shrink: 0;
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 8px;
  background: var(--theme-bg-secondary, #f5f5f5);
  border-radius: 8px;
  margin-bottom: 8px;
}
.hint-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--theme-text-secondary, #666);
}
.hint-icon {
  font-size: 16px;
}
.hint-text {
  font-weight: 500;
}

/* 结果 - 固定底部 */
.game-result {
  flex-shrink: 0;
  text-align: center;
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
  color: var(--theme-text-primary, #333);
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
  background: var(--theme-card-hover, #e0e0e0);
}
.confirm-btn.confirm {
  background: #ef5350;
  color: white;
}
.confirm-btn.confirm:hover {
  background: #e53935;
}
</style>