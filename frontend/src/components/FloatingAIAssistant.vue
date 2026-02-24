<template>
  <div>
    <!-- Floating character -->
    <div
      v-if="!isMobile || showOnMobile"
      class="floating-assistant"
      :class="{ dragging: isDragging, minimized: isMinimized }"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
      @mousedown="startDrag"
      @touchstart="startDrag"
    >
      <div
        class="assistant-character"
        :class="{ 'idle-animation': !isDragging }"
        @click.stop
      >
        <span class="character-emoji">{{ currentCharacter.emoji }}</span>
      </div>

      <!-- Character menu (on right-click or long-press) -->
      <div v-if="showMenu" class="character-menu" :style="menuPositionStyle" @click.stop>
        <!-- Tab switcher -->
        <div class="menu-tabs">
          <div class="menu-tab" :class="{ active: menuTab === 'assistant' }" @click="menuTab = 'assistant'">助手</div>
          <div class="menu-tab" :class="{ active: menuTab === 'shortcut' }" @click="menuTab = 'shortcut'">快捷功能</div>
        </div>

        <!-- Tab: 助手选择 -->
        <template v-if="menuTab === 'assistant'">
          <div class="character-options">
            <!-- Pet (小金) - undeletable, family shared -->
            <div
              class="character-option"
              :class="{ active: selectedCharacter === 'pet' }"
              @click="selectCharacter('pet')"
            >
              <span class="option-emoji">{{ petEmoji }}</span>
              <span class="option-name">{{ petDisplayName }}<span class="option-badge">理财助手</span></span>
            </div>
            <!-- Personal characters (presets + custom) -->
            <div
              v-for="char in personalCharacters"
              :key="char.id"
              class="character-option"
              :class="{ active: selectedCharacter === char.id }"
            >
              <div class="option-main" @click="selectCharacter(char.id)">
                <span class="option-emoji">{{ char.emoji }}</span>
                <span class="option-name">{{ char.name }}</span>
              </div>
              <div class="option-actions">
                <span class="option-action" @click.stop="startEditCharacter(char)" title="编辑">✏️</span>
                <span class="option-action" @click.stop="confirmDeleteCharacter(char)" title="删除">🗑️</span>
              </div>
            </div>
            <!-- Add new -->
            <div class="character-option add-option" @click="startAddCharacter">
              <span class="option-emoji">➕</span>
              <span class="option-name">添加助手</span>
            </div>
          </div>
        </template>

        <!-- Tab: 快捷功能设置 -->
        <template v-if="menuTab === 'shortcut'">
          <div class="shortcut-hint">点击按钮可快速跳转</div>
          <div class="shortcut-options">
            <div
              v-for="mod in quickActionModules"
              :key="mod.key"
              class="shortcut-option"
              :class="{ active: quickActionKey === mod.key }"
              @click="setQuickAction(mod.key)"
            >
              <span class="option-emoji">{{ mod.emoji }}</span>
              <span class="option-name">{{ mod.label }}</span>
              <span v-if="quickActionKey === mod.key" class="option-check">✓</span>
            </div>
          </div>
          <!-- 记账子模式选择 -->
          <template v-if="quickActionKey === 'accounting'">
            <div class="menu-divider"></div>
            <div class="shortcut-hint">记账快捷模式</div>
            <div class="shortcut-options">
              <div
                v-for="sub in accountingSubModes"
                :key="sub.key"
                class="shortcut-option"
                :class="{ active: accountingMode === sub.key }"
                @click="setAccountingMode(sub.key)"
              >
                <span class="option-emoji">{{ sub.emoji }}</span>
                <span class="option-name">{{ sub.label }}</span>
                <span v-if="accountingMode === sub.key" class="option-check">✓</span>
              </div>
            </div>
          </template>
        </template>

        <div class="menu-divider"></div>
        <div class="menu-actions">
          <div class="menu-item" @click="resetPosition">📍 重置位置</div>
          <div class="menu-item" @click="toggleMinimize">{{ isMinimized ? '📖 展开' : '📕 最小化' }}</div>
          <div class="menu-item" @click="resetCurrentChat">🗑️ 重置当前对话</div>
          <div class="menu-item close" @click="closeMenu">✕ 关闭菜单</div>
        </div>
      </div>
    </div>

    <!-- Character edit modal -->
    <div v-if="showEditModal" class="edit-overlay" @click.self="showEditModal = false">
      <div class="edit-modal" @click.stop>
        <div class="edit-header">{{ editingId ? '编辑助手' : '添加助手' }}</div>
        <div class="edit-body">
          <div class="edit-field">
            <label>表情</label>
            <div class="emoji-picker">
              <span
                v-for="e in emojiOptions"
                :key="e"
                class="emoji-choice"
                :class="{ sel: editForm.emoji === e }"
                @click="editForm.emoji = e"
              >{{ e }}</span>
            </div>
            <input v-model="editForm.emoji" class="edit-input" maxlength="2" placeholder="或直接输入 emoji" />
          </div>
          <div class="edit-field">
            <label>名字</label>
            <input v-model="editForm.name" class="edit-input" maxlength="10" placeholder="给助手取个名字" />
          </div>
          <div class="edit-field">
            <label>人设</label>
            <textarea v-model="editForm.persona" class="edit-textarea" maxlength="200" placeholder="描述性格和说话风格..." rows="3"></textarea>
          </div>
        </div>
        <div class="edit-footer">
          <button class="edit-btn cancel" @click="showEditModal = false">取消</button>
          <button class="edit-btn confirm" @click="saveCharacterEdit">确认</button>
        </div>
      </div>
    </div>

    <!-- AI Chat Dialog -->
    <AIChatDialog
      v-model:show="showChat"
      :title="isPetMode ? `💬 与${currentCharacter.name}对话` : `${currentCharacter.name}`"
      :ai-name="currentCharacter.name"
      :context-type="currentContextType"
      :suggestions="chatSuggestions"
      :on-chat="isPetMode ? handlePetChat : handleChat"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useRouter } from 'vue-router'
