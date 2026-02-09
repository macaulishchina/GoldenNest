<template>
  <div class="report-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>📊 年度财务报告</h1>
      <p>回顾家庭财务状况，规划美好未来</p>
    </div>

    <!-- 年份选择 -->
    <div class="year-selector">
      <button 
        v-for="y in availableYears" 
        :key="y"
        :class="['year-btn', { active: year === y }]"
        @click="year = y; loadReport()"
      >
        {{ y }}
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span>
      <p>正在生成报告...</p>
    </div>

    <!-- 报告内容 -->
    <template v-else-if="report">
      <!-- 总览卡片 -->
      <div class="overview-section">
        <h2>📈 年度总览</h2>
        <div class="overview-cards">
          <div class="overview-card income">
            <span class="card-icon">💰</span>
            <div class="card-info">
              <span class="card-label">年度总收入</span>
              <span class="card-value">¥{{ formatMoney(report.summary.total_income) }}</span>
            </div>
          </div>
          <div class="overview-card expense">
            <span class="card-icon">💸</span>
            <div class="card-info">
              <span class="card-label">年度总支出</span>
              <span class="card-value">¥{{ formatMoney(report.summary.total_expense) }}</span>
            </div>
          </div>
          <div class="overview-card net" :class="{ negative: report.summary.net_change < 0 }">
            <span class="card-icon">📊</span>
            <div class="card-info">
              <span class="card-label">净收益</span>
              <span class="card-value">¥{{ formatMoney(report.summary.net_change) }}</span>
            </div>
          </div>
          <div class="overview-card balance">
            <span class="card-icon">🏦</span>
            <div class="card-info">
              <span class="card-label">年末总资产</span>
              <span class="card-value">¥{{ formatMoney(report.summary.end_balance) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 月度趋势 -->
      <div class="trend-section">
        <h2>📅 月度收支趋势</h2>
        <div class="chart-container">
          <div class="bar-chart">
            <div 
              v-for="(month, idx) in report.monthly_data" 
              :key="idx"
              class="chart-bar-group"
            >
              <div class="bars">
                <div 
                  class="bar income" 
                  :style="{ height: getBarHeight(month.income) + 'px' }"
                  :title="'收入: ¥' + formatMoney(month.income)"
                ></div>
                <div 
                  class="bar expense" 
                  :style="{ height: getBarHeight(month.expense) + 'px' }"
                  :title="'支出: ¥' + formatMoney(month.expense)"
                ></div>
              </div>
              <span class="bar-label">{{ month.month }}月</span>
            </div>
          </div>
          <div class="chart-legend">
            <span class="legend-item income"><span class="dot"></span> 收入</span>
            <span class="legend-item expense"><span class="dot"></span> 支出</span>
          </div>
        </div>
      </div>

      <!-- 股权变化 -->
      <div class="equity-section">
        <h2>👥 股权变化</h2>
        <div class="equity-comparison">
          <div class="equity-col">
            <h4>年初分布</h4>
            <div class="equity-list">
              <div 
                v-for="eq in report.equity_start" 
                :key="eq.member_id"
                class="equity-item"
              >
                <span class="member-name">{{ eq.name }}</span>
                <div class="equity-bar-wrapper">
                  <div class="equity-bar" :style="{ width: eq.percentage + '%' }"></div>
                </div>
                <span class="equity-pct">{{ eq.percentage.toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          <div class="equity-arrow">→</div>
          <div class="equity-col">
            <h4>年末分布</h4>
            <div class="equity-list">
              <div 
                v-for="eq in report.equity_end" 
                :key="eq.member_id"
                class="equity-item"
              >
                <span class="member-name">{{ eq.name }}</span>
                <div class="equity-bar-wrapper">
                  <div class="equity-bar" :style="{ width: eq.percentage + '%' }"></div>
                </div>
                <span class="equity-pct">{{ eq.percentage.toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 财务亮点 -->
      <div class="highlights-section">
        <h2>✨ 财务亮点</h2>
        <div class="highlights-grid">
          <div class="highlight-card" v-if="report.highlights.biggest_deposit">
            <span class="highlight-icon">💎</span>
            <div class="highlight-info">
              <span class="highlight-label">最大单笔存款</span>
              <span class="highlight-value">¥{{ formatMoney(report.highlights.biggest_deposit.amount) }}</span>
              <span class="highlight-detail">{{ report.highlights.biggest_deposit.member }} · {{ formatDate(report.highlights.biggest_deposit.date) }}</span>
            </div>
          </div>
          <div class="highlight-card" v-if="report.highlights.most_deposits_member">
            <span class="highlight-icon">🏆</span>
            <div class="highlight-info">
              <span class="highlight-label">最佳存款人</span>
              <span class="highlight-value">{{ report.highlights.most_deposits_member.name }}</span>
              <span class="highlight-detail">共存入 ¥{{ formatMoney(report.highlights.most_deposits_member.total) }}</span>
            </div>
          </div>
          <div class="highlight-card" v-if="report.highlights.best_month">
            <span class="highlight-icon">📈</span>
            <div class="highlight-info">
              <span class="highlight-label">最佳月份</span>
              <span class="highlight-value">{{ report.highlights.best_month.month }}月</span>
              <span class="highlight-detail">净收入 ¥{{ formatMoney(report.highlights.best_month.net) }}</span>
            </div>
          </div>
          <div class="highlight-card" v-if="report.highlights.investment_return">
            <span class="highlight-icon">📊</span>
            <div class="highlight-info">
              <span class="highlight-label">投资收益</span>
              <span class="highlight-value">¥{{ formatMoney(report.highlights.investment_return) }}</span>
              <span class="highlight-detail">全年投资回报</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 建议分红 -->
      <div class="dividend-section" v-if="report.dividend_suggestion?.has_dividend">
        <h2>💰 建议分红</h2>
        <div class="dividend-card">
          <div class="dividend-header">
            <div class="dividend-total">
              <span class="dividend-label">可分配投资收益</span>
              <span class="dividend-amount">¥{{ formatMoney(report.dividend_suggestion.total_investment_income) }}</span>
            </div>
            <div class="dividend-note">按年末持股比例分配</div>
          </div>
          <div class="dividend-list">
            <div 
              class="dividend-item" 
              v-for="item in report.dividend_suggestion.distribution" 
              :key="item.member_id"
            >
              <div class="member-info">
                <UserAvatar :userId="item.member_id" :name="item.name" :size="32" :avatarVersion="item.avatar_version" />
                <span class="member-name">{{ item.name }}</span>
                <span class="member-equity">持股 {{ item.equity_percentage.toFixed(1) }}%</span>
              </div>
              <div class="member-dividend">
                <span class="dividend-value">¥{{ formatMoney(item.dividend_amount) }}</span>
              </div>
            </div>
          </div>
          <div class="dividend-footer">
            <span class="dividend-tip">💡 此为建议分红方案，仅供参考</span>
          </div>
        </div>
      </div>

      <!-- 年度总结 -->
      <div class="summary-section">
        <h2>📝 年度总结</h2>
        <div class="summary-content">
          <p v-if="report.summary.net_change >= 0">
            🎉 恭喜！{{ year }}年家庭财务状况良好，全年净收益 
            <strong>¥{{ formatMoney(report.summary.net_change) }}</strong>，
            家庭资产增长 <strong>{{ getGrowthRate() }}%</strong>。
            继续保持良好的理财习惯！
          </p>
          <p v-else>
            💪 {{ year }}年家庭支出超过收入，净亏损 
            <strong>¥{{ formatMoney(Math.abs(report.summary.net_change)) }}</strong>。
            建议审视支出结构，制定更合理的预算计划。
          </p>
        </div>
      </div>

      <!-- 下载/分享按钮 -->
      <div class="action-bar">
        <button class="btn-share" @click="shareReport">
          📤 分享报告
        </button>
      </div>
    </template>

    <!-- 无数据状态 -->
    <div v-else class="empty-state">
      <div class="empty-icon">📊</div>
      <p>{{ year }}年暂无财务数据</p>
      <button class="btn-primary" @click="year--; loadReport()">查看上一年</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { api } from '@/api'
import { usePrivacyStore } from '@/stores/privacy'
import UserAvatar from '@/components/UserAvatar.vue'

const message = useMessage()
const privacyStore = usePrivacyStore()

// 状态
const loading = ref(false)
const year = ref(new Date().getFullYear())
const report = ref(null)

// 可选年份（最近5年）
const availableYears = computed(() => {
  const currentYear = new Date().getFullYear()
  return [currentYear, currentYear - 1, currentYear - 2, currentYear - 3, currentYear - 4]
})

// 加载报告
const loadReport = async () => {
  loading.value = true
  try {
    const res = await api.get(`/report/annual/${year.value}`)
    report.value = res.data
  } catch (err) {
    console.error('获取报告失败:', err)
    report.value = null
  } finally {
    loading.value = false
  }
}

// 计算图表高度
const getBarHeight = (value) => {
  if (!report.value?.monthly_data) return 0
  const maxValue = Math.max(
    ...report.value.monthly_data.map(m => Math.max(m.income, m.expense))
  )
  if (maxValue === 0) return 0
  return Math.max(5, (value / maxValue) * 120)
}

// 计算增长率
const getGrowthRate = () => {
  if (!report.value) return 0
  const start = report.value.summary.start_balance || 1
  const change = report.value.summary.net_change
  return ((change / start) * 100).toFixed(1)
}

// 格式化金额（支持隐私模式）
const formatMoney = (value) => {
  if (privacyStore.privacyMode) return '****'
  if (value === undefined || value === null) return '0.00'
  return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

// 分享报告
const shareReport = () => {
  // 简单实现：复制摘要到剪贴板
  if (!report.value) return
  
  const text = `【${year.value}年度财务报告】
📈 总收入: ¥${formatMoney(report.value.summary.total_income)}
💸 总支出: ¥${formatMoney(report.value.summary.total_expense)}
📊 净收益: ¥${formatMoney(report.value.summary.net_change)}
🏦 年末资产: ¥${formatMoney(report.value.summary.end_balance)}
—— 小金库年度报告`

  navigator.clipboard.writeText(text).then(() => {
    message.success('报告摘要已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败，请手动复制')
  })
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.report-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin-bottom: 8px;
}

.page-header p {
  color: var(--theme-text-secondary);
}

/* 年份选择 */
.year-selector {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.year-btn {
  padding: 10px 24px;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 24px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  flex-shrink: 0;
}

.year-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

/* 移动端年份选择器 - 横向滚动 */
@media (max-width: 767px) {
  .year-selector {
    justify-content: flex-start;
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding: 4px 16px;
    margin-left: -16px;
    margin-right: -16px;
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE/Edge */
  }
  
  .year-selector::-webkit-scrollbar {
    display: none; /* Chrome/Safari */
  }
  
  .year-btn {
    padding: 10px 20px;
    font-size: 15px;
  }
}

/* 加载状态 */
.loading {
  text-align: center;
  padding: 60px;
  color: var(--theme-text-secondary);
}

.spinner {
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 总览卡片 */
.overview-section {
  margin-bottom: 32px;
}

.overview-section h2 {
  font-size: 20px;
  margin-bottom: 16px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.overview-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.overview-card.income {
  border-left: 4px solid #4caf50;
}

.overview-card.expense {
  border-left: 4px solid #f44336;
}

.overview-card.net {
  border-left: 4px solid #2196f3;
}

.overview-card.net.negative {
  border-left-color: #ff9800;
}

.overview-card.balance {
  border-left: 4px solid #9c27b0;
}

.card-icon {
  font-size: 32px;
}

.card-info {
  display: flex;
  flex-direction: column;
}

.card-label {
  font-size: 14px;
  color: #888;
}

.card-value {
  font-size: 22px;
  font-weight: bold;
  color: #333;
}

/* 月度趋势 */
.trend-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 32px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.trend-section h2 {
  font-size: 20px;
  margin: 0 0 20px 0;
}

.chart-container {
  overflow-x: auto;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  min-height: 160px;
  padding: 20px 0;
  border-bottom: 1px solid #e0e0e0;
}

.chart-bar-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  min-width: 50px;
}

.bars {
  display: flex;
  gap: 4px;
  align-items: flex-end;
  height: 120px;
}

.bar {
  width: 20px;
  border-radius: 4px 4px 0 0;
  transition: height 0.3s;
  cursor: pointer;
}

.bar.income {
  background: linear-gradient(180deg, #66bb6a, #4caf50);
}

.bar.expense {
  background: linear-gradient(180deg, #ef5350, #f44336);
}

.bar:hover {
  opacity: 0.8;
}

.bar-label {
  margin-top: 8px;
  font-size: 12px;
  color: #888;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.legend-item .dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-item.income .dot {
  background: #4caf50;
}

.legend-item.expense .dot {
  background: #f44336;
}

/* 股权变化 */
.equity-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 32px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.equity-section h2 {
  font-size: 20px;
  margin: 0 0 20px 0;
}

.equity-comparison {
  display: flex;
  align-items: center;
  gap: 20px;
}

.equity-col {
  flex: 1;
}

.equity-col h4 {
  margin: 0 0 12px 0;
  color: #666;
  font-size: 14px;
}

.equity-arrow {
  font-size: 24px;
  color: #ccc;
}

.equity-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.equity-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.member-name {
  width: 60px;
  font-size: 14px;
  color: #333;
}

.equity-bar-wrapper {
  flex: 1;
  height: 12px;
  background: #f0f0f0;
  border-radius: 6px;
  overflow: hidden;
}

.equity-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 6px;
  transition: width 0.5s;
}

.equity-pct {
  width: 50px;
  text-align: right;
  font-size: 14px;
  color: #666;
}

/* 财务亮点 */
.highlights-section {
  margin-bottom: 32px;
}

.highlights-section h2 {
  font-size: 20px;
  margin-bottom: 16px;
}

.highlights-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.highlight-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  gap: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.highlight-icon {
  font-size: 36px;
}

.highlight-info {
  display: flex;
  flex-direction: column;
}

.highlight-label {
  font-size: 13px;
  color: #888;
}

.highlight-value {
  font-size: 18px;
  font-weight: bold;
  color: #333;
  margin: 4px 0;
}

.highlight-detail {
  font-size: 12px;
  color: #999;
}

/* 建议分红 */
.dividend-section {
  margin-bottom: 32px;
}

.dividend-section h2 {
  font-size: 20px;
  margin-bottom: 16px;
}

.dividend-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.dividend-header {
  background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
  padding: 20px 24px;
  color: var(--theme-text-primary);
}

.dividend-total {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.dividend-label {
  font-size: 14px;
  color: #555;
}

.dividend-amount {
  font-size: 28px;
  font-weight: bold;
  color: var(--theme-text-primary);
}

.dividend-note {
  font-size: 13px;
  color: #666;
}

.dividend-list {
  padding: 16px 24px;
}

.dividend-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.dividend-item:last-child {
  border-bottom: none;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.member-avatar {
  font-size: 24px;
}

.dividend-section .member-name {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  width: auto;
}

.member-equity {
  font-size: 13px;
  color: #888;
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 12px;
}

.member-dividend {
  text-align: right;
}

.dividend-value {
  font-size: 20px;
  font-weight: bold;
  color: #f5a623;
}

.dividend-footer {
  background: #fafafa;
  padding: 12px 24px;
  text-align: center;
}

.dividend-tip {
  font-size: 13px;
  color: #999;
}

/* 年度总结 */
.summary-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 32px;
  color: white;
}

.summary-section h2 {
  font-size: 20px;
  margin: 0 0 16px 0;
}

.summary-content p {
  font-size: 16px;
  line-height: 1.8;
  margin: 0;
}

.summary-content strong {
  font-size: 18px;
}

/* 操作按钮 */
.action-bar {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.btn-share {
  padding: 14px 32px;
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
  border-radius: 24px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-share:hover {
  background: #667eea;
  color: white;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.btn-primary {
  margin-top: 16px;
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 24px;
  font-size: 16px;
  cursor: pointer;
}

/* 响应式 */
@media (max-width: 600px) {
  .overview-cards {
    grid-template-columns: 1fr;
  }
  
  .highlights-grid {
    grid-template-columns: 1fr;
  }
  
  .equity-comparison {
    flex-direction: column;
  }
  
  .equity-arrow {
    transform: rotate(90deg);
  }
}
</style>
