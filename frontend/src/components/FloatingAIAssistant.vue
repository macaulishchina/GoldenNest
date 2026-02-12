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
        @click.stop="toggleChat"
      >
        <span class="character-emoji">{{ currentCharacter.emoji }}</span>
      </div>

      <!-- Character menu (on right-click or long-press) -->
      <div v-if="showMenu" class="character-menu" @click.stop>
        <div class="menu-header">选择助手形象</div>
        <div class="character-options">
          <!-- Pet character option (uses real pet data) -->
          <div
            class="character-option"
            :class="{ active: selectedCharacter === 'pet' }"
            @click="selectCharacter('pet')"
          >
            <span class="option-emoji">{{ petInfo ? (petEmojiMap[petInfo.pet_type] || '🥚') : '🥚' }}</span>
            <span class="option-name">{{ petInfo ? petInfo.name : '宠物' }}<span v-if="petInfo" style="font-size: 11px; opacity: 0.6; margin-left: 4px;">（宠物对话）</span></span>
          </div>
          <div
            v-for="(char, key) in characters"
            :key="key"
            class="character-option"
            :class="{ active: selectedCharacter === key }"
            @click="selectCharacter(key)"
          >
            <span class="option-emoji">{{ char.emoji }}</span>
            <span class="option-name">{{ char.name }}</span>
          </div>
        </div>
        <div class="menu-divider"></div>
        <div class="menu-actions">
          <div class="menu-item" @click="resetPosition">
            📍 重置位置
          </div>
          <div class="menu-item" @click="toggleMinimize">
            {{ isMinimized ? '📖 展开' : '📕 最小化' }}
          </div>
          <div class="menu-item close" @click="closeMenu">
            ✕ 关闭菜单
          </div>
        </div>
      </div>
    </div>

    <!-- AI Chat Dialog -->
    <AIChatDialog
      v-model:show="showChat"
      :title="isPetMode ? `💬 与${currentCharacter.name}对话` : `${currentCharacter.name} AI 助手`"
      :ai-name="currentCharacter.name"
      :context-type="isPetMode ? 'pet' : 'general'"
      :suggestions="chatSuggestions"
      :on-chat="isPetMode ? handlePetChat : handleChat"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import AIChatDialog from './AIChatDialog.vue'
import { api, petAiApi } from '@/api'

interface Character {
  emoji: string
  name: string
}

interface Position {
  x: number
  y: number
}

const message = useMessage()

// Character definitions
const characters: Record<string, Character> = {
  cat: { emoji: '🐱', name: '小喵' },
  dog: { emoji: '🐶', name: '汪汪' },
  robot: { emoji: '🤖', name: 'AI助手' },
  dragon: { emoji: '🐉', name: '小龙' }
}

// Pet data
interface PetInfo {
  name: string
  pet_type: string
  happiness: number
  checked_in_today: boolean
}
const petInfo = ref<PetInfo | null>(null)

// Pet type → emoji mapping (same as Pet.vue evolutionStages)
const petEmojiMap: Record<string, string> = {
  golden_egg: '🥚',
  golden_chick: '🐣',
  golden_bird: '🐤',
  golden_phoenix: '🦅',
  golden_dragon: '🐉'
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
let lastTouchToggle = 0  // timestamp guard to prevent double toggle

// Whether current character mode uses pet chat API
const isPetMode = computed(() => selectedCharacter.value === 'pet')

// Chat suggestions - different for pet mode vs general AI mode
const chatSuggestions = computed(() => {
  if (isPetMode.value) {
    const suggestions = ['你好', '今天心情怎么样']
    if (petInfo.value && petInfo.value.happiness < 50) {
      suggestions.push('怎么不开心了')
    }
    if (petInfo.value && !petInfo.value.checked_in_today) {
      suggestions.push('一起签到吧')
    }
    return suggestions
  }
  return [
    '今天的家庭财务情况如何？',
    '帮我分析一下投资组合',
    '最近有哪些未完成的任务？',
    '给我一些理财建议'
  ]
})

// Current character display (pet mode uses real pet info)
const currentCharacter = computed(() => {
  if (selectedCharacter.value === 'pet' && petInfo.value) {
    return {
      emoji: petEmojiMap[petInfo.value.pet_type] || '🥚',
      name: petInfo.value.name
    }
  }
  if (selectedCharacter.value === 'pet') {
    return { emoji: '🥚', name: '宠物' }
  }
  return characters[selectedCharacter.value]
})

// Load saved preferences from localStorage
onMounted(() => {
  loadPreferences()
  loadPetInfo()
  window.addEventListener('resize', handleResize)
  document.addEventListener('mousemove', handleDragMove)
  document.addEventListener('touchmove', handleDragMove, { passive: false })
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchend', stopDrag)
  document.addEventListener('contextmenu', handleContextMenu)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('mousemove', handleDragMove)
  document.removeEventListener('touchmove', handleDragMove)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchend', stopDrag)
  document.removeEventListener('contextmenu', handleContextMenu)
  document.removeEventListener('click', handleClickOutside)
})

// Load pet info from server
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
    // No pet or failed to load — keep petInfo null
    petInfo.value = null
  }
}