import AIChatDialog from './AIChatDialog.vue'
import { api, petAiApi } from '@/api'
import { useUserStore } from '@/stores/user'

interface Character {
  emoji: string
  name: string
  persona: string
}

interface PersonalChar {
  id: string
  emoji: string
  name: string
  persona: string
}

interface Position {
  x: number
  y: number
}

interface PetInfo {
  name: string
  pet_type: string
  happiness: number
  checked_in_today: boolean
}

const message = useMessage()
const router = useRouter()
const userStore = useUserStore()

// Default presets for first-time users
const defaultPresets: PersonalChar[] = [
  { id: 'cat', emoji: '🐱', name: '小喵', persona: '你是一只可爱的猫咪"小喵"。说话慵懒可爱，偶尔用"喵~"结尾。你不是理财助手，只是一只陪伴聊天的猫咪，喜欢卖萌、吐槽，偶尔关心主人的生活。回复简短可爱有趣。' },
  { id: 'dog', emoji: '🐶', name: '汪汪', persona: '你是一只忠诚热情的狗狗"汪汪"。说话很有活力，经常用"汪!"表示兴奋。你不是理财助手，只是一只热情的狗狗陪伴者，喜欢鼓励主人、陪伴聊天、撒娇。回复热情简洁。' },
]

// Emoji options for character creation
const emojiOptions = ['🐱', '🐶', '🐰', '🦊', '🐼', '🐨', '🦁', '🐸', '🦉', '🐧', '🦄', '🐙', '👻', '🤡', '🎃', '💀']

// Accounting sub-modes for double-click into accounting
const accountingSubModes = [
  { key: 'voice', label: '语音记账', emoji: '🎤' },
  { key: 'photo', label: '拍照记账', emoji: '📷' },
]

// Quick action modules for double-click
const quickActionModules = [
  { key: 'accounting', label: '记账', emoji: '📝' },
  { key: 'deposit', label: '存款', emoji: '💰' },
  { key: 'expense', label: '支出', emoji: '💳' },
  { key: 'transaction', label: '流水', emoji: '📊' },
  { key: 'todo', label: '清单', emoji: '📋' },
  { key: 'calendar', label: '日历', emoji: '📅' },
  { key: 'pet', label: '宠物', emoji: '🐾' },
  { key: 'investment', label: '理财', emoji: '📈' },
  { key: 'report', label: '报告', emoji: '📑' },
]

// Pet data
const petInfo = ref<PetInfo | null>(null)
const petEmojiMap: Record<string, string> = {
  golden_egg: '🥚', golden_chick: '🐣', golden_bird: '🐤',
  golden_phoenix: '🦅', golden_dragon: '🐉'
}

