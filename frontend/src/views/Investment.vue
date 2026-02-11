<template>
  <div class="page-container">
    <div class="page-header-row">
      <h1 class="page-title"><span class="icon">📈</span> 理财配置</h1>
      <n-button
        type="primary"
        :loading="aiAnalyzing"
        @click="handleAIAnalysis"
        style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none"
      >
        🤖 AI 投资分析
      </n-button>
    </div>

    <!-- 家庭自由资金卡片 -->
    <n-card class="card-hover" style="margin-bottom: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
      <n-statistic label="家庭自由资金" :value="currentBalance">
        <template #prefix>¥</template>
      </n-statistic>
      <template #footer>
        <n-text style="color: rgba(255,255,255,0.8); font-size: 12px">
          💰 共享资金池 | <strong>外部资金</strong>=计入股权 | <strong>从自由资金扣除</strong>=不计股权
        </n-text>
      </template>
    </n-card>
    
    <n-card v-if="false" class="card-hover investment-form-card" style="margin-bottom: 24px">
      <template #header>
        <n-space align="center">
          <span>发起理财产品登记申请</span>
          <n-tag type="info" size="small">需全员通过</n-tag>
        </n-space>
      </template>
      <!-- 桌面端表单 -->
      <n-form inline :model="formData" class="desktop-only">
        <n-form-item label="产品名称">
          <n-input v-model:value="formData.name" placeholder="如：货币基金" style="width: 150px" />
        </n-form-item>
        <n-form-item label="理财类型">
          <n-select v-model:value="formData.investment_type" :options="typeOptions" style="width: 120px" />
        </n-form-item>
        <n-form-item label="币种">
          <n-select v-model:value="formData.currency" :options="currencyOptions" style="width: 130px" @update:value="handleCurrencyChange" />
        </n-form-item>
        <n-form-item :label="formData.currency === 'CNY' ? '投资本金' : '外币金额'">
          <n-input-number 
            :value="formData.currency === 'CNY' ? formData.principal : formData.foreign_amount" 
            :min="1" placeholder="金额" style="width: 140px"
            @update:value="handleAmountUpdate"
          >
            <template #prefix>{{ getCurrencySymbol(formData.currency) }}</template>
          </n-input-number>
        </n-form-item>
        <n-form-item v-if="formData.currency !== 'CNY' && currentExchangeRate" label="≈人民币">
          <n-text type="info">¥{{ equivalentCNY?.toLocaleString() }}</n-text>
        </n-form-item>
        <n-form-item label="资金来源">
          <n-radio-group v-model:value="formData.deduct_from_cash" size="small">
            <n-radio :value="false">外部资金</n-radio>
            <n-radio :value="true">从自由资金扣除</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item v-if="formData.deduct_from_cash" label="可用余额">
          <n-text type="warning">¥{{ formatMoney(currentBalance) }}</n-text>
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">
            <template #icon><n-icon><SendOutline /></n-icon></template>
            发起申请
          </n-button>
        </n-form-item>
      </n-form>
      <!-- 移动端紧凑表单 -->
      <div class="mobile-only mobile-investment-form">
        <!-- 第一行：产品名称 + 理财类型 -->
        <div class="form-row">
          <div class="form-col name-col">
            <label>产品名称</label>
            <n-input v-model:value="formData.name" placeholder="货币基金" size="small" />
          </div>
          <div class="form-col type-col">
            <label>类型</label>
            <n-select v-model:value="formData.investment_type" :options="typeOptions" size="small" />
          </div>
        </div>
        <!-- 第一点五行：币种 -->
        <div class="form-row" style="margin-top: 8px">
          <div class="form-col" style="flex: 1">
            <label>币种</label>
            <n-select v-model:value="formData.currency" :options="currencyOptions" size="small" @update:value="handleCurrencyChange" />
          </div>
        </div>
        <!-- 第二行：投资本金 + 提交按钮 -->
        <div class="form-row">
          <div class="form-col principal-col" style="flex: 1;">
            <label>{{ formData.currency === 'CNY' ? '本金' : '外币金额' }}</label>
            <n-input-number 
              :value="formData.currency === 'CNY' ? formData.principal : formData.foreign_amount" 
              :min="1" placeholder="0" size="small"
              @update:value="handleAmountUpdate"
            >
              <template #prefix>{{ getCurrencySymbol(formData.currency) }}</template>
            </n-input-number>
          </div>
          <div class="form-col btn-col">
            <label>&nbsp;</label>
            <n-button type="primary" :loading="submitting" @click="handleSubmit" size="small" class="submit-btn">
              申请
            </n-button>
          </div>
        </div>
        <!-- 汇率提示（外币时） -->
        <div v-if="formData.currency !== 'CNY'" class="form-row" style="margin-top: 4px">
          <div class="form-col" style="flex: 1">
            <n-text v-if="exchangeRateLoading" depth="3" style="font-size: 12px">获取汇率中...</n-text>
            <n-text v-else-if="currentExchangeRate" depth="3" style="font-size: 12px">
              1 {{ formData.currency }} = ¥{{ currentExchangeRate.toFixed(4) }}
              <span v-if="equivalentCNY"> | ≈¥{{ equivalentCNY.toLocaleString() }}</span>
            </n-text>
          </div>
        </div>
        <!-- 第三行：资金来源 -->
        <div class="form-row" style="margin-top: 8px">
          <div class="form-col" style="flex: 1">
            <label>资金来源</label>
            <n-radio-group v-model:value="formData.deduct_from_cash" size="small">
              <n-radio :value="false">外部资金</n-radio>
              <n-radio :value="true">从自由资金扣除</n-radio>
            </n-radio-group>
            <div v-if="formData.deduct_from_cash" style="margin-top: 4px; font-size: 12px; color: var(--theme-warning)">
              可用余额: ¥{{ formatMoney(currentBalance) }}
            </div>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 待审批的理财申请 -->
    <n-card title="待审批申请" class="card-hover" style="margin-bottom: 24px" v-if="pendingApprovals.length > 0">
      <!-- 桌面端：表格 -->
      <n-data-table class="desktop-only" :columns="approvalColumns" :data="pendingApprovals" :bordered="false" />
      <!-- 移动端：卡片列表 -->
      <div class="mobile-only approval-cards">
        <div v-for="item in pendingApprovals" :key="item.id" class="approval-card">
          <div class="approval-card-header">
            <n-tag size="small" type="info">{{ requestTypeLabels[item.request_type] || item.request_type }}</n-tag>
            <span class="approval-time">{{ formatShortDateTime(item.created_at) }}</span>
          </div>
          <div class="approval-card-body">
            <div class="approval-requester">{{ item.requester_nickname }} 发起</div>
            <div class="approval-detail">{{ item.title }}</div>
          </div>
          <div class="approval-card-footer">
            <span class="approval-progress">审批进度: {{ item.approved_count || 0 }}/{{ getRequiredCount(item) }}</span>
            <div class="approval-actions" v-if="item.requester_id !== userStore.user?.id && !item.has_voted">
              <n-button size="small" type="success" @click="handleApprove(item.id, true)">同意</n-button>
              <n-button size="small" type="error" @click="handleApprove(item.id, false)">拒绝</n-button>
            </div>
            <span v-else class="approval-wait">{{ item.has_voted ? '已投票' : '等待他人' }}</span>
          </div>
        </div>
      </div>
    </n-card>

    <n-card title="理财产品列表" class="card-hover">
      <!-- 桌面端：表格 -->
      <n-data-table class="desktop-only" :columns="columns" :data="investments" :loading="loading" :bordered="false" />
      <!-- 移动端：卡片列表 -->
      <div class="mobile-only">
        <n-spin :show="loading">
          <div class="investment-cards" v-if="investments.length > 0">
            <div v-for="item in investments" :key="item.id" class="investment-card" :class="{ 'deleted': item.is_deleted }">
              <div class="card-header">
                <span class="product-name">{{ item.name }}</span>
                <n-tag :type="item.is_deleted ? 'error' : (item.is_active ? 'success' : 'default')" size="small">
                  {{ item.is_deleted ? '已删除' : (item.is_active ? '持有中' : '已结束') }}
                </n-tag>
                <n-button v-if="!item.is_deleted" class="detail-btn" size="small" type="primary" secondary round @click="openHistoryModal(item)">详细</n-button>
              </div>
              <div class="card-type">
                <n-tag size="small" :bordered="false">{{ typeLabels[item.investment_type] || item.investment_type }}</n-tag>
                <n-tag v-if="item.currency && item.currency !== 'CNY'" size="small" :bordered="false" type="warning">{{ item.currency }}</n-tag>
              </div>
              <div class="card-stats">
                <div class="stat-item">
                  <span class="stat-label">初始本金</span>
                  <span class="stat-value">{{ formatInvAmountWithCNY(item, 'principal') }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">当前持仓</span>
                  <span class="stat-value">{{ formatInvAmountWithCNY(item, 'current_principal') }}</span>
                </div>
              </div>
              <div class="card-stats-row">
                <div class="stat-item">
                  <span class="stat-label">总收益</span>
                  <span class="stat-value" :class="(item.total_return || 0) >= 0 ? 'profit' : 'loss'">
                    {{ getCurrencySymbol(item.currency || 'CNY') }}{{ formatMoney(item.total_return || 0) }}
                  </span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">ROI</span>
                  <span class="stat-value" :class="(item.roi || 0) >= 0 ? 'profit' : 'loss'">
                    {{ (item.roi || 0).toFixed(2) }}%
                  </span>
                </div>
                <div class="stat-item" v-if="item.annualized_return != null">
                  <span class="stat-label">年化</span>
                  <span class="stat-value profit">
                    {{ item.annualized_return.toFixed(2) }}%
                  </span>
                </div>
              </div>
              <div class="card-footer" v-if="!item.is_deleted">
                <span class="start-date">{{ formatLocalDate(item.start_date) }} 起</span>
                <n-space size="small">
                  <n-button size="small" type="primary" text @click="openIncomeModal(item)">更新价值</n-button>
                  <n-button size="small" type="info" text @click="openIncreaseModal(item)">增持</n-button>
                  <n-button size="small" type="warning" text @click="openDecreaseModal(item)">减持</n-button>
                  <n-button size="small" type="error" text @click="handleDelete(item)">删除</n-button>
                </n-space>
              </div>
              <div class="card-footer" v-else>
                <span class="deleted-text">{{ item.deleted_at ? formatLocalDate(item.deleted_at) + ' 删除' : '已删除' }}</span>
              </div>
            </div>
          </div>
          <n-empty v-else description="暂无理财产品" />
        </n-spin>
      </div>
    </n-card>

    <!-- 登记收益弹窗（改为更新价值） -->
    <n-modal v-model:show="showIncomeModal" preset="dialog" title="更新投资价值" positive-text="提交申请" negative-text="取消" @positive-click="submitIncome">
      <n-form :model="incomeForm" label-placement="left" label-width="90px">
        <n-form-item label="理财产品">
          <n-text>{{ selectedInvestment?.name }}</n-text>
        </n-form-item>
        <n-form-item label="当前持仓">
          <n-text type="info">{{ formatInvAmountWithCNY(selectedInvestment || {}, 'current_principal') }}</n-text>
        </n-form-item>
        <n-form-item :label="selectedInvestment?.currency && selectedInvestment.currency !== 'CNY' ? '当前总价值('+selectedInvestment.currency+')' : '当前总价值'">
          <n-input-number v-model:value="incomeForm.current_value" style="width: 100%" :min="0">
            <template #prefix>{{ getCurrencySymbol(selectedInvestment?.currency || 'CNY') }}</template>
          </n-input-number>
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            输入投资产品的当前市场价值，系统将自动计算收益
          </n-text>
        </n-form-item>
        <n-form-item label="计算收益" v-if="incomeForm.current_value">
          <n-text :type="calculatedIncome >= 0 ? 'success' : 'error'" strong>
            {{ getCurrencySymbol(selectedInvestment?.currency || 'CNY') }}{{ formatMoney(calculatedIncome) }}
          </n-text>
        </n-form-item>
        <n-form-item label="更新日期">
          <n-date-picker v-model:value="incomeForm.income_date" type="date" style="width: 100%" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="incomeForm.note" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- 增持模态框 -->
    <n-modal v-model:show="showIncreaseModal" preset="dialog" title="投资增持" positive-text="提交申请" negative-text="取消" @positive-click="submitIncrease">
      <n-form :model="increaseForm" label-placement="left" label-width="90px">
        <n-form-item label="理财产品">
          <n-text>{{ selectedInvestment?.name }}<n-tag v-if="selectedInvestment?.currency && selectedInvestment.currency !== 'CNY'" size="small" :bordered="false" style="margin-left: 8px">{{ selectedInvestment.currency }}</n-tag></n-text>
        </n-form-item>
        <n-form-item label="当前持仓">
          <n-text type="info">{{ formatInvAmountWithCNY(selectedInvestment || {}, 'current_principal') }}</n-text>
        </n-form-item>
        <n-form-item label="资金来源">
          <n-radio-group v-model:value="increaseForm.deduct_from_cash" size="small">
            <n-radio :value="false">外部资金</n-radio>
            <n-radio :value="true">从自由资金扣除</n-radio>
          </n-radio-group>
          <template #feedback>
            <n-text depth="3" style="font-size: 12px">
              外部资金=计入股权 | 从自由资金扣除=不计股权
            </n-text>
          </template>
        </n-form-item>
        <n-form-item label="可用余额" v-if="increaseForm.deduct_from_cash">
          <n-text type="warning">¥{{ formatMoney(currentBalance) }}</n-text>
        </n-form-item>
        <n-form-item :label="selectedInvestment?.currency && selectedInvestment.currency !== 'CNY' ? '增持金额('+selectedInvestment.currency+')' : '增持金额'">
          <n-input-number v-model:value="increaseForm.amount" style="width: 100%" :min="1" :max="increaseForm.deduct_from_cash ? currentBalance : undefined">
            <template #prefix>{{ getCurrencySymbol(selectedInvestment?.currency || 'CNY') }}</template>
          </n-input-number>
        </n-form-item>
        <n-form-item label="增持日期">
          <n-date-picker v-model:value="increaseForm.operation_date" type="date" style="width: 100%" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="increaseForm.note" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- 减持模态框 -->
    <n-modal v-model:show="showDecreaseModal" preset="dialog" title="投资减持" positive-text="提交申请" negative-text="取消" @positive-click="submitDecrease">
      <n-form :model="decreaseForm" label-placement="left" label-width="90px">
        <n-form-item label="理财产品">
          <n-text>{{ selectedInvestment?.name }}<n-tag v-if="selectedInvestment?.currency && selectedInvestment.currency !== 'CNY'" size="small" :bordered="false" style="margin-left: 8px">{{ selectedInvestment.currency }}</n-tag></n-text>
        </n-form-item>
        <n-form-item label="当前持仓">
          <n-text type="info">{{ formatInvAmountWithCNY(selectedInvestment || {}, 'current_principal') }}</n-text>
        </n-form-item>
        <n-form-item :label="selectedInvestment?.currency && selectedInvestment.currency !== 'CNY' ? '减持金额('+selectedInvestment.currency+')' : '减持金额'">
          <n-input-number v-model:value="decreaseForm.amount" style="width: 100%" 
            :min="1" :max="selectedInvestment?.currency && selectedInvestment.currency !== 'CNY' ? (selectedInvestment?.current_foreign_amount || 0) : (selectedInvestment?.current_principal || 0)">
            <template #prefix>{{ getCurrencySymbol(selectedInvestment?.currency || 'CNY') }}</template>
          </n-input-number>
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            最多可减持 {{ formatInvAmount(selectedInvestment || {}, 'current_principal') }}
          </n-text>
        </n-form-item>
        <n-form-item label="减持日期">
          <n-date-picker v-model:value="decreaseForm.operation_date" type="date" style="width: 100%" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="decreaseForm.note" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- 历史详情模态框 -->
    <n-modal v-model:show="showHistoryModal" preset="card" title="操作历史" style="max-width: 600px; max-height: 80vh; overflow-y: auto">
      <n-spin :show="historyLoading">
        <div v-if="historyData.history && historyData.history.length > 0" class="history-list">
          <div v-for="(item, index) in historyData.history" :key="index" class="history-item">
            <div class="history-icon">
              <n-tag 
                v-if="item.type === 'position'" 
                :type="item.operation_type === 'CREATE' ? 'success' : (item.operation_type === 'INCREASE' ? 'info' : 'warning')"
                size="small"
              >
                {{ operationTypeLabels[item.operation_type] || item.operation_type }}
              </n-tag>
              <n-tag 
                v-else-if="item.type === 'transaction'" 
                :type="item.transaction_type === 'DEPOSIT' ? 'success' : 'error'"
                size="small"
              >
                {{ transactionTypeLabels[item.transaction_type] || item.transaction_type }}
              </n-tag>
              <n-tag 
                v-else-if="item.type === 'income'" 
                type="info"
                size="small"
              >
                收益记录
              </n-tag>
            </div>
            <div class="history-content">
              <div class="history-date">{{ formatHistoryTime(item.timestamp) }}</div>
              <div v-if="item.type === 'position'" class="history-details">
                <span class="label">金额:</span>
                <span class="value" v-if="item.foreign_amount && historyData.investment?.currency !== 'CNY'">
                  {{ getCurrencySymbol(historyData.investment?.currency || 'CNY') }}{{ formatMoney(item.foreign_amount) }}
                  <span style="color: var(--theme-text-tertiary); font-size: 12px">(≈¥{{ formatMoney(item.amount) }})</span>
                </span>
                <span class="value" v-else>¥{{ formatMoney(item.amount) }}</span>
                <span class="label" style="margin-left: 16px">本金变化:</span>
                <span class="value">¥{{ formatMoney(item.principal_before || 0) }} → ¥{{ formatMoney(item.principal_after || 0) }}</span>
                <div v-if="item.note" class="note">{{ item.note }}</div>
              </div>
              <div v-else-if="item.type === 'transaction'" class="history-details">
                <span class="label">金额:</span>
                <span :class="['value', item.transaction_type === 'DEPOSIT' ? 'profit' : 'loss']">
                  {{ item.transaction_type === 'DEPOSIT' ? '+' : '' }}¥{{ formatMoney(Math.abs(item.amount)) }}
                </span>
                <span class="label" style="margin-left: 16px">余额:</span>
                <span class="value">¥{{ formatMoney(item.balance_after) }}</span>
                <div v-if="item.description" class="note">{{ item.description }}</div>
              </div>
              <div v-else-if="item.type === 'income'" class="history-details">
                <span class="label">收益:</span>
                <span class="value profit">{{ getCurrencySymbol(historyData.investment?.currency || 'CNY') }}{{ formatMoney(item.amount) }}</span>
                <span v-if="item.current_value" class="label" style="margin-left: 16px">当前价值:</span>
                <span v-if="item.current_value" class="value">{{ getCurrencySymbol(historyData.investment?.currency || 'CNY') }}{{ formatMoney(item.current_value) }}</span>
                <div v-if="item.note" class="note">{{ item.note }}</div>
              </div>
            </div>
          </div>
        </div>
        <n-empty v-else description="暂无操作记录" />
      </n-spin>
    </n-modal>

    <!-- AI 投资分析模态框 -->
    <n-modal
      v-model:show="showAiModal"
      preset="card"
      title="AI 投资组合分析"
      style="width: 90%; max-width: 700px"
      :segmented="{ content: true }"
    >
      <n-spin :show="aiAnalyzing">
        <div v-if="aiAnalysisResult" class="ai-analysis-content">
          <!-- Risk Assessment -->
          <div class="analysis-section">
            <h3>📊 风险评估</h3>
            <n-progress
              type="line"
              :percentage="aiAnalysisResult.risk_score || 0"
              :color="getRiskColor(aiAnalysisResult.risk_score)"
              :show-indicator="true"
            />
            <p style="margin-top: 8px">{{ aiAnalysisResult.risk_level || '暂无数据' }}</p>
          </div>

          <!-- Diversification Score -->
          <div class="analysis-section">
            <h3>🎯 多元化评分</h3>
            <div style="display: flex; justify-content: center">
              <n-progress
                type="circle"
                :percentage="aiAnalysisResult.diversification_score || 0"
              />
            </div>
            <p class="score-desc">{{ aiAnalysisResult.diversification_desc || '暂无描述' }}</p>
          </div>

          <!-- Asset Allocation -->
          <div v-if="aiAnalysisResult.recommended_allocation && aiAnalysisResult.recommended_allocation.length > 0" class="analysis-section">
            <h3>💼 资产配置建议</h3>
            <n-space vertical>
              <n-tag
                v-for="(alloc, idx) in aiAnalysisResult.recommended_allocation"
                :key="idx"
                type="info"
              >
                {{ alloc.type }}: {{ alloc.percentage }}%
              </n-tag>
            </n-space>
          </div>

          <!-- Suggestions -->
          <div v-if="aiAnalysisResult.suggestions && aiAnalysisResult.suggestions.length > 0" class="analysis-section">
            <h3>💡 改进建议</h3>
            <n-list>
              <n-list-item v-for="(suggestion, idx) in aiAnalysisResult.suggestions" :key="idx">
                <n-thing>
                  <template #header>
                    <n-text>{{ suggestion }}</n-text>
                  </template>
                </n-thing>
              </n-list-item>
            </n-list>
          </div>
        </div>
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { useMessage, useDialog, NButton, NTag, NSpace, NInput, NRadio, NRadioGroup } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { investmentApi, approvalApi, transactionApi, assetApi, investmentAiApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useApprovalStore } from '@/stores/approval'
import { usePrivacyStore } from '@/stores/privacy'
import { SendOutline, CashOutline } from '@vicons/ionicons5'
import { formatShortDateTime, formatLocalDate } from '@/utils/date'
import { checkAndShowAchievements } from '@/utils/achievement'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)

