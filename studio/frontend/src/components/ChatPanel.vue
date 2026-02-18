<template>
  <div style="display: flex; flex-direction: column; height: 100%; min-height: 400px">
    <!-- 项目信息栏 -->
    <div class="project-info-bar" @click="showProjectEdit = true">
      <n-ellipsis :line-clamp="1" :tooltip="false" style="flex: 1; min-width: 0">
        <span class="project-info-title">{{ props.project.title }}</span>
        <span v-if="props.project.description" class="project-info-sep">—</span>
        <span v-if="props.project.description" class="project-info-desc">{{ props.project.description }}</span>
        <span v-else class="project-info-desc" style="opacity: 0.35">点击添加需求描述...</span>
      </n-ellipsis>
      <span class="project-info-edit-icon">✏️</span>
    </div>

    <!-- 项目信息编辑弹窗 -->
    <n-modal v-model:show="showProjectEdit" preset="card" title="编辑项目信息" style="width: 520px; max-width: 90vw" :mask-closable="true">
      <n-form label-placement="top" :show-feedback="false">
        <n-form-item label="项目名称">
          <n-input v-model:value="editProjectTitle" placeholder="项目名称" />
        </n-form-item>
        <n-form-item label="需求描述" style="margin-top: 12px">
          <n-input v-model:value="editProjectDesc" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="详细描述你的需求..." />
        </n-form-item>
      </n-form>
      <n-text depth="3" style="font-size: 11px; display: block; margin-top: 8px">需求描述会注入到每次 AI 对话的上下文中</n-text>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px">
          <n-button @click="showProjectEdit = false">取消</n-button>
          <n-button type="primary" @click="saveProjectInfo" :loading="savingProject">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 中间区域: 消息 + 右侧 slot (设计稿) 并排 -->
    <div style="flex: 1; display: flex; overflow: hidden; min-height: 0">
      <!-- 消息列表 -->
      <div ref="messageListRef" style="flex: 1; overflow-y: auto; padding: 4px 0; min-width: 0">

      <!-- 空对话欢迎状态 -->
      <div v-if="!messages.length && !streaming" class="empty-chat-welcome">
        <div class="empty-chat-icon">{{ props.project.skill?.icon || '💬' }}</div>
        <div class="empty-chat-title">{{ props.project.skill?.name || '讨论' }}</div>
        <div class="empty-chat-desc">{{ props.project.title }}</div>
        <n-button
          type="primary"
          size="large"
          :loading="startingChat"
          :disabled="aiMuted"
          style="margin-top: 20px; border-radius: 20px; padding: 0 32px"
          @click="handleStartChat"
        >
          <template #icon><span style="font-size: 16px">✨</span></template>
          开始对话
        </n-button>
        <n-text v-if="aiMuted" depth="3" style="font-size: 12px; margin-top: 8px">AI 已禁言，请先解除禁言</n-text>
      </div>

      <div v-for="msg in messages" :key="msg.id" style="margin-bottom: 6px">
        <!-- 系统消息 (上下文总结) -->
        <div v-if="msg.role === 'system'" style="display: flex; justify-content: center">
          <n-card size="small" style="max-width: 90%; background: #1a2a3e; border: 1px dashed #f0a020; border-radius: 6px; --n-padding-top: 4px; --n-padding-bottom: 4px">
            <n-collapse>
              <n-collapse-item name="summary">
                <template #header>
                  <n-space align="center" :size="4">
                    <span style="font-size: 14px">📝</span>
                    <n-text style="color: #f0a020; font-size: 11px; font-weight: 500">
                      上下文自动总结
                    </n-text>
                    <n-text depth="3" style="font-size: 10px">{{ formatTime(msg.created_at) }}</n-text>
                  </n-space>
                </template>
                <div class="thinking-block" v-html="renderMarkdown(msg.content)" />
              </n-collapse-item>
            </n-collapse>
          </n-card>
        </div>

        <!-- ask_user 回答: 紧凑指示器 (不重复显示已在卡片中展示的内容) -->
        <div
          v-else-if="msg.role === 'user' && msg.content?.startsWith('<!-- ask_user_response -->')"
          style="display: flex; justify-content: flex-end"
          @mouseenter="hoveredMessageId = msg.id"
          @mouseleave="hoveredMessageId = null"
        >
          <div class="ask-user-reply-indicator">
            <span style="opacity: 0.5">💬</span>
            <span>已提交回答</span>
            <n-popover trigger="click" placement="bottom" style="max-width: 400px">
              <template #trigger>
                <span class="ask-reply-detail-link">查看</span>
              </template>
              <div class="markdown-body" v-html="renderMarkdown(msg.content.replace('<!-- ask_user_response -->\n', ''))" />
            </n-popover>
            <n-text depth="3" style="font-size: 10px; margin-left: 4px">{{ formatTime(msg.created_at) }}</n-text>
          </div>
        </div>

        <!-- 用户/AI 消息 -->
        <div
          v-else
          :style="{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }"
          @mouseenter="hoveredMessageId = msg.id"
          @mouseleave="hoveredMessageId = null"
        >
          <div style="max-width: 85%; position: relative">
            <n-card
              size="small"
              :style="{
                background: msg.role === 'user' ? '#1a3a5c' : '#1a2a3e',
                borderLeft: msg.role === 'assistant' ? '2px solid #e94560' : 'none',
                borderRight: msg.role === 'user' ? '2px solid #0ea5e9' : 'none',
                '--n-padding-top': '6px',
                '--n-padding-bottom': '6px',
                '--n-padding-left': '10px',
                '--n-padding-right': '10px',
              }"
            >
            <template #header>
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px">
                <n-space align="center" :size="6" style="flex: 1; min-width: 0">
                  <n-text :style="{ color: msg.role === 'assistant' ? '#e94560' : getUserColor(msg.sender_name), fontSize: '12px' }">
                    {{ msg.sender_name || msg.role }}
                  </n-text>
                  <n-tag v-if="msg.model_used" size="tiny" :bordered="false" round>
                    {{ msg.model_used }}
                  </n-tag>
                  <n-text depth="3" style="font-size: 10px">
                    {{ formatTime(msg.created_at) }}
                  </n-text>
                </n-space>
                <!-- 操作按钮 (常驻显示在 header 右侧) -->
                <n-button-group size="tiny" class="msg-actions" :class="{ 'msg-actions-visible': hoveredMessageId === msg.id }">
                  <n-button quaternary @click.stop="copyMessage(msg)" title="复制">
                    <template #icon><span style="font-size: 11px">📋</span></template>
                  </n-button>
                  <n-button quaternary @click.stop="msg.role === 'user' ? retryMessage(msg) : regenerateMessage(msg)" :title="msg.role === 'user' ? '重新发送' : '重新生成'">
                    <template #icon><span style="font-size: 11px">🔄</span></template>
                  </n-button>
                </n-button-group>
              </div>
            </template>

            <!-- 图片附件 -->
            <n-space v-if="msg.attachments?.length" style="margin-bottom: 6px">
              <n-image
                v-for="(att, i) in msg.attachments.filter((a: any) => a.type === 'image')"
                :key="i"
                :src="att.url"
                width="180"
                style="border-radius: 6px"
              />
            </n-space>

            <!-- 思考过程 (已保存的消息) -->
            <n-collapse v-if="msg.thinking_content" style="margin-bottom: 6px">
              <n-collapse-item title="💭 思考过程" name="thinking">
                <div class="thinking-block" v-html="renderMarkdown(msg.thinking_content)" />
              </n-collapse-item>
            </n-collapse>

            <!-- 工具调用记录 (已保存消息, 折叠显示, 不含 ask_user) -->
            <div v-if="getRegularToolCalls(msg.tool_calls).length" style="margin-bottom: 4px">
              <div class="tool-group-header" @click="toggleToolGroup(msg.id)">
                <span class="tool-group-arrow" :class="{ open: expandedToolGroups[msg.id] }">▶</span>
                <span class="tool-group-icon">🛠️</span>
                <span class="tool-group-count">{{ getRegularToolCalls(msg.tool_calls).length }} 轮工具调用</span>
              </div>
              <div v-if="expandedToolGroups[msg.id]" class="tool-group-body">
                <template v-for="tc in getRegularToolCalls(msg.tool_calls)" :key="tc.id">
                  <div class="tool-inline">
                    <span :class="tc.result?.startsWith('ERROR:') ? 'tool-icon-error' : 'tool-icon-ok'">
                      {{ tc.result?.startsWith('ERROR:') ? '❌' : '✅' }}
                    </span>
                    <span class="tool-inline-name">{{ toolDisplayName(tc.name) }}</span>
                    <code v-if="tc.arguments" class="tool-inline-args">{{ formatToolArgs(tc.name, tc.arguments) }}</code>
                    <span v-if="tc.duration_ms" class="tool-inline-time">({{ tc.duration_ms }}ms)</span>
                    <n-popover trigger="click" placement="bottom" style="max-width: 500px; max-height: 300px; overflow: auto">
                      <template #trigger>
                        <span class="tool-inline-view">查看</span>
                      </template>
                      <div class="tool-result-content" v-html="renderMarkdown(tc.result || '(无结果)')" />
                    </n-popover>
                  </div>
                </template>
              </div>
            </div>

            <!-- 消息内容 (Markdown) -->
            <div class="markdown-body" v-html="renderMarkdown(msg.content)" />

            <!-- ask_user 问题卡片 (渲染在文本内容之后, 符合对话直觉) -->
            <template v-for="tc in (msg.tool_calls || []).filter(t => t.name === 'ask_user' && parseQuestions(t.arguments).length > 0)" :key="tc.id">
              <div class="question-card" style="margin-top: 6px">
                <template v-if="getCardState(tc.id).submitted || isAskUserAnswered(msg, tc)">
                  <!-- 已提交/已回答: 紧凑回显 -->
                  <div class="question-card-header question-card-header-done">
                    <span class="question-card-icon">{{ isAskUserAutoDecided(msg, tc) ? '🤖' : '✅' }}</span>
                    <span class="question-card-title" style="color: #8a8a8a">{{ isAskUserAutoDecided(msg, tc) ? 'AI 自行决定' : '已回答' }}</span>
                  </div>
                  <!-- 本地 cardState 或 DB 跳过: 逐题显示 (含 AI 推荐回显) -->
                  <template v-if="getCardState(tc.id).submitted || isAskUserAutoDecided(msg, tc)">
                    <div v-for="(q, qi) in parseQuestions(tc.arguments)" :key="qi" class="question-summary-row">
                      <span class="question-summary-q">{{ q.question }}</span>
                      <span v-if="getCardState(tc.id).answers[qi]?.length || getCardState(tc.id).customTexts[qi]?.trim()" class="question-summary-a">
                        {{ getCardState(tc.id).customTexts[qi]?.trim() || getCardState(tc.id).answers[qi]?.join('、') }}
                      </span>
                      <span v-else-if="getRecommendedLabels(q)" class="question-summary-a question-summary-a-auto">
                        🤖 {{ getRecommendedLabels(q) }}
                      </span>
                    </div>
                  </template>
                  <!-- 从 DB 加载的历史: 显示后续用户回答 -->
                  <div v-else class="question-result-text">
                    <div class="markdown-body" v-html="renderMarkdown(getAskUserAnswer(msg))" />
                  </div>
                </template>
                <template v-else>
                  <!-- 未提交: 交互选择 -->
                  <div class="question-card-header">
                    <span class="question-card-icon">💬</span>
                    <span class="question-card-title">AI 想了解以下问题</span>
                    <span class="question-card-hint">选择后点击提交，未回答的问题由 AI 决定</span>
                  </div>
                  <div v-for="(q, qi) in parseQuestions(tc.arguments)" :key="qi" class="question-item">
                    <div class="question-text">
                      {{ qi + 1 }}. {{ q.question }}
                      <span v-if="q.type === 'multi'" class="question-type-tag">多选</span>
                    </div>
                    <div v-if="q.context" class="question-context">{{ q.context }}</div>
                    <div v-if="q.options?.length" class="question-options">
                      <span v-for="(opt, oi) in q.options" :key="oi"
                        class="question-option-btn"
                        :class="{
                          'question-option-selected': getCardState(tc.id).answers[qi]?.includes(opt.label),
                          'question-option-recommended': opt.recommended && !getCardState(tc.id).answers[qi]?.includes(opt.label),
                        }"
                        @click="toggleOption(tc.id, qi, opt.label, q.type)">
                        <span v-if="opt.recommended" class="rec-dot" />
                        {{ opt.label }}
                        <span v-if="opt.description" class="option-desc">{{ opt.description }}</span>
                      </span>
                    </div>
                    <input v-if="!q.options?.length || getCardState(tc.id).answers[qi]?.some(a => a.includes('其他'))"
                      class="question-custom-input"
                      :placeholder="q.options?.length ? '请补充说明...' : '请输入你的回答...'"
                      :value="getCardState(tc.id).customTexts[qi] || ''"
                      @input="(e: any) => getCardState(tc.id).customTexts[qi] = e.target.value" />
                  </div>
                  <div class="question-submit-row">
                    <n-button size="small" type="primary" @click="submitQuestionCard(tc.id, parseQuestions(tc.arguments))">
                      提交回答
                    </n-button>
                    <n-button size="tiny" quaternary @click="submitQuestionCard(tc.id, parseQuestions(tc.arguments))">
                      跳过全部，AI 自行决定
                    </n-button>
                  </div>
                </template>
              </div>
            </template>

            <!-- 工具调用统计 -->
            <div v-if="msg.token_usage?.tool_rounds" style="margin-top: 4px; padding-top: 3px; border-top: 1px solid #333">
              <n-text depth="3" style="font-size: 10px; color: #63e2b7">
                🛠️ {{ msg.token_usage.tool_rounds }} 轮工具调用
              </n-text>
            </div>
          </n-card>
          </div>
        </div>
      </div>

      <!-- 上下文总结通知 -->
      <div v-if="summaryNotice" style="display: flex; justify-content: center; margin-bottom: 6px">
        <n-card size="small" style="max-width: 90%; background: #1a2a3e; border: 1px dashed #f0a020; border-radius: 6px">
          <n-collapse>
            <n-collapse-item name="summary">
              <template #header>
                <n-space align="center" :size="6">
                  <span style="font-size: 16px">📝</span>
                  <n-text style="color: #f0a020; font-size: 12px; font-weight: 500">
                    上下文已接近上限，自动总结了早期对话
                  </n-text>
                </n-space>
              </template>
              <div class="thinking-block" v-html="renderMarkdown(summaryNotice)" />
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </div>

      <!-- AI 正在回复 -->
      <div v-if="streaming" style="display: flex; justify-content: flex-start; margin-bottom: 6px">
        <n-card size="small" style="max-width: 85%; background: #1a2a3e; border-left: 2px solid #e94560; --n-padding-top: 6px; --n-padding-bottom: 6px">
          <template #header>
            <n-space align="center" :size="6">
              <n-text style="color: #e94560; font-size: 12px">{{ selectedModelDisplay }}</n-text>
              <span v-html="selectedModelProviderIcon" style="display:inline-flex"></span>
              <n-spin size="small" />
            </n-space>
          </template>

          <!-- 思考过程 (折叠) -->
          <n-collapse v-if="streamThinking" :default-expanded-names="['thinking']" style="margin-bottom: 8px">
            <n-collapse-item title="💭 思考过程" name="thinking">
              <div class="thinking-block" v-html="renderMarkdown(streamThinking)" />
            </n-collapse-item>
          </n-collapse>

          <!-- 流式内容段 (工具调用内联显示) -->
          <template v-for="(seg, segIdx) in streamSegments" :key="segIdx">
            <div v-if="seg.type === 'content'" class="markdown-body"
              v-html="renderMarkdown((seg.text || '') + (segIdx === streamSegments.length - 1 ? '▍' : ''))" />
            <!-- ask_user: 交互式问题卡片 (preparing 状态也显示) -->
            <div v-else-if="seg.type === 'tool' && seg.toolCall?.name === 'ask_user' && (seg.toolCall.status === 'preparing' || parseQuestions(seg.toolCall.arguments).length > 0)" class="question-card">
              <!-- 准备中: 参数还在流式传输 -->
              <template v-if="seg.toolCall.status === 'preparing'">
                <div class="question-card-header">
                  <span class="question-card-icon">💬</span>
                  <span class="question-card-title">AI 正在组织问题…</span>
                  <n-spin :size="12" style="margin-left: 6px" />
                </div>
                <div class="question-preparing-body">
                  <div class="question-preparing-skeleton">
                    <div class="skeleton-line" style="width: 70%"></div>
                    <div class="skeleton-options">
                      <div class="skeleton-pill"></div>
                      <div class="skeleton-pill" style="width: 80px"></div>
                      <div class="skeleton-pill" style="width: 100px"></div>
                    </div>
                    <div class="skeleton-line" style="width: 55%; margin-top: 10px"></div>
                    <div class="skeleton-options">
                      <div class="skeleton-pill" style="width: 90px"></div>
                      <div class="skeleton-pill" style="width: 70px"></div>
                    </div>
                  </div>
                </div>
              </template>
              <template v-else-if="getCardState(seg.toolCall.id).submitted">
                <!-- 已提交: 紧凑回显 (含 AI 推荐回显) -->
                <div class="question-card-header question-card-header-done">
                  <span class="question-card-icon">{{ parseQuestions(seg.toolCall.arguments).every((_: any, qi: number) => !getCardState(seg.toolCall.id).answers[qi]?.length && !getCardState(seg.toolCall.id).customTexts[qi]?.trim()) ? '🤖' : '✅' }}</span>
                  <span class="question-card-title" style="color: #8a8a8a">{{ parseQuestions(seg.toolCall.arguments).every((_: any, qi: number) => !getCardState(seg.toolCall.id).answers[qi]?.length && !getCardState(seg.toolCall.id).customTexts[qi]?.trim()) ? 'AI 自行决定' : '已回答' }}</span>
                </div>
                <div v-for="(q, qi) in parseQuestions(seg.toolCall.arguments)" :key="qi" class="question-summary-row">
                  <span class="question-summary-q">{{ q.question }}</span>
                  <span v-if="getCardState(seg.toolCall.id).answers[qi]?.length || getCardState(seg.toolCall.id).customTexts[qi]?.trim()" class="question-summary-a">
                    {{ getCardState(seg.toolCall.id).customTexts[qi]?.trim() || getCardState(seg.toolCall.id).answers[qi]?.join('、') }}
                  </span>
                  <span v-else-if="getRecommendedLabels(q)" class="question-summary-a question-summary-a-auto">
                    🤖 {{ getRecommendedLabels(q) }}
                  </span>
                </div>
              </template>
              <template v-else>
                <!-- 未提交: 交互选择 -->
                <div class="question-card-header">
                  <span class="question-card-icon">💬</span>
                  <span class="question-card-title">AI 想了解以下问题</span>
                  <n-spin v-if="seg.toolCall.status === 'calling'" :size="12" style="margin-left: 6px" />
                  <span v-else class="question-card-hint">选择后点击提交，未回答的问题由 AI 决定</span>
                </div>
                <div v-for="(q, qi) in parseQuestions(seg.toolCall.arguments)" :key="qi" class="question-item">
                  <div class="question-text">
                    {{ qi + 1 }}. {{ q.question }}
                    <span v-if="q.type === 'multi'" class="question-type-tag">多选</span>
                  </div>
                  <div v-if="q.context" class="question-context">{{ q.context }}</div>
                  <div v-if="q.options?.length" class="question-options">
                    <span v-for="(opt, oi) in q.options" :key="oi"
                      class="question-option-btn"
                      :class="{
                        'question-option-selected': getCardState(seg.toolCall.id).answers[qi]?.includes(opt.label),
                        'question-option-recommended': opt.recommended && !getCardState(seg.toolCall.id).answers[qi]?.includes(opt.label),
                      }"
                      @click="toggleOption(seg.toolCall.id, qi, opt.label, q.type)">
                      <span v-if="opt.recommended" class="rec-dot" />
                      {{ opt.label }}
                      <span v-if="opt.description" class="option-desc">{{ opt.description }}</span>
                    </span>
                  </div>
                  <input v-if="!q.options?.length || getCardState(seg.toolCall.id).answers[qi]?.some(a => a.includes('其他'))"
                    class="question-custom-input"
                    :placeholder="q.options?.length ? '请补充说明...' : '请输入你的回答...'"
                    :value="getCardState(seg.toolCall.id).customTexts[qi] || ''"
                    @input="(e: any) => getCardState(seg.toolCall.id).customTexts[qi] = e.target.value" />
                </div>
                <div v-if="seg.toolCall.status !== 'calling'" class="question-submit-row">
                  <n-button size="small" type="primary" @click="submitQuestionCard(seg.toolCall.id, parseQuestions(seg.toolCall.arguments))">
                    提交回答
                  </n-button>
                  <n-button size="tiny" quaternary @click="submitQuestionCard(seg.toolCall.id, parseQuestions(seg.toolCall.arguments))">
                    跳过全部，AI 自行决定
                  </n-button>
                </div>
              </template>
            </div>
            <!-- 普通工具: 单行内联 -->
            <div v-else-if="seg.type === 'tool' && seg.toolCall" class="tool-inline">
              <span v-if="seg.toolCall.status === 'calling' || seg.toolCall.status === 'preparing'" class="tool-icon-pending">⏳</span>
              <span v-else-if="seg.toolCall.status === 'error'" class="tool-icon-error">❌</span>
              <span v-else class="tool-icon-ok">✅</span>
              <span class="tool-inline-name">{{ toolDisplayName(seg.toolCall.name) }}</span>
              <code v-if="seg.toolCall.arguments" class="tool-inline-args">{{ formatToolArgs(seg.toolCall.name, seg.toolCall.arguments) }}</code>
              <span v-if="seg.toolCall.duration_ms" class="tool-inline-time">({{ seg.toolCall.duration_ms }}ms)</span>
              <n-spin v-if="seg.toolCall.status === 'calling' || seg.toolCall.status === 'preparing'" :size="10" style="margin-left: 2px" />
              <n-popover v-if="seg.toolCall.result" trigger="click" placement="bottom" style="max-width: 500px; max-height: 300px; overflow: auto">
                <template #trigger>
                  <span class="tool-inline-view">查看</span>
                </template>
                <div class="tool-result-content" v-html="renderMarkdown(seg.toolCall.result)" />
              </n-popover>
            </div>
          </template>
          <div v-if="!streamSegments.length" class="markdown-body" v-html="renderMarkdown('▍')" />
        </n-card>
      </div>
    </div>
      <!-- 右侧插槽 (设计稿面板在此渲染) -->
      <slot name="aside" />
    </div>

    <!-- 图片预览区 -->
    <div v-if="pendingImages.length" style="padding: 6px 8px; background: #16213e; border-radius: 6px; margin-bottom: 4px">
      <n-space :size="6">
        <div v-for="(img, i) in pendingImages" :key="i" style="position: relative">
          <n-image :src="img.preview" width="64" height="64" style="border-radius: 6px; object-fit: cover" />
          <n-button circle size="tiny" type="error" style="position: absolute; top: -4px; right: -4px" @click="pendingImages.splice(i, 1)">✕</n-button>
        </div>
      </n-space>
    </div>

    <!-- 隐藏的文件选择器 (绕过 n-upload 的 DOM 问题) -->
    <input ref="fileInputRef" type="file" accept="image/*" style="display: none" @change="onFileInputChange" />

    <!-- ========== 输入区 ========== -->
    <div class="input-area">
      <!-- 第 1 行: 工具栏 -->
      <div class="toolbar-row">
        <n-dropdown :options="sourceFilterOptions" @select="onSourceFilterChange" trigger="click" size="small">
          <n-button size="small" quaternary style="padding: 0 6px">
            {{ sourceFilterLabel }} <span style="font-size: 10px; margin-left: 2px; opacity: 0.6">▾</span>
          </n-button>
        </n-dropdown>
        <div class="model-select-group">
          <n-select
            v-model:value="selectedModel"
            :options="modelOptions"
            :render-label="renderModelLabel"
            size="small"
            style="width: 100%"
            filterable
            :consistent-menu-width="false"
            @update:value="handleModelChange"
          />
          <button class="model-refresh-btn" @click="refreshModels" :disabled="loadingModels" :title="loadingModels ? '刷新中...' : '刷新模型列表'">
            <span :class="{ 'spin-icon': loadingModels }">⟲</span>
          </button>
        </div>
        <n-button v-if="currentModelCaps.supports_vision" size="small" quaternary :disabled="streaming" @click="fileInputRef?.click()">📷 图片</n-button>
        <n-popover v-if="currentModelCaps.supports_tools" trigger="click" placement="bottom" style="max-width: 320px">
          <template #trigger>
            <n-button size="small" quaternary :type="toolPermissions.length ? 'info' : 'default'">🛠️ 工具</n-button>
          </template>
          <div style="padding: 4px 0">
            <n-text strong style="font-size: 13px">AI 工具权限</n-text>
            <n-text depth="3" style="font-size: 11px; display: block; margin: 4px 0 8px">
              开启后 AI 可查看项目源码（可在设置页配置工具轮次上限）
            </n-text>
            <n-checkbox-group v-model:value="toolPermissions" @update:value="saveToolPermissions">
              <n-space vertical :size="4">
                <n-checkbox value="ask_user" label="❓ 主动提问澄清" />
                <n-checkbox value="read_source" label="📖 读取源码文件" />
                <n-checkbox value="read_config" label="📄 读取配置文件" />
                <n-checkbox value="search" label="🔍 搜索代码内容" />
                <n-checkbox value="tree" label="🌳 浏览目录结构" />
              </n-space>
            </n-checkbox-group>
          </div>
        </n-popover>
        <n-tag v-if="remoteStreaming" type="warning" size="small" :bordered="false" round>⏳ AI 回复中...</n-tag>
      </div>

      <!-- 第 2 行: 文本输入框 -->
      <n-input
        ref="inputRef"
        v-model:value="inputText"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 5 }"
        :placeholder="aiMuted ? '人工讨论模式 (Enter 发送)' : '描述你的需求... (Enter 发送, Shift+Enter 换行)'"
        :disabled="streaming"
        @keydown="handleKeydown"
        style="margin: 4px 0"
      />

      <!-- 第 3 行: 操作栏 -->
      <div class="action-bar">
        <n-popover trigger="click" placement="top-start" style="padding: 0">
          <template #trigger>
            <div class="action-bar-item" style="cursor: pointer">
              <n-progress
                type="line"
                :percentage="displayContextInfo.percentage"
                :show-indicator="false"
                :height="3"
                style="width: 48px"
                :color="displayContextInfo.percentage > 80 ? '#e94560' : displayContextInfo.percentage > 50 ? '#f0a020' : '#18a058'"
              />
              <span class="action-bar-stat">
                {{ formatTokens(displayContextInfo.used) }}/{{ formatTokens(displayContextInfo.total) }} · {{ displayContextInfo.percentage }}%
              </span>
              <n-spin v-if="contextCompressing" :size="12" style="margin-left: 4px" />
            </div>
          </template>
          <!-- 上下文占用明细气泡 (树形检查器) -->
          <div class="ctx-breakdown">
            <div class="ctx-breakdown-title">📊 上下文占用明细</div>
            <div class="ctx-breakdown-bar">
              <div class="ctx-bar-seg ctx-bar-system" :style="{ width: ctxBreakdownPercents.system + '%' }" />
              <div class="ctx-bar-seg ctx-bar-tools" :style="{ width: ctxBreakdownPercents.tools + '%' }" />
              <div class="ctx-bar-seg ctx-bar-history" :style="{ width: ctxBreakdownPercents.history + '%' }" />
            </div>

            <!-- 可展开的树形明细 -->
            <div class="ctx-tree">
              <!-- System Prompt (可展开子节点) -->
              <div class="ctx-tree-node">
                <div class="ctx-tree-row" @click="ctxExpanded.system = !ctxExpanded.system">
                  <span class="ctx-tree-arrow" :class="{ open: ctxExpanded.system }">▶</span>
                  <span class="ctx-dot" style="background:#a855f7" />
                  <span class="ctx-tree-label">System Prompt</span>
                  <span class="ctx-val">{{ formatTokens(ctxBreakdown.system) }}</span>
                </div>
                <div v-if="ctxExpanded.system && ctxSystemSections.length" class="ctx-tree-children">
                  <div v-for="(sec, si) in ctxSystemSections" :key="si" class="ctx-tree-node">
                    <div class="ctx-tree-row ctx-tree-row-child"
                         @click="sec.children ? (ctxExpanded['sys_' + si] = !ctxExpanded['sys_' + si]) : openCtxContent(sec.name, sec.content)">
                      <span v-if="sec.children" class="ctx-tree-arrow" :class="{ open: ctxExpanded['sys_' + si] }">▶</span>
                      <span v-else class="ctx-tree-arrow ctx-tree-leaf">·</span>
                      <span class="ctx-tree-label" :class="{ 'ctx-clickable': !sec.children }">{{ sec.name }}</span>
                      <span class="ctx-val">{{ formatTokens(sec.tokens) }}</span>
                    </div>
                    <!-- 子节点的 children (如关键文件) -->
                    <div v-if="sec.children && ctxExpanded['sys_' + si]" class="ctx-tree-children">
                      <div v-for="(child, ci) in sec.children" :key="ci" class="ctx-tree-row ctx-tree-row-leaf ctx-clickable-row"
                           @click="openCtxContent(child.name, child.content)">
                        <span class="ctx-tree-arrow ctx-tree-leaf">·</span>
                        <span class="ctx-tree-label ctx-clickable">{{ child.name }}</span>
                        <span class="ctx-val">{{ formatTokens(child.tokens) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 工具定义 -->
              <div class="ctx-tree-node">
                <div class="ctx-tree-row">
                  <span class="ctx-tree-arrow ctx-tree-leaf">·</span>
                  <span class="ctx-dot" style="background:#0ea5e9" />
                  <span class="ctx-tree-label">工具定义</span>
                  <span class="ctx-val">{{ formatTokens(ctxBreakdown.tools) }}</span>
                </div>
              </div>

              <!-- 对话历史 (可展开每条消息) -->
              <div class="ctx-tree-node">
                <div class="ctx-tree-row" @click="ctxExpanded.history = !ctxExpanded.history">
                  <span class="ctx-tree-arrow" :class="{ open: ctxExpanded.history }">▶</span>
                  <span class="ctx-dot" style="background:#f59e0b" />
                  <span class="ctx-tree-label">对话历史</span>
                  <span class="ctx-val">{{ formatTokens(ctxBreakdown.history) }}</span>
                </div>
                <div v-if="ctxExpanded.history && ctxHistoryDetail.length" class="ctx-tree-children">
                  <div v-for="(hm, hi) in ctxHistoryDetail" :key="hi" class="ctx-tree-row ctx-tree-row-leaf">
                    <span class="ctx-tree-arrow ctx-tree-leaf">·</span>
                    <span class="ctx-tree-label ctx-tree-msg-label" :class="'ctx-role-' + hm.role">
                      {{ hm.role === 'user' ? '👤' : hm.role === 'assistant' ? '🤖' : '📋' }}
                      <span class="ctx-msg-preview">{{ hm.preview || '(空)' }}</span>
                    </span>
                    <span class="ctx-val">{{ formatTokens(hm.tokens) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 汇总 -->
            <div class="ctx-tree-summary">
              <span>总计 / 上限</span>
              <span class="ctx-val">{{ formatTokens(displayContextInfo.used) }} / {{ formatTokens(displayContextInfo.total) }}</span>
            </div>
            <div v-if="ctxMessages.total" class="ctx-breakdown-msgs">
              💬 消息: 保留 {{ ctxMessages.kept }} / 共 {{ ctxMessages.total }}
              <span v-if="ctxMessages.dropped"> · 丢弃 {{ ctxMessages.dropped }}</span>
            </div>
          </div>
        </n-popover>
        <!-- 上下文内容查看气泡 -->
        <n-modal v-model:show="ctxContentModal" preset="card" :title="ctxContentTitle"
                 style="width: min(620px, 90vw); max-height: 70vh;"
                 :bordered="false" size="small"
                 :segmented="{ content: true }">
          <n-scrollbar style="max-height: calc(70vh - 80px)">
            <pre class="ctx-content-pre">{{ ctxContentText }}</pre>
          </n-scrollbar>
        </n-modal>
        <n-button-group size="tiny">
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button size="tiny" quaternary :loading="summarizing" :disabled="streaming || messages.length < 4" @click="handleSummarize">
                📝
              </n-button>
            </template>
            总结上下文：将旧消息压缩为摘要，释放上下文空间
          </n-tooltip>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button size="tiny" quaternary :disabled="streaming || !messages.length" @click="handleClearContext">
                🗑️
              </n-button>
            </template>
            清空上下文：删除所有讨论消息，重新开始
          </n-tooltip>
        </n-button-group>
        <span class="action-bar-spring" />
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button size="small" :type="aiMuted ? 'error' : 'default'" quaternary :loading="muteLoading" @click="toggleAiMute">
              {{ aiMuted ? '🔇 AI已禁言' : '🔊 禁言AI' }}
            </n-button>
          </template>
          {{ aiMuted ? '解除禁言后，AI 会阅读所有新消息并回复' : '禁言后仅人工讨论，AI 不参与回复' }}
        </n-tooltip>
        <n-button size="small" type="warning" quaternary @click="handleFinalizePlan" :loading="finalizingPlan" :disabled="messages.length < 2 || streaming">
          📋 {{ props.project.skill?.ui_labels?.finalize_action || '敲定' }}
        </n-button>
        <n-button v-if="streaming" size="small" type="error" @click="stopStreaming">⏹ 停止</n-button>
        <n-button v-else size="small" type="primary" @click="sendMessage()" :disabled="!inputText.trim() && !pendingImages.length">发送</n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch, h } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { discussionApi, modelApi, projectApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useStudioConfigStore } from '@/stores/studioConfig'
import { getProviderIcon } from '@/utils/providerIcons'
import type { Project } from '@/stores/project'
import { marked } from 'marked'

const authStore = useAuthStore()
const studioConfig = useStudioConfigStore()

const props = defineProps<{ project: Project }>()
const emit = defineEmits(['plan-finalized'])
const message = useMessage()
const dialog = useDialog()

const messages = ref<any[]>([])
const inputText = ref('')
const streaming = ref(false)
const startingChat = ref(false)
const streamContent = ref('')
const streamThinking = ref('')
const streamToolCalls = ref<Array<{
  id: string
  name: string
  arguments: any
  status: 'calling' | 'done' | 'error'
  result?: string
  duration_ms?: number
}>>([])
const streamSegments = ref<Array<{
  type: 'content' | 'tool'
  text?: string
  toolCall?: {
    id: string
    name: string
    arguments: any
    status: 'calling' | 'done' | 'error'
    result?: string
    duration_ms?: number
  }
}>>([])
const contextInfo = ref<any>(null)
const tokenUsage = ref<any>(null)
const summaryNotice = ref<string>('')
const finalizingPlan = ref(false)
const messageListRef = ref<HTMLElement>()
const inputRef = ref()
const fileInputRef = ref<HTMLInputElement>()

// ---- 项目信息编辑 ----
const showProjectEdit = ref(false)
const editProjectTitle = ref('')
const editProjectDesc = ref('')
const savingProject = ref(false)

watch(showProjectEdit, (val) => {
  if (val) {
    editProjectTitle.value = props.project.title || ''
    editProjectDesc.value = props.project.description || ''
  }
})

async function saveProjectInfo() {
  savingProject.value = true
  try {
    await projectApi.update(props.project.id, {
      title: editProjectTitle.value,
      description: editProjectDesc.value,
    })
    // 直接更新 props 对象 (reactive)
    ;(props.project as any).title = editProjectTitle.value
    ;(props.project as any).description = editProjectDesc.value
    showProjectEdit.value = false
    message.success('项目信息已更新')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '保存失败')
  } finally {
    savingProject.value = false
  }
}
const models = ref<any[]>([])
const selectedModel = ref(props.project.discussion_model || 'gpt-4o')
const loadingModels = ref(false)
const modelSourceFilter = computed({
  get: () => studioConfig.chatModelSourceFilter,
  set: (v: string) => { studioConfig.chatModelSourceFilter = v }
})

// AbortController for canceling streams
const abortController = ref<AbortController | null>(null)

// Message hover state for action buttons
const hoveredMessageId = ref<number | null>(null)

// Last token usage for display
const lastTokenUsage = ref<any>(null)

// 上下文信息 (常驻显示, 不随 streaming 重置)
const persistentContextInfo = ref<any>(null)

// 刷新上下文使用率 (复用在 mount / sendMessage / regenerate / summarize 等场景)
function refreshContextInfo() {
  const model = selectedModel.value
  if (!model || !props.project?.id) return
  discussionApi.checkContext(props.project.id, model).then(({ data: ctx }) => {
    if (ctx?.context) persistentContextInfo.value = ctx.context
  }).catch(() => {})
}

// 当前选中模型的最大上下文 tokens
const selectedModelMaxTokens = computed(() => {
  const model = models.value.find((m: any) => m.id === selectedModel.value)
  if (!model) return 0
  return studioConfig.getEffectiveMaxInput(model.id, model.max_input_tokens || 0) || model.max_input_tokens || 0
})

// 始终显示的上下文信息: 分母跟随活跃模型
const displayContextInfo = computed(() => {
  const total = selectedModelMaxTokens.value
  if (persistentContextInfo.value) {
    // 有实际数据时, 使用实际 used 但 total 以当前模型为准
    const used = persistentContextInfo.value.used || 0
    const effectiveTotal = total || persistentContextInfo.value.total || 1
    const percentage = Math.min(100, Math.round(used * 100 / Math.max(effectiveTotal, 1)))
    return { used, total: effectiveTotal, percentage }
  }
  // 无数据时, 显示 0/模型上限
  return { used: 0, total: total || 0, percentage: 0 }
})

// 上下文占用明细 (breakdown)
const ctxBreakdown = computed(() => {
  const bd = persistentContextInfo.value?.breakdown
  return { system: bd?.system || 0, tools: bd?.tools || 0, history: bd?.history || 0 }
})
const ctxMessages = computed(() => {
  const m = persistentContextInfo.value?.messages
  return { kept: m?.kept || 0, dropped: m?.dropped || 0, total: m?.total || 0 }
})
const ctxBreakdownPercents = computed(() => {
  const total = displayContextInfo.value.total || 1
  return {
    system: Math.round(ctxBreakdown.value.system * 100 / total),
    tools: Math.round(ctxBreakdown.value.tools * 100 / total),
    history: Math.round(ctxBreakdown.value.history * 100 / total),
  }
})
// System Prompt 分段明细 (树形子节点)
const ctxSystemSections = computed(() => {
  return persistentContextInfo.value?.system_sections || []
})
// 对话历史每条消息的 token 明细
const ctxHistoryDetail = computed(() => {
  return persistentContextInfo.value?.history_detail || []
})
// 树形展开状态
const ctxExpanded = reactive<Record<string, boolean>>({})
// 工具调用分组展开状态
const expandedToolGroups = reactive<Record<number, boolean>>({})
function toggleToolGroup(msgId: number) {
  expandedToolGroups[msgId] = !expandedToolGroups[msgId]
}
function getRegularToolCalls(toolCalls: any[] | undefined) {
  return (toolCalls || []).filter((tc: any) => tc.name !== 'ask_user')
}
// 判断 ask_user 是否已被用户回答 (查找后续的 ask_user_response 消息)
function isAskUserAnswered(currentMsg: any, _tc: any): boolean {
  const idx = messages.value.findIndex((m: any) => m.id === currentMsg.id)
  if (idx < 0) return false
  // 往后找紧邻的 user 消息是否是 ask_user_response
  for (let i = idx + 1; i < messages.value.length; i++) {
    const m = messages.value[i]
    if (m.role === 'user' && m.content?.startsWith('<!-- ask_user_response -->')) return true
    if (m.role === 'assistant') break // 碰到下一个 AI 消息就停
  }
  return false
}
// 获取 ask_user 的用户回答内容
function getAskUserAnswer(currentMsg: any): string {
  const idx = messages.value.findIndex((m: any) => m.id === currentMsg.id)
  if (idx < 0) return ''
  for (let i = idx + 1; i < messages.value.length; i++) {
    const m = messages.value[i]
    if (m.role === 'user' && m.content?.startsWith('<!-- ask_user_response -->')) {
      return m.content.replace('<!-- ask_user_response -->\n', '').replace('<!-- ask_user_response -->', '')
    }
    if (m.role === 'assistant') break
  }
  return ''
}
// 判断 ask_user 是否全部由 AI 自行决定 (用户未选任何选项)
function isAskUserAutoDecided(msg: any, tc: any): boolean {
  const state = getCardState(tc.id)
  if (state.submitted) {
    // 本地 state: 全部问题都没有回答
    const questions = parseQuestions(tc.arguments)
    return questions.every((_: any, qi: number) => !state.answers[qi]?.length && !state.customTexts[qi]?.trim())
  }
  // DB 加载: 回答文本含跳过标记
  const answer = getAskUserAnswer(msg)
  return answer.includes('以上问题由你来决定')
}

// 获取问题的推荐选项文本 (用于 AI 自行决定的显示)
function getRecommendedLabels(q: ParsedQuestion): string {
  const recs = q.options?.filter(o => o.recommended)
  if (recs?.length) return recs.map(o => o.label).join('、')
  return ''
}

// 内容查看器 (气泡弹窗)
const ctxContentModal = ref(false)
const ctxContentTitle = ref('')
const ctxContentText = ref('')
function openCtxContent(name: string, content?: string) {
  if (!content) return
  ctxContentTitle.value = name
  ctxContentText.value = content
  ctxContentModal.value = true
}

// AI 禁言状态
const aiMuted = ref(false)
const muteLoading = ref(false)

// 上下文压缩状态 (转圈圈特效)
const contextCompressing = ref(false)
const summarizing = ref(false)
let contextCheckVersion = 0  // 快速切换模型时取消旧请求

// 自动继续计数器 (防止无限循环)
let autoContinueCount = 0

// 来源过滤 — 下拉菜单
const sourceFilterOptions = computed(() => {
  const base: Array<{label: string; key: string}> = [
    { label: '全部', key: 'all' },
    { label: 'GitHub (免费)', key: 'github' },
  ]
  if (models.value.some(m => m.api_backend === 'copilot')) {
    base.push({ label: 'Copilot (付费)', key: 'copilot' })
  }
  const seen = new Set<string>()
  for (const m of models.value) {
    const slug = m.provider_slug || ''
    if (slug && slug !== 'github' && slug !== 'copilot' && !seen.has(slug)) {
      seen.add(slug)
      base.push({ label: m.publisher || slug, key: slug })
    }
  }
  if (studioConfig.customModelsEnabled) {
    base.push({ label: '🧩 补充模型', key: 'custom' })
  }
  return base
})
const sourceFilterLabel = computed(() => {
  const opt = sourceFilterOptions.value.find(o => o.key === modelSourceFilter.value)
  return opt?.label || '全部'
})
function onSourceFilterChange(key: string) {
  if (key === 'custom' && !studioConfig.customModelsEnabled) {
    modelSourceFilter.value = 'all'
    return
  }
  modelSourceFilter.value = key as any
}

// 当前选中模型的能力 (用于动态显示/隐藏按钮)
const currentModelCaps = computed(() => {
  const model = models.value.find((m: any) => m.id === selectedModel.value)
  if (!model) return { supports_vision: false, supports_tools: false }
  return { supports_vision: !!model.supports_vision, supports_tools: !!model.supports_tools }
})

const selectedModelDisplay = computed(() => {
  const model = models.value.find((m: any) => m.id === selectedModel.value)
  if (!model) return selectedModel.value
  const customStr = model.is_custom ? ' 🧩' : ''
  return `${selectedModel.value}${customStr}`
})

const selectedModelProviderIcon = computed(() => {
  const model = models.value.find((m: any) => m.id === selectedModel.value)
  if (!model) return ''
  const slug = model.provider_slug || (model.api_backend === 'copilot' ? 'copilot' : 'github')
  return getProviderIcon(slug, '', 12)
})

// 工具权限 (代码工具默认关闭, ask_user 默认开启)
const toolPermissions = ref<string[]>(
  props.project.tool_permissions?.length ? props.project.tool_permissions : ['ask_user']
)

// 当前模型的工具轮次上限 (根据免费/付费配置)
const currentModelToolRounds = computed(() => {
  const model = models.value.find(m => m.id === selectedModel.value)
  if (!model) return studioConfig.freeToolRounds
  return studioConfig.getToolRounds(model)
})

async function saveToolPermissions(val: string[]) {
  try {
    await projectApi.update(props.project.id, { tool_permissions: val })
  } catch {
    message.error('保存工具权限失败')
  }
}

// 远程流式输出检测 (其他用户触发的 AI 流式)
const remoteStreaming = ref(false)
let streamingPollTimer: ReturnType<typeof setInterval> | null = null

// 待发送的图片
const pendingImages = ref<Array<{ file: File; preview: string; uploaded?: any }>>([])

// 用户颜色映射
const userColorMap: Record<string, string> = {}
const userColors = ['#0ea5e9', '#a855f7', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4', '#84cc16']
let colorIndex = 0

function getUserColor(senderName: string): string {
  if (!senderName || senderName === 'assistant') return '#e94560'
  if (!userColorMap[senderName]) {
    userColorMap[senderName] = userColors[colorIndex % userColors.length]
    colorIndex++
  }
  return userColorMap[senderName]
}

// 模型选项，保持 API 返回顺序, 按 model_family 分组, 应用配置过滤
const modelOptions = computed(() => {
  const byCategory = models.value.filter(m => m.category === 'discussion' || m.category === 'both')
  // 按来源过滤
  const sourceFiltered = modelSourceFilter.value === 'all'
    ? byCategory
    : modelSourceFilter.value === 'copilot'
      ? byCategory.filter(m => m.provider_slug === 'copilot' || m.api_backend === 'copilot')
      : modelSourceFilter.value === 'custom'
        ? byCategory.filter(m => m.is_custom)
        : modelSourceFilter.value === 'github'
          ? byCategory.filter(m => m.provider_slug === 'github' || (!m.provider_slug && m.api_backend === 'models'))
          : byCategory.filter(m => m.provider_slug === modelSourceFilter.value)

  // 应用配置过滤 (免费模式 + 黑名单)
  const filtered = sourceFiltered.filter(m => studioConfig.isModelVisible(m))

  const mapOpt = (m: any) => ({
    label: m.name, value: m.id,
    description: m.summary || m.description || '',
    supports_vision: m.supports_vision, supports_tools: m.supports_tools,
    is_reasoning: m.is_reasoning, api_backend: m.api_backend,
    is_custom: m.is_custom,
    provider_slug: m.provider_slug || (m.api_backend === 'copilot' ? 'copilot' : 'github'),
    pricing_tier: m.pricing_tier, premium_multiplier: m.premium_multiplier,
    is_deprecated: m.is_deprecated, pricing_note: m.pricing_note,
    max_input_tokens: studioConfig.getEffectiveMaxInput(m.id, m.max_input_tokens || 0),
    max_output_tokens: m.max_output_tokens || 0,
  })
  // 按 model_family 保序分组
  const groups: Array<{ key: string; label: string; slug: string; items: any[] }> = []
  const groupMap: Record<string, typeof groups[0]> = {}
  for (const m of filtered) {
    const family = m.model_family || m.publisher || m.provider_slug || 'Other'
    const slug = m.provider_slug || (m.api_backend === 'copilot' ? 'copilot' : 'github')
    const gKey = slug + ':' + family
    if (!groupMap[gKey]) {
      const g = { key: gKey, label: family, slug, items: [] as any[] }
      groups.push(g)
      groupMap[gKey] = g
    }
    groupMap[gKey].items.push(m)
  }
  return groups.map(g => ({
    type: 'group', label: g.label, key: g.key, provider_slug: g.slug,
    children: g.items.map(mapOpt),
  }))
})

// 自定义模型选项渲染 (能力图标 + 上下文窗口 + 定价标识)
function renderModelLabel(option: any, selected: boolean) {
  if (option.type === 'group') {
    const iconHtml = getProviderIcon(option.provider_slug || 'github', option.label, 14)
    return h('span', { style: 'display:inline-flex;align-items:center;gap:4px' }, [
      h('span', { innerHTML: iconHtml, style: 'display:inline-flex' }),
      option.label,
    ])
  }
  const caps: string[] = []
  if (option.is_reasoning) caps.push('🧠')
  if (option.supports_vision) caps.push('👁️')
  if (option.supports_tools) caps.push('🔧')
  const depStr = option.is_deprecated ? ' ⚠️' : ''
  const capStr = caps.length ? ` ${caps.join('')}` : ''
  const iconHtml = getProviderIcon(option.provider_slug || 'github', '', 12)
  const iconVNode = h('span', { innerHTML: iconHtml, style: 'display:inline-flex;vertical-align:middle;margin:0 2px' })
  const customStr = option.is_custom ? ' 🧩' : ''
  const priceText = option.pricing_note || 'x0'
  const ctxText = option.max_input_tokens ? formatTokens(option.max_input_tokens) : ''
  const nameStyle = selected ? 'font-weight:600' : ''
  const priceStyle = selected
    ? 'color:#18a058;font-size:11px;flex-shrink:0;margin-left:8px;font-weight:600'
    : 'color:#888;font-size:11px;flex-shrink:0;margin-left:8px'
  return h('div', { style: 'display:flex;justify-content:space-between;align-items:center;width:100%' }, [
    h('span', { style: nameStyle }, [selected ? '● ' : '', option.label as string, ' ', iconVNode, customStr, capStr, depStr]),
    h('span', { style: priceStyle }, [
      ctxText ? h('span', { style: 'color:#666;margin-right:6px' }, ctxText) : null,
      priceText,
    ]),
  ])
}

async function refreshModels() {
  loadingModels.value = true
  try {
    await modelApi.refresh()
    const { data } = await modelApi.list({ category: 'discussion', custom_models: studioConfig.customModelsEnabled })
    models.value = data
    message.success(`已刷新，共 ${data.length} 个可用模型`)
  } catch (e: any) {
    message.error('刷新模型列表失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loadingModels.value = false
  }
}

function renderMarkdown(text: string) {
  if (!text) return ''
  try {
    return marked.parse(text, { async: false }) as string
  } catch {
    return text.replace(/\n/g, '<br>')
  }
}

function formatTime(d: string) {
  // 后端存储 UTC 时间 (datetime.utcnow)，ISO 字符串不含 Z 后缀
  // 需要手动补 Z 让浏览器正确转为本地时区
  const utcStr = d && !d.endsWith('Z') && !d.includes('+') ? d + 'Z' : d
  return new Date(utcStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

function scrollToTop() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = 0
    }
  })
}

function formatTokens(n: number): string {
  if (!n) return '0'
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`
  return `${n}`
}

// ==================== 错误解析 ====================

function parseErrorMeta(errorText: string, backendMeta?: any): any {
  const meta: any = { ...(backendMeta || {}) }

  // 速率限制
  const rlMatch = errorText.match(/Rate limit.*?(\d+)\s*per\s*(\d+)s/i)
  if (rlMatch) {
    meta.error_type = meta.error_type || 'rate_limit'
    meta.rate_limit = `${rlMatch[1]} per ${rlMatch[2]}s`
    meta.rate_limit_count = parseInt(rlMatch[1])
    meta.rate_limit_seconds = parseInt(rlMatch[2])
  }
  const waitMatch = errorText.match(/wait\s+(\d+)\s*seconds?/i)
  if (waitMatch) {
    meta.wait_seconds = parseInt(waitMatch[1])
    meta.error_type = meta.error_type || 'rate_limit'
  }

  // 上下文超限
  const ctxMatch = errorText.match(/maximum context length.*?(\d{3,})/i)
  if (ctxMatch) {
    meta.error_type = meta.error_type || 'context_overflow'
    meta.max_context_tokens = parseInt(ctxMatch[1])
  }
  const maxSizeMatch = errorText.match(/Max size:\s*(\d+)\s*tokens/i)
  if (maxSizeMatch) {
    meta.error_type = meta.error_type || 'context_overflow'
    meta.max_context_tokens = parseInt(maxSizeMatch[1])
  }
  const requestedMatch = errorText.match(/requested\s+(\d+)\s*tokens/i)
  if (requestedMatch) {
    meta.requested_tokens = parseInt(requestedMatch[1])
  }

  // 生成摘要
  if (meta.error_type === 'rate_limit') {
    meta.summary = `🚦 速率限制 (${meta.rate_limit || ''}${meta.wait_seconds ? `, 等待 ${meta.wait_seconds}s` : ''})`
  } else if (meta.error_type === 'context_overflow') {
    meta.summary = `📏 上下文超限 (最大 ${formatTokens(meta.max_context_tokens || 0)})`
  } else if (meta.error_type === 'auth_error') {
    meta.summary = '🔒 认证错误，请检查授权状态'
  } else {
    meta.summary = '⚠️ AI 服务错误'
  }

  return meta
}

function formatErrorAsMessage(error: string, meta: any): string {
  const parts = ['**⚠️ AI 服务错误**\n']

  if (meta.error_type === 'rate_limit') {
    if (meta.rate_limit_count && meta.rate_limit_seconds) {
      parts.push(`> 🚦 **速率限制**: 每 ${meta.rate_limit_seconds}秒 最多 ${meta.rate_limit_count} 次请求`)
    }
    if (meta.wait_seconds) {
      parts.push(`> ⏱️ **等待**: ${meta.wait_seconds} 秒后可重试`)
    }
    parts.push('\n💡 *建议：稍后重新发送消息，或切换到其他模型*')
  } else if (meta.error_type === 'context_overflow') {
    const limit = meta.max_context_tokens
    if (limit) {
      parts.push(`> 📏 **上下文超限**: 模型最大 ${formatTokens(limit)} tokens`)
    }
    if (meta.requested_tokens) {
      parts.push(`> 📊 **实际请求**: ${formatTokens(meta.requested_tokens)} tokens`)
    }
    parts.push('\n💡 *建议：删除部分历史消息，或切换到上下文更大的模型*')
  } else if (meta.error_type === 'auth_error') {
    parts.push('> 🔒 **认证失败**: 请前往设置页面检查 Copilot 授权状态')
  } else {
    // 通用错误 — 显示前 300 字符
    const brief = error.length > 300 ? error.slice(0, 300) + '...' : error
    parts.push('```\n' + brief + '\n```')
  }

  return parts.join('\n')
}

// 工具显示名称映射
const toolNames: Record<string, string> = {
  read_file: '📖 读取文件',
  search_text: '🔍 搜索',
  list_directory: '📂 列目录',
  get_file_tree: '🌳 目录树',
  ask_user: '❓ 提问',
}

/** 解析 ask_user 的 questions 参数 (支持新格式: options 为对象数组) */
interface QuestionOption {
  label: string
  description?: string
  recommended?: boolean
}
interface ParsedQuestion {
  question: string
  type: 'single' | 'multi'
  options: QuestionOption[]
  context?: string
}
function parseQuestions(args: any): ParsedQuestion[] {
  if (!args?.questions) return []
  try {
    const qs = typeof args.questions === 'string' ? JSON.parse(args.questions) : args.questions
    if (!Array.isArray(qs)) return []
    return qs.map((q: any) => ({
      question: q.question || '',
      type: q.type === 'multi' ? 'multi' : 'single',
      options: (q.options || []).map((opt: any) =>
        typeof opt === 'string' ? { label: opt } : { label: opt.label || '', description: opt.description, recommended: !!opt.recommended }
      ),
      context: q.context,
    }))
  } catch { return [] }
}

/** 问题卡片状态管理 (toolCallId → { answers, submitted }) */
interface QuestionCardState {
  answers: Record<number, string[]>  // questionIndex → selected labels
  customTexts: Record<number, string> // questionIndex → custom input text
  submitted: boolean
}
const questionCardStates = ref<Record<string, QuestionCardState>>({})

function getCardState(tcId: string): QuestionCardState {
  if (!questionCardStates.value[tcId]) {
    questionCardStates.value[tcId] = { answers: {}, customTexts: {}, submitted: false }
  }
  return questionCardStates.value[tcId]
}

function toggleOption(tcId: string, qi: number, label: string, type: 'single' | 'multi') {
  const state = getCardState(tcId)
  if (!state.answers[qi]) state.answers[qi] = []
  if (type === 'single') {
    state.answers[qi] = state.answers[qi][0] === label ? [] : [label]
  } else {
    const idx = state.answers[qi].indexOf(label)
    if (idx >= 0) state.answers[qi].splice(idx, 1)
    else state.answers[qi].push(label)
  }
}

function submitQuestionCard(tcId: string, questions: ParsedQuestion[]) {
  const state = getCardState(tcId)
  state.submitted = true

  // 格式化回答为用户消息
  const parts: string[] = []
  questions.forEach((q, qi) => {
    const selected = state.answers[qi] || []
    const custom = state.customTexts[qi]?.trim()
    if (selected.length || custom) {
      const answer = custom || selected.join('、')
      parts.push(`**${q.question}**\n${answer}`)
    }
    // 未回答的问题省略，AI 自行决定
  })

  if (parts.length === 0) {
    parts.push('以上问题由你来决定，请继续。')
  }

  // 添加标记，让 UI 可以识别这是 ask_user 回答，渲染为紧凑形式
  const content = `<!-- ask_user_response -->\n${parts.join('\n\n')}`
  sendMessage(content)
}

function toolDisplayName(name: string): string {
  return toolNames[name] || name
}

/** 追加流式内容到 streamContent + streamSegments */
function appendStreamContent(text: string) {
  streamContent.value += text
  const segs = streamSegments.value
  const last = segs[segs.length - 1]
  if (last && last.type === 'content') {
    last.text = (last.text || '') + text
  } else {
    segs.push({ type: 'content', text })
  }
}

function formatToolArgs(name: string, args: any): string {
  if (!args) return ''
  if (name === 'read_file') {
    let s = args.path || ''
    if (args.start_line) s += ` L${args.start_line}`
    if (args.end_line) s += `-${args.end_line}`
    return s
  }
  if (name === 'search_text') {
    let s = `"${args.query || ''}"`
    if (args.include_pattern) s += ` in ${args.include_pattern}`
    return s
  }
  if (name === 'list_directory' || name === 'get_file_tree') {
    return args.path || '.'
  }
  if (name === 'ask_user') {
    const qs = parseQuestions(args)
    return `${qs.length} 个问题`
  }
  return JSON.stringify(args)
}

// 图片上传
// 图片上传 (通过隐藏 input[type=file] 触发)
async function onFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = '' // 重置以允许重复选择同一文件
  try {
    const preview = URL.createObjectURL(file)
    const { data } = await discussionApi.uploadImage(props.project.id, file)
    pendingImages.value.push({ file, preview, uploaded: data })
  } catch (e: any) {
    message.error(e.response?.data?.detail || '图片上传失败')
  }
}

async function handleImageUpload({ file }: any) {
  try {
    const preview = URL.createObjectURL(file.file)
    const { data } = await discussionApi.uploadImage(props.project.id, file.file)
    pendingImages.value.push({
      file: file.file,
      preview,
      uploaded: data,
    })
  } catch (e: any) {
    message.error(e.response?.data?.detail || '图片上传失败')
  }
}

// ==================== 停止生成 ====================

function stopStreaming() {
  abortController.value?.abort()
  // 保留已生成的部分内容
  if (streamContent.value) {
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      sender_name: selectedModel.value,
      content: streamContent.value + '\n\n---\n*⏹ 已手动停止*',
      model_used: selectedModel.value,
      thinking_content: streamThinking.value || null,
      tool_calls: streamToolCalls.value.length ? [...streamToolCalls.value] : null,
      created_at: new Date().toISOString(),
    })
  }
  streaming.value = false
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  streamSegments.value = []
  abortController.value = null
  scrollToBottom()
}

// ==================== 消息操作 ====================

async function copyMessage(msg: any) {
  try {
    await navigator.clipboard.writeText(msg.content)
    message.success('已复制到剪贴板')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = msg.content
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    message.success('已复制到剪贴板')
  }
}

function confirmDeleteMessage(msg: any) {
  dialog.warning({
    title: '确认删除',
    content: `删除这条${msg.role === 'user' ? '用户' : 'AI'}消息？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => doDeleteMessage(msg),
  })
}