// State
const isMobile = ref(window.innerWidth < 768)
const showOnMobile = ref(true)
const selectedCharacter = ref<string>('pet')
const position = ref<Position>({ x: 20, y: window.innerHeight - 120 })
const isDragging = ref(false)
const wasDragged = ref(false)
const dragStartPos = ref<Position>({ x: 0, y: 0 })
const dragOffset = ref<Position>({ x: 0, y: 0 })
const showChat = ref(false)
const showMenu = ref(false)
const isMinimized = ref(false)
const longPressTimer = ref<number | null>(null)
let singleTapTimer: number | null = null
const menuTab = ref<'assistant' | 'shortcut'>('assistant')
let lastTouchTime = 0
let lastTapTime = 0
const DOUBLE_TAP_MS = 200

// Personal characters (presets + custom), persisted in localStorage
const personalCharacters = ref<PersonalChar[]>([])

// Quick action
const quickActionKey = ref<string>('accounting')
const accountingMode = ref<string>('voice')  // voice or photo

// Character edit modal
const showEditModal = ref(false)
const editingId = ref<string | null>(null)
const editForm = ref({ emoji: '🐱', name: '', persona: '' })

// ---- Computed ----

const isPetMode = computed(() => selectedCharacter.value === 'pet')

const currentContextType = computed(() => {
  if (selectedCharacter.value === 'pet') return 'pet'
  return `char_${selectedCharacter.value}`
})

const petEmoji = computed(() => {
  if (petInfo.value) return petEmojiMap[petInfo.value.pet_type] || '🥚'
  return '🥚'
})

const petDisplayName = computed(() => petInfo.value?.name || '小金')

const chatSuggestions = computed(() => {
  if (isPetMode.value) {
    const s = ['你好', '今天心情怎么样']
    if (petInfo.value && petInfo.value.happiness < 50) s.push('怎么不开心了')
    if (petInfo.value && !petInfo.value.checked_in_today) s.push('一起签到吧')
    return s
  }
  const char = personalCharacters.value.find(c => c.id === selectedCharacter.value)
  if (char) return ['你好', '陪我聊聊天', '讲个笑话']
  return ['今天的家庭财务情况如何？', '帮我分析一下投资组合', '给我一些理财建议']
})

const currentCharacter = computed((): Character => {
  if (selectedCharacter.value === 'pet') {
    return { emoji: petEmoji.value, name: petDisplayName.value, persona: '' }
  }
  const char = personalCharacters.value.find(c => c.id === selectedCharacter.value)
  if (char) return { emoji: char.emoji, name: char.name, persona: char.persona }
  // Fallback to pet if selected character was deleted
  return { emoji: petEmoji.value, name: petDisplayName.value, persona: '' }
})

const menuPositionStyle = computed(() => {
  const btnX = position.value.x
  const btnY = position.value.y
  const vw = window.innerWidth
  const vh = window.innerHeight
  const style: Record<string, string> = {}
  if (btnX + 40 > vw / 2) { style.right = '80px'; style.left = 'auto' }
  else { style.left = '80px'; style.right = 'auto' }
  if (btnY + 40 > vh / 2) { style.bottom = '0'; style.top = 'auto' }
  else { style.top = '0'; style.bottom = 'auto' }
  return style
})

// ---- Storage ----

const storageKeyChars = computed(() => `ai_assistants_${userStore.user?.id || 'anon'}`)
const PREFS_KEY = 'floatingAssistant'

// ---- Lifecycle ----

onMounted(() => {
  loadPersonalCharacters()
  loadPreferences()
  loadPetInfo()
  window.addEventListener('resize', handleResize)
  document.addEventListener('mousemove', handleDragMove)
  document.addEventListener('touchmove', handleDragMove, { passive: false })
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchend', stopDrag)
  document.addEventListener('contextmenu', handleContextMenu)
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('selectstart', handleSelectStart)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('mousemove', handleDragMove)
  document.removeEventListener('touchmove', handleDragMove)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchend', stopDrag)
  document.removeEventListener('contextmenu', handleContextMenu)
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('selectstart', handleSelectStart)
})

// ---- Load / Save ----

