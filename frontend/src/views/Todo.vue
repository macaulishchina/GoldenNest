<template>
  <div class="todo-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>📋 家庭清单</h1>
      <p>共享待办事项，让家庭生活更有条理</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-bar" v-if="stats">
      <div class="stat-card">
        <span class="stat-number">{{ stats.pending_tasks }}</span>
        <span class="stat-label">待完成</span>
      </div>
      <div class="stat-card">
        <span class="stat-number">{{ stats.my_pending }}</span>
        <span class="stat-label">我的任务</span>
      </div>
      <div class="stat-card urgent">
        <span class="stat-number">{{ stats.due_today }}</span>
        <span class="stat-label">今日截止</span>
      </div>
      <div class="stat-card success">
        <span class="stat-number">{{ stats.completion_rate }}%</span>
        <span class="stat-label">完成率</span>
      </div>
    </div>

    <div class="todo-container">
      <!-- 左侧：清单列表 -->
      <div class="lists-panel">
        <div class="panel-header">
          <h3>我的清单</h3>
          <button class="btn-add-list" @click="showListModal = true">+</button>
        </div>
        
        <div class="lists-wrapper">
          <div 
            v-for="list in todoLists" 
            :key="list.id"
            class="list-item"
            :class="{ active: currentListId === list.id }"
            @click="selectList(list.id)"
          >
            <span class="list-icon" :style="{ backgroundColor: list.color + '20' }">{{ list.icon }}</span>
            <span class="list-name">{{ list.name }}</span>
            <span class="list-count">{{ list.item_count - list.completed_count }}</span>
            <button class="btn-edit-list" @click.stop="editList(list)">⋮</button>
          </div>
        </div>

        <div class="list-item add-new" @click="showListModal = true">
          <span class="list-icon">➕</span>
          <span class="list-name">新建清单</span>
        </div>
      </div>

      <!-- 右侧：任务列表 -->
      <div class="tasks-panel">
        <div class="panel-header" v-if="currentList">
          <div class="current-list-info">
            <span class="list-icon large" :style="{ backgroundColor: currentList.color + '20' }">
              {{ currentList.icon }}
            </span>
            <h3>{{ currentList.name }}</h3>
          </div>
          <div class="task-actions">
            <button class="btn-ai-assist" @click="showAIDialog = true" title="AI 任务助手">
              🤖 AI
            </button>
            <label class="toggle-completed">
              <input type="checkbox" v-model="showCompleted" @change="loadItems">
              显示已完成
            </label>
          </div>
        </div>

        <!-- 快速添加任务 -->
        <div class="quick-add" v-if="currentListId">
          <input 
            v-model="quickAddTitle"
            @keyup.enter="quickAddItem"
            placeholder="添加新任务或试试 AI 任务建议 🤖"
            class="quick-add-input"
          />
          <button class="btn-quick-add" @click="quickAddItem">添加</button>
        </div>

        <!-- 加载状态 -->
        <div v-if="loadingItems" class="loading">
          <span class="spinner"></span>
          <p>加载中...</p>
        </div>

        <!-- 任务列表 -->
        <div v-else-if="currentListId" class="items-list">
          <div v-if="todoItems.length === 0" class="empty-state">
            <div class="empty-icon">✅</div>
            <p>暂无任务，开始添加吧！</p>
          </div>

          <div 
            v-for="item in todoItems" 
            :key="item.id"
            class="task-item"
            :class="{ 
              completed: item.is_completed,
              ['priority-' + item.priority]: true
            }"
          >
            <div class="task-checkbox" @click="toggleComplete(item)">
              <span v-if="item.is_completed">✅</span>
              <span v-else class="checkbox-empty"></span>
            </div>

            <div class="task-content" @click="editItem(item)">
              <div class="task-title">{{ item.title }}</div>
              <div class="task-meta">
                <span v-if="item.assignee_name" class="meta-tag assignee">
                  <UserAvatar 
                    :userId="item.assignee_id" 
                    :name="item.assignee_name" 
                    :size="16" 
                    :avatarVersion="item.assignee_avatar_version" 
                  />
                  {{ item.assignee_name }}
                </span>
                <span v-if="item.due_date" class="meta-tag due-date" :class="{ overdue: isOverdue(item.due_date) }">
                  📅 {{ formatDueDate(item.due_date) }}
                </span>
                <span v-if="item.repeat_type !== 'none'" class="meta-tag repeat">
                  🔄 {{ getRepeatText(item.repeat_type) }}
                </span>
              </div>
            </div>

            <div class="task-priority" :class="item.priority">
              {{ getPriorityIcon(item.priority) }}
            </div>

            <button class="btn-delete-item" @click.stop="deleteItem(item)">🗑️</button>
          </div>
        </div>

        <!-- 未选择清单 -->
        <div v-else class="empty-state select-list">
          <div class="empty-icon">📋</div>
          <p>请选择或创建一个清单</p>
        </div>
      </div>
    </div>

    <!-- AI 任务助手弹窗 -->
    <div v-if="showAIDialog" class="modal-overlay" @click.self="showAIDialog = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>🤖 AI 任务助手</h2>
          <button class="btn-close-modal" @click="closeAIDialog">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
        
        <div class="ai-tabs">
          <button 
            class="ai-tab" 
            :class="{ active: aiMode === 'suggest' }"
            @click="aiMode = 'suggest'"
          >
            💡 任务建议
          </button>
          <button 
            class="ai-tab" 
            :class="{ active: aiMode === 'prioritize' }"
            @click="aiMode = 'prioritize'"
          >
            📊 优先级分析
          </button>
        </div>

        <!-- 任务建议模式 -->
        <div v-if="aiMode === 'suggest'" class="ai-content">
          <div class="form-group">
            <label>描述你的目标或需求</label>
            <textarea
              v-model="aiGoal"
              placeholder="例如：我要准备全家春节旅行、整理家里的杂物、学习新技能..."
              rows="4"
              class="ai-input"
            ></textarea>
          </div>
          
          <button 
            class="btn-ai-suggest" 
            @click="getAISuggestions"
            :disabled="aiLoading || !aiGoal.trim()"
          >
            <span v-if="aiLoading" class="btn-loading">
              <svg class="spinner" viewBox="0 0 50 50">
                <circle cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
              </svg>
              AI 分析中...
            </span>
            <span v-else>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="margin-right: 6px;">
                <path d="M8 2L8 14M2 8L14 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              获取 AI 建议
            </span>
          </button>

          <!-- AI 建议结果 -->
          <div v-if="aiSuggestions" class="ai-results">
            <div class="ai-reasoning">
              <p><strong>💭 分析思路：</strong></p>
              <p>{{ aiSuggestions.reasoning }}</p>
            </div>
            
            <div class="suggested-tasks">
              <p><strong>📝 建议任务：</strong></p>
              <div 
                v-for="(task, index) in aiSuggestions.suggested_tasks"
                :key="index"
                class="suggested-task"
              >
                <div class="task-header">
                  <span class="task-title">{{ task.title }}</span>
                  <span class="task-priority" :class="task.priority">
                    {{ getPriorityLabel(task.priority) }}
                  </span>
                </div>
                <p class="task-desc">{{ task.description }}</p>
                <p class="task-due">建议 {{ task.due_days }} 天内完成</p>
                <button 
                  v-if="!addedSuggestedTaskIndexes.has(index)"
                  class="btn-add-suggested"
                  @click="addSuggestedTask(task, index)"
                  :disabled="addingTaskIndex === index"
                >
                  <span v-if="addingTaskIndex === index" class="btn-loading-small">
                    <svg class="spinner-small" viewBox="0 0 50 50">
                      <circle cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
                    </svg>
                    添加中...
                  </span>
                  <span v-else>添加到清单</span>
                </button>
                <span v-else class="adopted-badge">✓ 已添加</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 优先级分析模式 -->
        <div v-if="aiMode === 'prioritize'" class="ai-content">
          <div class="form-group">
            <label>AI 将分析当前清单中的待办任务，给出优先级建议</label>
          </div>
          
          <button 
            class="btn-ai-suggest" 
            @click="getAIPrioritization"
            :disabled="aiLoading || !hasPendingTasks"
          >
            <span v-if="aiLoading" class="btn-loading">
              <svg class="spinner" viewBox="0 0 50 50">
                <circle cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
              </svg>
              AI 分析中...
            </span>
            <span v-else>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="margin-right: 6px;">
                <path d="M8 2L8 14M2 8L14 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              开始分析
            </span>
          </button>

          <!-- AI 优先级结果 -->
          <div v-if="aiPrioritization" class="ai-results">
            <div class="ai-advice">
              <p><strong>💡 整体建议：</strong></p>
              <p>{{ aiPrioritization.overall_advice }}</p>
            </div>
            
            <div class="prioritized-tasks">
              <p><strong>📊 任务优先级：</strong></p>
              <div 
                v-for="(task, index) in aiPrioritization.prioritized_tasks"
                :key="task.task_id"
                class="prioritized-task"
              >
                <div class="task-rank">#{{ index + 1 }}</div>
                <div class="task-info">
                  <div class="task-header">
                    <span class="task-title">{{ task.title }}</span>
                    <span class="task-priority" :class="task.suggested_priority">
                      {{ getPriorityLabel(task.suggested_priority) }}
                    </span>
                  </div>
                  <div class="task-urgency">
                    紧急度：{{ task.urgency_score }}/100
                  </div>
                  <p class="task-reasoning">{{ task.reasoning }}</p>
                  <button 
                    v-if="!adoptedTaskIds.has(task.task_id) && shouldShowAdoptButton(task)"
                    class="btn-add-suggested"
                    @click="adoptPrioritySuggestion(task)"
                    :disabled="adoptingTaskId === task.task_id"
                  >
                    <span v-if="adoptingTaskId === task.task_id" class="btn-loading-small">
                      <svg class="spinner-small" viewBox="0 0 50 50">
                        <circle cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
                      </svg>
                      采纳中...
                    </span>
                    <span v-else>采纳建议</span>
                  </button>
                  <span v-else-if="adoptedTaskIds.has(task.task_id)" class="adopted-badge">✓ 已采纳</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑清单弹窗 -->
    <div v-if="showListModal" class="modal-overlay" @click.self="closeListModal">
      <div class="modal-content small">
        <h2>{{ editingList ? '编辑清单' : '新建清单' }}</h2>
        
        <div class="form-group">
          <label>清单名称</label>
          <input v-model="listForm.name" placeholder="请输入清单名称" maxlength="50" />
        </div>

        <div class="form-group">
          <label>图标</label>
          <div class="icon-picker">
            <span 
              v-for="icon in listIcons" 
              :key="icon"
              class="icon-option"
              :class="{ selected: listForm.icon === icon }"
              @click="listForm.icon = icon"
            >{{ icon }}</span>
          </div>
        </div>

        <div class="form-group">
          <label>颜色</label>
          <div class="color-picker">
            <span 
              v-for="color in listColors" 
              :key="color"
              class="color-option"
              :class="{ selected: listForm.color === color }"
              :style="{ backgroundColor: color }"
              @click="listForm.color = color"
            ></span>
          </div>
        </div>

        <div class="modal-actions">
          <button v-if="editingList" class="btn-danger" @click="deleteList">删除清单</button>
          <div class="spacer"></div>
          <button class="btn-cancel" @click="closeListModal">取消</button>
          <button class="btn-submit" @click="saveList" :disabled="!listForm.name">
            保存
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑任务弹窗 -->
    <div v-if="showItemModal" class="modal-overlay" @click.self="closeItemModal">
      <div class="modal-content">
        <h2>{{ editingItem ? '编辑任务' : '添加任务' }}</h2>
        
        <div class="form-group">
          <label>任务标题</label>
          <input v-model="itemForm.title" placeholder="请输入任务标题" />
        </div>

        <div class="form-group">
          <label>详细描述</label>
          <textarea v-model="itemForm.description" placeholder="添加备注..." rows="3"></textarea>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>指派给</label>
            <select v-model="itemForm.assignee_id">
              <option :value="null">不指派</option>
              <option v-for="member in familyMembers" :key="member.id" :value="member.id">
                {{ member.nickname }}
              </option>
            </select>
          </div>

          <div class="form-group half">
            <label>优先级</label>
            <select v-model="itemForm.priority">
              <option value="low">🟢 低</option>
              <option value="medium">🟡 中</option>
              <option value="high">🔴 高</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>截止日期</label>
            <input type="datetime-local" v-model="itemForm.due_date" />
          </div>

          <div class="form-group half">
            <label>重复</label>
            <select v-model="itemForm.repeat_type">
              <option value="none">不重复</option>
              <option value="daily">每天</option>
              <option value="weekly">每周</option>
              <option value="monthly">每月</option>
            </select>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-cancel" @click="closeItemModal">取消</button>
          <button class="btn-submit" @click="saveItem" :disabled="!itemForm.title">
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, todoAiApi } from '@/api'
import { useMessage } from 'naive-ui'
import UserAvatar from '@/components/UserAvatar.vue'

