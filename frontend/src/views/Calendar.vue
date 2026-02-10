<template>
  <div class="calendar-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>📅 共享日历</h1>
      <p>家庭事件一目了然</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="view-switcher">
        <button :class="{ active: viewMode === 'month' }" @click="viewMode = 'month'">月</button>
        <button :class="{ active: viewMode === 'week' }" @click="viewMode = 'week'">周</button>
        <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">列表</button>
      </div>
      
      <div class="nav-controls">
        <button class="nav-btn" @click="prevPeriod">◀</button>
        <span class="current-period">{{ currentPeriodLabel }}</span>
        <button class="nav-btn" @click="nextPeriod">▶</button>
        <button class="today-btn" @click="goToday">今天</button>
      </div>

      <div class="actions">
        <button class="sync-btn" @click="syncEvents">🔄 同步</button>
        <button class="add-btn" @click="openEventModal()">+ 新建事件</button>
      </div>
    </div>

    <!-- 分类筛选 -->
    <div class="category-filter">
      <span 
        v-for="cat in categories" 
        :key="cat.value"
        class="category-tag"
        :class="{ active: selectedCategory === cat.value || selectedCategory === null }"
        :style="{ borderColor: cat.color }"
        @click="toggleCategory(cat.value)"
      >
        {{ cat.icon }} {{ cat.label }}
      </span>
    </div>

    <!-- 月视图 -->
    <div v-if="viewMode === 'month'" class="month-view">
      <div class="weekday-header">
        <span v-for="day in weekDays" :key="day">{{ day }}</span>
      </div>
      <div class="calendar-grid">
        <div 
          v-for="(day, index) in calendarDays" 
          :key="index"
          class="calendar-cell"
          :class="{ 
            'other-month': !day.isCurrentMonth,
            'today': day.isToday,
            'selected': isSelectedDate(day.date)
          }"
          @click="selectDate(day.date)"
        >
          <span class="day-number">{{ day.day }}</span>
          <div class="day-events">
            <div 
              v-for="event in day.events.slice(0, 3)" 
              :key="event.id"
              class="event-bar"
              :style="{ backgroundColor: event.color }"
              @click.stop="openEventModal(event)"
            >
              <span class="event-icon">{{ getCategoryIcon(event.category) }}</span>
              <span class="event-text">{{ event.title }}</span>
            </div>
            <div v-if="day.events.length > 3" class="more-events" @click.stop="selectDate(day.date)">
              +{{ day.events.length - 3 }} 更多
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 周视图 -->
    <div v-else-if="viewMode === 'week'" class="week-view">
      <div class="week-header">
        <div v-for="day in weekViewDays" :key="day.date" class="week-day-header" :class="{ today: day.isToday }">
          <span class="day-name">{{ day.dayName }}</span>
          <span class="day-num">{{ day.day }}</span>
        </div>
      </div>
      <div class="week-body">
        <div v-for="day in weekViewDays" :key="day.date" class="week-day-column">
          <div 
            v-for="event in day.events" 
            :key="event.id"
            class="week-event"
            :style="{ backgroundColor: event.color }"
            @click="openEventModal(event)"
          >
            <span class="event-time">{{ formatTime(event.start_time) }}</span>
            <span class="event-title">{{ event.title }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 列表视图 -->
    <div v-else class="list-view">
      <div v-if="groupedEvents.length === 0" class="empty-state">
        <div class="empty-icon">📅</div>
        <p>暂无事件</p>
      </div>
      <div v-for="group in groupedEvents" :key="group.date" class="event-group">
        <div class="group-header">
          <span class="group-date">{{ group.dateLabel }}</span>
          <span class="group-weekday">{{ group.weekday }}</span>
        </div>
        <div 
          v-for="event in group.events" 
          :key="event.id"
          class="list-event"
          @click="openEventModal(event)"
        >
          <div class="event-color" :style="{ backgroundColor: event.color }"></div>
          <div class="event-info">
            <div class="event-title">{{ event.title }}</div>
            <div class="event-meta">
              <span v-if="!event.is_all_day">{{ formatTime(event.start_time) }}</span>
              <span v-else>全天</span>
              <span v-if="event.location">📍 {{ event.location }}</span>
            </div>
          </div>
          <div class="event-category">{{ getCategoryIcon(event.category) }}</div>
        </div>
      </div>
    </div>

    <!-- 事件弹窗 -->
    <div v-if="showEventModal" class="modal-overlay" @click.self="closeEventModal">
      <div class="modal-content">
        <h2>{{ editingEvent ? '编辑事件' : '新建事件' }}</h2>
        
        <div class="form-group">
          <label>事件标题</label>
          <input v-model="eventForm.title" placeholder="请输入事件标题" />
        </div>

        <div class="form-group">
          <label>分类</label>
          <select v-model="eventForm.category">
            <option v-for="cat in categories.filter(c => c.value !== 'system')" :key="cat.value" :value="cat.value">
              {{ cat.icon }} {{ cat.label }}
            </option>
          </select>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>开始时间</label>
            <input type="datetime-local" v-model="eventForm.start_time" />
          </div>
          <div class="form-group half">
            <label>结束时间</label>
            <input type="datetime-local" v-model="eventForm.end_time" />
          </div>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="eventForm.is_all_day" />
            全天事件
          </label>
        </div>

        <div class="form-group">
          <label>重复</label>
          <select v-model="eventForm.repeat_type">
            <option value="none">不重复</option>
            <option value="daily">每天</option>
            <option value="weekly">每周</option>
            <option value="monthly">每月</option>
            <option value="yearly">每年</option>
          </select>
        </div>

        <div class="form-group">
          <label>地点</label>
          <input v-model="eventForm.location" placeholder="可选" />
        </div>

        <div class="form-group">
          <label>备注</label>
          <textarea v-model="eventForm.description" rows="2" placeholder="可选"></textarea>
        </div>

        <div class="form-group">
          <label>颜色</label>
          <div class="color-picker">
            <span 
              v-for="color in eventColors" 
              :key="color"
              class="color-option"
              :class="{ selected: eventForm.color === color }"
              :style="{ backgroundColor: color }"
              @click="eventForm.color = color"
            ></span>
          </div>
        </div>

        <div class="modal-actions">
          <button v-if="editingEvent && !editingEvent.is_system" class="btn-danger" @click="deleteEvent">删除</button>
          <div class="spacer"></div>
          <button class="btn-cancel" @click="closeEventModal">取消</button>
          <button class="btn-submit" @click="saveEvent" :disabled="!eventForm.title || editingEvent?.is_system">
            {{ editingEvent?.is_system ? '系统事件' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/api'

// 类型定义
interface CalendarEvent {
  id: number
  title: string
  category: string
  start_time: string
  end_time?: string
  is_all_day: boolean
  location?: string
  description?: string
  color: string
  repeat_type: string
  is_system?: boolean
  source_type?: string
}

// 分类定义
const categories = [
  { value: 'personal', label: '个人', icon: '👤', color: '#3B82F6' },
  { value: 'family', label: '家庭', icon: '👨‍👩‍👧', color: '#10B981' },
  { value: 'investment', label: '理财', icon: '💰', color: '#F59E0B' },
  { value: 'todo', label: '待办', icon: '✅', color: '#8B5CF6' },
  { value: 'gift', label: '赠与', icon: '🎁', color: '#EC4899' },
]

const eventColors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6B7280']
const weekDays = ['日', '一', '二', '三', '四', '五', '六']

// 响应式状态
const viewMode = ref<'month' | 'week' | 'list'>('month')
const currentDate = ref(new Date())
const selectedDate = ref<Date | null>(null)
const selectedCategory = ref<string | null>(null)
const events = ref<CalendarEvent[]>([])
const showEventModal = ref(false)
const editingEvent = ref<CalendarEvent | null>(null)

// 表单数据
const eventForm = ref({
  title: '',
  category: 'personal',
  start_time: '',
  end_time: '',
  is_all_day: false,
  repeat_type: 'none',
  location: '',
  description: '',
  color: '#3B82F6'
})

// 计算属性：当前周期标签
const currentPeriodLabel = computed(() => {
  const year = currentDate.value.getFullYear()
  const month = currentDate.value.getMonth() + 1
  if (viewMode.value === 'month') {
    return `${year}年${month}月`
  } else if (viewMode.value === 'week') {
    const weekStart = getWeekStart(currentDate.value)
    const weekEnd = new Date(weekStart)
    weekEnd.setDate(weekEnd.getDate() + 6)
    return `${weekStart.getMonth() + 1}/${weekStart.getDate()} - ${weekEnd.getMonth() + 1}/${weekEnd.getDate()}`
  }
  return `${year}年${month}月`
})

// 计算属性：月视图日历格子
const calendarDays = computed(() => {
  const year = currentDate.value.getFullYear()
  const month = currentDate.value.getMonth()
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startOffset = firstDay.getDay()
  
  const days = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // 上个月的日期
  for (let i = startOffset - 1; i >= 0; i--) {
    const date = new Date(year, month, -i)
    days.push({
      date,
      day: date.getDate(),
      isCurrentMonth: false,
      isToday: false,
      events: getEventsForDate(date)
    })
  }

  // 当前月的日期
  for (let i = 1; i <= lastDay.getDate(); i++) {
    const date = new Date(year, month, i)
    days.push({
      date,
      day: i,
      isCurrentMonth: true,
      isToday: date.getTime() === today.getTime(),
      events: getEventsForDate(date)
    })
  }

  // 下个月的日期（补齐到42格）
  const remaining = 42 - days.length
  for (let i = 1; i <= remaining; i++) {
    const date = new Date(year, month + 1, i)
    days.push({
      date,
      day: i,
      isCurrentMonth: false,
      isToday: false,
      events: getEventsForDate(date)
    })
  }

  return days
})

// 计算属性：周视图日期
const weekViewDays = computed(() => {
  const weekStart = getWeekStart(currentDate.value)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  return Array.from({ length: 7 }, (_, i) => {
    const date = new Date(weekStart)
    date.setDate(date.getDate() + i)
    return {
      date: date.toISOString().split('T')[0],
      day: date.getDate(),
      dayName: weekDays[date.getDay()],
      isToday: date.getTime() === today.getTime(),
      events: getEventsForDate(date)
    }
  })
})

// 计算属性：列表视图分组事件
const groupedEvents = computed(() => {
  const filtered = selectedCategory.value 
    ? events.value.filter(e => e.category === selectedCategory.value)
    : events.value
  
  const groups: { [key: string]: CalendarEvent[] } = {}
  
  filtered.forEach(event => {
    const dateKey = event.start_time.split('T')[0]
    if (!groups[dateKey]) {
      groups[dateKey] = []
    }
    groups[dateKey].push(event)
  })

  return Object.entries(groups)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, events]) => {
      const d = new Date(date)
      return {
        date,
        dateLabel: `${d.getMonth() + 1}月${d.getDate()}日`,
        weekday: weekDays[d.getDay()],
        events: events.sort((a, b) => a.start_time.localeCompare(b.start_time))
      }
    })
})