const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()
const approvalStore = useApprovalStore()
const privacyStore = usePrivacyStore()
const { privacyMode } = storeToRefs(privacyStore)
const loading = ref(false)

// 隐私模式格式化金额
const formatMoney = (num: number) => privacyStore.formatMoney(num)

// 格式化时间（处理时区）
const formatHistoryTime = (timestamp: string) => {
  return dayjs.utc(timestamp).local().format('YYYY-MM-DD HH:mm:ss')
}

// 计算需要的审批人数
const getRequiredCount = (item: any): number => {
  // 单人家庭：需要1人（自己）
  if (item.total_members === 1) {
    return 1
  }
  // 多人家庭：需要所有人审批（除申请人）= total_members - 1
  return item.total_members - 1
}

const submitting = ref(false)
const investments = ref<any[]>([])
const pendingApprovals = ref<any[]>([])
const formData = ref({ 
  name: '', 
  investment_type: 'fund' as 'fund' | 'stock' | 'bond' | 'other',
  principal: null as number | null,
  currency: 'CNY' as string,
  foreign_amount: null as number | null,
  deduct_from_cash: false
})

// 币种相关
const currencyOptions = [
  { label: '人民币 CNY', value: 'CNY' },
  { label: '美元 USD', value: 'USD' },
  { label: '港币 HKD', value: 'HKD' },
  { label: '日元 JPY', value: 'JPY' },
  { label: '欧元 EUR', value: 'EUR' },
  { label: '英镑 GBP', value: 'GBP' },
  { label: '澳元 AUD', value: 'AUD' },
  { label: '加元 CAD', value: 'CAD' },
  { label: '新币 SGD', value: 'SGD' },
  { label: '韩元 KRW', value: 'KRW' }
]
const currencySymbols: Record<string, string> = {
  CNY: '¥', USD: '$', HKD: 'HK$', JPY: '¥', EUR: '€',
  GBP: '£', AUD: 'A$', CAD: 'C$', SGD: 'S$', KRW: '₩'
}
const getCurrencySymbol = (c: string) => currencySymbols[c] || c
const currentExchangeRate = ref<number | null>(null)
const exchangeRateLoading = ref(false)