async function doDeleteMessage(msg: any) {
  try {
    // 只对有真实 DB ID 的消息发起删除请求 (Date.now() 生成的 ID > 1e12)
    if (msg.id && msg.id < 1e12) {
      await discussionApi.deleteMessage(props.project.id, msg.id)
    }
    messages.value = messages.value.filter(m => m.id !== msg.id)
    message.success('已删除')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

async function retryMessage(msg: any) {
  const retryContent = msg.content
  const retryAttachments = msg.attachments || []
  try {
    // 只对有真实 DB ID 的消息发起删除请求 (Date.now() 生成的 ID > 1e12)
    if (msg.id && msg.id < 1e12) {
      await discussionApi.deleteMessageAndAfter(props.project.id, msg.id)
    }
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx >= 0) messages.value = messages.value.slice(0, idx)
    await sendMessage(retryContent, retryAttachments)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '重试失败')
  }
}

async function regenerateMessage(msg: any) {
  try {
    // 只对有真实 DB ID 的消息发起删除请求 (Date.now() 生成的 ID > 1e12)
    if (msg.id && msg.id < 1e12) {
      await discussionApi.deleteMessage(props.project.id, msg.id)
    }
    messages.value = messages.value.filter(m => m.id !== msg.id)

    streaming.value = true
    streamContent.value = ''
    streamThinking.value = ''
    streamToolCalls.value = []
    streamSegments.value = []
    contextInfo.value = null
    tokenUsage.value = null
    summaryNotice.value = ''
    abortController.value = new AbortController()

    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    const response = await fetch(discussionApi.discussUrl(props.project.id), {
      method: 'POST',
      headers,
      body: JSON.stringify({ message: '', sender_name: 'user', regenerate: true, max_tool_rounds: currentModelToolRounds.value }),
      signal: abortController.value.signal,
    })

    await handleSSEResponse(response)
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      message.error('重新生成失败: ' + (e.message || ''))
    }
  } finally {
    streaming.value = false
    streamContent.value = ''
    streamThinking.value = ''
    streamToolCalls.value = []
    streamSegments.value = []
    abortController.value = null
    scrollToBottom()
    // 每次 AI 请求完成后刷新上下文使用率
    refreshContextInfo()
  }
}