// 工具函数
function getWeekStart(date: Date): Date {
  const d = new Date(date)
  const day = d.getDay()
  d.setDate(d.getDate() - day)
  d.setHours(0, 0, 0, 0)
  return d
}

function getEventsForDate(date: Date): CalendarEvent[] {
  const dateStr = date.toISOString().split('T')[0]
  let filtered = events.value.filter(e => e.start_time.startsWith(dateStr))
  
  if (selectedCategory.value) {
    filtered = filtered.filter(e => e.category === selectedCategory.value)
  }
  
  return filtered
}

function isSelectedDate(date: Date): boolean {
  if (!selectedDate.value) return false
  return date.toDateString() === selectedDate.value.toDateString()
}

function formatTime(datetime: string): string {
  if (!datetime) return ''
  const d = new Date(datetime)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function getCategoryIcon(category: string): string {
  return categories.find(c => c.value === category)?.icon || '📅'
}

function formatDateTimeLocal(date: Date): string {
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

// 导航
function prevPeriod() {
  const d = new Date(currentDate.value)
  if (viewMode.value === 'month') {
    d.setMonth(d.getMonth() - 1)
  } else if (viewMode.value === 'week') {
    d.setDate(d.getDate() - 7)
  }
  currentDate.value = d
}

function nextPeriod() {
  const d = new Date(currentDate.value)
  if (viewMode.value === 'month') {
    d.setMonth(d.getMonth() + 1)
  } else if (viewMode.value === 'week') {
    d.setDate(d.getDate() + 7)
  }
  currentDate.value = d
}

function goToday() {
  currentDate.value = new Date()
}

function selectDate(date: Date) {
  selectedDate.value = date
}

function toggleCategory(value: string) {
  selectedCategory.value = selectedCategory.value === value ? null : value
}

// API 请求
async function fetchEvents() {
  try {
    const year = currentDate.value.getFullYear()
    const month = currentDate.value.getMonth()
    const start = new Date(year, month - 1, 1).toISOString()
    const end = new Date(year, month + 2, 0).toISOString()
    
    const response = await api.get('/calendar/events', {
      params: { start, end }
    })
    events.value = response.data
  } catch (error) {
    console.error('获取日历事件失败:', error)
  }
}

async function syncEvents() {
  try {
    await api.post('/calendar/sync')
    await fetchEvents()
    alert('同步完成！')
  } catch (error) {
    console.error('同步失败:', error)
    alert('同步失败，请稍后重试')
  }
}

// 事件弹窗
function openEventModal(event?: CalendarEvent) {
  if (event) {
    editingEvent.value = event
    eventForm.value = {
      title: event.title,
      category: event.category,
      start_time: event.start_time.replace('Z', '').slice(0, 16),
      end_time: event.end_time ? event.end_time.replace('Z', '').slice(0, 16) : '',
      is_all_day: event.is_all_day,
      repeat_type: event.repeat_type,
      location: event.location || '',
      description: event.description || '',
      color: event.color
    }
  } else {
    editingEvent.value = null
    const now = new Date()
    const later = new Date(now.getTime() + 60 * 60 * 1000)
    eventForm.value = {
      title: '',
      category: 'personal',
      start_time: formatDateTimeLocal(now),
      end_time: formatDateTimeLocal(later),
      is_all_day: false,
      repeat_type: 'none',
      location: '',
      description: '',
      color: '#3B82F6'
    }
  }
  showEventModal.value = true
}

function closeEventModal() {
  showEventModal.value = false
  editingEvent.value = null
}

async function saveEvent() {
  try {
    const payload = {
      ...eventForm.value,
      start_time: new Date(eventForm.value.start_time).toISOString(),
      end_time: eventForm.value.end_time ? new Date(eventForm.value.end_time).toISOString() : null
    }

    if (editingEvent.value) {
      await api.put(`/calendar/events/${editingEvent.value.id}`, payload)
    } else {
      await api.post('/calendar/events', payload)
    }
    
    await fetchEvents()
    closeEventModal()
  } catch (error) {
    console.error('保存事件失败:', error)
    alert('保存失败，请稍后重试')
  }
}

async function deleteEvent() {
  if (!editingEvent.value) return
  
  if (!confirm('确定要删除这个事件吗？')) return
  
  try {
    await api.delete(`/calendar/events/${editingEvent.value.id}`)
    await fetchEvents()
    closeEventModal()
  } catch (error) {
    console.error('删除事件失败:', error)
    alert('删除失败，请稍后重试')
  }
}

// 监听日期变化重新获取数据
watch(currentDate, () => {
  fetchEvents()
})

// 初始化
onMounted(() => {
  fetchEvents()
})
</script>

<style scoped>
.calendar-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  color: var(--theme-text-primary);
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin: 0 0 8px 0;
  color: var(--theme-text-primary);
}

.page-header p {
  color: var(--theme-text-secondary);
  margin: 0;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  background: var(--theme-bg-card);
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--theme-border-light);
  box-shadow: 0 12px 32px var(--theme-shadow);
}