const handleAmountUpdate = (val: any) => {
  if (formData.value.currency === 'CNY') {
    formData.value.principal = val
  } else {
    formData.value.foreign_amount = val
  }
}

const handleCurrencyChange = async (currency: string) => {
  if (currency !== 'CNY') {
    await fetchExchangeRate(currency)
  } else {
    currentExchangeRate.value = null
    formData.value.foreign_amount = null
  }
}

const fetchExchangeRate = async (currency: string) => {
  if (currency === 'CNY') return
  exchangeRateLoading.value = true
  try {
    const { data } = await assetApi.getExchangeRate(currency)
    currentExchangeRate.value = data.rate
  } catch (error) {
    console.error('Failed to fetch exchange rate:', error)
    currentExchangeRate.value = null
  } finally {
    exchangeRateLoading.value = false
  }
}

const equivalentCNY = computed(() => {
  if (formData.value.currency === 'CNY') return formData.value.principal
  const foreignAmt = formData.value.foreign_amount
  if (!foreignAmt || foreignAmt <= 0 || !currentExchangeRate.value) return null
  return Number((foreignAmt * currentExchangeRate.value).toFixed(2))
})

// 格式化投资产品的金额显示
const formatInvAmount = (item: any, amountField: string = 'principal') => {
  const currency = item.currency || 'CNY'
  if (currency === 'CNY') {
    return `¥${formatMoney(item[amountField] || 0)}`
  }
  // 外币显示外币金额 + CNY换算
  const symbol = getCurrencySymbol(currency)
  if (amountField === 'principal') {
    const foreignAmt = item.foreign_amount || 0
    return `${symbol}${formatMoney(foreignAmt)}`
  } else if (amountField === 'current_principal') {
    const foreignAmt = item.current_foreign_amount || 0
    return `${symbol}${formatMoney(foreignAmt)}`
  }
  return `¥${formatMoney(item[amountField] || 0)}`
}