const message = useMessage()

// 状态
const loading = ref(true)
const loadingItems = ref(false)
const todoLists = ref([])
const todoItems = ref([])
const currentListId = ref(null)
const showCompleted = ref(true)
const stats = ref(null)
const familyMembers = ref([])

// AI 助手
const showAIDialog = ref(false)
const aiMode = ref('suggest') // 'suggest' | 'prioritize'
const aiLoading = ref(false)
const aiGoal = ref('')
const aiSuggestions = ref(null)
const aiPrioritization = ref(null)
const adoptingTaskId = ref(null)
const adoptedTaskIds = ref(new Set())
const addedSuggestedTaskIndexes = ref(new Set())
const addingTaskIndex = ref(null)

// 快速添加
const quickAddTitle = ref('')

// 清单弹窗
const showListModal = ref(false)
const editingList = ref(null)
const listForm = ref({
  name: '',
  icon: '📋',
  color: '#667eea'
})

// 任务弹窗
const showItemModal = ref(false)
const editingItem = ref(null)
const itemForm = ref({
  title: '',
  description: '',
  assignee_id: null,
  priority: 'medium',
  due_date: '',
  repeat_type: 'none'
})

// 可选图标和颜色
const listIcons = ['📋', '🛒', '🏠', '💼', '📚', '🎯', '🎨', '🍽️', '🧹', '💪', '🎁', '✈️']
const listColors = ['#667eea', '#f97316', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

// 计算属性
const currentList = computed(() => {
  return todoLists.value.find(l => l.id === currentListId.value)
})

const hasPendingTasks = computed(() => {
  return todoItems.value.some(item => !item.completed)
})

// AI 助手方法
async function getAISuggestions() {
  if (!aiGoal.value.trim()) return
  
  aiLoading.value = true
  try {
    const response = await todoAiApi.suggest({
      context: aiGoal.value
    })
    aiSuggestions.value = response.data
  } catch (error) {
    console.error('AI suggest error:', error)
    const errorMsg = error.response?.data?.detail || 'AI 建议获取失败'
    message.error(errorMsg)
  } finally {
    aiLoading.value = false
  }
}

async function getAIPrioritization() {
  aiLoading.value = true
  try {
    const pendingTaskIds = todoItems.value
      .filter(item => !item.completed)
      .map(item => item.id)
    
    const response = await todoAiApi.prioritize({
      task_ids: pendingTaskIds.length > 0 ? pendingTaskIds : undefined
    })
    aiPrioritization.value = response.data
  } catch (error) {
    console.error('AI prioritize error:', error)
    const errorMsg = error.response?.data?.detail || 'AI 分析失败'
    message.error(errorMsg)
  } finally {
    aiLoading.value = false
  }
}

async function addSuggestedTask(task, index) {
  if (!currentListId.value) {
    message.warning('请先选择一个清单')
    return
  }
  
  addingTaskIndex.value = index
  try {
    const dueDate = new Date()
    dueDate.setDate(dueDate.getDate() + (task.due_days || 7))
    
    await api.post('/todo/items', {
      list_id: currentListId.value,
      title: task.title,
      description: task.description,
      priority: task.priority,
      due_date: dueDate.toISOString()
    })
    
    message.success('任务已添加')
    addedSuggestedTaskIndexes.value.add(index)
    await loadItems()
  } catch (error) {
    message.error('添加任务失败')
  } finally {
    addingTaskIndex.value = null
  }
}

function closeAIDialog() {
  showAIDialog.value = false
  aiGoal.value = ''
  aiSuggestions.value = null
  aiPrioritization.value = null
  aiMode.value = 'suggest'
  adoptedTaskIds.value.clear()
  addedSuggestedTaskIndexes.value.clear()
}

function getPriorityLabel(priority) {
  const labels = {
    low: '低',
    medium: '中',
    high: '高'
  }
  return labels[priority] || priority
}

function shouldShowAdoptButton(task) {
  const currentItem = todoItems.value.find(t => t.id === task.task_id)
  if (!currentItem) return false
  return currentItem.priority !== task.suggested_priority
}

async function adoptPrioritySuggestion(task) {
  adoptingTaskId.value = task.task_id
  try {
    await api.put(`/todo/items/${task.task_id}`, {
      priority: task.suggested_priority
    })
    message.success(`已将"${task.title}"的优先级调整为${getPriorityLabel(task.suggested_priority)}`)
    // 添加到已采纳集合
    adoptedTaskIds.value.add(task.task_id)
    // 刷新任务列表
    await loadItems()
    // 更新本地优先级显示
    const item = todoItems.value.find(t => t.id === task.task_id)
    if (item) {
      item.priority = task.suggested_priority
    }
  } catch (error) {
    console.error('Adopt priority error:', error)
    message.error('采纳建议失败')
  } finally {
    adoptingTaskId.value = null
  }
}

// 方法
const loadLists = async () => {
  try {
    const response = await api.get('/todo/lists')
    todoLists.value = response.data
    
    // 如果没有选中的清单，选择第一个
    if (!currentListId.value && todoLists.value.length > 0) {
      currentListId.value = todoLists.value[0].id
      await loadItems()
    }
  } catch (error) {
    console.error('加载清单失败:', error)
  } finally {
    loading.value = false
  }
}

const loadItems = async () => {
  if (!currentListId.value) return
  
  loadingItems.value = true
  try {
    const response = await api.get(`/todo/lists/${currentListId.value}/items`, {
      params: { show_completed: showCompleted.value }
    })
    todoItems.value = response.data
  } catch (error) {
    console.error('加载任务失败:', error)
  } finally {
    loadingItems.value = false
  }
}

const loadStats = async () => {
  try {
    const response = await api.get('/todo/stats')
    stats.value = response.data
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const loadMembers = async () => {
  try {
    const response = await api.get('/todo/members')
    familyMembers.value = response.data
  } catch (error) {
    console.error('加载成员失败:', error)
  }
}

const selectList = async (listId) => {
  currentListId.value = listId
  await loadItems()
}

// 快速添加任务
const quickAddItem = async () => {
  if (!quickAddTitle.value.trim() || !currentListId.value) return
  
  try {
    await api.post('/todo/items', {
      list_id: currentListId.value,
      title: quickAddTitle.value.trim()
    })
    quickAddTitle.value = ''
    await loadItems()
    await loadStats()
    await loadLists()
  } catch (error) {
    console.error('添加任务失败:', error)
    alert(error.response?.data?.detail || '添加失败')
  }
}

// 切换任务完成状态
const toggleComplete = async (item) => {
  try {
    if (item.is_completed) {
      await api.post(`/todo/items/${item.id}/uncomplete`)
    } else {
      await api.post(`/todo/items/${item.id}/complete`)
    }
    await loadItems()
    await loadStats()
    await loadLists()
  } catch (error) {
    console.error('操作失败:', error)
    alert(error.response?.data?.detail || '操作失败')
  }
}

// 清单操作
const editList = (list) => {
  editingList.value = list
  listForm.value = {
    name: list.name,
    icon: list.icon,
    color: list.color
  }
  showListModal.value = true
}

const closeListModal = () => {
  showListModal.value = false
  editingList.value = null
  listForm.value = { name: '', icon: '📋', color: '#667eea' }
}

const saveList = async () => {
  try {
    if (editingList.value) {
      await api.put(`/todo/lists/${editingList.value.id}`, listForm.value)
    } else {
      const response = await api.post('/todo/lists', listForm.value)
      currentListId.value = response.data.list_id
    }
    closeListModal()
    await loadLists()
    await loadItems()
  } catch (error) {
    console.error('保存清单失败:', error)
    alert(error.response?.data?.detail || '保存失败')
  }
}

const deleteList = async () => {
  if (!editingList.value) return
  if (!confirm(`确定要删除清单"${editingList.value.name}"及其所有任务吗？`)) return
  
  try {
    await api.delete(`/todo/lists/${editingList.value.id}`)
    if (currentListId.value === editingList.value.id) {
      currentListId.value = null
      todoItems.value = []
    }
    closeListModal()
    await loadLists()
    await loadStats()
  } catch (error) {
    console.error('删除清单失败:', error)
    alert(error.response?.data?.detail || '删除失败')
  }
}

// 任务操作
const editItem = (item) => {
  editingItem.value = item
  itemForm.value = {
    title: item.title,
    description: item.description || '',
    assignee_id: item.assignee_id,
    priority: item.priority,
    due_date: item.due_date ? item.due_date.slice(0, 16) : '',
    repeat_type: item.repeat_type
  }
  showItemModal.value = true
}

const closeItemModal = () => {
  showItemModal.value = false
  editingItem.value = null
  itemForm.value = {
    title: '',
    description: '',
    assignee_id: null,
    priority: 'medium',
    due_date: '',
    repeat_type: 'none'
  }
}

const saveItem = async () => {
  try {
    const data = {
      ...itemForm.value,
      due_date: itemForm.value.due_date || null
    }
    
    if (editingItem.value) {
      await api.put(`/todo/items/${editingItem.value.id}`, data)
    } else {
      data.list_id = currentListId.value
      await api.post('/todo/items', data)
    }
    closeItemModal()
    await loadItems()
    await loadStats()
    await loadLists()
  } catch (error) {
    console.error('保存任务失败:', error)
    alert(error.response?.data?.detail || '保存失败')
  }
}

const deleteItem = async (item) => {
  if (!confirm(`确定要删除任务"${item.title}"吗？`)) return
  
  try {
    await api.delete(`/todo/items/${item.id}`)
    await loadItems()
    await loadStats()
    await loadLists()
  } catch (error) {
    console.error('删除任务失败:', error)
    alert(error.response?.data?.detail || '删除失败')
  }
}

// 工具方法
const formatDueDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)
  
  if (date.toDateString() === today.toDateString()) {
    return '今天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  if (date.toDateString() === tomorrow.toDateString()) {
    return '明天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const isOverdue = (dateStr) => {
  if (!dateStr) return false
  return new Date(dateStr) < new Date()
}

const getRepeatText = (type) => {
  const map = { daily: '每天', weekly: '每周', monthly: '每月' }
  return map[type] || ''
}

const getPriorityIcon = (priority) => {
  const map = { high: '🔴', medium: '🟡', low: '🟢' }
  return map[priority] || '🟡'
}

// 初始化
onMounted(async () => {
  await Promise.all([loadLists(), loadStats(), loadMembers()])
})
</script>

<style scoped>
.todo-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  color: var(--theme-text-primary);
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin: 0;
  color: var(--theme-text-primary);
}

.page-header p {
  color: var(--theme-text-secondary);
  margin: 8px 0 0;
}

/* 统计卡片 */
.stats-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 100px;
  background: var(--theme-bg-card);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  border: 1px solid var(--theme-border-light);
  box-shadow: 0 12px 32px var(--theme-shadow);
}