// ==================== SSE 响应处理 (共用) ====================

// 标记 handleSSEResponse 是否已将内容添加到 messages
let sseContentSaved = false

async function handleSSEResponse(response: Response) {
  const reader = response.body?.getReader()
  const decoder = new TextDecoder()
  if (!reader) throw new Error('No response body')

  let savedThinking = ''
  let savedToolCalls: any[] = []
  sseContentSaved = false
  let streamTruncated = false
  let streamAskUserPending = false
  streamToolCalls.value = []
  streamSegments.value = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value, { stream: true })
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const data = JSON.parse(line.slice(6))
        if (data.type === 'content') {
          appendStreamContent(data.content)
          scrollToBottom()
        } else if (data.type === 'thinking') {
          streamThinking.value += data.content
          savedThinking += data.content
          scrollToBottom()
        } else if (data.type === 'context') {
          contextInfo.value = data.context
          persistentContextInfo.value = data.context  // 常驻保存
        } else if (data.type === 'summary') {
          summaryNotice.value = data.summary
          scrollToBottom()
        } else if (data.type === 'tool_call_start') {
          // ask_user 提前通知: 工具名已确认但参数还在流式中, 显示 loading 卡片
          const tc_data = data.tool_call || data
          const toolCall = {
            id: tc_data.id || '',
            name: tc_data.name || '',
            arguments: null as any,
            status: 'preparing' as const,
          }
          streamToolCalls.value.push(toolCall)
          streamSegments.value.push({ type: 'tool', toolCall })
          scrollToBottom()
        } else if (data.type === 'tool_call') {
          // backend sends: {type: 'tool_call', tool_call: {id, name, arguments}}
          const tc_data = data.tool_call || data
          const tcId = tc_data.id || data.tool_call_id || ''
          // 尝试合并已有的 preparing 段
          const existingTc = streamToolCalls.value.find(t => t.id === tcId)
          if (existingTc) {
            existingTc.arguments = tc_data.arguments || data.arguments || ''
            existingTc.status = 'calling'
          } else {
            const toolCall = {
              id: tcId,
              name: tc_data.name || data.name || '',
              arguments: tc_data.arguments || data.arguments || '',
              status: 'calling' as const,
            }
            streamToolCalls.value.push(toolCall)
            streamSegments.value.push({ type: 'tool', toolCall })
          }
          scrollToBottom()
        } else if (data.type === 'tool_result') {
          const tc = streamToolCalls.value.find(t => t.id === data.tool_call_id)
          if (tc) {
            tc.status = 'done'
            tc.result = data.result
            tc.duration_ms = data.duration_ms
          }
          savedToolCalls = [...streamToolCalls.value]
          scrollToBottom()
        } else if (data.type === 'tool_error') {
          const tc = streamToolCalls.value.find(t => t.id === data.tool_call_id)
          if (tc) {
            tc.status = 'error'
            tc.result = data.error
            tc.duration_ms = data.duration_ms
          }
          savedToolCalls = [...streamToolCalls.value]
          scrollToBottom()
        } else if (data.type === 'truncated') {
          // AI 输出因 max_tokens 截断，标记为需要自动继续
          streamTruncated = true
        } else if (data.type === 'ask_user_pending') {
          // AI 调用了 ask_user 后停止，等待用户回答
          // 不设 truncated，不自动继续，但保留 streaming 状态直到 done
          streamAskUserPending = true
        } else if (data.type === 'usage') {
          tokenUsage.value = data.usage
          lastTokenUsage.value = data.usage
        } else if (data.type === 'done') {
          // 有内容 或 有工具调用时保存消息 (AI 可能只调用 ask_user 无文本)
          if (streamContent.value || savedToolCalls.length) {
            messages.value.push({
              id: data.message_id || Date.now(),
              role: 'assistant',
              sender_name: selectedModel.value,
              content: streamContent.value || '',
              model_used: selectedModel.value,
              thinking_content: savedThinking || null,
              tool_calls: savedToolCalls.length ? savedToolCalls : null,
              token_usage: tokenUsage.value || null,
              created_at: new Date().toISOString(),
            })
            sseContentSaved = true
          }
        } else if (data.type === 'error') {
          const errorMeta = parseErrorMeta(data.error, data.error_meta)

          if (!streamContent.value && !sseContentSaved) {
            // 无内容生成 — 将错误作为聊天消息显示
            messages.value.push({
              id: Date.now(),
              role: 'assistant',
              sender_name: selectedModel.value,
              content: formatErrorAsMessage(data.error, errorMeta),
              model_used: selectedModel.value,
              thinking_content: savedThinking || null,
              tool_calls: savedToolCalls.length ? savedToolCalls : null,
              token_usage: tokenUsage.value || null,
              created_at: new Date().toISOString(),
            })
            sseContentSaved = true
            // 从错误中学习模型能力
            if (errorMeta.max_context_tokens || errorMeta.rate_limit) {
              studioConfig.updateModelCapability(selectedModel.value, errorMeta)
            }
          } else if (streamContent.value && !sseContentSaved) {
            // 有部分内容 — 保留已生成的部分并附加错误
            messages.value.push({
              id: Date.now(),
              role: 'assistant',
              sender_name: selectedModel.value,
              content: streamContent.value + '\n\n---\n' + formatErrorAsMessage(data.error, errorMeta),
              model_used: selectedModel.value,
              thinking_content: savedThinking || null,
              tool_calls: savedToolCalls.length ? savedToolCalls : null,
              token_usage: tokenUsage.value || null,
              created_at: new Date().toISOString(),
            })
            sseContentSaved = true
          }
          // 简短提示 (warning 不会自动消失)
          message.warning(errorMeta.summary || '⚠️ AI 服务错误', { duration: 10000 })
        }
      } catch {}
    }
  }

  // 流结束后, 如果有内容或工具调用但未保存 (没收到 done 也没收到 error), 兜底保存
  if ((streamContent.value || savedToolCalls.length) && !sseContentSaved) {
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      sender_name: selectedModel.value,
      content: streamContent.value || '',
      model_used: selectedModel.value,
      thinking_content: savedThinking || null,
      tool_calls: savedToolCalls.length ? savedToolCalls : null,
      token_usage: tokenUsage.value || null,
      created_at: new Date().toISOString(),
    })
    sseContentSaved = true
  }

  // 返回是否截断 (供调用方决定是否自动继续)
  return { truncated: streamTruncated }
}