const formatInvAmountWithCNY = (item: any, amountField: string = 'principal') => {
  const currency = item.currency || 'CNY'
  if (currency === 'CNY') return `¥${formatMoney(item[amountField] || 0)}`
  const base = formatInvAmount(item, amountField)
  const cnyVal = item.cny_value || item.current_principal || 0
  return `${base} (≈¥${formatMoney(cnyVal)})`
}

// 收益登记相关
const showIncomeModal = ref(false)
const selectedInvestment = ref<any>(null)
const incomeForm = ref({
  current_value: null as number | null,
  income_date: Date.now(),
  note: ''
})

// 增持/减持相关
const showIncreaseModal = ref(false)
const showDecreaseModal = ref(false)
const showHistoryModal = ref(false)
const historyLoading = ref(false)
const historyData = ref({
  investment: null as any,
  history: [] as any[]
})
const increaseForm = ref({
  amount: null as number | null,
  operation_date: Date.now(),
  note: '',
  deduct_from_cash: true  // 默认从自由资金扣除
})
const decreaseForm = ref({
  amount: null as number | null,
  operation_date: Date.now(),
  note: ''
})

// 当前余额（从transactions获取）
const currentBalance = ref(0)

// AI 分析相关
const aiAnalyzing = ref(false)
const showAiModal = ref(false)
const aiAnalysisResult = ref<any>(null)

