<template>
  <div class="stock-game">
    <div class="game-header">
      <div class="stat">回合: <strong>{{ state.current_round }}/{{ state.total_rounds }}</strong></div>
      <div class="stat">资金: <strong>¥{{ formatNum(state.cash) }}</strong></div>
      <div class="stat">持股: <strong>{{ state.shares }}</strong></div>
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

    <!-- 操作区 -->
    <div v-if="!state.completed" class="action-area">
      <div class="quantity-row">
        <label>数量:</label>
        <input v-model.number="quantity" type="number" min="1" :max="maxBuy" class="qty-input" />
        <button class="qty-btn" @click="quantity = maxBuy">全仓</button>
        <button class="qty-btn" @click="quantity = Math.floor(maxBuy / 2)">半仓</button>
      </div>
      <div class="btn-row">
        <button class="action-btn buy" @click="doAction('buy')" :disabled="quantity <= 0 || quantity * currentPrice > state.cash">
          买入
        </button>
        <button class="action-btn hold" @click="doAction('hold')">
          持有
        </button>
        <button class="action-btn sell" @click="doAction('sell')" :disabled="state.shares <= 0 || quantity <= 0 || quantity > state.shares">
          卖出
        </button>
      </div>
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

const maxBuy = computed(() => Math.floor(props.state.cash / currentPrice.value))

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
  color: #666;
  margin-bottom: 8px;
}
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
.chart-area {
  background: #fafafa;
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
  background: #f5f5f5;
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
  color: #666;
}
.qty-input {
  flex: 1;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 14px;
  max-width: 80px;
}
.qty-btn {
  padding: 4px 8px;
  font-size: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.qty-btn:hover { background: #f0f0f0; }
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

/* 结果 */
.game-result {
  text-align: center;
  padding: 12px;
  border-radius: 8px;
  margin-top: 8px;
}
.game-result.win {
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
}
.game-result.lose {
  background: linear-gradient(135deg, #ffebee, #ffcdd2);
}
.result-title {
  font-size: 18px;
  font-weight: bold;
}
.win .result-title { color: #1565c0; }
.lose .result-title { color: #c62828; }
.result-detail {
  font-size: 14px;
  margin-top: 4px;
}
.win .result-detail { color: #1976d2; }
.lose .result-detail { color: #e57373; }
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