.stat-card.urgent {
  background: linear-gradient(135deg, var(--theme-warning-light, #fde68a) 0%, rgba(253, 230, 138, 0.6) 100%);
}

.stat-card.success {
  background: linear-gradient(135deg, var(--theme-success-light, #a7f3d0) 0%, rgba(167, 243, 208, 0.6) 100%);
}

.stat-number {
  display: block;
  font-size: 28px;
  font-weight: bold;
  color: var(--theme-text-primary);
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--theme-text-secondary);
  margin-top: 4px;
}

/* 主容器 */
.todo-container {
  display: flex;
  gap: 20px;
  min-height: 500px;
}

/* 左侧清单面板 */
.lists-panel {
  width: 260px;
  background: var(--theme-bg-card);
  border-radius: 16px;
  padding: 16px;
  border: 1px solid var(--theme-border-light);
  box-shadow: 0 12px 32px var(--theme-shadow);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--theme-text-primary);
}

.btn-add-list {
  width: 28px;
  height: 28px;
  border: none;
  background: var(--theme-primary);
  color: white;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-add-list:hover {
  background: var(--theme-primary-hover);
}

.lists-wrapper {
  flex: 1;
  overflow-y: auto;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.list-item:hover {
  background: var(--theme-card-hover, rgba(0,0,0,0.03));
}

.list-item.active {
  background: linear-gradient(135deg, var(--theme-primary-light, rgba(24,160,88,0.15)) 0%, var(--theme-bg-card) 100%);
  border: 1px solid var(--theme-primary);
}

.list-item.add-new {
  border: 2px dashed var(--theme-border);
  opacity: 0.7;
}

.list-item.add-new:hover {
  border-color: var(--theme-primary);
  opacity: 1;
}

.list-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.list-icon.large {
  width: 40px;
  height: 40px;
  font-size: 24px;
}

.list-name {
  flex: 1;
  font-size: 14px;
  color: var(--theme-text-primary);
}

.list-count {
  background: var(--theme-bg-secondary);
  color: var(--theme-text-secondary);
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  min-width: 24px;
  text-align: center;
}

.btn-edit-list {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  font-size: 16px;
  color: var(--theme-text-secondary);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.list-item:hover .btn-edit-list {
  opacity: 1;
}

/* 右侧任务面板 */
.tasks-panel {
  flex: 1;
  background: var(--theme-bg-card);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid var(--theme-border-light);
  box-shadow: 0 12px 32px var(--theme-shadow);
  display: flex;
  flex-direction: column;
}

.current-list-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-completed {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--theme-text-secondary);
  cursor: pointer;
}

/* 快速添加 */
.quick-add {
  display: flex;
  gap: 12px;
  margin: 16px 0;
}

.quick-add-input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid var(--theme-border);
  border-radius: 10px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.quick-add-input:focus {
  outline: none;
  border-color: var(--theme-primary);
}

.btn-quick-add {
  padding: 12px 24px;
  background: linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-primary-hover) 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  transition: transform 0.2s;
}

.btn-quick-add:hover {
  transform: scale(1.02);
}

/* 任务列表 */
.items-list {
  flex: 1;
  overflow-y: auto;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  margin-bottom: 8px;
  background: var(--theme-bg-card);
  border: 1px solid var(--theme-border-light);
  transition: all 0.2s;
}

.task-item:hover {
  background: var(--theme-card-hover, rgba(0,0,0,0.03));
}

.task-item.completed {
  opacity: 0.6;
}

.task-item.completed .task-title {
  text-decoration: line-through;
  color: var(--theme-text-tertiary);
}

.task-item.priority-high {
  border-left: 3px solid var(--theme-error);
}

.task-item.priority-medium {
  border-left: 3px solid var(--theme-warning);
}

.task-item.priority-low {
  border-left: 3px solid var(--theme-success);
}

.task-checkbox {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 18px;
}

.checkbox-empty {
  width: 20px;
  height: 20px;
  border: 2px solid var(--theme-border);
  border-radius: 50%;
  transition: all 0.2s;
}

.task-checkbox:hover .checkbox-empty {
  border-color: var(--theme-primary);
  background: var(--theme-primary-light, rgba(24,160,88,0.15));
}

.task-content {
  flex: 1;
  cursor: pointer;
}

.task-title {
  font-size: 14px;
  color: var(--theme-text-primary);
  margin-bottom: 4px;
}

.task-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--theme-bg-secondary);
  color: var(--theme-text-secondary);
}

.meta-tag.assignee {
  background: var(--theme-info-bg);
  color: var(--theme-info);
}

.meta-tag.due-date {
  background: var(--theme-warning-bg);
  color: var(--theme-warning);
}

.meta-tag.due-date.overdue {
  background: var(--theme-error-bg);
  color: var(--theme-error);
}

.meta-tag.repeat {
  background: var(--theme-success-bg);
  color: var(--theme-success);
}

.task-priority {
  font-size: 14px;
}

.btn-delete-item {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  font-size: 14px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.task-item:hover .btn-delete-item {
  opacity: 1;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--theme-text-tertiary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state.select-list {
  background: var(--theme-bg-secondary);
  border-radius: 16px;
}

/* 加载状态 */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--theme-border);
  border-top-color: var(--theme-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--theme-bg-card);
  border: 1px solid var(--theme-border-light);
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 16px 40px var(--theme-shadow);
}

.modal-content.small {
  max-width: 360px;
}

.modal-content h2 {
  margin: 0 0 20px;
  font-size: 20px;
  color: var(--theme-text-primary);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  color: var(--theme-text-secondary);
  margin-bottom: 6px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
  background: var(--theme-bg-card);
  color: var(--theme-text-primary);
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--theme-primary);
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-group.half {
  flex: 1;
}

.icon-picker,
.color-picker {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.icon-option {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border: 2px solid var(--theme-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-option:hover,
.icon-option.selected {
  border-color: var(--theme-primary);
  background: var(--theme-primary-light, rgba(24, 160, 88, 0.15));
}

.color-option {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  border: 3px solid transparent;
  transition: all 0.2s;
}

.color-option:hover,
.color-option.selected {
  transform: scale(1.1);
  border-color: var(--theme-text-primary);
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.spacer {
  flex: 1;
}

.btn-cancel {
  padding: 10px 20px;
  background: var(--theme-bg-secondary);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--theme-text-primary);
}

.btn-submit {
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-primary-hover) 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  padding: 10px 20px;
  background: var(--theme-error-bg);
  color: var(--theme-error);
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

/* 响应式 */
@media (max-width: 768px) {
  .todo-container {
    flex-direction: column;
  }
  
  .lists-panel {
    width: 100%;
  }
  
  .stats-bar {
    flex-wrap: wrap;
  }
  
  .stat-card {
    min-width: calc(50% - 8px);
  }
  
  .form-row {
    flex-direction: column;
    gap: 0;
  }
}

/* AI 助手样式 */
.btn-ai-assist {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  margin-right: 12px;
  transition: all 0.2s;
}

.btn-ai-assist:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.btn-close-modal {
  background: none;
  border: none;
  color: var(--theme-text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-close-modal:hover {
  background: var(--theme-bg-soft);
  color: var(--theme-text-primary);
}

.ai-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--theme-border);
  padding-bottom: 2px;
}

.ai-tab {
  flex: 1;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 10px;
  cursor: pointer;
  font-size: 14px;
  color: var(--theme-text-primary);
  transition: all 0.2s;
}

.ai-tab.active {
  border-bottom-color: var(--theme-primary);
  color: var(--theme-primary);
  font-weight: 600;
}

.ai-content {
  margin-top: 16px;
}

.ai-input {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  background: var(--theme-bg-secondary);
  color: var(--theme-text-primary);
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  transition: all 0.2s;
}

.ai-input:focus {
  outline: none;
  border-color: var(--theme-primary);
  box-shadow: 0 0 0 3px var(--theme-primary-light, rgba(102, 126, 234, 0.1));
}

.ai-input::placeholder {
  color: var(--theme-text-tertiary);
}

.btn-ai-suggest {
  width: 100%;
  margin-top: 16px;
  padding: 12px 24px;
  background: linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-primary-hover) 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25);
}

.btn-ai-suggest:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
}

.btn-ai-suggest:active:not(:disabled) {
  transform: translateY(0);
}

.btn-ai-suggest:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-loading {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 16px;
  height: 16px;
  animation: rotate 1s linear infinite;
}

.spinner circle {
  stroke: currentColor;
  stroke-linecap: round;
  animation: dash 1.5s ease-in-out infinite;
}

@keyframes rotate {
  100% {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dasharray: 1, 150;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -35;
  }
  100% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -124;
  }
}