function loadPreferences() {
  try {
    const saved = localStorage.getItem('floatingAssistant')
    if (saved) {
      const prefs = JSON.parse(saved)
      if (prefs.character && (characters[prefs.character] || prefs.character === 'pet')) {
        selectedCharacter.value = prefs.character
      }
      if (prefs.position) {
        // Validate position is within screen bounds
        const x = Math.max(0, Math.min(prefs.position.x, window.innerWidth - 80))
        const y = Math.max(0, Math.min(prefs.position.y, window.innerHeight - 80))
        position.value = { x, y }
      }
      if (prefs.isMinimized !== undefined) {
        isMinimized.value = prefs.isMinimized
      }
    }
  } catch (error) {
    console.error('Failed to load assistant preferences:', error)
  }
}

function savePreferences() {
  try {
    const prefs = {
      character: selectedCharacter.value,
      position: position.value,
      isMinimized: isMinimized.value
    }
    localStorage.setItem('floatingAssistant', JSON.stringify(prefs))
  } catch (error) {
    console.error('Failed to save assistant preferences:', error)
  }
}

function handleResize() {
  isMobile.value = window.innerWidth < 768

  // Ensure assistant stays within bounds on resize
  position.value.x = Math.max(0, Math.min(position.value.x, window.innerWidth - 80))
  position.value.y = Math.max(0, Math.min(position.value.y, window.innerHeight - 80))
  savePreferences()
}

function startDrag(e: MouseEvent | TouchEvent) {
  // Prevent drag if clicking menu
  if (showMenu.value) return

  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY

  isDragging.value = true
  wasDragged.value = false
  dragStartPos.value = { x: clientX, y: clientY }
  dragOffset.value = {
    x: clientX - position.value.x,
    y: clientY - position.value.y
  }

  // Start long-press timer for touch devices
  if (e.type === 'touchstart') {
    longPressTimer.value = window.setTimeout(() => {
      showMenu.value = true
      isDragging.value = false
      wasDragged.value = true  // prevent tap action
    }, 500)
  }
}

function handleDragMove(e: MouseEvent | TouchEvent) {
  if (!isDragging.value) return

  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY

  // Only treat as drag if moved > 5px from start
  const dx = Math.abs(clientX - dragStartPos.value.x)
  const dy = Math.abs(clientY - dragStartPos.value.y)
  if (dx < 5 && dy < 5) return

  wasDragged.value = true
  e.preventDefault()  // prevent scrolling during actual drag

  // Clear long-press timer once dragging
  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }

  let x = clientX - dragOffset.value.x
  let y = clientY - dragOffset.value.y

  // Keep within screen bounds
  x = Math.max(0, Math.min(x, window.innerWidth - 80))
  y = Math.max(0, Math.min(y, window.innerHeight - 80))

  position.value = { x, y }
}

function stopDrag(e: Event) {
  const wasNotDragged = isDragging.value && !wasDragged.value

  if (isDragging.value && wasDragged.value) {
    savePreferences()
  }
  isDragging.value = false

  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }

  // On touch devices, handle tap via touchend.
  // Record timestamp so the synthetic click (300ms later) is ignored.
  if (e.type === 'touchend' && wasNotDragged && !showMenu.value) {
    lastTouchToggle = Date.now()
    toggleChat()
  }
}