// ==================== 发送消息 ====================

async function handleStartChat() {
  startingChat.value = true
  try {
    await sendMessage('', [], true)
  } finally {
    startingChat.value = false
  }
}

async function sendMessage(overrideContent?: string, overrideAttachments?: any[], regenerate = false) {
  const text = overrideContent ?? inputText.value.trim()
  const isOverride = overrideContent !== undefined

  if (!text && !pendingImages.value.length && !isOverride) return

  const attachments = isOverride
    ? (overrideAttachments || [])
    : pendingImages.value
        .filter(img => img.uploaded)
        .map(img => ({
          type: 'image',
          url: img.uploaded.url,
          base64: img.uploaded.base64,
          mime_type: img.uploaded.mime_type,
          name: img.file.name,
        }))

  // 使用认证用户的昵称作为发送者
  const senderName = authStore.user?.nickname || authStore.user?.username || 'user'

  if (!isOverride) {
    inputText.value = ''
    pendingImages.value = []
  }

  // regenerate 模式不推送用户消息（AI 直接发言）
  if (!regenerate) {
    messages.value.push({
      id: Date.now(),
      role: 'user',
      sender_name: senderName,
      content: text,
      attachments,
      created_at: new Date().toISOString(),
    })
    scrollToBottom()
  }

  streaming.value = true
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  streamSegments.value = []
  contextInfo.value = null
  tokenUsage.value = null
  summaryNotice.value = ''
  abortController.value = new AbortController()

  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    const response = await fetch(discussionApi.discussUrl(props.project.id), {
      method: 'POST',
      headers,
      body: JSON.stringify({ message: text, sender_name: senderName, attachments, max_tool_rounds: currentModelToolRounds.value, regenerate }),
      signal: abortController.value.signal,
    })

    // 处理非流式响应 (AI 正在输出 / AI 禁言)
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const result = await response.json()
      if (result.status === 'queued') {
        message.info('AI 正在输出中，你的消息已保存，稍后一并回复')
      } else if (result.status === 'muted') {
        message.info('AI 已禁言，消息已保存')
      }
      streaming.value = false
      streamContent.value = ''
      streamThinking.value = ''
      streamToolCalls.value = []
      streamSegments.value = []
      abortController.value = null
      return
    }

    const sseResult = await handleSSEResponse(response)

    // 自动继续: AI 输出因 max_tokens 截断时自动发 "请继续"
    if (sseResult?.truncated && autoContinueCount < studioConfig.maxAutoContinues) {
      autoContinueCount++
      streaming.value = false
      streamContent.value = ''
      streamThinking.value = ''
      streamToolCalls.value = []
      streamSegments.value = []
      abortController.value = null
      await new Promise(r => setTimeout(r, 300))
      message.info(`AI 输出被截断，自动继续 (${autoContinueCount}/${studioConfig.maxAutoContinues})`)
      await sendMessage('请继续上面没说完的内容')
      return
    }
    autoContinueCount = 0
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      message.error('AI 通信异常: ' + (e.message || ''))
    }
  } finally {
    streaming.value = false
    streamContent.value = ''
    streamThinking.value = ''
    streamToolCalls.value = []
    streamSegments.value = []
    abortController.value = null
    scrollToBottom()
    // 每次 AI 请求完成后刷新上下文使用率
    refreshContextInfo()
  }
}