async function loadPetInfo() {
  try {
    const res = await api.get('/pet')
    if (res.data) {
      petInfo.value = {
        name: res.data.name,
        pet_type: res.data.pet_type,
        happiness: res.data.happiness,
        checked_in_today: res.data.checked_in_today
      }
    }
  } catch {
    petInfo.value = null
  }
}

function loadPersonalCharacters() {
  try {
    const saved = localStorage.getItem(storageKeyChars.value)
    if (saved) {
      personalCharacters.value = JSON.parse(saved)
    } else {
      // First time → initialize with presets
      personalCharacters.value = [...defaultPresets]
      savePersonalCharacters()
    }
  } catch {
    personalCharacters.value = [...defaultPresets]
  }
}

function savePersonalCharacters() {
  try {
    localStorage.setItem(storageKeyChars.value, JSON.stringify(personalCharacters.value))
  } catch { /* ignore */ }
}

function loadPreferences() {
  try {
    const saved = localStorage.getItem(PREFS_KEY)
    if (saved) {
      const prefs = JSON.parse(saved)
      if (prefs.character) {
        // Validate character still exists
        if (prefs.character === 'pet' || personalCharacters.value.some(c => c.id === prefs.character)) {
          selectedCharacter.value = prefs.character
        }
      }
      if (prefs.position) {
        position.value = {
          x: Math.max(0, Math.min(prefs.position.x, window.innerWidth - 80)),
          y: Math.max(0, Math.min(prefs.position.y, window.innerHeight - 80))
        }
      }
      if (prefs.isMinimized !== undefined) isMinimized.value = prefs.isMinimized
      if (prefs.quickAction) quickActionKey.value = prefs.quickAction
      if (prefs.accountingMode) accountingMode.value = prefs.accountingMode
    }
  } catch { /* ignore */ }
}

function savePreferences() {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify({
      character: selectedCharacter.value,
      position: position.value,
      isMinimized: isMinimized.value,
      quickAction: quickActionKey.value,
      accountingMode: accountingMode.value
    }))
  } catch { /* ignore */ }
}

function handleResize() {
  isMobile.value = window.innerWidth < 768
  position.value.x = Math.max(0, Math.min(position.value.x, window.innerWidth - 80))
  position.value.y = Math.max(0, Math.min(position.value.y, window.innerHeight - 80))
  savePreferences()
}

// ---- Drag & Click ----

function startDrag(e: MouseEvent | TouchEvent) {
  if (showMenu.value || showEditModal.value) return

  if ('touches' in e) {
    e.preventDefault()
    lastTouchTime = Date.now()
  } else if (Date.now() - lastTouchTime < 800) {
    return
  }

  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY

  isDragging.value = true
  wasDragged.value = false
  dragStartPos.value = { x: clientX, y: clientY }
  dragOffset.value = { x: clientX - position.value.x, y: clientY - position.value.y }

  // Long press → open config menu (both touch and mouse)
  longPressTimer.value = window.setTimeout(() => {
    isDragging.value = false
    wasDragged.value = true
    showMenu.value = true
    menuTab.value = 'assistant'
  }, 500)
}

function handleDragMove(e: MouseEvent | TouchEvent) {
  if (!isDragging.value) return

  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  const dx = Math.abs(clientX - dragStartPos.value.x)
  const dy = Math.abs(clientY - dragStartPos.value.y)
  if (dx < 5 && dy < 5) return

  wasDragged.value = true
  e.preventDefault()

  if (longPressTimer.value) { clearTimeout(longPressTimer.value); longPressTimer.value = null }

  let x = clientX - dragOffset.value.x
  let y = clientY - dragOffset.value.y
  x = Math.max(0, Math.min(x, window.innerWidth - 80))
  y = Math.max(0, Math.min(y, window.innerHeight - 80))
  position.value = { x, y }
}

function stopDrag(e: Event) {
  const wasNotDragged = isDragging.value && !wasDragged.value
  if (isDragging.value && wasDragged.value) savePreferences()
  isDragging.value = false
  if (longPressTimer.value) { clearTimeout(longPressTimer.value); longPressTimer.value = null }

  if (wasNotDragged && !showMenu.value) {
    if (e.type === 'touchend') lastTouchTime = Date.now()
    handleTap()
  }
}

