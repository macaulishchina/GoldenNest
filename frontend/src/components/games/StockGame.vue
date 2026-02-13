<template>
  <div class="stock-game">
    <div class="game-header">
      <div class="stat">回合: <strong>{{ state.current_round }}/{{ state.total_rounds }}</strong></div>
      <div class="stat">资金: <strong>¥{{ formatNum(state.cash) }}</strong></div>
      <div class="stat">
        <strong :class="positionClass">{{ positionLabel }}</strong>
      </div>
    </div>

    <!-- 价格走势图 -->
    <div class="chart-area">
      <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="chart-svg">
        <!-- 网格线 -->
        <line v-for="i in 4" :key="'g'+i"
          :x1="0" :y1="chartHeight * i / 5" :x2="chartWidth" :y2="chartHeight * i / 5"
          stroke="#eee" stroke-width="0.5" />
        <!-- 价格折线 -->
        <polyline v-if="chartPoints.length > 1"
          :points="chartPoints.map(p => `${p.x},${p.y}`).join(' ')"
          fill="none"
          :stroke="priceColor"
          stroke-width="2"
          stroke-linejoin="round"
        />
        <!-- 价格点 -->
        <circle v-for="(p, i) in chartPoints" :key="i"
          :cx="p.x" :cy="p.y" r="3"
          :fill="i === chartPoints.length - 1 ? priceColor : '#999'"
        />
      </svg>
      <div class="current-price">
        当前价格: <strong :style="{ color: priceColor }">¥{{ currentPrice.toFixed(2) }}</strong>
        <span v-if="priceChange !== 0" :class="priceChange > 0 ? 'up' : 'down'">
          {{ priceChange > 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}%
        </span>
      </div>
    </div>

    <!-- 总资产 -->
    <div class="portfolio">
      总资产: <strong>¥{{ formatNum(state.portfolio_value) }}</strong>
      <span :class="profitPct >= 0 ? 'up' : 'down'">
        ({{ profitPct >= 0 ? '+' : '' }}{{ profitPct.toFixed(1) }}%)
      </span>
    </div>

    <!-- 持仓信息条 (做空模式) -->
    <div v-if="state.allow_short && !state.completed" class="position-bar">
      <div class="pos-indicator" :class="positionClass">
        <span class="pos-icon">{{ state.shares > 0 ? '📈' : state.shares < 0 ? '📉' : '⏸️' }}</span>
        <span>{{ positionLabel }}</span>
      </div>
      <div class="pos-details">
        <span v-if="state.shares > 0">持仓市值 ¥{{ formatNum(state.shares * currentPrice) }}</span>
        <span v-else-if="state.shares < 0">做空市值 ¥{{ formatNum(Math.abs(state.shares) * currentPrice) }}</span>
        <span v-else>空仓观望中</span>
      </div>
    </div>

    <!-- 操作区 -->
    <div v-if="!state.completed" class="action-area">
      <!-- 数量输入 -->
      <div class="quantity-row">
        <label>数量:</label>
        <input v-model.number="quantity" type="number" min="1" class="qty-input" />
        <div class="quick-btns">
          <button class="qty-btn" @click="quantity = maxBuy" title="用全部资金买入">全买</button>
          <button class="qty-btn" @click="quantity = Math.floor(maxBuy / 2)">半仓</button>
          <button v-if="state.shares !== 0" class="qty-btn clear-btn" @click="quantity = Math.abs(state.shares)" title="平掉当前所有持仓">平仓</button>
        </div>
      </div>

      <!-- 做空模式操作按钮 -->
      <template v-if="state.allow_short">
        <div class="btn-row short-mode">
          <button class="action-btn buy-long"
            @click="doAction('buy')"
            :disabled="quantity <= 0 || quantity * currentPrice > state.cash">
            <span class="btn-icon">📈</span>
            <span class="btn-label">{{ state.shares < 0 ? '买入平空' : '买入做多' }}</span>
          </button>
          <button class="action-btn hold" @click="doAction('hold')">
            <span class="btn-icon">⏳</span>
            <span class="btn-label">观望</span>
          </button>
          <button class="action-btn sell-short"
            @click="doAction('sell')"
            :disabled="quantity <= 0 || (state.shares - quantity < -maxShort)">
            <span class="btn-icon">📉</span>
            <span class="btn-label">{{ state.shares > 0 ? '卖出平多' : '卖出做空' }}</span>
          </button>
        </div>
        <div class="short-info-bar">
          <span>可做多: {{ maxBuy }} 股</span>
          <span>可做空: {{ maxShortable }} 股</span>
        </div>
      </template>

      <!-- 普通模式操作按钮 -->
      <template v-else>
        <div class="btn-row">
          <button class="action-btn buy" @click="doAction('buy')" :disabled="quantity <= 0 || quantity * currentPrice > state.cash">
            买入
          </button>
          <button class="action-btn hold" @click="doAction('hold')">
            持有
          </button>
          <button class="action-btn sell" @click="doAction('sell')" :disabled="quantity <= 0 || state.shares <= 0 || quantity > state.shares">
            卖出
          </button>
        </div>
      </template>
    </div>

    <!-- 结果 -->
    <div v-if="state.completed" class="game-result" :class="resultClass">
      <div class="result-title">{{ resultTitle }}</div>
      <div class="result-detail">
        最终资产: ¥{{ formatNum(state.final_value) }} ({{ state.profit_pct >= 0 ? '+' : '' }}{{ state.profit_pct }}%)
      </div>
      <div v-if="state.exp_earned > 0" class="result-exp">获得 {{ state.exp_earned }} EXP</div>
      <div v-else class="result-exp lost">未获得经验</div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { stockSound } from '../../utils/gameSound'

const props = defineProps<{ state: any }>()
const emit = defineEmits<{ (e: 'action', action: any): void }>()

const quantity = ref(10)
const chartWidth = 280
const chartHeight = 120
const showAbandonConfirm = ref(false)

const currentPrice = computed(() => {
  const prices = props.state.prices || [100]
  return prices[prices.length - 1]
})

const priceChange = computed(() => {
  const prices = props.state.prices || [100]
  if (prices.length < 2) return 0
  return ((prices[prices.length - 1] - prices[prices.length - 2]) / prices[prices.length - 2]) * 100
})

const priceColor = computed(() => priceChange.value >= 0 ? '#e53935' : '#43a047')

const initialCash = computed(() => props.state.initial_cash || 10000)
const profitPct = computed(() => ((props.state.portfolio_value - initialCash.value) / initialCash.value) * 100)

const maxBuy = computed(() => {
  return Math.floor(props.state.cash / currentPrice.value)
})

const maxShort = computed(() => {
  // 做空保证金限制：可做空的最大股数 = cash / price
  return Math.floor(props.state.cash / currentPrice.value)
})

const maxShortable = computed(() => {
  // 当前还能做空多少股（考虑已有持仓）
  // shares > 0: 先卖平多再做空，可做空 = shares + maxShort
  // shares < 0: 已有空仓，还能做空 = maxShort - |shares|
  // shares = 0: 可做空 = maxShort
  return Math.max(0, props.state.shares + maxShort.value)
})

// 持仓状态
const positionLabel = computed(() => {
  const shares = props.state.shares
  if (shares > 0) return `持有 ${shares} 股`
  if (shares < 0) return `做空 ${Math.abs(shares)} 股`
  return '空仓'
})

const positionClass = computed(() => {
  if (props.state.shares > 0) return 'pos-long'
  if (props.state.shares < 0) return 'pos-short'
  return 'pos-flat'
})

const chartPoints = computed(() => {
  const prices: number[] = props.state.prices || [100]
  if (prices.length === 0) return []
  const min = Math.min(...prices) * 0.95
  const max = Math.max(...prices) * 1.05
  const range = max - min || 1
  const stepX = chartWidth / Math.max(prices.length - 1, 1)
  return prices.map((p: number, i: number) => ({
    x: i * stepX,
    y: chartHeight - ((p - min) / range) * chartHeight,
  }))
})

// 结果展示
const resultClass = computed(() => {
  if (props.state?.abandoned) return 'lose'
  return props.state?.profit_pct >= 0 ? 'win' : 'lose'
})

const resultTitle = computed(() => {
  if (props.state?.abandoned) return '🏳️ 已放弃'
  const pct = props.state?.profit_pct || 0
  if (pct >= 50) return '🎉 股神！'
  if (pct >= 10) return '👍 不错的收益！'
  if (pct >= 0) return '✅ 保本了！'
  return '📉 亏损了...'
})

function formatNum(n: number) {
  return n?.toFixed(2) ?? '0.00'
}

function doAction(act: string) {
  if (act === 'buy') stockSound.buy()
  else if (act === 'sell') stockSound.sell()
  else stockSound.hold()
  emit('action', { action: act, quantity: act === 'hold' ? 0 : quantity.value })
}

function doAbandon() {
  showAbandonConfirm.value = false
  emit('action', { action: 'abandon' })
}
</script>

<style scoped>
.stock-game {
  padding: 8px;
  position: relative;
}
.game-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--theme-text-secondary, #666);
  margin-bottom: 8px;
}
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
.chart-area {
  background: var(--theme-bg-secondary, #fafafa);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}
.chart-svg {
  width: 100%;
  height: 120px;
}
.current-price {
  text-align: center;
  margin-top: 8px;
  font-size: 14px;
}
.up { color: #e53935; }
.down { color: #43a047; }
.portfolio {
  text-align: center;
  padding: 8px;
  background: var(--theme-bg-secondary, #f5f5f5);
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 14px;
}
.action-area {
  padding: 8px 0;
}
.quantity-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.quantity-row label {
  font-size: 13px;
  color: var(--theme-text-secondary, #666);
}
.qty-input {
  flex: 1;
  border: 1px solid var(--theme-border, #ddd);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 14px;
  max-width: 80px;
  background: var(--theme-bg-card, #fff);
  color: var(--theme-text-primary);
}
.qty-btn {
  padding: 4px 8px;
  font-size: 12px;
  border: 1px solid var(--theme-border, #ccc);
  border-radius: 4px;
  background: var(--theme-bg-card, #fff);
  color: var(--theme-text-primary);
  cursor: pointer;
}
.qty-btn:hover { background: var(--theme-bg-secondary, #f0f0f0); }
.qty-btn.clear-btn {
  border-color: var(--theme-warning, #ff9800);
  color: var(--theme-warning, #ff9800);
}
.qty-btn.clear-btn:hover {
  background: #fff3e0;
}
.quick-btns {
  display: flex;
  gap: 4px;
}
.btn-row {
  display: flex;
  gap: 8px;
}
.action-btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: bold;
  cursor: pointer;
  color: white;
}
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.action-btn.buy { background: #e53935; }
.action-btn.hold { background: #757575; }
.action-btn.sell { background: #43a047; }

/* 做空模式按钮 */
.btn-row.short-mode {
  gap: 6px;
}
.btn-row.short-mode .action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 6px;
}
.btn-icon { font-size: 16px; line-height: 1; }
.btn-label { font-size: 12px; line-height: 1; }
.action-btn.buy-long { background: #e53935; }
.action-btn.sell-short { background: #43a047; }

/* 持仓信息条 */
.position-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 6px;
  font-size: 13px;
  background: var(--theme-bg-secondary, #f5f5f5);
  border-left: 3px solid #999;
}
.position-bar:has(.pos-long) { border-left-color: #e53935; }
.position-bar:has(.pos-short) { border-left-color: #43a047; }
.pos-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: bold;
}
.pos-icon { font-size: 14px; }
.pos-long { color: #e53935; }
.pos-short { color: #43a047; }
.pos-flat { color: #999; }
.pos-details {
  font-size: 12px;
  color: var(--theme-text-secondary, #666);
}

/* 做空信息栏 */
.short-info-bar {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--theme-text-tertiary, #999);
  padding: 4px 2px 0;
}

.short-position { color: #e53935; }

/* 结果 */
.game-result {
  text-align: center;
  padding: 12px;
  border-radius: 8px;
  margin-top: 8px;
}
.game-result.win {
  background: var(--theme-info-bg, linear-gradient(135deg, #e3f2fd, #bbdefb));
}
.game-result.lose {
  background: var(--theme-error-bg, linear-gradient(135deg, #ffebee, #ffcdd2));
}
.result-title {
  font-size: 18px;
  font-weight: bold;
}
.win .result-title { color: var(--theme-info, #1565c0); }
.lose .result-title { color: var(--theme-error, #c62828); }
.result-detail {
  font-size: 14px;
  margin-top: 4px;
}
.win .result-detail { color: var(--theme-info, #1976d2); }
.lose .result-detail { color: var(--theme-error-light, #e57373); }
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