// 敲定方案
async function handleFinalizePlan() {
  finalizingPlan.value = true
  streaming.value = true
  streamContent.value = ''
  streamThinking.value = ''
  streamSegments.value = []
  abortController.value = new AbortController()

  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    const response = await fetch(discussionApi.finalizePlanUrl(props.project.id), {
      method: 'POST',
      headers,
      signal: abortController.value.signal,
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    if (!reader) throw new Error('No response body')

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value, { stream: true })
      for (const line of text.split('\n')) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'content') {
            appendStreamContent(data.content)
            scrollToBottom()
          } else if (data.type === 'thinking') {
            streamThinking.value += data.content
            scrollToBottom()
          } else if (data.type === 'done') {
            message.success(`设计稿已生成 (v${data.plan_version})`)
            emit('plan-finalized')
          } else if (data.type === 'error') {
            message.error(data.error)
          }
        } catch {}
      }
    }

    // 保存 plan 消息到列表
    if (streamContent.value) {
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        sender_name: `Plan Generator (${selectedModel.value})`,
        content: streamContent.value,
        message_type: 'plan_final',
        created_at: new Date().toISOString(),
      })
    }
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      message.error('Plan 生成异常: ' + (e.message || ''))
    }
  } finally {
    finalizingPlan.value = false
    streaming.value = false
    streamContent.value = ''
    streamThinking.value = ''
    streamSegments.value = []
    abortController.value = null
    scrollToBottom()
  }
}

