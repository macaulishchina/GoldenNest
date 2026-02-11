<template>
  <div class="approval-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>📋 审批中心</h1>
      <p class="subtitle">所有资金变动都需要全体家庭成员同意后才能执行</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card pending">
        <div class="stat-icon">⏳</div>
        <div class="stat-info">
          <div class="stat-value">{{ approvalList?.pending_count || 0 }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-card approved">
        <div class="stat-icon">✅</div>
        <div class="stat-info">
          <div class="stat-value">{{ approvalList?.approved_count || 0 }}</div>
          <div class="stat-label">已通过</div>
        </div>
      </div>
      <div class="stat-card rejected">
        <div class="stat-icon">❌</div>
        <div class="stat-info">
          <div class="stat-value">{{ approvalList?.rejected_count || 0 }}</div>
          <div class="stat-label">已拒绝</div>
        </div>
      </div>
      <div class="stat-card total">
        <div class="stat-icon">📊</div>
        <div class="stat-info">
          <div class="stat-value">{{ approvalList?.total || 0 }}</div>
          <div class="stat-label">全部申请</div>
        </div>
      </div>
    </div>

    <!-- 时间范围选择器 -->
    <TimeRangeSelector v-model="timeRange" @change="loadApprovals" />

    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="filters">
        <select v-model="filterType" @change="loadApprovals" class="filter-select">
          <option value="">全部类型</option>
          <option value="deposit">资金注入</option>
          <option value="expense">大额支出</option>
          <option value="investment_create">创建理财</option>
          <option value="investment_update">更新理财</option>
          <option value="investment_income">理财收益</option>
          <option value="investment_increase">投资增持</option>
          <option value="investment_decrease">投资减持</option>
          <option value="investment_delete">删除投资</option>
          <option value="member_join">成员加入</option>
          <option value="member_remove">成员剔除</option>
        </select>
        <select v-model="filterStatus" @change="loadApprovals" class="filter-select">
          <option value="">全部状态</option>
          <option value="pending">待处理</option>
          <option value="approved">已通过</option>
          <option value="rejected">已拒绝</option>
          <option value="cancelled">已取消</option>
        </select>
      </div>
      <div class="actions">
        <button @click="openCreateModal" class="btn-primary">
          ➕ 发起申请
        </button>
      </div>
    </div>

    <!-- 待我审批的申请（醒目提示） -->
    <div v-if="pendingApprovals.length > 0" class="pending-section">
      <h2>🔔 待我审批 ({{ pendingApprovals.length }})</h2>
      <div class="approval-cards">
        <div v-for="item in pendingApprovals" :key="item.id" class="approval-card pending-card">
          <div class="card-header">
            <span class="type-badge" :class="getTypeClass(item.request_type)">
              {{ getTypeLabel(item.request_type) }}
            </span>
            <span class="status-badge pending">待审批</span>
          </div>
          <div class="card-body">
            <h3>{{ item.title }}</h3>
            <p class="description">{{ item.description }}</p>
            <div class="meta">
              <span v-if="!isMemberRequest(item.request_type)">💰 ¥{{ formatAmount(item.amount) }}</span>
              <span class="requester-info">
                <!-- 分红领取显示目标用户，其他显示发起人 -->
                <template v-if="item.request_type === 'dividend_claim' && item.target_user_id">
                  <UserAvatar :userId="item.target_user_id" :name="item.target_user_nickname || ''" :avatarVersion="item.target_user_avatar_version || 0" :size="20" />
                  {{ item.target_user_nickname }}
                </template>
                <template v-else>
                  <UserAvatar :userId="item.requester_id" :name="item.requester_nickname" :avatarVersion="item.requester_avatar_version" :size="20" />
                  {{ item.requester_nickname }}
                </template>
              </span>
              <span>📅 {{ formatDate(item.created_at) }}</span>
            </div>
            <!-- 支付比例分配（仅支出类型显示） -->
            <div v-if="item.request_type === 'expense' && item.request_data?.deduction_ratios" class="payment-ratios">
              <div class="ratios-header">💳 支付比例分配</div>
              <div class="ratios-list">
                <div v-for="ratio in getDeductionRatiosArray(item.request_data.deduction_ratios)" :key="ratio.user_id" class="ratio-item">
                  <div class="member-info">
                    <UserAvatar :userId="ratio.user_id" :name="getMemberName(ratio.user_id)" :size="24" />
                    <span class="member-name">{{ getMemberName(ratio.user_id) }}</span>
                  </div>
                  <div class="ratio-bar desktop-only">
                    <div class="bar-bg">
                      <div class="bar-fill" :style="{ width: (ratio.ratio * 100) + '%' }"></div>
                    </div>
                    <span class="ratio-text">{{ (ratio.ratio * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="amount-text">¥{{ formatAmount(item.amount * ratio.ratio) }} <span class="ratio-suffix">({{ (ratio.ratio * 100).toFixed(1) }}%)</span></div>
                </div>
              </div>
            </div>
            <div class="progress-bar">
              <div class="progress" :style="{ width: getProgressWidth(item) }"></div>
              <span class="progress-text">{{ getProgressText(item) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <!-- 分红领取特殊处理 -->
            <template v-if="item.request_type === 'dividend_claim' && item.status === 'pending'">
              <button 
                @click="handleDividendClaim(item.id, true)" 
                class="btn-reinvest"
                :disabled="processingApprovalId === item.id"
              >
                {{ processingApprovalId === item.id ? '⏳ 处理中...' : '💰 红利再投' }}
              </button>
              <button 
                @click="handleDividendClaim(item.id, false)" 
                class="btn-withdraw"
                :disabled="processingApprovalId === item.id"
              >
                {{ processingApprovalId === item.id ? '⏳ 处理中...' : '💵 提现' }}
              </button>
            </template>
            <!-- 普通审核 -->
            <template v-else-if="item.status === 'pending'">
              <button 
                @click="handleApprove(item.id, true)" 
                class="btn-approve"
                :disabled="processingApprovalId === item.id"
              >
                {{ processingApprovalId === item.id ? '⏳ 处理中...' : '✅ 同意' }}
              </button>
              <button 
                @click="handleApprove(item.id, false)" 
                class="btn-reject"
                :disabled="processingApprovalId === item.id"
              >
                {{ processingApprovalId === item.id ? '⏳ 处理中...' : '❌ 拒绝' }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 所有申请列表 -->
    <div class="all-approvals">
      <h2>📋 所有申请</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="approvalList?.items?.length === 0" class="empty">
        <p>暂无申请记录</p>
      </div>
      <div v-else class="approval-cards">
        <div v-for="item in approvalList?.items" :key="item.id" class="approval-card">
          <div class="card-header">
            <span class="type-badge" :class="getTypeClass(item.request_type)">
              {{ getTypeLabel(item.request_type) }}
            </span>
            <div class="header-right">
              <span class="status-badge" :class="item.status">
                {{ getStatusLabel(item.status) }}
              </span>
              <span v-if="item.status === 'approved' && item.execution_failed" class="status-badge failed">
                ⚠️ 执行失败
              </span>
              <button 
                v-if="item.status === 'pending'"
                @click.stop="handleRemind(item.id)" 
                class="btn-remind-small"
                :disabled="remindingId === item.id"
                :title="'发送催促通知'"
              >
                {{ remindingId === item.id ? '⏳' : '⏰ 催促' }}
              </button>
            </div>
          </div>
          <div class="card-body">
            <h3>{{ item.title }}</h3>
            <p class="description">{{ item.description }}</p>
            <div class="meta">
              <span v-if="!isMemberRequest(item.request_type)">💰 ¥{{ formatAmount(item.amount) }}</span>
              <span class="requester-info">
                <!-- 分红领取显示目标用户，其他显示发起人 -->
                <template v-if="item.request_type === 'dividend_claim' && item.target_user_id">
                  <UserAvatar :userId="item.target_user_id" :name="item.target_user_nickname || ''" :avatarVersion="item.target_user_avatar_version || 0" :size="20" />
                  {{ item.target_user_nickname }}
                </template>
                <template v-else>
                  <UserAvatar :userId="item.requester_id" :name="item.requester_nickname" :avatarVersion="item.requester_avatar_version" :size="20" />
                  {{ item.requester_nickname }}
                </template>
              </span>
              <span>📅 {{ formatDate(item.created_at) }}</span>
            </div>
            <!-- 执行失败原因 -->
            <div v-if="item.status === 'approved' && item.execution_failed && item.failure_reason" class="failure-reason">
              <span class="failure-icon">⚠️</span>
              <span class="failure-text">{{ item.failure_reason }}</span>
            </div>
            <!-- 支付比例分配（仅支出类型显示） -->
            <div v-if="item.request_type === 'expense' && item.request_data?.deduction_ratios" class="payment-ratios">
              <div class="ratios-header">💳 支付比例分配</div>
              <div class="ratios-list">
                <div v-for="ratio in getDeductionRatiosArray(item.request_data.deduction_ratios)" :key="ratio.user_id" class="ratio-item">
                  <div class="member-info">
                    <UserAvatar :userId="ratio.user_id" :name="getMemberName(ratio.user_id)" :size="24" />
                    <span class="member-name">{{ getMemberName(ratio.user_id) }}</span>
                  </div>
                  <div class="ratio-bar desktop-only">
                    <div class="bar-bg">
                      <div class="bar-fill" :style="{ width: (ratio.ratio * 100) + '%' }"></div>
                    </div>
                    <span class="ratio-text">{{ (ratio.ratio * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="amount-text">¥{{ formatAmount(item.amount * ratio.ratio) }}<span class="ratio-suffix"> ({{ (ratio.ratio * 100).toFixed(1) }}%)</span></div>
                </div>
              </div>
            </div>
            <!-- 审批进度 -->
            <div v-if="item.status === 'pending'" class="progress-bar">
              <div class="progress" :style="{ width: getProgressWidth(item) }"></div>
              <span class="progress-text">{{ getProgressText(item) }}</span>
            </div>
            <!-- 审批记录 -->
            <div v-if="item.approvals?.length > 0" class="approval-records">
              <div v-for="record in item.approvals" :key="record.id" class="record">
                <span :class="record.is_approved ? 'approved' : 'rejected'">
                  {{ record.is_approved ? '✅' : '❌' }}
                </span>
                <span class="approver-info">
                  <UserAvatar :userId="record.approver_id" :name="record.approver_nickname" :avatarVersion="record.approver_avatar_version" :size="18" />
                  <span class="approver">{{ record.approver_nickname }}</span>
                </span>
                <span v-if="record.comment" class="comment">: {{ record.comment }}</span>
              </div>
            </div>
          </div>
          <div class="card-actions" v-if="item.status === 'pending'">
            <button 
              v-if="item.requester_id === currentUserId"
              @click="handleCancel(item.id)" 
              class="btn-cancel"
            >
              🚫 取消申请
            </button>
          </div>
          <!-- 执行失败的重试按钮 -->
          <div class="card-actions" v-if="item.status === 'approved' && item.execution_failed">
            <button 
              @click="handleRetry(item.id)" 
              class="btn-retry"
              :disabled="processingApprovalId === item.id"
            >
              {{ processingApprovalId === item.id ? '⏳ 重试中...' : '🔄 重试' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 发起申请弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>发起新申请</h2>
          <button @click="showCreateModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <!-- 申请类型选择 -->
          <div class="form-group">
            <label>申请类型</label>
            <div class="type-selector">
              <button 
                v-for="type in requestTypes" 
                :key="type.value"
                :class="{ active: createForm.type === type.value }"
                @click="createForm.type = type.value"
                class="type-btn"
              >
                {{ type.icon }} {{ type.label }}
              </button>
            </div>
          </div>

          <!-- 资金注入表单 -->
          <template v-if="createForm.type === 'deposit'">
            <div class="form-group">
              <label>注入金额 (元)</label>
              <input v-model.number="createForm.amount" type="number" min="0" step="0.01" placeholder="请输入金额">
            </div>
            <div class="form-group">
              <label>注入日期</label>
              <input v-model="createForm.deposit_date" type="date">
            </div>
            <div class="form-group">
              <label>备注 (可选)</label>
              <textarea v-model="createForm.note" placeholder="备注说明"></textarea>
            </div>
            <!-- 图片识别上传 -->
            <div class="form-group">
              <label>上传凭证图片 (可选)</label>
              <div class="image-upload-section">
                <input 
                  ref="imageInputRef" 
                  type="file" 
                  accept="image/*" 
                  style="display: none" 
                  @change="handleImageSelected"
                  aria-label="选择凭证图片文件"
                />
                <button 
                  @click="triggerImageUpload" 
                  class="btn-image-upload"
                  type="button"
                  :disabled="imageParsing"
                >
                  📷 {{ imageParsing ? '识别中...' : '导入图片识别' }}
                </button>
                <div v-if="imagePreview" class="image-preview">
                  <img :src="imagePreview" alt="上传的凭证图片预览" />
                  <button @click="clearImage" class="btn-clear-image" type="button" aria-label="清除图片">✕</button>
                </div>
                <div v-if="imageParseSuccess" class="parse-success">✓ {{ imageParseSuccess }}</div>
                <div v-if="imageParseError" class="parse-error">⚠ {{ imageParseError }}</div>
              </div>
            </div>
          </template>

          <!-- 创建理财产品表单 -->
          <template v-if="createForm.type === 'investment_create'">
            <div class="form-group">
              <label>产品名称</label>
              <input v-model="createForm.name" type="text" placeholder="请输入理财产品名称">
            </div>
            <div class="form-group">
              <label>产品类型</label>
              <select v-model="createForm.investment_type">
                <option value="fund">基金</option>
                <option value="stock">股票</option>
                <option value="bond">债券</option>
                <option value="other">其他</option>
              </select>
            </div>
            <div class="form-group">
              <label>币种</label>
              <select v-model="createForm.currency" @change="handleCurrencyChange">
                <option v-for="opt in currencyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="form-group" v-if="createForm.currency === 'CNY'">
              <label>本金 (元)</label>
              <input v-model.number="createForm.principal" type="number" min="0" step="0.01" placeholder="请输入本金">
            </div>
            <div class="form-group" v-else>
              <label>外币金额 ({{ createForm.currency }})</label>
              <input v-model.number="createForm.foreign_amount" type="number" min="0" step="0.01" :placeholder="'请输入' + createForm.currency + '金额'">
              <div class="hint-text" v-if="exchangeRateLoading">获取汇率中...</div>
              <div class="hint-text" v-else-if="currentExchangeRate">
                汇率: 1 {{ createForm.currency }} = ¥{{ currentExchangeRate.toFixed(4) }}
                <span v-if="equivalentCNY"> | 约 ¥{{ equivalentCNY.toLocaleString() }}</span>
              </div>
            </div>
            <div class="form-group">
              <label>资金来源</label>
              <select v-model="createForm.deduct_from_cash">
                <option :value="false">外部资金（计入股权）</option>
                <option :value="true">从自由资金扣除（不计股权）</option>
              </select>
            </div>
            <div class="form-group" v-if="createForm.deduct_from_cash">
              <label>当前余额</label>
              <div class="info-text">¥{{ formatAmount(balance) }}</div>
            </div>
            <div class="form-group">
              <label>开始日期</label>
              <input v-model="createForm.start_date" type="date">
            </div>
            <div class="form-group">
              <label>到期日期 (可选)</label>
              <input v-model="createForm.end_date" type="date">
            </div>
            <div class="form-group">
              <label>备注 (可选)</label>
              <textarea v-model="createForm.note" placeholder="备注说明"></textarea>
            </div>
          </template>

          <!-- 理财收益登记表单（改为更新价值） -->
          <template v-if="createForm.type === 'investment_income'">
            <div class="form-group">
              <label>理财产品</label>
              <select v-model="createForm.investment_id" @change="onInvestmentChange">
                <option v-for="inv in investments" :key="inv.id" :value="inv.id">
                  {{ inv.name }} (持仓: {{ formatInvDisplayAmount(inv) }})
                </option>
              </select>
            </div>
            <div class="form-group" v-if="selectedInvestmentForIncome">
              <label>当前持仓本金</label>
              <div class="info-text">{{ formatInvDisplayAmount(selectedInvestmentForIncome) }}</div>
            </div>
            <div class="form-group">
              <label>当前总价值 ({{ getInvestmentCurrency(createForm.investment_id) !== 'CNY' ? getInvestmentCurrency(createForm.investment_id) : '元' }})</label>
              <input v-model.number="createForm.current_value" type="number" step="0.01" placeholder="输入投资产品的当前市场价值">
              <div class="hint-text">系统将自动计算收益 = 当前价值 - 持仓本金 - 历史收益</div>
            </div>
            <div class="form-group" v-if="createForm.current_value && selectedInvestmentForIncome">
              <label>计算收益</label>
              <div class="info-text" :class="calculateIncome() >= 0 ? 'success' : 'error'">
                {{ getCurrencySymbol(getInvestmentCurrency(createForm.investment_id)) }}{{ formatAmount(calculateIncome()) }}
              </div>
            </div>
            <div class="form-group">
              <label>更新日期</label>
              <input v-model="createForm.income_date" type="date">
            </div>
            <div class="form-group">
              <label>备注 (可选)</label>
              <textarea v-model="createForm.note" placeholder="备注说明"></textarea>
            </div>
          </template>

          <!-- 投资增持表单 -->
          <template v-if="createForm.type === 'investment_increase'">
            <div class="form-group">
              <label>理财产品</label>
              <select v-model="createForm.investment_id">
                <option v-for="inv in investments" :key="inv.id" :value="inv.id">
                  {{ inv.name }} (持仓: {{ formatInvDisplayAmount(inv) }})
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>资金来源</label>
              <div class="radio-group">
                <label class="radio-label">
                  <input type="radio" :value="false" v-model="createForm.deduct_from_cash">
                  <span>外部资金</span>
                  <span class="hint-inline">（计入股权贡献）</span>
                </label>
                <label class="radio-label">
                  <input type="radio" :value="true" v-model="createForm.deduct_from_cash">
                  <span>从自由资金扣除</span>
                  <span class="hint-inline">（不计股权）</span>
                </label>
              </div>
            </div>
            <div class="form-group" v-if="createForm.deduct_from_cash">
              <label>当前余额</label>
              <div class="info-text">¥{{ formatAmount(balance) }}</div>
            </div>
            <div class="form-group">
              <label>增持金额 ({{ getInvestmentCurrency(createForm.investment_id) !== 'CNY' ? getInvestmentCurrency(createForm.investment_id) : '元' }})</label>
              <input v-model.number="createForm.amount" type="number" step="0.01" placeholder="请输入增持金额" 
                :max="createForm.deduct_from_cash ? balance : undefined">
              <div class="hint-text" v-if="createForm.deduct_from_cash">从家庭自由资金扣除，不计入股权贡献</div>
              <div class="hint-text" v-else>外部资金增持，将计入您的股权贡献</div>
            </div>
            <div class="form-group">
              <label>增持日期</label>
              <input v-model="createForm.operation_date" type="date">
            </div>
            <div class="form-group">
              <label>备注 (可选)</label>
              <textarea v-model="createForm.note" placeholder="备注说明"></textarea>
            </div>
          </template>

          <!-- 投资减持表单 -->
          <template v-if="createForm.type === 'investment_decrease'">
            <div class="form-group">
              <label>理财产品</label>
              <select v-model="createForm.investment_id" @change="onInvestmentChangeForDecrease">
                <option v-for="inv in investments" :key="inv.id" :value="inv.id">
                  {{ inv.name }} (持仓: {{ formatInvDisplayAmount(inv) }})
                </option>
              </select>
            </div>
            <div class="form-group" v-if="selectedInvestmentForDecrease">
              <label>当前持仓</label>
              <div class="info-text">{{ formatInvDisplayAmount(selectedInvestmentForDecrease) }}</div>
            </div>
            <div class="form-group">
              <label>减持金额 ({{ getInvestmentCurrency(createForm.investment_id) !== 'CNY' ? getInvestmentCurrency(createForm.investment_id) : '元' }})</label>
              <input v-model.number="createForm.amount" type="number" step="0.01" placeholder="请输入减持金额" 
                :max="getInvestmentCurrency(createForm.investment_id) !== 'CNY' ? getInvestmentForeignAmount(createForm.investment_id) : (selectedInvestmentForDecrease?.current_principal || selectedInvestmentForDecrease?.principal)">
              <div class="hint-text">减持将返还资金到家庭余额，并减少您的权益贡献</div>
            </div>
            <div class="form-group">
              <label>减持日期</label>
              <input v-model="createForm.operation_date" type="date">
            </div>
            <div class="form-group">
              <label>备注 (可选)</label>
              <textarea v-model="createForm.note" placeholder="备注说明"></textarea>
            </div>
          </template>

          <!-- 删除投资表单 -->
          <template v-if="createForm.type === 'investment_delete'">
            <div class="form-group">
              <label>理财产品</label>
              <select v-model="createForm.investment_id">
                <option v-for="inv in investments" :key="inv.id" :value="inv.id">
                  {{ inv.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>删除原因 (可选)</label>
              <textarea v-model="createForm.reason" placeholder="请说明删除理由"></textarea>
              <div class="hint-text">此操作为软删除，历史数据将保留用于分红计算</div>
            </div>
          </template>

          <!-- 大额支出表单 -->
          <template v-if="createForm.type === 'expense'">
            <div class="form-group">
              <label>支出标题</label>
              <input v-model="createForm.expense_title" type="text" placeholder="请输入支出标题，如：购买设备">
            </div>
            <div class="form-group">
              <label>支出金额 (元)</label>
              <input v-model.number="createForm.amount" type="number" min="0" step="0.01" placeholder="请输入支出金额">
            </div>
            <div class="form-group">
              <label>支出原因</label>
              <textarea v-model="createForm.expense_reason" placeholder="请详细说明支出原因"></textarea>
            </div>
            <!-- 图片识别上传 -->
            <div class="form-group">
              <label>上传凭证图片 (可选)</label>
              <div class="image-upload-section">
                <input 
                  ref="imageInputRef" 
                  type="file" 
                  accept="image/*" 
                  style="display: none" 
                  @change="handleImageSelected"
                  aria-label="选择凭证图片文件"
                />
                <button 
                  @click="triggerImageUpload" 
                  class="btn-image-upload"
                  type="button"
                  :disabled="imageParsing"
                >
                  📷 {{ imageParsing ? '识别中...' : '导入图片识别' }}
                </button>
                <div v-if="imagePreview" class="image-preview">
                  <img :src="imagePreview" alt="上传的凭证图片预览" />
                  <button @click="clearImage" class="btn-clear-image" type="button" aria-label="清除图片">✕</button>
                </div>
                <div v-if="imageParseSuccess" class="parse-success">✓ {{ imageParseSuccess }}</div>
                <div v-if="imageParseError" class="parse-error">⚠ {{ imageParseError }}</div>
              </div>
            </div>
            <div class="form-group">
              <label>各成员扣减比例 (%)</label>
              <div class="ratio-list">
                <div v-for="(item, index) in createForm.deduction_ratios" :key="item.user_id" class="ratio-input-item">
                  <span class="member-name">{{ getMemberNickname(item.user_id) }}</span>
                  <input 
                    :value="item.ratio"
                    @input="handleRatioChange(index, $event)"
                    type="number" 
                    min="0" 
                    max="100" 
                    step="1"
                    class="ratio-input"
                    :disabled="isSingleMember"
                  >
                  <span class="ratio-unit">%</span>
                </div>
              </div>
              <div class="ratio-summary" :class="{ valid: expenseTotalRatio === 100 }">
                合计: {{ expenseTotalRatio }}% ✓
              </div>
            </div>
          </template>
        </div>
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn-secondary">取消</button>
          <button @click="submitCreate" class="btn-primary" :disabled="submitting">
            {{ submitting ? '提交中...' : '提交申请' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, h, watch } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { api, approvalApi, investmentApi, familyApi, transactionApi, assetApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useApprovalStore } from '@/stores/approval'
import { checkAndShowAchievements } from '@/utils/achievement'
import UserAvatar from '@/components/UserAvatar.vue'
import TimeRangeSelector from '@/components/TimeRangeSelector.vue'

const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()
const approvalStore = useApprovalStore()
const currentUserId = computed(() => userStore.user?.id)

const loading = ref(false)
const submitting = ref(false)
const showCreateModal = ref(false)
const filterType = ref('')
const filterStatus = ref('')
const timeRange = ref('month')
const processingApprovalId = ref<number | null>(null)  // 防重复点击：当前正在处理的审批ID
const remindingId = ref<number | null>(null)  // 催促中的申请ID

interface ApprovalRecord {
  id: number
  request_id: number
  approver_id: number
  approver_nickname: string
  approver_avatar?: string
  is_approved: boolean
  comment?: string
  created_at: string
}

interface ApprovalItem {
  id: number
  family_id: number
  requester_id: number
  requester_nickname: string
  requester_avatar?: string
  requester_avatar_version?: number
  target_user_id?: number  // 目标用户ID（个人专属审核）
  target_user_nickname?: string  // 目标用户昵称
  target_user_avatar_version?: number  // 目标用户头像版本号
  request_type: string
  title: string
  description: string
  amount: number
  request_data: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
  executed_at?: string
  execution_failed: boolean
  failure_reason?: string
  approvals: ApprovalRecord[]
  pending_approvers: number[]
  total_members: number
  approved_count: number
  rejected_count: number
}

interface ApprovalListResponse {
  total: number
  pending_count: number
  approved_count: number
  rejected_count: number
  items: ApprovalItem[]
}

interface Investment {
  id: number
  name: string
  principal: number
  current_principal?: number
  total_income?: number
}

const approvalList = ref<ApprovalListResponse | null>(null)
const pendingApprovals = ref<ApprovalItem[]>([])
const investments = ref<Investment[]>([])
const balance = ref(0) // 当前家庭余额

const requestTypes = [
  { value: 'deposit', label: '资金注入', icon: '💰' },
  { value: 'expense', label: '大额支出', icon: '💸' }
  // 理财相关操作已移至理财管理模块
]

interface FamilyMember {
  user_id: number
  nickname: string
}

const familyMembers = ref<FamilyMember[]>([])

const createForm = ref({
  type: 'deposit',
  amount: 0,
  deposit_date: new Date().toISOString().split('T')[0],
  note: '',
  name: '',
  investment_type: 'fund',
  principal: 0,
  currency: 'CNY',  // 多币种支持
  foreign_amount: null as number | null,  // 外币金额
  start_date: new Date().toISOString().split('T')[0],
  end_date: '',
  deduct_from_cash: false,  // 新增：是否从家庭自由资金扣除
  investment_id: 0,
  income_date: new Date().toISOString().split('T')[0],
  current_value: 0, // 用于更新价值
  operation_date: new Date().toISOString().split('T')[0], // 用于增持/减持
  reason: '', // 用于删除投资
  // 支出申请字段
  expense_title: '',
  expense_reason: '',
  deduction_ratios: [] as Array<{ user_id: number; ratio: number }>
})

// 多币种相关
const currencyOptions = [
  { value: 'CNY', label: '人民币 CNY' },
  { value: 'USD', label: '美元 USD' },
  { value: 'HKD', label: '港币 HKD' },
  { value: 'JPY', label: '日元 JPY' },
  { value: 'EUR', label: '欧元 EUR' },
  { value: 'GBP', label: '英镑 GBP' },
  { value: 'AUD', label: '澳元 AUD' },
  { value: 'CAD', label: '加元 CAD' },
  { value: 'SGD', label: '新币 SGD' },
  { value: 'KRW', label: '韩元 KRW' }
]
const currencySymbols: Record<string, string> = {
  CNY: '¥', USD: '$', HKD: 'HK$', JPY: '¥', EUR: '€',
  GBP: '£', AUD: 'A$', CAD: 'C$', SGD: 'S$', KRW: '₩'
}
const getCurrencySymbol = (c: string) => currencySymbols[c] || c
const currentExchangeRate = ref<number | null>(null)
const exchangeRateLoading = ref(false)

const handleCurrencyChange = async () => {
  const currency = createForm.value.currency
  if (currency !== 'CNY') {
    exchangeRateLoading.value = true
    try {
      const { data } = await assetApi.getExchangeRate(currency)
      currentExchangeRate.value = data.rate
    } catch (e) {
      console.error('Failed to fetch exchange rate:', e)
      currentExchangeRate.value = null
    } finally {
      exchangeRateLoading.value = false
    }
  } else {
    currentExchangeRate.value = null
    createForm.value.foreign_amount = null
  }
}

// ==================== 图片识别功能 ====================
// Note: imageInputRef is shared between deposit and expense forms
// This is safe because only one form type is rendered at a time (v-if conditional)
const imageInputRef = ref<HTMLInputElement | null>(null)
const imageParsing = ref(false)
const imagePreview = ref('')
const imageParseError = ref('')
const imageParseSuccess = ref('')

const triggerImageUpload = () => {
  imageInputRef.value?.click()
}

const clearImage = () => {
  imagePreview.value = ''
  imageParseError.value = ''
  imageParseSuccess.value = ''
  imageParsing.value = false  // Reset parsing state
  if (imageInputRef.value) {
    imageInputRef.value.value = ''
  }
}

const handleImageSelected = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  
  if (!file) return
  
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    imageParseError.value = '请上传图片文件'
    return
  }
  
  // 验证文件大小（最大20MB）
  if (file.size > 20 * 1024 * 1024) {
    imageParseError.value = '图片大小不能超过 20MB'
    return
  }
  
  // 清空之前的状态
  imageParseError.value = ''
  imageParseSuccess.value = ''
  
  try {
    // 读取图片为 Base64
    const reader = new FileReader()
    reader.onload = async (e) => {
      const base64 = e.target?.result as string
      imagePreview.value = base64
      
      // 开始解析
      imageParsing.value = true
      try {
        const { data } = await assetApi.parseImage(base64)
        
        if (data.success) {
          const parsed = data.data
          
          // 根据表单类型自动填充
          if (createForm.value.type === 'deposit') {
            if (parsed.amount) createForm.value.amount = parsed.amount
            if (parsed.start_date) createForm.value.deposit_date = parsed.start_date
            // Prefer parsed.note, fallback to parsed.name
            createForm.value.note = parsed.note || parsed.name || ''
          } else if (createForm.value.type === 'expense') {
            if (parsed.amount) createForm.value.amount = parsed.amount
            if (parsed.name) createForm.value.expense_title = parsed.name
            if (parsed.note) createForm.value.expense_reason = parsed.note
          }
          
          imageParseSuccess.value = '识别成功！已自动填充表单'
          message.success('图片识别成功，已自动填充表单')
        } else {
          imageParseError.value = data.error || '图片识别失败'
          message.warning('图片识别失败，请手动填写')
        }
      } catch (error: any) {
        console.error('图片解析失败:', error)
        imageParseError.value = error.response?.data?.detail || '图片解析失败，请重试'
        message.error('图片解析失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        imageParsing.value = false
      }
    }
    reader.readAsDataURL(file)
  } catch (error) {
    console.error('读取图片失败:', error)
    imageParseError.value = '读取图片失败'
  }
}

// 监听表单类型变化，清空图片状态
watch(() => createForm.value.type, () => {
  clearImage()
})


const equivalentCNY = computed(() => {
  if (createForm.value.currency === 'CNY') return null
  if (!createForm.value.foreign_amount || !currentExchangeRate.value) return null
  return Number((createForm.value.foreign_amount * currentExchangeRate.value).toFixed(2))
})

// 获取投资的币种信息
const getInvestmentCurrency = (investmentId: number) => {
  const inv = investments.value.find(i => i.id === investmentId)
  return (inv as any)?.currency || 'CNY'
}
const getInvestmentForeignAmount = (investmentId: number) => {
  const inv = investments.value.find(i => i.id === investmentId)
  return (inv as any)?.current_foreign_amount || 0
}
const formatInvDisplayAmount = (inv: any) => {
  const currency = inv?.currency || 'CNY'
  if (currency === 'CNY') return `¥${formatAmount(inv?.current_principal || inv?.principal || 0)}`
  const symbol = getCurrencySymbol(currency)
  const foreignAmt = inv?.current_foreign_amount || inv?.foreign_amount || 0
  return `${symbol}${formatAmount(foreignAmt)} (≈¥${formatAmount(inv?.current_principal || inv?.principal || 0)})`
}

// 用于收益计算的选中投资
const selectedInvestmentForIncome = ref<Investment | null>(null)
const selectedInvestmentForDecrease = ref<Investment | null>(null)

// 计算支出扣减比例总和
const expenseTotalRatio = computed(() => {
  return createForm.value.deduction_ratios.reduce((sum, r) => sum + r.ratio, 0)
})

// 判断是否只有单个成员
const isSingleMember = computed(() => {
  return createForm.value.deduction_ratios.length <= 1
})

// 处理比例变化 - 联动调整其他成员的比例
const handleRatioChange = (changedIndex: number, event: Event) => {
  const input = event.target as HTMLInputElement
  let newValue = parseInt(input.value) || 0
  
  // 限制范围 0-100
  newValue = Math.max(0, Math.min(100, newValue))
  
  const ratios = createForm.value.deduction_ratios
  const memberCount = ratios.length
  
  // 单成员时固定100%
  if (memberCount <= 1) {
    ratios[0].ratio = 100
    return
  }
  
  // 计算当前成员之外的其他成员总比例
  const otherIndices = ratios.map((_, i) => i).filter(i => i !== changedIndex)
  const oldOtherTotal = otherIndices.reduce((sum, i) => sum + ratios[i].ratio, 0)
  
  // 计算剩余需要分配给其他成员的比例
  const remainingForOthers = 100 - newValue
  
  // 设置当前成员的新值
  ratios[changedIndex].ratio = newValue
  
  if (remainingForOthers <= 0) {
    // 如果当前成员占了100%或更多，其他成员都设为0
    otherIndices.forEach(i => {
      ratios[i].ratio = 0
    })
  } else if (oldOtherTotal === 0) {
    // 如果其他成员原来总和为0，平均分配剩余比例
    const avgRatio = Math.floor(remainingForOthers / otherIndices.length)
    const remainder = remainingForOthers - avgRatio * otherIndices.length
    otherIndices.forEach((idx, i) => {
      ratios[idx].ratio = avgRatio + (i === 0 ? remainder : 0)
    })
  } else {
    // 按比例调整其他成员
    let distributed = 0
    otherIndices.forEach((idx, i) => {
      if (i === otherIndices.length - 1) {
        // 最后一个成员获得剩余的所有比例（避免四舍五入误差）
        ratios[idx].ratio = remainingForOthers - distributed
      } else {
        const proportion = ratios[idx].ratio / oldOtherTotal
        const newRatio = Math.round(remainingForOthers * proportion)
        ratios[idx].ratio = Math.max(0, Math.min(100, newRatio))
        distributed += ratios[idx].ratio
      }
    })
  }
  
  // 确保每个比例都在有效范围内
  ratios.forEach(r => {
    r.ratio = Math.max(0, Math.min(100, r.ratio))
  })
}

// 初始化支出扣减比例（平均分配）
const initDeductionRatios = () => {
  if (familyMembers.value.length > 0) {
    const avgRatio = Math.floor(100 / familyMembers.value.length)
    const remainder = 100 - avgRatio * familyMembers.value.length
    createForm.value.deduction_ratios = familyMembers.value.map((m, index) => ({
      user_id: m.user_id,
      ratio: avgRatio + (index === 0 ? remainder : 0)
    }))
  }
}

// 获取成员昵称
const getMemberNickname = (userId: number): string => {
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || `用户${userId}`
}

const loadApprovals = async () => {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (filterType.value) params.request_type = filterType.value
    if (filterStatus.value) params.status = filterStatus.value
    params.time_range = timeRange.value
    
    const response = await approvalApi.list(params)
    approvalList.value = response.data
  } catch (error) {
    console.error('加载申请列表失败:', error)
  } finally {
    loading.value = false
  }
}

const loadPendingApprovals = async () => {
  try {
    const response = await approvalApi.getPending()
    pendingApprovals.value = response.data
  } catch (error) {
    console.error('加载待审批列表失败:', error)
  }
}

const loadInvestments = async () => {
  try {
    const response = await investmentApi.list()
    investments.value = response.data
  } catch (error) {
    console.error('加载理财产品列表失败:', error)
  }
}

// 加载当前余额
const loadBalance = async () => {
  try {
    const response = await transactionApi.list({ time_range: 'all' })
    if (response.data && response.data.length > 0) {
      // 取第一条记录的余额（已按created_at desc排序）
      balance.value = response.data[0].balance_after || 0
    }
  } catch (error) {
    console.error('加载余额失败:', error)
  }
}

// 打开创建申请模态框
const openCreateModal = async () => {
  await Promise.all([loadInvestments(), loadBalance()])
  // 清空图片上传状态
  clearImage()
  showCreateModal.value = true
}

// 选择投资产品时更新选中状态（用于收益计算）
const onInvestmentChange = () => {
  const inv = investments.value.find(i => i.id === createForm.value.investment_id)
  selectedInvestmentForIncome.value = inv || null
}

// 选择投资产品时更新选中状态（用于减持验证）
const onInvestmentChangeForDecrease = () => {
  const inv = investments.value.find(i => i.id === createForm.value.investment_id)
  selectedInvestmentForDecrease.value = inv || null
}

// 计算收益（当前价值 - 持仓本金 - 历史收益）
const calculateIncome = (): number => {
  if (!selectedInvestmentForIncome.value || !createForm.value.current_value) {
    return 0
  }
  const inv = selectedInvestmentForIncome.value as any
  const isForeign = inv.currency && inv.currency !== 'CNY'
  // 外币投资用外币持仓计算，人民币用CNY持仓
  const currentPrincipal = isForeign
    ? (inv.current_foreign_amount || inv.foreign_amount || 0)
    : (inv.current_principal || inv.principal || 0)
  const historicalIncome = inv.total_income || 0
  return createForm.value.current_value - currentPrincipal - historicalIncome
}

const loadFamilyMembers = async () => {
  try {
    const response = await familyApi.getMy()
    // /family/my 返回的数据中包含 members 数组
    familyMembers.value = response.data.members || []
    // 初始化支出扣减比例
    initDeductionRatios()
  } catch (error) {
    console.error('加载家庭成员失败:', error)
  }
}

const handleApprove = async (id: number, isApproved: boolean) => {
  // 防重复点击：如果正在处理则返回
  if (processingApprovalId.value !== null) {
    return
  }
  
  // 拒绝时需要输入原因
  if (!isApproved) {
    dialog.create({
      title: '拒绝原因',
      content: () => h('input', {
        type: 'text',
        placeholder: '请输入拒绝原因（可选）',
        id: 'reject-reason-input',
        style: { width: '100%', padding: '8px', border: '1px solid #e5e7eb', borderRadius: '4px' }
      }),
      positiveText: '确认拒绝',
      negativeText: '取消',
      onPositiveClick: async () => {
        const reason = (document.getElementById('reject-reason-input') as HTMLInputElement)?.value || ''
        await doApproval(id, false, reason)
      }
    })
    return
  }
  
  await doApproval(id, true, '')
}

const doApproval = async (id: number, isApproved: boolean, reason: string) => {
  processingApprovalId.value = id
  
  try {
    if (isApproved) {
      await approvalApi.approve(id)
    } else {
      await approvalApi.reject(id, reason)
    }
    message.success(isApproved ? '已同意该申请' : '已拒绝该申请')
    loadApprovals()
    loadPendingApprovals()

    // 立即刷新审批红点（使用refreshNow代替fetchPendingCount）
    await approvalStore.refreshNow()

    // 审批通过后检查成就
    if (isApproved) {
      setTimeout(() => checkAndShowAchievements(), 500)
    }
  } catch (error: unknown) {
    const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '审批失败'
    message.error(errMsg)
  } finally {
    processingApprovalId.value = null
  }
}

// 处理分红领取（特殊审批）
const handleDividendClaim = async (id: number, reinvest: boolean) => {
  if (processingApprovalId.value !== null) {
    return
  }
  
  processingApprovalId.value = id
  
  try {
    await api.post(`/approval/${id}/dividend-claim`, {
      reinvest: reinvest
    })
    message.success(reinvest ? '已选择红利再投' : '已选择提现')
    loadApprovals()
    loadPendingApprovals()
    
    // 刷新导航徽章计数
    await approvalStore.fetchPendingCount()
  } catch (error: unknown) {
    const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '处理失败'
    message.error(errMsg)
  } finally {
    processingApprovalId.value = null
  }
}

const handleCancel = async (id: number) => {
  dialog.warning({
    title: '确认取消',
    content: '确定要取消这个申请吗？',
    positiveText: '确认取消',
    negativeText: '返回',
    onPositiveClick: async () => {
      try {
        await approvalApi.cancel(id)
        message.success('申请已取消')
        loadApprovals()
      } catch (error: unknown) {
        const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '取消失败'
        message.error(errMsg)
      }
    }
  })
}

const handleRemind = async (id: number) => {
  if (remindingId.value !== null) return
  
  remindingId.value = id
  try {
    const response = await approvalApi.remind(id)
    if (response.data.success) {
      message.success('催促通知已发送到企业微信')
    } else {
      message.warning(response.data.message || '发送失败')
    }
  } catch (error: unknown) {
    const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '催促失败'
    message.error(errMsg)
  } finally {
    remindingId.value = null
  }
}

const handleRetry = async (id: number) => {
  dialog.warning({
    title: '确认重试',
    content: '确定要重试执行这个失败的申请吗？',
    positiveText: '确认重试',
    negativeText: '返回',
    onPositiveClick: async () => {
      processingApprovalId.value = id
      try {
        await approvalApi.retry(id)
        message.success('已重试执行申请，请稍候...')
        loadApprovals()
      } catch (error: unknown) {
        const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '重试失败'
        message.error(errMsg)
      } finally {
        processingApprovalId.value = null
      }
    }
  })
}

const submitCreate = async () => {
  submitting.value = true
  try {
    if (createForm.value.type === 'deposit') {
      await approvalApi.createDeposit({
        amount: createForm.value.amount,
        deposit_date: createForm.value.deposit_date,
        note: createForm.value.note || undefined
      })
    } else if (createForm.value.type === 'investment_create') {
      const isForeign = createForm.value.currency !== 'CNY'
      const hasAmount = isForeign ? createForm.value.foreign_amount : createForm.value.principal
      if (!hasAmount || hasAmount <= 0) {
        message.warning(isForeign ? '请输入有效的外币金额' : '请输入有效的本金')
        submitting.value = false
        return
      }
      
      // 计算CNY等值（外币需要换算）
      let cnyAmount = createForm.value.principal || 0
      if (isForeign && currentExchangeRate.value && createForm.value.foreign_amount) {
        cnyAmount = Math.round(createForm.value.foreign_amount * currentExchangeRate.value * 100) / 100
      }
      
      // 检查是否需要从自由资金扣除，如果是则检查余额
      if (createForm.value.deduct_from_cash) {
        const currentBalance = balance.value || 0
        if (currentBalance < cnyAmount) {
          message.error(`家庭自由资金不足：需要¥${cnyAmount.toFixed(2)}，当前仅有¥${currentBalance.toFixed(2)}`)
          submitting.value = false
          return
        }
      }
      
      await approvalApi.createInvestment({
        name: createForm.value.name,
        investment_type: createForm.value.investment_type,
        currency: createForm.value.currency,
        principal: isForeign ? undefined : createForm.value.principal,
        foreign_amount: isForeign ? createForm.value.foreign_amount! : undefined,
        start_date: createForm.value.start_date,
        end_date: createForm.value.end_date || undefined,
        deduct_from_cash: createForm.value.deduct_from_cash,
        note: createForm.value.note || undefined
      })
    } else if (createForm.value.type === 'investment_income') {
      // 使用current_value模式
      if (!createForm.value.current_value || createForm.value.current_value <= 0) {
        message.warning('请输入有效的当前总价值')
        submitting.value = false
        return
      }
      await approvalApi.createInvestmentIncome({
        investment_id: createForm.value.investment_id,
        current_value: createForm.value.current_value,
        income_date: createForm.value.income_date,
        note: createForm.value.note || undefined
      })
    } else if (createForm.value.type === 'investment_increase') {
      if (!createForm.value.amount || createForm.value.amount <= 0) {
        message.warning('请输入有效的增持金额')
        submitting.value = false
        return
      }
      // 只有从自由资金扣除时才检查余额
      if (createForm.value.deduct_from_cash && createForm.value.amount > balance.value) {
        message.warning(`增持金额不能超过当前余额 ¥${formatAmount(balance.value)}`)
        submitting.value = false
        return
      }
      const incCurrency = getInvestmentCurrency(createForm.value.investment_id)
      const isForeignInc = incCurrency !== 'CNY'
      await approvalApi.increaseInvestment({
        investment_id: createForm.value.investment_id,
        amount: createForm.value.amount,
        foreign_amount: isForeignInc ? createForm.value.amount : undefined,
        operation_date: createForm.value.operation_date,
        note: createForm.value.note || undefined,
        deduct_from_cash: createForm.value.deduct_from_cash
      })
    } else if (createForm.value.type === 'investment_decrease') {
      if (!createForm.value.amount || createForm.value.amount <= 0) {
        message.warning('请输入有效的减持金额')
        submitting.value = false
        return
      }
      const decCurrency = getInvestmentCurrency(createForm.value.investment_id)
      const isForeignDec = decCurrency !== 'CNY'
      const selectedInv = selectedInvestmentForDecrease.value as any
      const maxAmount = isForeignDec 
        ? (selectedInv?.current_foreign_amount || selectedInv?.foreign_amount || 0) 
        : (selectedInv?.current_principal || selectedInv?.principal || 0)
      if (createForm.value.amount > maxAmount) {
        const sym = getCurrencySymbol(decCurrency)
        message.warning(`减持金额不能超过当前持仓 ${sym}${formatAmount(maxAmount)}`)
        submitting.value = false
        return
      }
      await approvalApi.decreaseInvestment({
        investment_id: createForm.value.investment_id,
        amount: createForm.value.amount,
        foreign_amount: isForeignDec ? createForm.value.amount : undefined,
        operation_date: createForm.value.operation_date,
        note: createForm.value.note || undefined
      })
    } else if (createForm.value.type === 'investment_delete') {
      await approvalApi.deleteInvestment({
        investment_id: createForm.value.investment_id,
        reason: createForm.value.reason || undefined
      })
    } else if (createForm.value.type === 'expense') {
      // 验证扣减比例
      if (expenseTotalRatio.value !== 100) {
        message.warning('扣减比例合计必须等于100%')
        submitting.value = false
        return
      }
      if (!createForm.value.expense_title.trim()) {
        message.warning('请输入支出标题')
        submitting.value = false
        return
      }
      if (createForm.value.amount <= 0) {
        message.warning('请输入有效的支出金额')
        submitting.value = false
        return
      }
      if (!createForm.value.expense_reason.trim()) {
        message.warning('请输入支出原因')
        submitting.value = false
        return
      }
      
      // 转换 deduction_ratios 为数组格式 [{ user_id, ratio }]，比例转换为 0-1
      const deductionRatios = createForm.value.deduction_ratios.map(r => ({
        user_id: r.user_id,
        ratio: r.ratio / 100  // 百分比转换为 0-1 小数
      }))
      
      await approvalApi.createExpense({
        title: createForm.value.expense_title,
        amount: createForm.value.amount,
        reason: createForm.value.expense_reason,
        deduction_ratios: deductionRatios
      })
    }
    
    message.success('申请已提交，等待家庭成员审批')
    showCreateModal.value = false
    resetForm()
    loadApprovals()
    loadPendingApprovals()
  } catch (error: unknown) {
    const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '提交失败'
    message.error(errMsg)
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  createForm.value = {
    type: 'deposit',
    amount: 0,
    deposit_date: new Date().toISOString().split('T')[0],
    note: '',
    name: '',
    investment_type: 'fund',
    principal: 0,
    currency: 'CNY',
    foreign_amount: null as number | null,
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    deduct_from_cash: false,
    investment_id: 0,
    income_date: new Date().toISOString().split('T')[0],
    current_value: 0,
    operation_date: new Date().toISOString().split('T')[0],
    reason: '',
    expense_title: '',
    expense_reason: '',
    deduction_ratios: [] as Array<{ user_id: number; ratio: number }>
  }
  // 重置选中的投资
  selectedInvestmentForIncome.value = null
  selectedInvestmentForDecrease.value = null
  // 重新初始化支出扣减比例
  initDeductionRatios()
  // 清空图片上传状态
  clearImage()
}

const formatAmount = (amount: number) => {
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    deposit: '资金注入',
    asset_create: '资产登记',
    investment_create: '创建理财',
    investment_update: '更新理财',
    investment_income: '更新价值',
    investment_increase: '投资增持',
    investment_decrease: '投资减持',
    investment_delete: '删除投资',
    expense: '大额支出',
    dividend_claim: '分红领取',
    member_join: '成员加入',
    member_remove: '成员剔除'
  }
  return labels[type] || type
}

const getTypeClass = (type: string) => {
  const classes: Record<string, string> = {
    deposit: 'type-deposit',
    asset_create: 'type-investment',
    investment_create: 'type-investment',
    investment_update: 'type-investment',
    investment_income: 'type-income',
    investment_increase: 'type-investment',
    investment_decrease: 'type-expense',
    investment_delete: 'type-member-remove',
    expense: 'type-expense',
    dividend_claim: 'type-income',
    member_join: 'type-member-join',
    member_remove: 'type-member-remove'
  }
  return classes[type] || ''
}

// 判断是否是成员相关的申请类型（不显示金额）
const isMemberRequest = (type: string) => {
  return ['member_join', 'member_remove'].includes(type)
}

// 获取成员昵称
const getMemberName = (userId: number) => {
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || '未知成员'
}

// 将 deduction_ratios 对象格式转换为数组格式
// 后端存储格式: { "user_id": ratio, ... } 例如 { "1": 0.5, "2": 0.5 }
// 前端期望格式: [{ user_id: 1, ratio: 0.5 }, { user_id: 2, ratio: 0.5 }]
const getDeductionRatiosArray = (deductionRatios: Record<string, number> | undefined) => {
  if (!deductionRatios || typeof deductionRatios !== 'object') {
    return []
  }
  return Object.entries(deductionRatios).map(([userId, ratio]) => ({
    user_id: parseInt(userId),
    ratio: Number(ratio)
  }))
}

// 获取审批进度的描述文本
const getProgressText = (item: ApprovalItem) => {
  if (item.request_type === 'member_join') {
    // 成员加入：任一成员同意即可
    return item.approved_count > 0 ? '已有成员同意' : '等待任一成员同意'
  } else if (item.request_type === 'member_remove') {
    // 成员剔除：需要管理员同意
    return item.approved_count > 0 ? '管理员已同意' : '等待管理员同意'
  } else {
    // 资金相关：全体成员同意
    return `${item.approved_count} / ${Math.max(item.total_members - 1, 1)} 已同意`
  }
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已拒绝',
    cancelled: '已取消'
  }
  return labels[status] || status
}

const getProgressWidth = (item: ApprovalItem) => {
  const required = Math.max(item.total_members - 1, 1)
  return `${(item.approved_count / required) * 100}%`
}

onMounted(() => {
  loadApprovals()
  loadPendingApprovals()
  loadInvestments()
  loadFamilyMembers()
})
</script>

<style scoped>
.approval-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin: 0 0 8px 0;
}

.subtitle {
  color: var(--theme-text-secondary);
  margin: 0;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--theme-bg-card);
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
}

.stat-icon {
  font-size: 32px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
}

.stat-label {
  font-size: 14px;
  color: var(--theme-text-secondary);
}

.stat-card.pending { border-left: 4px solid var(--theme-warning); }
.stat-card.approved { border-left: 4px solid var(--theme-success); }
.stat-card.rejected { border-left: 4px solid var(--theme-error); }
.stat-card.total { border-left: 4px solid var(--theme-info); }

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.filters {
  display: flex;
  gap: 12px;
}

.filter-select {
  padding: 10px 16px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--theme-bg-card);
  color: var(--theme-text-primary);
  cursor: pointer;
}

.btn-primary {
  padding: 12px 24px;
  background: var(--theme-warning);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 待审批区域 */
.pending-section {
  background: var(--theme-warning-bg);
  padding: 24px;
  border-radius: 16px;
  margin-bottom: 32px;
}

.pending-section h2 {
  margin: 0 0 16px 0;
  font-size: 20px;
}

/* 申请卡片 */
.approval-cards {
  display: grid;
  gap: 16px;
}

.approval-card {
  background: var(--theme-bg-card);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
}

.pending-card {
  border: 2px solid var(--theme-warning);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-remind-small {
  padding: 4px 10px;
  background: var(--theme-warning, #f59e0b);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-remind-small:hover {
  background: #d97706;
  transform: scale(1.02);
}

.btn-remind-small:disabled {
  background: #fcd34d;
  cursor: not-allowed;
  opacity: 0.8;
}

.type-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.type-deposit { background: var(--theme-info-bg, #dbeafe); color: var(--theme-info, #1d4ed8); }
.type-investment { background: var(--theme-success-bg, #dcfce7); color: var(--theme-success, #16a34a); }
.type-income { background: var(--theme-warning-bg, #fef3c7); color: var(--theme-warning, #d97706); }
.type-expense { background: var(--theme-error-bg, #fee2e2); color: var(--theme-error, #dc2626); }
.type-member-join { background: var(--theme-info-bg, #e0e7ff); color: var(--theme-purple, #4f46e5); }
.type-member-remove { background: var(--theme-error-bg, #fce7f3); color: var(--theme-error, #db2777); }

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.pending { background: var(--theme-warning-bg, #fef3c7); color: var(--theme-warning, #d97706); }
.status-badge.approved { background: var(--theme-success-bg, #dcfce7); color: var(--theme-success, #16a34a); }
.status-badge.rejected { background: var(--theme-error-bg, #fee2e2); color: var(--theme-error, #dc2626); }
.status-badge.cancelled { background: var(--theme-bg-secondary, #f3f4f6); color: var(--theme-text-secondary, #6b7280); }
.status-badge.failed { background: var(--theme-warning-bg, #fef3c7); color: var(--theme-warning, #d97706); border: 1px solid var(--theme-warning, #f59e0b); }

.card-body h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
}

.description {
  color: var(--theme-text-secondary);
  margin: 0 0 12px 0;
  font-size: 14px;
}

.meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--theme-text-tertiary, #888);
  margin-bottom: 12px;
}

/* 执行失败原因提示 */
.failure-reason {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 16px;
  background: var(--theme-warning-bg, linear-gradient(135deg, #fef3c7, #fed7aa));
  border-left: 4px solid var(--theme-warning, #f59e0b);
  border-radius: 8px;
  margin-bottom: 12px;
}

.failure-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}

.failure-text {
  font-size: 14px;
  color: var(--theme-warning, #92400e);
  font-weight: 500;
  line-height: 1.4;
}

/* 支付比例分配 - 桌面端卡片式布局 */
.payment-ratios {
  background: var(--theme-warning-bg, linear-gradient(135deg, #fef9e7, #fef3c7));
  border-radius: 16px;
  padding: 20px;
  margin: 16px 0;
  border: 1px solid var(--theme-border-light, rgba(251, 191, 36, 0.2));
}

.ratios-header {
  font-size: 14px;
  font-weight: 600;
  color: var(--theme-warning, #92400e);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ratios-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ratio-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  background: var(--theme-bg-card);
  padding: 14px 20px;
  border-radius: 10px;
  box-shadow: 0 1px 3px var(--theme-shadow-sm);
  border: 1px solid var(--theme-border-light);
}

.ratio-item:hover {
  background: var(--theme-bg-secondary);
}

.member-info {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.member-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--theme-text-primary, #374151);
}

/* 桌面端：比例和金额组合靠右 */
.ratio-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.bar-bg {
  display: none;
}

.bar-fill {
  display: none;
}

.ratio-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--theme-warning, #b45309);
  background: var(--theme-warning-bg, #fef3c7);
  padding: 4px 10px;
  border-radius: 6px;
  min-width: unset;
}

.amount-text {
  font-size: 15px;
  font-weight: 700;
  color: var(--theme-success, #16a34a);
  min-width: 90px;
  text-align: right;
}

/* 桌面端隐藏括号百分比 */
.ratio-suffix {
  display: none;
}

/* 移动端支付比例分配布局优化 - 单行紧凑式 */
@media (max-width: 767px) {
  .payment-ratios {
    padding: 10px;
  }

  .ratios-header {
    font-size: 12px;
    margin-bottom: 8px;
  }

  .ratios-list {
    gap: 6px;
  }

  .ratio-item {
    display: flex !important;
    flex-direction: row !important;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 16px !important;
  }

  .member-info {
    flex: 1;
    min-width: 0;
  }

  .member-name {
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* 移动端隐藏进度条（包含里面所有内容） */
  .ratio-bar.desktop-only {
    display: none !important;
  }

  /* 移动端显示括号百分比 */
  .ratio-suffix {
    display: inline;
    font-size: 12px;
    color: var(--theme-warning, #d97706);
    font-weight: 500;
  }

  .amount-text {
    font-size: 14px;
    min-width: unset;
    white-space: nowrap;
  }
}

.progress-bar {
  position: relative;
  height: 24px;
  background: var(--theme-bg-secondary, #f3f4f6);
  border-radius: 12px;
  overflow: hidden;
  margin-top: 12px;
}

.progress {
  height: 100%;
  background: linear-gradient(135deg, var(--theme-success, #10b981), var(--theme-success-light, #34d399));
  transition: width 0.3s ease;
}

.progress-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--theme-text-primary, #374151);
}

.approval-records {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--theme-border, #e5e7eb);
}

.record {
  display: flex;
  align-items: center;
  font-size: 13px;
  margin-bottom: 4px;
}

.record .approved { color: var(--theme-success, #16a34a); }
.record .rejected { color: var(--theme-error, #dc2626); }
.record .approver { font-weight: 600; margin-left: 4px; }
.record .comment { color: var(--theme-text-tertiary, #666); }

/* 申请人/审批人头像样式 */
.requester-info,
.approver-info {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.card-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--theme-border-light, #f3f4f6);
}

.btn-approve {
  flex: 1;
  padding: 12px;
  background: var(--theme-success, #10b981);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-approve:hover:not(:disabled) { background: #059669; }

.btn-approve:disabled,
.btn-reject:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-reject {
  flex: 1;
  padding: 12px;
  background: var(--theme-error, #ef4444);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-reject:hover { background: #dc2626; }

.btn-reinvest {
  flex: 1;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-reinvest:hover:not(:disabled) { 
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-reinvest:disabled,
.btn-withdraw:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-withdraw {
  flex: 1;
  padding: 12px;
  background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-withdraw:hover:not(:disabled) { 
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 193, 7, 0.4);
}

.btn-cancel {
  padding: 10px 20px;
  background: var(--theme-bg-secondary, #f3f4f6);
  color: var(--theme-text-primary, #374151);
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-cancel:hover { background: var(--theme-border, #e5e7eb); }

.btn-retry {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-retry:hover {
  background: #2563eb;
}

.btn-retry:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.btn-remind {
  padding: 6px 12px;
  background: #f59e0b;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-remind:hover { background: #d97706; }

.btn-remind:disabled {
  background: #fcd34d;
  cursor: not-allowed;
  opacity: 0.8;
}

/* 区块标题 */
.all-approvals h2 {
  margin: 0 0 16px 0;
  font-size: 20px;
}

.loading, .empty {
  text-align: center;
  padding: 48px;
  color: var(--theme-text-tertiary, #888);
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000; /* 高于底部导航栏 */
}

.modal-content {
  background: var(--theme-bg-primary);
  border-radius: 16px;
  width: 90%;
  max-width: 520px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--theme-border);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--theme-border);
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--theme-text-primary);
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--theme-bg-secondary);
  border-radius: 50%;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--theme-text-primary);
  transition: all 0.3s ease;
}

.close-btn:hover {
  background: var(--theme-border);
  transform: scale(1.1);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  font-size: 14px;
  color: var(--theme-text-primary);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
  background-color: var(--theme-bg-secondary);
  color: var(--theme-text-primary);
  transition: all 0.3s ease;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--theme-info);
  box-shadow: 0 0 0 2px rgba(50, 151, 211, 0.1);
}

.form-group textarea {
  min-height: 80px;
  resize: vertical;
}

.hint-text {
  font-size: 12px;
  color: var(--theme-text-tertiary);
  margin-top: 4px;
}

.hint-inline {
  font-size: 11px;
  color: var(--theme-text-tertiary);
  margin-left: 4px;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-label {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-label:hover {
  border-color: var(--theme-purple);
  background: var(--theme-bg-secondary);
}

.radio-label input[type="radio"] {
  margin-right: 8px;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.radio-label input[type="radio"]:checked + span {
  color: var(--theme-purple);
  font-weight: 600;
}

.info-text {
  padding: 8px 12px;
  background: var(--theme-bg-secondary, #f3f4f6);
  border-radius: 6px;
  font-size: 14px;
  color: var(--theme-text-primary, #374151);
  font-weight: 600;
}

.info-text.success {
  color: var(--theme-success, #10b981);
  background: var(--theme-success-bg, #d1fae5);
}

.info-text.error {
  color: var(--theme-error, #ef4444);
  background: var(--theme-error-bg, #fee2e2);
}

.type-selector {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.type-btn {
  padding: 10px 16px;
  border: 2px solid var(--theme-border);
  background: var(--theme-bg-secondary);
  color: var(--theme-text-primary);
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn.active {
  border-color: var(--theme-warning);
  background: rgba(245, 158, 11, 0.15);
  color: var(--theme-warning);
  font-weight: 600;
}

.type-btn:hover {
  border-color: var(--theme-warning);
  background: rgba(245, 158, 11, 0.08);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid var(--theme-border);
}

.btn-secondary {
  padding: 12px 24px;
  background: var(--theme-bg-secondary);
  color: var(--theme-text-primary);
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover { 
  background: var(--theme-border);
}

/* 支出比例列表（弹窗用） */
.ratio-list {
  background: var(--theme-bg-secondary, #f9fafb);
  border-radius: 8px;
  padding: 12px;
}

.ratio-list .ratio-input-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--theme-border, #e5e7eb);
}

.ratio-list .ratio-input-item:last-child {
  border-bottom: none;
}

.member-name {
  flex: 1;
  font-weight: 500;
  color: var(--theme-text-primary, #374151);
}

.ratio-input {
  width: 80px !important;
  padding: 8px 12px !important;
  text-align: center;
}

.ratio-unit {
  color: var(--theme-text-secondary, #666);
  font-size: 14px;
}

.ratio-summary {
  margin-top: 12px;
  padding: 10px;
  background: var(--theme-success-bg, #dcfce7);
  border-radius: 8px;
  text-align: center;
  font-weight: 600;
  color: var(--theme-success, #16a34a);
}

.ratio-summary.error {
  background: var(--theme-error-bg, #fee2e2);
  color: var(--theme-error, #dc2626);
}

/* 响应式 */
@media (max-width: 767px) {
  .approval-page {
    padding: 16px;
  }
  
  .page-header h1 {
    font-size: 22px;
  }
  
  .subtitle {
    font-size: 13px;
  }
  
  /* 统计卡片 2列 */
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }
  
  .stat-card {
    padding: 14px;
    gap: 12px;
  }
  
  .stat-icon {
    font-size: 24px;
  }
  
  .stat-value {
    font-size: 22px;
  }
  
  .stat-label {
    font-size: 12px;
  }
  
  /* 操作栏 */
  .action-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .filters {
    flex-direction: row;
    gap: 8px;
  }
  
  .filter-select {
    flex: 1;
    padding: 10px 12px;
    font-size: 13px;
  }
  
  .btn-primary {
    width: 100%;
    padding: 14px;
    font-size: 15px;
    min-height: 48px;
  }
  
  /* 待审批区域 */
  .pending-section {
    padding: 16px;
    margin-bottom: 20px;
    border-radius: 12px;
  }
  
  .pending-section h2 {
    font-size: 18px;
  }
  
  /* 卡片 */
  .approval-card {
    padding: 16px;
    border-radius: 10px;
  }
  
  .card-header {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .type-badge,
  .status-badge {
    font-size: 11px;
    padding: 3px 10px;
  }
  
  .card-body h3 {
    font-size: 16px;
  }
  
  .description {
    font-size: 13px;
  }
  
  .meta {
    flex-wrap: wrap;
    gap: 10px;
    font-size: 12px;
  }
  
  /* 按钮触控区域优化 */
  .card-actions {
    flex-direction: column;
    gap: 10px;
  }
  
  .btn-approve,
  .btn-reject {
    padding: 14px;
    font-size: 15px;
    min-height: 48px;
  }
  
  .btn-cancel {
    width: 100%;
    padding: 12px;
    min-height: 44px;
  }
  
  /* 弹窗移动端适配 - Bottom Sheet 样式 */
  .modal-overlay {
    align-items: flex-end; /* 底部对齐 */
  }
  
  .modal-content {
    width: 100%;
    max-width: 100%;
    height: auto;
    max-height: 85vh; /* 最多占屏幕85%，露出底部导航 */
    border-radius: 20px 20px 0 0; /* 只有顶部圆角 */
    animation: slideUp 0.3s ease-out;
  }
  
  @keyframes slideUp {
    from {
      transform: translateY(100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }
  
  .modal-header {
    padding: 16px;
    position: relative;
  }
  
  /* 添加顶部拖拽指示条 */
  .modal-header::before {
    content: '';
    position: absolute;
    top: 8px;
    left: 50%;
    transform: translateX(-50%);
    width: 36px;
    height: 4px;
    background: var(--theme-border, #d1d5db);
    border-radius: 2px;
  }
  
  .modal-header h2 {
    font-size: 18px;
    margin-top: 8px;
  }
  
  .modal-body {
    padding: 16px;
    max-height: calc(85vh - 140px); /* 预留 header 和 footer 空间 */
    overflow-y: auto;
  }
  
  .form-group input,
  .form-group select,
  .form-group textarea {
    padding: 14px 16px;
    font-size: 16px; /* 防止 iOS 放大 */
  }
  
  .type-selector {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }
  
  .type-btn {
    padding: 12px;
    font-size: 13px;
    text-align: center;
  }
  
  .modal-footer {
    padding: 16px;
    padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  }
  
  .btn-secondary {
    flex: 1;
    padding: 14px;
    min-height: 48px;
  }
  
  /* 比例输入（弹窗用） */
  .ratio-list .ratio-input-item {
    flex-wrap: wrap;
  }
  
  .ratio-input {
    width: 70px !important;
  }
  
  /* 区块标题 */
  .all-approvals h2 {
    font-size: 18px;
    margin-bottom: 12px;
  }
  
  .loading, .empty {
    padding: 32px;
  }
}

/* ==================== 图片上传样式 ==================== */
.image-upload-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-image-upload {
  padding: 10px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 200px;
}

.btn-image-upload:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-image-upload:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.image-preview {
  position: relative;
  max-width: 300px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.image-preview img {
  width: 100%;
  height: auto;
  display: block;
}

.btn-clear-image {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  background: rgba(255, 59, 48, 0.9);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.btn-clear-image:hover {
  background: rgba(255, 59, 48, 1);
  transform: scale(1.1);
}

.parse-success {
  padding: 10px 12px;
  background: var(--theme-success-bg, #d4edda);
  color: var(--theme-success, #155724);
  border: 1px solid var(--theme-success-light, #c3e6cb);
  border-radius: 6px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.parse-error {
  padding: 10px 12px;
  background: var(--theme-error-bg, #f8d7da);
  color: var(--theme-error, #721c24);
  border: 1px solid var(--theme-error-light, #f5c6cb);
  border-radius: 6px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
