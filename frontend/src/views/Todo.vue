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
            placeholder="添加新任务，按回车保存..."
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
import { api } from '@/api'
import UserAvatar from '@/components/UserAvatar.vue'

// 状态
const loading = ref(true)
const loadingItems = ref(false)
const todoLists = ref([])
const todoItems = ref([])
const currentListId = ref(null)
const showCompleted = ref(true)
const stats = ref(null)
const familyMembers = ref([])

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
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin: 0;
}

.page-header p {
  color: #666;
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
  background: white;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.stat-card.urgent {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
}

.stat-card.success {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}

.stat-number {
  display: block;
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #666;
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
  background: white;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
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
  color: #333;
}

.btn-add-list {
  width: 28px;
  height: 28px;
  border: none;
  background: #667eea;
  color: white;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
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
  background: #f3f4f6;
}

.list-item.active {
  background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
}

.list-item.add-new {
  border: 2px dashed #e5e7eb;
  opacity: 0.7;
}

.list-item.add-new:hover {
  border-color: #667eea;
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
  color: #333;
}

.list-count {
  background: #e5e7eb;
  color: #666;
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
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
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
  color: #666;
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
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.quick-add-input:focus {
  outline: none;
  border-color: #667eea;
}

.btn-quick-add {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  background: #f9fafb;
  transition: all 0.2s;
}

.task-item:hover {
  background: #f3f4f6;
}

.task-item.completed {
  opacity: 0.6;
}

.task-item.completed .task-title {
  text-decoration: line-through;
  color: #999;
}

.task-item.priority-high {
  border-left: 3px solid #ef4444;
}

.task-item.priority-medium {
  border-left: 3px solid #f59e0b;
}

.task-item.priority-low {
  border-left: 3px solid #10b981;
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
  border: 2px solid #d1d5db;
  border-radius: 50%;
  transition: all 0.2s;
}

.task-checkbox:hover .checkbox-empty {
  border-color: #667eea;
  background: #667eea10;
}

.task-content {
  flex: 1;
  cursor: pointer;
}

.task-title {
  font-size: 14px;
  color: #333;
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
  background: #e5e7eb;
  color: #666;
}

.meta-tag.assignee {
  background: #dbeafe;
  color: #1d4ed8;
}

.meta-tag.due-date {
  background: #fef3c7;
  color: #92400e;
}

.meta-tag.due-date.overdue {
  background: #fee2e2;
  color: #dc2626;
}

.meta-tag.repeat {
  background: #f0fdf4;
  color: #166534;
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
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state.select-list {
  background: #f9fafb;
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
  border: 3px solid #e5e7eb;
  border-top-color: #667eea;
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
  background: white;
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content.small {
  max-width: 360px;
}

.modal-content h2 {
  margin: 0 0 20px;
  font-size: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 6px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
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
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-option:hover,
.icon-option.selected {
  border-color: #667eea;
  background: #667eea10;
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
  border-color: #333;
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
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.btn-submit {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  background: #fee2e2;
  color: #dc2626;
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
</style>