// ==================== AI 禁言控制 ====================

async function toggleAiMute() {
  muteLoading.value = true
  try {
    const { data } = await discussionApi.toggleAiMute(props.project.id)
    aiMuted.value = data.ai_muted
    if (data.ai_muted) {
      message.warning('AI 已禁言 · 仅人工讨论模式')
    } else {
      message.success('AI 已解除禁言 · 发送消息将触发 AI 回复')
    }
  } catch (e: any) {
    if (e.response?.status === 401) {
      message.error('Token 已过期，请刷新页面重新登录')
    } else {
      message.error(e.response?.data?.detail || '操作失败')
    }
  } finally {
    muteLoading.value = false
  }
}

// ==================== 上下文管理 ====================

async function handleSummarize() {
  summarizing.value = true
  try {
    const { data } = await discussionApi.summarizeContext(props.project.id)
    message.success(`已总结 ${data.summarized_count} 条旧消息 → 1 条摘要`)
    // 刷新消息列表
    const { data: msgs } = await discussionApi.getMessages(props.project.id)
    messages.value = msgs
    scrollToBottom()
    // 刷新上下文使用率
    refreshContextInfo()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '总结失败')
  } finally {
    summarizing.value = false
  }
}

function handleClearContext() {
  dialog.warning({
    title: '确认清空',
    content: '将删除所有讨论消息，此操作不可撤销。确定清空？',
    positiveText: '清空',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await discussionApi.clearContext(props.project.id)
        messages.value = []
        persistentContextInfo.value = null
        message.success('已清空所有讨论消息')
      } catch (e: any) {
        message.error(e.response?.data?.detail || '清空失败')
      }
    },
  })
}