// AI 分析函数
async function handleAIAnalysis() {
  if (investments.value.length === 0) {
    message.warning('暂无投资数据可供分析')
    return
  }

  aiAnalyzing.value = true
  try {
    const { data } = await investmentAiApi.analyze()
    aiAnalysisResult.value = data
    showAiModal.value = true
  } catch (error: any) {
    message.error(error.response?.data?.detail || 'AI 分析失败')
  } finally {
    aiAnalyzing.value = false
  }
}

// 风险颜色
function getRiskColor(score: number) {
  if (score < 30) return '#18a058'
  if (score < 60) return '#f0a020'
  return '#d03050'
}

// 计算收益（实时预览）
const calculatedIncome = computed(() => {
  if (!incomeForm.value.current_value || !selectedInvestment.value) return 0
  const inv = selectedInvestment.value
  const isForeign = inv.currency && inv.currency !== 'CNY'
  // 外币投资用外币持仓计算，人民币投资用CNY持仓计算
  const currentPrincipal = isForeign 
    ? (inv.current_foreign_amount || inv.foreign_amount || 0)
    : (inv.current_principal || inv.principal || 0)
  const historicalIncome = inv.total_return || 0
  return incomeForm.value.current_value - currentPrincipal - historicalIncome
})

const typeOptions = [
  { label: '基金', value: 'fund' },
  { label: '股票', value: 'stock' },
  { label: '债券', value: 'bond' },
  { label: '其他', value: 'other' }
]

const typeLabels: Record<string, string> = {
  fund: '基金',
  stock: '股票',
  bond: '债券',
  time_deposit: '定期存款',
  other: '其他'
}

const operationTypeLabels: Record<string, string> = {
  CREATE: '创建投资',
  INCREASE: '增持',
  DECREASE: '减持',
  DELETE: '删除'
}

const transactionTypeLabels: Record<string, string> = {
  DEPOSIT: '资金注入',
  WITHDRAW: '资金提取',
  INVESTMENT_BUY: '投资买入',
  INVESTMENT_SELL: '投资卖出',
  TRANSFER: '资金转账',
  EXPENSE: '支出'
}

const requestTypeLabels: Record<string, string> = {
  asset_create: '资产登记',
  investment_create: '登记产品',
  investment_update: '更新产品',
  investment_income: '登记收益',
  investment_increase: '投资增持',
  investment_decrease: '投资减持',
  investment_delete: '删除产品'
}

const columns = computed(() => [
  { title: '产品名称', key: 'name' },
  { title: '类型', key: 'investment_type', render: (row: any) => typeLabels[row.investment_type] || row.investment_type },
  { title: '币种', key: 'currency', render: (row: any) => row.currency && row.currency !== 'CNY' ? row.currency : '' },
  { title: '初始本金', key: 'principal', render: (row: any) => formatInvAmountWithCNY(row, 'principal') },
  { title: '当前持仓', key: 'current_principal', render: (row: any) => formatInvAmountWithCNY(row, 'current_principal') },
  { title: '总收益', key: 'total_return', render: (row: any) => {
    const cur = row.currency || 'CNY'
    const sym = currencySymbols[cur] || '¥'
    return h('span', { style: { color: (row.total_return || 0) >= 0 ? 'var(--theme-success)' : 'var(--theme-error)' } }, `${sym}${formatMoney(row.total_return || 0)}`)
  }},
  { title: 'ROI', key: 'roi', render: (row: any) => {
    const roi = row.roi || 0
    return h('span', { style: { color: roi >= 0 ? 'var(--theme-success)' : 'var(--theme-error)' } }, `${roi.toFixed(2)}%`)
  }},
  { title: '年化', key: 'annualized_return', render: (row: any) => {
    const rate = row.annualized_return || 0
    if (rate <= 0) return '-'
    return h('span', { style: { color: 'var(--theme-info)', fontWeight: 600 } }, `${rate.toFixed(2)}%`)
  }},
  { title: '状态', key: 'is_active', render: (row: any) => {
    if (row.is_deleted) return h(NTag, { type: 'error', size: 'small' }, { default: () => '已删除' })
    return h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? '持有中' : '已结束' })
  }},
  { title: '开始日期', key: 'start_date', render: (row: any) => formatLocalDate(row.start_date) },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => {
      if (row.is_deleted) return h('span', { style: { color: 'var(--theme-text-tertiary)' } }, '已删除')
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => openIncomeModal(row) }, { default: () => '更新价值' }),
          h(NButton, { size: 'small', text: true, type: 'info', onClick: () => openIncreaseModal(row) }, { default: () => '增持' }),
          h(NButton, { size: 'small', text: true, type: 'warning', onClick: () => openDecreaseModal(row) }, { default: () => '减持' }),
          h(NButton, { size: 'small', text: true, type: 'default', onClick: () => openHistoryModal(row) }, { default: () => '详细' }),
          h(NButton, { size: 'small', text: true, type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' })
        ]
      })
    }
  }
])

const approvalColumns = computed(() => [
  { title: '申请人', key: 'requester_nickname' },
  { 
    title: '类型', 
    key: 'request_type',
    render: (row: any) => h(NTag, { size: 'small', type: 'info' }, { default: () => requestTypeLabels[row.request_type] || row.request_type })
  },
  { 
    title: '详情', 
    key: 'details', 
    render: (row: any) => row.title || '-'
  },
  { title: '申请时间', key: 'created_at', render: (row: any) => dayjs(row.created_at).format('YYYY-MM-DD HH:mm') },
  { 
    title: '审批进度', 
    key: 'progress',
    render: (row: any) => `${row.approved_count || 0}/${getRequiredCount(row)}`
  },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => {
      const canApprove = row.requester_id !== userStore.user?.id && !row.has_voted
      if (!canApprove) return h('span', { style: 'color: var(--theme-text-tertiary)' }, row.has_voted ? '已投票' : '等待他人')
      return h(NSpace, { size: 'small' }, { default: () => [
        h(NButton, { size: 'small', type: 'success', onClick: () => handleApprove(row.id, true) }, { default: () => '同意' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleApprove(row.id, false) }, { default: () => '拒绝' })
      ]})
    }
  }
])