.view-switcher {
  display: flex;
  background: var(--theme-bg-secondary);
  border-radius: 8px;
  overflow: hidden;
}

.view-switcher button {
  padding: 8px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: var(--theme-text-secondary);
  transition: all 0.2s;
}

.view-switcher button.active {
  background: var(--theme-primary);
  color: white;
}

.nav-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--theme-bg-secondary);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.nav-btn:hover {
  background: var(--theme-card-hover, rgba(0,0,0,0.04));
}

.current-period {
  font-weight: 600;
  min-width: 120px;
  text-align: center;
}

.today-btn {
  padding: 6px 12px;
  border: 1px solid var(--theme-border);
  background: var(--theme-bg-card);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.today-btn:hover {
  background: var(--theme-bg-secondary);
}

.actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.sync-btn {
  padding: 8px 16px;
  border: none;
  background: var(--theme-info-bg);
  color: var(--theme-info);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.sync-btn:hover {
  background: var(--theme-card-hover, rgba(0,0,0,0.04));
}

.add-btn {
  padding: 8px 16px;
  border: none;
  background: var(--theme-primary);
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.add-btn:hover {
  background: var(--theme-primary-hover);
}

/* 分类筛选 */
.category-filter {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.category-tag {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  border: 2px solid;
  background: var(--theme-bg-card);
  opacity: 0.6;
  transition: all 0.2s;
}

.category-tag.active {
  opacity: 1;
}

.category-tag:hover {
  opacity: 1;
}

/* 月视图 */
.month-view {
  background: var(--theme-bg-card);
  border-radius: 12px;
  border: 1px solid var(--theme-border-light);
  box-shadow: 0 12px 32px var(--theme-shadow);
  overflow: hidden;
}

.weekday-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  background: var(--theme-bg-secondary);
  border-bottom: 1px solid var(--theme-border);
}

.weekday-header span {
  padding: 12px;
  text-align: center;
  font-weight: 500;
  color: var(--theme-text-secondary);
  font-size: 13px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.calendar-cell {
  min-height: 90px;
  border-right: 1px solid var(--theme-border-light);
  border-bottom: 1px solid var(--theme-border-light);
  padding: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.calendar-cell:nth-child(7n) {
  border-right: none;
}

.calendar-cell:hover {
  background: var(--theme-bg-secondary);
}

.calendar-cell.other-month {
  background: var(--theme-bg-secondary);
}

.calendar-cell.other-month .day-number {
  color: var(--theme-text-tertiary);
}

.calendar-cell.today {
  background: var(--theme-info-bg);
}

.calendar-cell.today .day-number {
  background: var(--theme-info);
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.calendar-cell.selected {
  background: var(--theme-primary-light, rgba(24,160,88,0.15));
}

.day-number {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.day-events {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
}

.event-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  color: white;
  font-size: 11px;
  line-height: 1.3;
  transition: opacity 0.2s, transform 0.1s;
  overflow: hidden;
}

.event-bar:hover {
  opacity: 0.9;
  transform: scale(1.02);
}

.event-bar .event-icon {
  font-size: 10px;
  flex-shrink: 0;
}

.event-bar .event-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.more-events {
  font-size: 11px;
  color: var(--theme-info);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  background: var(--theme-info-bg);
  text-align: center;
}

.more-events:hover {
  background: var(--theme-card-hover, rgba(0,0,0,0.04));
}

/* 周视图 */
.week-view {
  background: var(--theme-bg-card);
  border-radius: 12px;
  border: 1px solid var(--theme-border-light);
  box-shadow: 0 12px 32px var(--theme-shadow);
  overflow: hidden;
}

.week-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  background: var(--theme-bg-secondary);
  border-bottom: 1px solid var(--theme-border);
}

.week-day-header {
  padding: 12px;
  text-align: center;
}

.week-day-header.today {
  background: var(--theme-info-bg);
}

.week-day-header .day-name {
  display: block;
  font-size: 12px;
  color: var(--theme-text-secondary);
}

.week-day-header .day-num {
  display: block;
  font-size: 18px;
  font-weight: 600;
}

.week-body {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  min-height: 400px;
}

.week-day-column {
  border-right: 1px solid var(--theme-border-light);
  padding: 8px;
}

.week-day-column:last-child {
  border-right: none;
}

.week-event {
  padding: 6px 8px;
  border-radius: 6px;
  margin-bottom: 4px;
  color: white;
  cursor: pointer;
  font-size: 12px;
}

.week-event .event-time {
  display: block;
  font-size: 10px;
  opacity: 0.8;
}

.week-event .event-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 列表视图 */
.list-view {
  background: var(--theme-bg-card);
  border-radius: 12px;
  border: 1px solid var(--theme-border-light);
  box-shadow: 0 12px 32px var(--theme-shadow);
  padding: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--theme-text-tertiary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.event-group {
  margin-bottom: 20px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--theme-border-light);
}

.group-date {
  font-weight: 600;
  font-size: 15px;
}

.group-weekday {
  color: var(--theme-text-tertiary);
  font-size: 13px;
}

.list-event {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.list-event:hover {
  background: var(--theme-bg-secondary);
}

.event-color {
  width: 4px;
  height: 40px;
  border-radius: 2px;
}

.event-info {
  flex: 1;
}

.event-info .event-title {
  font-weight: 500;
  margin-bottom: 4px;
}

.event-meta {
  font-size: 12px;
  color: var(--theme-text-secondary);
  display: flex;
  gap: 12px;
}

.event-category {
  font-size: 20px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--theme-bg-card);
  border-radius: 16px;
  padding: 24px;
  width: 90%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid var(--theme-border-light);
  box-shadow: 0 16px 40px var(--theme-shadow);
}

.modal-content h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: var(--theme-text-primary);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--theme-text-secondary);
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
  gap: 12px;
}

.form-group.half {
  flex: 1;
}

.checkbox-label {
  display: flex !important;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input {
  width: auto !important;
}

.color-picker {
  display: flex;
  gap: 8px;
}

.color-option {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: transform 0.2s;
}

.color-option:hover {
  transform: scale(1.1);
}

.color-option.selected {
  border-color: var(--theme-text-primary);
}

.modal-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--theme-border-light);
}

.spacer {
  flex: 1;
}

.btn-danger {
  padding: 10px 20px;
  border: none;
  background: var(--theme-error-bg);
  color: var(--theme-error);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.btn-danger:hover {
  background: rgba(220, 38, 38, 0.15);
}

.btn-cancel {
  padding: 10px 20px;
  border: 1px solid var(--theme-border);
  background: var(--theme-bg-card);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.btn-cancel:hover {
  background: var(--theme-bg-secondary);
}

.btn-submit {
  padding: 10px 20px;
  border: none;
  background: var(--theme-primary);
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.btn-submit:hover {
  background: var(--theme-primary-hover);
}

.btn-submit:disabled {
  background: var(--theme-border);
  cursor: not-allowed;
}

/* 响应式 */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .nav-controls {
    justify-content: center;
  }

  .actions {
    margin-left: 0;
    justify-content: center;
  }

  .calendar-cell {
    min-height: 60px;
    padding: 4px;
  }

  .day-number {
    font-size: 12px;
  }

  .week-body {
    min-height: 300px;
  }

  .form-row {
    flex-direction: column;
    gap: 0;
  }
}
</style>