// 轮询远程流式输出状态 (检测其他用户是否在使用 AI)
function startStreamingPoll() {
  stopStreamingPoll() // 确保不重复启动
  streamingPollTimer = setInterval(async () => {
    if (streaming.value) return // 自己正在流式输出, 不需要轮询
    try {
      const { data } = await discussionApi.getStreamingStatus(props.project.id)
      const wasStreaming = remoteStreaming.value
      remoteStreaming.value = data.streaming
      // 远程流式结束时刷新消息列表 (可能有新 AI 回复)
      if (wasStreaming && !data.streaming) {
        const { data: msgs } = await discussionApi.getMessages(props.project.id)
        messages.value = msgs
        scrollToBottom()
        refreshContextInfo()
      }
    } catch {}
  }, 5000)
}

function stopStreamingPoll() {
  if (streamingPollTimer) {
    clearInterval(streamingPollTimer)
    streamingPollTimer = null
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function handleModelChange(val: string) {
  try {
    await projectApi.update(props.project.id, { discussion_model: val })
  } catch {}

  // 切换模型后检查上下文使用情况
  const myVersion = ++contextCheckVersion
  contextCompressing.value = true
  try {
    const { data } = await discussionApi.checkContext(props.project.id, val)
    // 快速切换时忽略过期结果
    if (myVersion !== contextCheckVersion) return
    if (data.context) {
      persistentContextInfo.value = data.context
    }
    if (data.summarized && data.summary_text) {
      message.info('上下文已自动压缩以适应新模型窗口')
    }
  } catch {} finally {
    if (myVersion === contextCheckVersion) {
      contextCompressing.value = false
    }
  }
}

onMounted(async () => {
  // 加载消息历史
  try {
    const { data } = await discussionApi.getMessages(props.project.id)
    messages.value = data
    scrollToTop()
  } catch {}

  // 加载 AI 禁言状态
  try {
    const { data } = await discussionApi.getAiMuteStatus(props.project.id)
    aiMuted.value = data.ai_muted
  } catch {}

  // 加载模型列表 (使用后端缓存，不阻塞页面; 手动点击刷新按钮强制刷新)
  modelApi.list({ category: 'discussion', custom_models: studioConfig.customModelsEnabled }).then(({ data }) => {
    models.value = data
    if (data.length && !data.find((m: any) => m.id === selectedModel.value)) {
      selectedModel.value = data[0].id
    }
    // 模型加载完成后，获取当前模型的上下文使用率
    refreshContextInfo()
  }).catch(() => {})

  // 兜底: 即使模型列表加载慢/失败，也尝试用默认模型获取上下文
  setTimeout(() => {
    if (!persistentContextInfo.value) refreshContextInfo()
  }, 3000)

  // 启动远程流式输出轮询
  startStreamingPoll()
})

onUnmounted(() => {
  stopStreamingPoll()
})
</script>

<style>
.markdown-body {
  color: #e0e0e0;
  line-height: 1.5;
  font-size: 13px;
}
.markdown-body pre {
  background: #0d1b2a;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.markdown-body code {
  background: #0d1b2a;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}
.markdown-body pre code {
  background: none;
  padding: 0;
}
.markdown-body p { margin: 0.4em 0; }
.markdown-body h1, .markdown-body h2, .markdown-body h3 { color: #e94560; margin: 0.6em 0 0.3em; }
.markdown-body ul, .markdown-body ol { padding-left: 1.5em; }
.markdown-body blockquote {
  border-left: 3px solid #e94560;
  margin: 0.4em 0;
  padding: 0.3em 0.8em;
  background: rgba(233, 69, 96, 0.1);
}
.markdown-body table { border-collapse: collapse; width: 100%; }
.markdown-body th, .markdown-body td { border: 1px solid #333; padding: 4px 10px; }
.markdown-body th { background: #0d1b2a; }
.markdown-body img { max-width: 100%; border-radius: 6px; }
.thinking-block {
  color: #999;
  font-size: 12px;
  line-height: 1.4;
  font-style: italic;
  border-left: 2px solid #555;
  padding-left: 8px;
  margin: 3px 0;
}
.thinking-block p { margin: 0.2em 0; }

/* 消息操作按钮 (header 内联, 默认半透明) */
.msg-actions {
  opacity: 0.2;
  transition: opacity 0.15s ease;
  flex-shrink: 0;
}
.msg-actions:hover, .msg-actions-visible {
  opacity: 0.8;
}
.msg-actions .n-button {
  padding: 0 3px !important;
}

/* Tool call visualization */
.tool-group-header {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 6px;
  font-size: 11px;
  color: #63e2b7;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
  user-select: none;
}
.tool-group-header:hover {
  background: rgba(99, 226, 183, 0.06);
}
.tool-group-arrow {
  font-size: 8px;
  transition: transform 0.15s;
  color: #666;
}
.tool-group-arrow.open {
  transform: rotate(90deg);
}
.tool-group-icon {
  font-size: 12px;
}
.tool-group-count {
  font-size: 11px;
  color: #888;
}
.tool-group-body {
  margin-left: 4px;
}
.question-result-text {
  padding: 4px 0;
  font-size: 12px;
  color: #aaa;
}
.tool-inline {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  margin: 2px 0;
  font-size: 11px;
  color: #aaa;
  background: rgba(99, 226, 183, 0.04);
  border-left: 2px solid rgba(99, 226, 183, 0.4);
  border-radius: 0 4px 4px 0;
  line-height: 1.6;
  flex-wrap: wrap;
}
.tool-inline-name {
  color: #e0e0e0;
  font-weight: 500;
  white-space: nowrap;
}
.tool-inline-args {
  color: #888;
  font-size: 10px;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  background: none;
  padding: 0;
  word-break: break-all;
}
.tool-inline-time {
  color: #666;
  font-size: 10px;
  white-space: nowrap;
}
.tool-inline-view {
  color: #63e2b7;
  font-size: 10px;
  cursor: pointer;
  white-space: nowrap;
  margin-left: 2px;
  text-decoration: underline;
  text-decoration-style: dotted;
}
.tool-inline-view:hover {
  color: #7eebca;
}
.tool-call-item {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 5px;
  padding: 4px 8px;
  margin: 3px 0;
  font-size: 11px;
}
.tool-call-header {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
  color: #ccc;
}
.tool-result-content {
  color: #999;
  font-size: 10px;
  margin-top: 3px;
  max-height: 160px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  padding: 4px 6px;
}
.tool-icon-ok { color: #63e2b7; }
.tool-icon-error { color: #e88080; }
.tool-icon-pending { color: #f2c97d; }

/* ============ ask_user 问题卡片 ============ */
.question-card {
  background: linear-gradient(135deg, rgba(99, 226, 183, 0.06), rgba(14, 165, 233, 0.06));
  border: 1px solid rgba(99, 226, 183, 0.2);
  border-radius: 8px;
  padding: 10px 12px;
  margin: 6px 0;
}
.question-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.question-card-header-done {
  margin-bottom: 4px;
  padding-bottom: 4px;
}
.question-card-icon {
  font-size: 14px;
  flex-shrink: 0;
}
.question-card-title {
  color: #63e2b7;
  font-size: 12px;
  font-weight: 600;
}
.question-card-hint {
  color: #666;
  font-size: 10px;
  margin-left: auto;
}
.question-type-tag {
  display: inline-block;
  font-size: 10px;
  color: #0ea5e9;
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(14, 165, 233, 0.3);
  border-radius: 3px;
  padding: 0 4px;
  margin-left: 6px;
  vertical-align: middle;
  font-weight: 400;
}
.question-item {
  margin-bottom: 10px;
}
.question-item:last-child {
  margin-bottom: 0;
}
.question-text {
  color: #e0e0e0;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
  margin-bottom: 3px;
}
.question-context {
  color: #777;
  font-size: 11px;
  line-height: 1.3;
  margin-bottom: 5px;
  padding-left: 14px;
  font-style: italic;
}
.question-options {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  padding-left: 14px;
}
.question-option-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  font-size: 12px;
  color: #b0b0b0;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
  line-height: 1.4;
}
.question-option-btn:hover {
  color: #e0e0e0;
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.25);
}
/* 推荐标记 (未选中时显示) */
.question-option-recommended {
  color: #63e2b7;
  border-color: rgba(99, 226, 183, 0.3);
  background: rgba(99, 226, 183, 0.06);
}
.question-option-recommended:hover {
  border-color: rgba(99, 226, 183, 0.5);
  background: rgba(99, 226, 183, 0.12);
}
.rec-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: #63e2b7;
  border-radius: 50%;
  flex-shrink: 0;
}
/* 选中状态 */
.question-option-selected {
  color: #fff !important;
  background: rgba(99, 226, 183, 0.25) !important;
  border-color: #63e2b7 !important;
}
.option-desc {
  color: #777;
  font-size: 10px;
  margin-left: 2px;
}
.question-option-selected .option-desc {
  color: rgba(255,255,255,0.6);
}
.question-custom-input {
  display: block;
  width: calc(100% - 14px);
  margin: 6px 0 0 14px;
  padding: 4px 8px;
  font-size: 12px;
  color: #e0e0e0;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  outline: none;
  transition: border-color 0.15s;
}
.question-custom-input:focus {
  border-color: rgba(99, 226, 183, 0.5);
}
.question-custom-input::placeholder {
  color: #555;
}
.question-submit-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
/* 已回答的紧凑摘要 */
.question-summary-row {
  display: flex;
  gap: 6px;
  font-size: 11px;
  line-height: 1.5;
  padding: 1px 0;
}
.question-summary-q {
  color: #888;
  flex-shrink: 0;
  max-width: 50%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.question-summary-a {
  color: #63e2b7;
  font-weight: 500;
}
/* AI 自行决定的推荐答案 (区别于用户选择的绿色) */
.question-summary-a-auto {
  color: #8a8a8a;
  font-weight: 400;
  font-style: italic;
}
/* 问题准备中骨架屏 */
.question-preparing-body {
  padding: 4px 0;
}
.question-preparing-skeleton {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: skeleton-shimmer 1.5s infinite;
}
.skeleton-options {
  display: flex;
  gap: 6px;
  padding-left: 14px;
}
.skeleton-pill {
  height: 24px;
  width: 60px;
  background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%);
  background-size: 200% 100%;
  border-radius: 12px;
  animation: skeleton-shimmer 1.5s infinite;
}
@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ============ 项目信息栏 ============ */
.project-info-bar {
  display: flex;
  align-items: center;
  padding: 3px 10px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  cursor: pointer;
  gap: 6px;
  flex-shrink: 0;
  transition: background 0.15s;
}
.project-info-bar:hover {
  background: rgba(255,255,255,0.05);
}
.project-info-title {
  font-weight: 600;
  font-size: 12px;
  color: rgba(255,255,255,0.8);
}
.project-info-sep {
  margin: 0 4px;
  opacity: 0.25;
  font-size: 11px;
}
.project-info-desc {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
}
.project-info-edit-icon {
  font-size: 11px;
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
}
.project-info-bar:hover .project-info-edit-icon {
  opacity: 0.5;
}

/* ============ 上下文明细气泡 (树形检查器) ============ */
.ctx-breakdown {
  padding: 10px 12px;
  min-width: 240px;
  max-width: 360px;
  max-height: 420px;
  overflow-y: auto;
  font-size: 12px;
}
.ctx-breakdown-title {
  font-weight: 600;
  color: #e0e0e0;
  margin-bottom: 8px;
}
.ctx-breakdown-bar {
  display: flex;
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
  background: rgba(255,255,255,0.06);
  margin-bottom: 10px;
}
.ctx-bar-seg {
  height: 100%;
  min-width: 1px;
  transition: width 0.3s;
}
.ctx-bar-system { background: #a855f7; }
.ctx-bar-tools { background: #0ea5e9; }
.ctx-bar-history { background: #f59e0b; }

/* 树形节点 */
.ctx-tree { display: flex; flex-direction: column; gap: 1px; }
.ctx-tree-node { display: flex; flex-direction: column; }
.ctx-tree-row {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 0;
  color: #bbb;
  font-size: 11px;
  cursor: pointer;
  border-radius: 3px;
  transition: background 0.1s;
}
.ctx-tree-row:hover { background: rgba(255,255,255,0.04); }
.ctx-tree-row-child { padding-left: 16px; }
.ctx-tree-row-leaf { padding-left: 32px; cursor: default; }
.ctx-clickable-row { cursor: pointer !important; }
.ctx-clickable { text-decoration-style: dotted; text-decoration-line: underline; text-underline-offset: 2px; text-decoration-color: #555; }
.ctx-clickable:hover { color: #e0e0e0; text-decoration-color: #999; }
.ctx-tree-arrow {
  font-size: 8px;
  width: 10px;
  text-align: center;
  flex-shrink: 0;
  transition: transform 0.15s;
  color: #666;
}
.ctx-tree-arrow.open { transform: rotate(90deg); }
.ctx-tree-leaf { font-size: 9px; color: #444; }
.ctx-tree-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ctx-tree-children {
  display: flex;
  flex-direction: column;
}
.ctx-tree-msg-label {
  display: flex;
  align-items: center;
  gap: 4px;
}
.ctx-msg-preview {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
  color: #777;
}
.ctx-role-user { color: #0ea5e9; }
.ctx-role-assistant { color: #e94560; }
.ctx-role-system { color: #63e2b7; }

.ctx-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ctx-val {
  margin-left: auto;
  color: #ddd;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.ctx-tree-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(255,255,255,0.08);
  color: #aaa;
  font-size: 11px;
}
.ctx-breakdown-msgs {
  margin-top: 4px;
  color: #888;
  font-size: 10px;
}

/* ask_user 回答紧凑指示器 */
.ask-user-reply-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 10px;
  background: rgba(14, 165, 233, 0.08);
  color: #8aa;
  font-size: 11px;
}
.ask-reply-detail-link {
  cursor: pointer;
  color: #0ea5e9;
  font-size: 10px;
  opacity: 0.7;
  transition: opacity 0.15s;
}
.ask-reply-detail-link:hover { opacity: 1; }

/* ============ 输入区布局 ============ */
.input-area {
  background: #16213e;
  border-radius: 8px;
  padding: 5px 8px;
  flex-shrink: 0;
}

/* 第 1 行工具栏: flexbox + nowrap + 模型选择器自动缩小 */
.toolbar-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}
.toolbar-row > * {
  flex-shrink: 0;
}
/* 模型选择器适应内容宽度，空间不足时可缩小 */
.model-select-group {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  min-width: 100px;
  overflow: hidden;
}
.model-select-group .n-select {
  min-width: 0;
}
.model-select-group .n-base-selection {
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}
.model-refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 28px;
  border: 1px solid rgba(255,255,255,0.15);
  border-left: none;
  border-radius: 0 4px 4px 0;
  background: rgba(255,255,255,0.04);
  color: #aaa;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.model-refresh-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.1);
  color: #e0e0e0;
}
.model-refresh-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 第 3 行操作栏 */
.action-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-top: 2px;
}
.action-bar-item {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.action-bar-stat {
  font-size: 10px;
  color: rgba(255,255,255,0.35);
  white-space: nowrap;
  flex-shrink: 0;
}
.action-bar-spring {
  flex: 1;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.spin-icon {
  display: inline-block;
  animation: spin 0.8s linear infinite;
}

/* 上下文内容气泡 */
.ctx-content-pre {
  margin: 0;
  padding: 0;
  font-family: 'Menlo', 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #ccc;
  white-space: pre-wrap;
  word-break: break-all;
  background: transparent;
}

/* 空对话欢迎状态 */
.empty-chat-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 280px;
  padding: 40px 20px;
  opacity: 0;
  animation: fadeInUp 0.5s ease forwards;
}
.empty-chat-icon {
  font-size: 56px;
  margin-bottom: 12px;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.3));
  animation: gentleBounce 2s ease-in-out infinite;
}
.empty-chat-title {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255,255,255,0.85);
  margin-bottom: 6px;
}
.empty-chat-desc {
  font-size: 13px;
  color: rgba(255,255,255,0.4);
  max-width: 320px;
  text-align: center;
  line-height: 1.5;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes gentleBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
</style>