async function loadData() {
  loading.value = true
  try {
    const [investmentsRes, approvalsRes, cashBalanceRes] = await Promise.all([
      investmentApi.list(),
      approvalApi.list({ status: 'pending' }),
      assetApi.getCashBalance()  // 获取家庭自由资金余额
    ])
    investments.value = investmentsRes.data
    // 显示所有理财相关的待审批申请（包括新的 asset_create 类型）
    const investmentTypes = ['asset_create', 'investment_create', 'investment_update', 'investment_income', 'investment_increase', 'investment_decrease', 'investment_delete']
    pendingApprovals.value = (approvalsRes.data?.items || []).filter((item: any) => investmentTypes.includes(item.request_type))
    // 从API获取家庭自由资金余额
    currentBalance.value = cashBalanceRes.data?.balance || 0
  } catch (error) {
    console.error('loadData error:', error)
    message.error('数据加载失败')
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  const isForeign = formData.value.currency !== 'CNY'
  const hasAmount = isForeign ? formData.value.foreign_amount : formData.value.principal
  if (!formData.value.name || !hasAmount) { message.warning('请填写完整信息'); return }
  
  // 计算人民币等值金额（外币需要换算）
  let cnyAmount = formData.value.principal || 0
  if (isForeign && currentExchangeRate.value && formData.value.foreign_amount) {
    cnyAmount = Math.round(formData.value.foreign_amount * currentExchangeRate.value * 100) / 100
  }
  
  // 检查是否需要从自由资金扣除，如果是则检查余额
  if (formData.value.deduct_from_cash) {
    try {
      const { data } = await assetApi.getCashBalance()
      const cashBalance = data.balance || 0
      if (cashBalance < cnyAmount) {
        message.error(`家庭自由资金不足：需要¥${cnyAmount}，当前仅有¥${cashBalance.toFixed(2)}`)
        return
      }
    } catch (error) {
      console.error('Failed to check cash balance:', error)
      message.error('无法获取家庭自由资金余额，请稍后重试')
      return
    }
  }
  
  submitting.value = true
  try {
    await approvalApi.createAsset({
      user_id: userStore.user?.id || 0,
      name: formData.value.name,
      asset_type: formData.value.investment_type as any,
      currency: formData.value.currency as 'CNY' | 'USD' | 'HKD' | 'JPY' | 'EUR' | 'GBP' | 'AUD' | 'CAD' | 'SGD' | 'KRW',
      amount: isForeign ? cnyAmount : formData.value.principal!,
      foreign_amount: isForeign ? (formData.value.foreign_amount ?? undefined) : undefined,
      start_date: new Date().toISOString(),
      deduct_from_cash: formData.value.deduct_from_cash
    })
    message.success('申请已提交，等待审批！📈')
    formData.value = { name: '', investment_type: 'fund', principal: null, currency: 'CNY', foreign_amount: null, deduct_from_cash: false }
    currentExchangeRate.value = null
    // 延迟加载数据，给后端时间处理（单人家庭自动执行）
    setTimeout(() => {
      loadData()
      approvalStore.refreshNow()
    }, 800)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

function openIncomeModal(investment: any) {
  selectedInvestment.value = investment
  incomeForm.value = {
    current_value: null,
    income_date: Date.now(),
    note: ''
  }
  showIncomeModal.value = true
}

async function submitIncome() {
  if (incomeForm.value.current_value === null || incomeForm.value.current_value <= 0) { 
    message.warning('请输入有效的当前总价值')
    return false
  }
  try {
    await approvalApi.createInvestmentIncome({
      investment_id: selectedInvestment.value.id,
      current_value: incomeForm.value.current_value,
      income_date: new Date(incomeForm.value.income_date).toISOString(),
      note: incomeForm.value.note || undefined
    })
    message.success('价值更新申请已提交！')
    showIncomeModal.value = false
    // 延迟加载数据，给后端时间处理（单人家庭自动执行）
    setTimeout(() => {
      loadData()
      approvalStore.refreshNow()
    }, 800)
    return true
  } catch (e: any) {
    console.error('Income submission error:', e.response?.data)
    message.error(e.response?.data?.detail || '操作失败')
    return false
  }
}

function openIncreaseModal(investment: any) {
  selectedInvestment.value = investment
  increaseForm.value = {
    amount: null,
    operation_date: Date.now(),
    note: '',
    deduct_from_cash: true
  }
  showIncreaseModal.value = true
}

async function submitIncrease() {
  if (increaseForm.value.amount === null) { 
    message.warning('请输入增持金额')
    return false
  }
  // 只有从自由资金扣除时才检查余额
  if (increaseForm.value.deduct_from_cash && increaseForm.value.amount > currentBalance.value) {
    message.warning('余额不足')
    return false
  }
  const isForeign = selectedInvestment.value?.currency && selectedInvestment.value.currency !== 'CNY'
  try {
    await approvalApi.increaseInvestment({
      investment_id: selectedInvestment.value.id,
      amount: increaseForm.value.amount,
      foreign_amount: isForeign ? increaseForm.value.amount : undefined,
      operation_date: new Date(increaseForm.value.operation_date).toISOString(),
      note: increaseForm.value.note,
      deduct_from_cash: increaseForm.value.deduct_from_cash
    })
    message.success('增持申请已提交！')
    showIncreaseModal.value = false
    // 延迟加载数据，给后端时间处理（单人家庭自动执行）
    setTimeout(() => {
      loadData()
      approvalStore.refreshNow()
    }, 800)
    return true
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
    return false
  }
}

function openDecreaseModal(investment: any) {
  selectedInvestment.value = investment
  decreaseForm.value = {
    amount: null,
    operation_date: Date.now(),
    note: ''
  }
  showDecreaseModal.value = true
}

async function openHistoryModal(investment: any) {
  selectedInvestment.value = investment
  showHistoryModal.value = true
  historyLoading.value = true
  try {
    const response = await investmentApi.getHistory(investment.id)
    historyData.value = response.data
  } catch (e: any) {
    console.error('History fetch error:', e)
    message.error(e.response?.data?.detail || '获取历史记录失败')
  } finally {
    historyLoading.value = false
  }
}

async function submitDecrease() {
  if (decreaseForm.value.amount === null) { 
    message.warning('请输入减持金额')
    return false
  }
  const isForeign = selectedInvestment.value?.currency && selectedInvestment.value.currency !== 'CNY'
  const maxDecrease = isForeign ? (selectedInvestment.value.current_foreign_amount || 0) : (selectedInvestment.value.current_principal || 0)
  if (decreaseForm.value.amount > maxDecrease) {
    const sym = getCurrencySymbol(selectedInvestment.value?.currency || 'CNY')
    message.warning(`减持金额不能超过当前持仓 ${sym}${maxDecrease}`)
    return false
  }
  try {
    await approvalApi.decreaseInvestment({
      investment_id: selectedInvestment.value.id,
      amount: decreaseForm.value.amount,
      foreign_amount: isForeign ? decreaseForm.value.amount : undefined,
      operation_date: new Date(decreaseForm.value.operation_date).toISOString(),
      note: decreaseForm.value.note
    })
    message.success('减持申请已提交！')
    showDecreaseModal.value = false
    // 延迟加载数据，给后端时间处理（单人家庭自动执行）
    setTimeout(() => {
      loadData()
      approvalStore.refreshNow()
    }, 800)
    return true
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
    return false
  }
}

function handleDelete(investment: any) {
  dialog.warning({
    title: '确认删除',
    content: `确认删除投资产品「${investment.name}」？此操作为软删除，历史数据将保留。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await approvalApi.deleteInvestment({
          investment_id: investment.id,
          reason: '用户请求删除'
        })
        message.success('删除申请已提交！')
        // 延迟加载数据，给后端时间处理（单人家庭自动执行）
        setTimeout(() => {
          loadData()
          approvalStore.refreshNow()
        }, 800)
      } catch (e: any) {
        message.error(e.response?.data?.detail || '操作失败')
      }
    }
  })
}

async function doApprove(id: number, approved: boolean, reason?: string) {
  try {
    if (approved) {
      await approvalApi.approve(id)
    } else {
      await approvalApi.reject(id, reason || '未说明原因')
    }
    message.success(approved ? '已同意' : '已拒绝')
    loadData()
    
    // 立即刷新审批红点
    await approvalStore.refreshNow()
    
    // 审批通过后检查成就
    if (approved) {
      setTimeout(() => checkAndShowAchievements(), 500)
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

function handleApprove(id: number, approved: boolean) {
  if (approved) {
    doApprove(id, true)
  } else {
    dialog.create({
      title: '拒绝原因',
      content: () => h(NInput, {
        id: 'reject-reason-input',
        placeholder: '请输入拒绝原因（可选）',
        style: { width: '100%' }
      }),
      positiveText: '确认拒绝',
      negativeText: '取消',
      onPositiveClick: () => {
        const reason = (document.getElementById('reject-reason-input') as HTMLInputElement)?.value || ''
        doApprove(id, false, reason)
      }
    })
  }
}

onMounted(loadData)
</script>

<style scoped>
/* 页面头部样式 */
.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

/* AI 分析内容样式 */
.ai-analysis-content {
  padding: 16px 0;
}

.analysis-section {
  margin-bottom: 24px;
}

.analysis-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--theme-text-primary);
}

.score-desc {
  margin-top: 8px;
  text-align: center;
  color: var(--theme-text-secondary);
}

/* 家庭自由资金卡片样式 */
:deep(.n-statistic) {
  color: white;
}

:deep(.n-statistic .n-statistic-value__prefix),
:deep(.n-statistic .n-statistic-value__content) {
  color: white !important;
}

/* 桌面/移动端显示控制 */
.desktop-only {
  display: block;
}
.mobile-only {
  display: none;
}

/* 移动端响应式 */
@media (max-width: 767px) {
  .desktop-only {
    display: none !important;
  }
  .mobile-only {
    display: block !important;
  }

  .page-container {
    padding: 16px;
  }

  /* 页面头部移动端适配 */
  .page-header-row {
    flex-direction: column;
    align-items: stretch;
  }

  .page-header-row .n-button {
    width: 100%;
  }

  /* 表单垂直布局 */
  :deep(.n-form--inline) {
    display: flex;
    flex-direction: column;
    gap: 0;
  }
  
  :deep(.n-form--inline .n-form-item) {
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
    margin-right: 0;
  }
  
  :deep(.n-form--inline .n-form-item-label) {
    display: block;
    text-align: left;
    padding-bottom: 8px;
    width: auto;
  }
  
  :deep(.n-form--inline .n-form-item-blank) {
    min-height: auto;
  }
  
  :deep(.n-form--inline .n-input),
  :deep(.n-form--inline .n-input-number),
  :deep(.n-form--inline .n-select) {
    width: 100% !important;
    font-size: 16px; /* 防止 iOS 放大 */
  }
  
  /* 修复 n-input-number 在移动端的布局 */
  :deep(.n-input-number) {
    flex-direction: row !important;
  }
  
  :deep(.n-input-number .n-input) {
    flex: 1 !important;
  }
  
  :deep(.n-input-number .n-input-wrapper) {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
  }
  
  :deep(.n-input-number .n-input__input-el) {
    text-align: left !important;
  }
  
  :deep(.n-input-number .n-input__suffix) {
    margin-left: auto !important;
  }
  
  :deep(.n-input-number-button-group) {
    display: flex !important;
    flex-direction: row !important;
  }
  
  /* 提交按钮 */
  :deep(.n-form--inline .n-button) {
    width: 100%;
    height: 48px;
    font-size: 15px;
  }
  
  /* 表格优化 */
  :deep(.n-data-table) {
    font-size: 13px;
  }
  
  :deep(.n-data-table-th),
  :deep(.n-data-table-td) {
    padding: 10px 8px !important;
  }
  
  /* 弹窗样式适配 */
  :deep(.n-modal-mask .n-dialog) {
    width: 100% !important;
    max-width: calc(100vw - 32px);
    margin: 16px;
    background-color: var(--theme-bg-primary) !important;
  }
  
  :deep(.n-dialog__title) {
    color: var(--theme-text-primary) !important;
    font-weight: 600;
  }
  
  :deep(.n-dialog .n-form-item) {
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
  }
  
  :deep(.n-dialog .n-form-item-label) {
    display: block;
    text-align: left;
    padding-bottom: 8px;
    width: auto !important;
    color: var(--theme-text-primary) !important;
    font-weight: 500;
  }
  
  :deep(.n-dialog .n-input) {
    background-color: var(--theme-bg-secondary) !important;
  }
  
  :deep(.n-dialog .n-input__input) {
    color: var(--theme-text-primary) !important;
  }
  
  :deep(.n-dialog .n-input-number) {
    background-color: var(--theme-bg-secondary) !important;
  }
  
  :deep(.n-dialog .n-input-number__input) {
    color: var(--theme-text-primary) !important;
  }
  
  :deep(.n-dialog .n-date-picker) {
    background-color: var(--theme-bg-secondary) !important;
  }
  
  :deep(.n-dialog .n-text) {
    color: var(--theme-text-primary) !important;
  }
  
  :deep(.n-dialog .n-button) {
    border-color: var(--theme-border) !important;
  }
  
  /* 卡片间距 */
  :deep(.n-card) {
    margin-bottom: 16px !important;
  }

  /* ===== 理财产品卡片样式 ===== */
  .investment-cards {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .investment-card {
    background: linear-gradient(135deg, var(--theme-bg-secondary) 0%, var(--theme-border-light) 100%);
    border-radius: 16px;
    padding: 12px;
    border: 1px solid var(--theme-border);
    position: relative;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transition: all 0.3s ease;
  }
  
  .investment-card:hover {
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
    border-color: var(--theme-success);
  }

  .investment-card .card-header {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    gap: 8px;
    min-height: 24px;
  }
  
  .investment-card .detail-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    opacity: 0.8;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(50, 151, 211, 0.15);
  }
  
  .investment-card:hover .detail-btn {
    opacity: 1;
    box-shadow: 0 4px 12px rgba(50, 151, 211, 0.25);
    transform: translateY(-1px);
  }

  .investment-card .product-name {
    font-size: 16px;
    font-weight: 700;
    color: var(--theme-text-primary);
    flex-shrink: 0;
  }

  .investment-card .card-type {
    margin-bottom: 10px;
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .investment-card .card-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 10px;
    background: rgba(0, 0, 0, 0.05);
    border-radius: 12px;
    padding: 10px;
  }

  .investment-card .card-stats-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 10px;
    background: rgba(0, 0, 0, 0.05);
    border-radius: 12px;
    padding: 10px;
  }

  .investment-card .stat-item {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .investment-card .stat-label {
    font-size: 11px;
    color: var(--theme-text-secondary);
    font-weight: 500;
    letter-spacing: 0.5px;
  }

  .investment-card .stat-value {
    font-size: 15px;
    font-weight: 700;
    color: var(--theme-text-primary);
  }

  .investment-card .stat-value.profit {
    color: var(--theme-success);
  }

  .investment-card .stat-value.loss {
    color: var(--theme-error);
  }

  .investment-card .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 8px;
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    gap: 8px;
  }

  .investment-card .start-date {
    font-size: 12px;
    color: var(--theme-text-secondary);
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* ===== 待审批卡片样式 ===== */
  .approval-cards {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .approval-card {
    background: var(--theme-warning-bg);
    border-radius: 10px;
    padding: 12px;
    border: 1px solid var(--theme-warning);
  }

  .approval-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .approval-time {
    font-size: 11px;
    color: var(--theme-text-tertiary);
  }

  .approval-card-body {
    margin-bottom: 10px;
  }

  .approval-requester {
    font-size: 14px;
    font-weight: 500;
    color: var(--theme-text-primary);
    margin-bottom: 4px;
  }

  .approval-detail {
    font-size: 13px;
    color: var(--theme-text-secondary);
  }

  .approval-card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 10px;
    border-top: 1px solid var(--theme-border);
  }

  .approval-progress {
    font-size: 12px;
    color: var(--theme-text-secondary);
  }

  .approval-actions {
    display: flex;
    gap: 8px;
  }

  .approval-wait {
    font-size: 12px;
    color: var(--theme-text-tertiary);
  }

  /* ===== 移动端紧凑表单样式 ===== */
  .investment-form-card :deep(.n-card__content) {
    padding: 12px !important;
  }
  
  .mobile-investment-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  
  .mobile-investment-form .form-row {
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }
  
  .mobile-investment-form .form-col {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .mobile-investment-form .form-col.name-col {
    flex: 1.2;
    min-width: 0;
  }
  
  .mobile-investment-form .form-col.type-col {
    flex: 0.8;
    min-width: 0;
  }
  
  .mobile-investment-form .form-col.principal-col {
    flex: 1;
    min-width: 0;
  }
  
  .mobile-investment-form .form-col.rate-col {
    flex: 0.8;
    min-width: 0;
  }
  
  .mobile-investment-form .form-col.btn-col {
    flex-shrink: 0;
  }
  
  .mobile-investment-form label {
    font-size: 12px;
    color: #6b7280;
    font-weight: 500;
  }
  
  /* 统一输入框高度 32px */
  .mobile-investment-form :deep(.n-input),
  .mobile-investment-form :deep(.n-input-number),
  .mobile-investment-form :deep(.n-select) {
    font-size: 14px !important;
    width: 100% !important;
  }
  
  .mobile-investment-form :deep(.n-input--small .n-input__input-el),
  .mobile-investment-form :deep(.n-input-number--small .n-input__input-el) {
    height: 32px !important;
    line-height: 32px !important;
  }
  
  .mobile-investment-form :deep(.n-base-selection--small) {
    height: 32px !important;
  }
  
  .mobile-investment-form :deep(.n-input-number--small) {
    display: flex !important;
    flex-direction: row !important;
  }
  
  .mobile-investment-form :deep(.n-input-number--small .n-input) {
    flex: 1 !important;
    min-width: 0 !important;
  }
  
  .mobile-investment-form :deep(.n-input-number--small .n-input-number-button-group) {
    display: flex !important;
    flex-shrink: 0 !important;
    height: 32px !important;
  }
  
  .mobile-investment-form :deep(.n-input-number--small .n-input-number-button) {
    height: 16px !important;
  }
  
  /* 提交按钮样式 */
  .mobile-investment-form .submit-btn {
    height: 32px !important;
    padding: 0 16px !important;
    font-size: 14px !important;
    width: auto !important;
  }
}

/* 历史列表样式 */
.history-list {
  padding: 0;
}

.history-item {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--theme-bg-border);

  &:last-child {
    border-bottom: none;
  }
}

.history-icon {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
}

.history-content {
  flex: 1;
  min-width: 0;
}

.history-date {
  font-size: 12px;
  color: var(--theme-text-tertiary);
  margin-bottom: 4px;
}

.history-details {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 14px;
}

.history-details .label {
  color: var(--theme-text-tertiary);
  font-size: 12px;
}

.history-details .value {
  color: var(--theme-text-primary);
  font-weight: 500;
}

.history-details .value.profit {
  color: var(--theme-success);
}

.history-details .value.loss {
  color: var(--theme-error);
}

.history-details .note {
  width: 100%;
  margin-top: 4px;
  padding: 6px 8px;
  background-color: var(--theme-bg-secondary);
  border-radius: 4px;
  font-size: 12px;
  color: var(--theme-text-secondary);
}
</style>
