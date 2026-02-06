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
              gridTemplateColumns: `repeat(${state.cols}, minmax(28px, 1fr))`,
            }"
          >
            <div
              v-for="(_, idx) in state.rows * state.cols"
              :key="idx"
              class="cell"
              :class="cellClass(Math.floor(idx / state.cols), idx % state.cols)"
              @click="cellClick(Math.floor(idx / state.cols), idx % state.cols)"
              @contextmenu.prevent="cellRightClick(Math.floor(idx / state.cols), idx % state.cols)"
            >
              <span v-if="cellContent(Math.floor(idx / state.cols), idx % state.cols)" :class="'n' + state.board[Math.floor(idx / state.cols)][idx % state.cols]">
                {{ cellContent(Math.floor(idx / state.cols), idx % state.cols) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作栏 - 固定底部 -->
      <div v-if="!state.completed" class="action-bar">
        <button
          class="mode-btn"
          :class="{ active: flagMode }"
          @click="flagMode = !flagMode"
        >
          {{ flagMode ? '🚩 标旗模式' : '👆 翻开模式' }}
        </button>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{ state: any }>()
const emit = defineEmits<{
  (e: 'action', action: any): void
}>()

const flagMode = ref(false)
const startTime = ref(Date.now())
const elapsedTime = ref(0)
const showAbandonConfirm = ref(false)
const boardScrollRef = ref<HTMLElement | null>(null)
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
  
  // 处理触摸滚动，阻止事件冒泡到父容器
  const el = boardScrollRef.value
  if (el) {
    el.addEventListener('touchmove', (e: TouchEvent) => {
      // 只有当内容需要滚动时才阻止冒泡
      const { scrollHeight, clientHeight, scrollWidth, clientWidth } = el
      if (scrollHeight > clientHeight || scrollWidth > clientWidth) {
        e.stopPropagation()
      }
    }, { passive: true })
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

function cellClass(r: number, c: number) {
  if (!props.state) return ''
  const revealed = props.state.revealed[r][c]
  const flagged = props.state.flagged[r][c]
  const val = props.state.board[r][c]
  const classes: string[] = []
  if (revealed) {
    classes.push('revealed')
    if (val === -1) classes.push('mine')
  } else {
    classes.push('hidden')
    if (flagged) classes.push('flagged')
  }
  return classes.join(' ')
}

function cellContent(r: number, c: number): string {
  if (!props.state) return ''
  const revealed = props.state.revealed[r][c]
  const flagged = props.state.flagged[r][c]
  const val = props.state.board[r][c]
  if (!revealed && flagged) return '🚩'
  if (!revealed) return ''
  if (val === -1) return '💣'
  if (val === 0) return ''
  return String(val)
}

function cellClick(r: number, c: number) {
  if (!props.state || props.state.completed) return
  const revealed = props.state.revealed[r][c]
  const flagged = props.state.flagged[r][c]

  if (flagMode.value) {
    if (!revealed) {
      emit('action', { action: 'flag', row: r, col: c })
    }
    return
  }

  if (revealed) {
    const val = props.state.board[r][c]
    if (val > 0) {
      emit('action', { action: 'chord', row: r, col: c })
    }
    return
  }

  if (flagged) return
  emit('action', { action: 'reveal', row: r, col: c })
}

function cellRightClick(r: number, c: number) {
  if (!props.state || props.state.completed) return
  if (!props.state.revealed[r][c]) {
    emit('action', { action: 'flag', row: r, col: c })
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
  background: #f5f5f5;
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: bold;
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
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.abandon-btn-inline:hover {
  background: #ffebee;
  border-color: #ef9a9a;
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
  background: #fafafa;
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
  transition: background 0.1s;
  min-width: 0;
}
.cell.hidden {
  background: linear-gradient(135deg, #90a4ae, #78909c);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.15);
}
.cell.hidden:hover {
  background: linear-gradient(135deg, #a0b4be, #8ca0ac);
}
.cell.flagged {
  background: linear-gradient(135deg, #90a4ae, #78909c);
}
.cell.revealed {
  background: #e8e8e8;
}
.cell.mine {
  background: #ef5350;
}

/* 数字颜色 */
.n1 { color: #1976d2; }
.n2 { color: #388e3c; }
.n3 { color: #d32f2f; }
.n4 { color: #1a237e; }
.n5 { color: #795548; }
.n6 { color: #00897b; }
.n7 { color: #212121; }
.n8 { color: #9e9e9e; }

/* 操作栏 - 固定底部 */
.action-bar {
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  padding: 8px 0;
}
.mode-btn {
  padding: 8px 20px;
  border: 2px solid #90a4ae;
  border-radius: 20px;
  background: white;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  color: #546e7a;
}
.mode-btn.active {
  background: #fff3e0;
  border-color: #ff9800;
  color: #e65100;
}

/* 结果 - 固定底部 */
.game-result {
  flex-shrink: 0;
  text-align: center;
  padding: 12px;
  border-radius: 8px;
}
.game-result.win {
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
}
.game-result.lose {
  background: linear-gradient(135deg, #ffebee, #ffcdd2);
}
.result-title {
  font-size: 18px;
  font-weight: bold;
}
.win .result-title { color: #2e7d32; }
.lose .result-title { color: #c62828; }
.result-exp {
  font-size: 14px;
  color: #388e3c;
  margin-top: 4px;
}
.result-exp.lost {
  color: #999;
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
  background: white;
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
  color: #666;
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
  background: #f5f5f5;
  color: #666;
}
.confirm-btn.cancel:hover {
  background: #e0e0e0;
}
.confirm-btn.confirm {
  background: #ef5350;
  color: white;
}
.confirm-btn.confirm:hover {
  background: #e53935;
}
</style>