.ai-hint {
  color: var(--theme-text-secondary);
  font-size: 14px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--theme-bg-soft);
  border-radius: 6px;
}

.ai-results {
  margin-top: 20px;
  max-height: 400px;
  overflow-y: auto;
}

.ai-reasoning, .ai-advice {
  background: var(--theme-bg-soft);
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.suggested-tasks, .prioritized-tasks {
  margin-top: 16px;
}

.suggested-task, .prioritized-task {
  background: var(--theme-bg-secondary);
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.prioritized-task {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.task-rank {
  background: var(--theme-primary);
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.task-info {
  flex: 1;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-title {
  font-weight: 500;
  font-size: 14px;
  color: var(--theme-text-primary);
}

.task-priority {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.task-priority.low {
  background: var(--theme-info-bg, #e3f2fd);
  color: var(--theme-info, #1976d2);
}

.task-priority.medium {
  background: var(--theme-warning-bg, #fff3e0);
  color: var(--theme-warning, #f57c00);
}

.task-priority.high {
  background: var(--theme-error-bg, #ffebee);
  color: var(--theme-error, #d32f2f);
}

.task-desc, .task-reasoning {
  font-size: 13px;
  color: var(--theme-text-secondary);
  margin: 8px 0;
}

.task-due, .task-urgency {
  font-size: 12px;
  color: var(--theme-text-tertiary);
  margin-top: 4px;
}

.btn-add-suggested {
  margin-top: 8px;
  background: var(--theme-primary);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-suggested:hover {
  background: var(--theme-primary-hover);
  transform: translateY(-1px);
}

html.dark .suggested-task,
html.dark .prioritized-task {
  background: var(--theme-bg-elevated);
  border-color: var(--theme-border);
}

.btn-loading-small {
  display: flex;
  align-items: center;
  gap: 6px;
}

.spinner-small {
  width: 12px;
  height: 12px;
  animation: rotate 1s linear infinite;
}

.spinner-small circle {
  stroke: currentColor;
  stroke-linecap: round;
  animation: dash 1.5s ease-in-out infinite;
}

.adopted-badge {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 12px;
  background: var(--theme-success-bg, #f0fdf4);
  color: var(--theme-success, #16a34a);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

html.dark .adopted-badge {
  background: rgba(22, 163, 74, 0.15);
  color: #4ade80;
}
</style>