function handleTap() {
  if (isMinimized.value) {
    isMinimized.value = false
    savePreferences()
    return
  }

  const now = Date.now()
  if (now - lastTapTime < DOUBLE_TAP_MS) {
    // Double-tap → cancel pending single-tap and execute quick action
    lastTapTime = 0
    if (singleTapTimer) { clearTimeout(singleTapTimer); singleTapTimer = null }
    executeQuickAction()
    return
  }
  lastTapTime = now
  // Defer single-tap to allow double-tap cancellation (200ms, barely perceptible)
  singleTapTimer = window.setTimeout(() => {
    singleTapTimer = null
    if (lastTapTime === now) {
      showChat.value = !showChat.value
    }
  }, DOUBLE_TAP_MS)
}

function executeQuickAction() {
  const mod = quickActionModules.find(m => m.key === quickActionKey.value)
  if (quickActionKey.value === 'accounting') {
    router.push({ path: '/accounting', query: { mode: accountingMode.value } })
  } else {
    router.push(`/${quickActionKey.value}`)
  }
  message.info(`快捷跳转：${mod?.label || quickActionKey.value}`)
}

function handleSelectStart(e: Event) {
  const target = e.target
  if (!(target instanceof HTMLElement)) return
  if (target.closest('.floating-assistant') || isDragging.value) {
    e.preventDefault()
  }
}

function handleContextMenu(e: MouseEvent) {
  const target = e.target
  if (!(target instanceof HTMLElement)) return
  if (target.closest('.floating-assistant')) {
    e.preventDefault()
    // Right-click on desktop → open config menu (same as double-tap)
    showMenu.value = true
    menuTab.value = 'assistant'
  }
}

function handleClickOutside(e: MouseEvent) {
  const target = e.target
  if (!(target instanceof HTMLElement)) return
  if (!target.closest('.character-menu') && !target.closest('.assistant-character')) {
    showMenu.value = false
  }
}

// ---- Character Management ----

function selectCharacter(key: string) {
  selectedCharacter.value = key
  savePreferences()
  message.success(`已切换至 ${currentCharacter.value.name}`)
  closeMenu()
}

function startAddCharacter() {
  editingId.value = null
  editForm.value = { emoji: '🐱', name: '', persona: '' }
  showEditModal.value = true
}

function startEditCharacter(char: PersonalChar) {
  editingId.value = char.id
  editForm.value = { emoji: char.emoji, name: char.name, persona: char.persona }
  showEditModal.value = true
}

function saveCharacterEdit() {
  if (!editForm.value.name.trim()) {
    message.warning('请输入助手名字')
    return
  }
  if (!editForm.value.emoji.trim()) {
    message.warning('请选择一个表情')
    return
  }

  if (editingId.value) {
    // Edit existing
    const idx = personalCharacters.value.findIndex(c => c.id === editingId.value)
    if (idx >= 0) {
      personalCharacters.value[idx] = {
        ...personalCharacters.value[idx],
        emoji: editForm.value.emoji,
        name: editForm.value.name,
        persona: editForm.value.persona,
      }
    }
  } else {
    // Add new
    personalCharacters.value.push({
      id: `custom_${Date.now()}`,
      emoji: editForm.value.emoji,
      name: editForm.value.name,
      persona: editForm.value.persona,
    })
  }

  savePersonalCharacters()
  showEditModal.value = false
  message.success(editingId.value ? '助手已更新' : '助手已添加')
}

function confirmDeleteCharacter(char: PersonalChar) {
  if (selectedCharacter.value === char.id) {
    selectedCharacter.value = 'pet'
    savePreferences()
  }
  personalCharacters.value = personalCharacters.value.filter(c => c.id !== char.id)
  savePersonalCharacters()
  // Clear chat history for deleted character
  const userId = userStore.user?.id || 'anonymous'
  localStorage.removeItem(`ai_chat_${userId}_char_${char.id}`)
  message.success(`已删除 ${char.name}`)
}

function setQuickAction(key: string) {
  quickActionKey.value = key
  savePreferences()
  message.success(`快捷功能已设为：${quickActionModules.find(m => m.key === key)?.label}`)
}

function setAccountingMode(key: string) {
  accountingMode.value = key
  savePreferences()
  const sub = accountingSubModes.find(s => s.key === key)
  message.success(`记账快捷模式：${sub?.label}`)
}

function resetPosition() {
  position.value = { x: 20, y: window.innerHeight - 120 }
  savePreferences()
  message.success('位置已重置')
  closeMenu()
}