function toggleChat() {
  if (wasDragged.value) return
  // Guard against synthetic click after touchend (browser fires click ~300ms later)
  if (Date.now() - lastTouchToggle < 400) return
  if (isMinimized.value) {
    isMinimized.value = false
    savePreferences()
    return
  }
  showChat.value = !showChat.value
}

function handleContextMenu(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.closest('.floating-assistant')) {
    e.preventDefault()
    showMenu.value = true
  }
}

function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.character-menu') && !target.closest('.assistant-character')) {
    showMenu.value = false
  }
}

function selectCharacter(key: string) {
  selectedCharacter.value = key
  savePreferences()
  const name = key === 'pet'
    ? (petInfo.value?.name || '宠物')
    : characters[key].name
  message.success(`已切换至 ${name}`)
  closeMenu()
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

async function handleChat(userMessage: string): Promise<{ reply: string; suggestions?: string[] }> {
  try {
    const response = await api.post('/ai/chat', {
      message: userMessage,
      context_type: 'general'
    })

    return {
      reply: response.data.reply,
      suggestions: response.data.suggestions || []
    }
  } catch (error: any) {
    console.error('Chat error:', error)
    throw new Error(error.response?.data?.detail || 'AI 服务暂时不可用')
  }
}

async function handlePetChat(userMessage: string, history: any[] = []): Promise<{ reply: string; suggestions?: string[] }> {
  try {
    const response = await petAiApi.chat({
      message: userMessage,
      history: history
    })

    return {
      reply: response.data.reply,
      suggestions: []
    }
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
  user-select: none;
  touch-action: none;
  transition: transform 0.2s ease;
}

.floating-assistant:active {
  cursor: grabbing;
}

.floating-assistant.dragging {
  transition: none;
}

.floating-assistant.minimized .assistant-character {
  width: 48px;
  height: 48px;
  font-size: 24px;
  opacity: 0.6;
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

.assistant-character:active {
  transform: scale(0.95);
}

.character-emoji {
  font-size: 32px;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.minimized .character-emoji {
  font-size: 24px;
}

/* Idle animation */
.idle-animation {
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

/* Character menu */
.character-menu {
  position: absolute;
  top: 0;
  left: 80px;
  background: var(--theme-bg-card, #ffffff);
  border: 1px solid var(--theme-border-light, #e0e0e0);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  padding: 12px;
  min-width: 200px;
  z-index: 1001;
}

.menu-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--theme-text-secondary, #666);
  margin-bottom: 8px;
  padding: 4px 8px;
}

.character-options {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.character-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.character-option:hover {
  background: var(--theme-bg-secondary, #f5f5f5);
}

.character-option.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 1px solid rgba(102, 126, 234, 0.3);
}

.option-emoji {
  font-size: 24px;
  line-height: 1;
}

.option-name {
  font-size: 14px;
  color: var(--theme-text-primary, #333);
}

.menu-divider {
  height: 1px;
  background: var(--theme-border-light, #e0e0e0);
  margin: 8px 0;
}

.menu-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.menu-item {
  padding: 8px 12px;
  font-size: 13px;
  color: var(--theme-text-primary, #333);
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.menu-item:hover {
  background: var(--theme-bg-secondary, #f5f5f5);
}

.menu-item.close {
  color: var(--theme-text-tertiary, #999);
}

/* Dark mode support */
html.dark .character-menu {
  background: var(--theme-bg-card, #1a1a1a);
  border-color: var(--theme-border-light, #333);
}

html.dark .menu-header {
  color: var(--theme-text-secondary, #999);
}

html.dark .option-name {
  color: var(--theme-text-primary, #e0e0e0);
}

html.dark .menu-item {
  color: var(--theme-text-primary, #e0e0e0);
}

html.dark .character-option:hover,
html.dark .menu-item:hover {
  background: var(--theme-bg-secondary, #2a2a2a);
}

/* Mobile adjustments */
@media (max-width: 767px) {
  .assistant-character {
    width: 56px;
    height: 56px;
  }

  .character-emoji {
    font-size: 28px;
  }

  .character-menu {
    left: auto;
    right: 0;
    top: 70px;
  }

  .floating-assistant.minimized .assistant-character {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }

  .minimized .character-emoji {
    font-size: 20px;
  }
}
</style>