function toggleMinimize() {
  isMinimized.value = !isMinimized.value
  savePreferences()
  closeMenu()
}

function closeMenu() {
  showMenu.value = false
}

function resetCurrentChat() {
  const userId = userStore.user?.id || 'anonymous'
  localStorage.removeItem(`ai_chat_${userId}_${currentContextType.value}`)
  showChat.value = false
  message.success(`已重置 ${currentCharacter.value.name} 的对话`)
  closeMenu()
}

// ---- Chat Handlers ----

async function handleChat(userMessage: string, history: any[] = []): Promise<{ reply: string; suggestions?: string[] }> {
  try {
    const char = personalCharacters.value.find(c => c.id === selectedCharacter.value)
    const response = await api.post('/ai/chat', {
      message: userMessage,
      context_type: currentContextType.value,
      history: history,
      persona: char?.persona || ''
    })
    return { reply: response.data.reply, suggestions: response.data.suggestions || [] }
  } catch (error: any) {
    console.error('Chat error:', error)
    throw new Error(error.response?.data?.detail || 'AI 服务暂时不可用')
  }
}

async function handlePetChat(userMessage: string, history: any[] = []): Promise<{ reply: string; suggestions?: string[] }> {
  try {
    const response = await petAiApi.chat({ message: userMessage, history: history })
    return { reply: response.data.reply, suggestions: [] }
  } catch (error: any) {
    console.error('Pet chat error:', error)
    throw new Error(error.response?.data?.detail || '宠物对话服务暂时不可用')
  }
}
</script>

<style scoped>
.floating-assistant {
  position: fixed;
  z-index: 1000;
  cursor: move;
  -webkit-user-select: none;
  user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition: transform 0.2s ease;
}

.floating-assistant:active { cursor: grabbing; }
.floating-assistant.dragging { transition: none; }
.floating-assistant.minimized .assistant-character {
  width: 48px; height: 48px; font-size: 24px; opacity: 0.6;
}

.assistant-character {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
  cursor: pointer;
  transition: all 0.3s ease;
}

.assistant-character:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.6);
}
.assistant-character:active { transform: scale(0.95); }

.character-emoji {
  font-size: 32px;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}
.minimized .character-emoji { font-size: 24px; }

.idle-animation {
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

/* Character menu */
.character-menu {
  position: absolute;
  background: var(--theme-bg-card, #fff);
  border: 1px solid var(--theme-border-light, #e0e0e0);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  padding: 12px;
  min-width: 220px;
  max-height: 70vh;
  overflow-y: auto;
  z-index: 1001;
}

/* Menu tabs */
.menu-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
  background: var(--theme-bg-secondary, #f5f5f5);
  border-radius: 8px;
  padding: 2px;
}

.menu-tab {
  flex: 1;
  text-align: center;
  padding: 6px 8px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--theme-text-secondary, #666);
}

.menu-tab.active {
  background: var(--theme-bg-card, #fff);
  color: var(--theme-text-primary, #333);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.character-options { display: flex; flex-direction: column; gap: 2px; }

.character-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.character-option:hover { background: var(--theme-bg-secondary, #f5f5f5); }

.character-option.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 1px solid rgba(102, 126, 234, 0.3);
}

.character-option .option-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.character-option .option-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}

.character-option:hover .option-actions { opacity: 1; }

.option-action {
  font-size: 14px;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  transition: background 0.15s;
}

.option-action:hover { background: rgba(0, 0, 0, 0.08); }
.add-option { opacity: 0.7; }
.add-option:hover { opacity: 1; }

.option-emoji { font-size: 22px; line-height: 1; flex-shrink: 0; }

.option-name {
  font-size: 13px;
  color: var(--theme-text-primary, #333);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-badge {
  font-size: 10px;
  opacity: 0.55;
  margin-left: 4px;
  background: rgba(102, 126, 234, 0.12);
  padding: 1px 5px;
  border-radius: 4px;
}

.option-check { font-size: 14px; color: #667eea; margin-left: auto; }

/* Shortcut options */
.shortcut-hint {
  font-size: 11px;
  color: var(--theme-text-tertiary, #999);
  padding: 4px 8px;
  margin-bottom: 4px;
}

.shortcut-options { display: flex; flex-direction: column; gap: 2px; }

.shortcut-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.shortcut-option:hover { background: var(--theme-bg-secondary, #f5f5f5); }
.shortcut-option.active { background: rgba(102, 126, 234, 0.08); }

.menu-divider {
  height: 1px;
  background: var(--theme-border-light, #e0e0e0);
  margin: 8px 0;
}

.menu-actions { display: flex; flex-direction: column; gap: 2px; }

.menu-item {
  padding: 8px 12px;
  font-size: 13px;
  color: var(--theme-text-primary, #333);
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.menu-item:hover { background: var(--theme-bg-secondary, #f5f5f5); }
.menu-item.close { color: var(--theme-text-tertiary, #999); }

/* Edit modal */
.edit-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}

.edit-modal {
  background: var(--theme-bg-card, #fff);
  border-radius: 14px;
  padding: 20px;
  width: 320px;
  max-width: 90vw;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
}

.edit-header {
  font-size: 16px;
  font-weight: 600;
  color: var(--theme-text-primary, #333);
  margin-bottom: 16px;
}

.edit-body { display: flex; flex-direction: column; gap: 14px; }

.edit-field label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--theme-text-secondary, #666);
  margin-bottom: 6px;
}

.emoji-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.emoji-choice {
  font-size: 22px;
  padding: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  border: 2px solid transparent;
}

.emoji-choice:hover { background: rgba(102, 126, 234, 0.1); }
.emoji-choice.sel { border-color: #667eea; background: rgba(102, 126, 234, 0.1); }

.edit-input {
  width: 100%;
  padding: 8px 10px;
  font-size: 14px;
  border: 1px solid var(--theme-border-light, #ddd);
  border-radius: 8px;
  outline: none;
  background: var(--theme-bg-card, #fff);
  color: var(--theme-text-primary, #333);
  box-sizing: border-box;
}

.edit-input:focus { border-color: #667eea; }

.edit-textarea {
  width: 100%;
  padding: 8px 10px;
  font-size: 13px;
  border: 1px solid var(--theme-border-light, #ddd);
  border-radius: 8px;
  outline: none;
  resize: vertical;
  background: var(--theme-bg-card, #fff);
  color: var(--theme-text-primary, #333);
  box-sizing: border-box;
  font-family: inherit;
}

.edit-textarea:focus { border-color: #667eea; }

.edit-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.edit-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.edit-btn.cancel {
  background: var(--theme-bg-secondary, #f0f0f0);
  color: var(--theme-text-primary, #333);
}

.edit-btn.cancel:hover { background: #e0e0e0; }

.edit-btn.confirm {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}

.edit-btn.confirm:hover { opacity: 0.9; }

/* Dark mode */
html.dark .character-menu {
  background: var(--theme-bg-card, #1a1a1a);
  border-color: var(--theme-border-light, #333);
}

html.dark .menu-tabs { background: var(--theme-bg-secondary, #2a2a2a); }
html.dark .menu-tab { color: var(--theme-text-secondary, #999); }
html.dark .menu-tab.active {
  background: var(--theme-bg-card, #1a1a1a);
  color: var(--theme-text-primary, #e0e0e0);
}

html.dark .option-name,
html.dark .menu-item {
  color: var(--theme-text-primary, #e0e0e0);
}

html.dark .character-option:hover,
html.dark .menu-item:hover,
html.dark .shortcut-option:hover {
  background: var(--theme-bg-secondary, #2a2a2a);
}

html.dark .edit-modal {
  background: var(--theme-bg-card, #1a1a1a);
}

html.dark .edit-header {
  color: var(--theme-text-primary, #e0e0e0);
}

html.dark .edit-input,
html.dark .edit-textarea {
  background: var(--theme-bg-secondary, #2a2a2a);
  color: var(--theme-text-primary, #e0e0e0);
  border-color: var(--theme-border-light, #444);
}

html.dark .edit-btn.cancel { background: #333; color: #ccc; }

/* Mobile adjustments */
@media (max-width: 767px) {
  .assistant-character {
    width: 56px;
    height: 56px;
  }

  .character-emoji {
    font-size: 28px;
  }

  .floating-assistant.minimized .assistant-character {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }

  .minimized .character-emoji {
    font-size: 20px;
  }

  /* Always show action buttons on mobile (no hover) */
  .character-option .option-actions { opacity: 1; }
}
</style>
