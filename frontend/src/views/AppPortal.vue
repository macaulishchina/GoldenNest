<template>
  <div class="page-container">
    <div class="page-header-row">
      <h1 class="page-title">
        <span class="icon">🧩</span>
        应用中心
      </h1>
      <div class="header-actions" v-if="userStore.isAdmin">
        <n-button type="primary" @click="openCreateModal">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加应用
        </n-button>
      </div>
    </div>

    <!-- 全屏 iframe 覆盖层 -->
    <Teleport to="body">
      <Transition name="fullscreen-fade">
        <div v-if="fullscreenApp" class="fullscreen-overlay">
          <div class="fullscreen-header">
            <div class="fullscreen-title">
              <span v-if="fullscreenApp.icon_type === 'emoji'" class="fullscreen-icon-emoji">{{ fullscreenApp.icon_emoji || '🔗' }}</span>
              <img v-else-if="fullscreenApp.icon_image" :src="fullscreenApp.icon_image" class="fullscreen-icon-img" />
              <span>{{ fullscreenApp.name }}</span>
            </div>
            <div class="fullscreen-actions">
              <n-button text @click="openInNewTab(fullscreenApp.url)" title="在新标签页打开">
                <template #icon><n-icon :size="20"><OpenOutline /></n-icon></template>
              </n-button>
              <n-button text @click="closeFullscreen" title="关闭">
                <template #icon><n-icon :size="22"><CloseOutline /></n-icon></template>
              </n-button>
            </div>
          </div>
          <!-- 加载提示层 -->
          <div v-if="iframeLoading" class="iframe-loading">
            <n-spin size="large" />
            <p style="margin-top: 12px; color: var(--n-text-color-3, #999)">正在加载应用...</p>
          </div>
          <!-- 加载失败提示 -->
          <div v-if="iframeError" class="iframe-error-hint">
            <p>如果应用长时间未加载，可能不支持嵌入显示</p>
            <n-button type="primary" size="small" @click="openInNewTab(fullscreenApp!.url)">在新标签页打开</n-button>
          </div>
          <iframe
            ref="fullscreenIframeRef"
            :src="fullscreenApp.url"
            class="fullscreen-iframe"
            frameborder="0"
            allow="fullscreen; clipboard-write; clipboard-read; camera; microphone"
            referrerpolicy="no-referrer-when-downgrade"
            @load="onIframeLoad"
          />
        </div>
      </Transition>
    </Teleport>

    <!-- 应用网格 -->
    <div v-if="loading" class="loading-container">
      <n-spin size="large" />
    </div>

    <template v-else>
      <div v-if="apps.length > 0" class="app-grid">
        <div
          v-for="app in apps"
          :key="app.id"
          class="app-card"
          @click="handleAppClick(app)"
        >
          <!-- 管理操作浮层 -->
          <div v-if="userStore.isAdmin" class="app-card-actions" @click.stop>
            <n-dropdown :options="appActionOptions" @select="(key: string) => handleAppAction(key, app)" trigger="click" placement="bottom-end">
              <n-button text size="tiny" class="action-btn">
                <n-icon :size="16"><EllipsisVerticalOutline /></n-icon>
              </n-button>
            </n-dropdown>
          </div>

          <!-- 图标 -->
          <div class="app-icon-wrapper">
            <span v-if="app.icon_type === 'emoji'" class="app-icon-emoji">{{ app.icon_emoji || '🔗' }}</span>
            <img v-else-if="app.icon_image" :src="app.icon_image" class="app-icon-img" />
            <span v-else class="app-icon-emoji">🔗</span>
          </div>

          <!-- 名称 -->
          <div class="app-name">{{ app.name }}</div>

          <!-- 描述 -->
          <div v-if="app.description" class="app-desc">{{ app.description }}</div>

          <!-- 打开方式标记 -->
          <div class="app-mode-badge" v-if="app.open_mode === 'fullscreen'">
            <n-icon :size="12"><ExpandOutline /></n-icon>
          </div>

          <!-- 未激活标记（仅管理员可见） -->
          <div v-if="!app.is_active && userStore.isAdmin" class="app-inactive-badge">
            已停用
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty v-else :description="userStore.isAdmin ? '还没有添加任何应用' : '暂无可用应用'" style="margin-top: 60px">
        <template #extra v-if="userStore.isAdmin">
          <n-button type="primary" @click="openCreateModal">添加第一个应用</n-button>
        </template>
      </n-empty>
    </template>

    <!-- 创建/编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card" :title="editingApp ? '编辑应用' : '添加应用'" style="max-width: 520px" :mask-closable="false">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="80">
        <n-form-item label="应用名称" path="name">
          <n-input v-model:value="formData.name" placeholder="如：文档协作、项目看板" maxlength="50" show-count />
        </n-form-item>

        <n-form-item label="应用地址" path="url">
          <n-input v-model:value="formData.url" placeholder="https://example.com" />
        </n-form-item>

        <n-form-item label="简短描述">
          <n-input v-model:value="formData.description" placeholder="可选的描述信息" maxlength="100" show-count />
        </n-form-item>

        <n-form-item label="图标类型">
          <n-radio-group v-model:value="formData.icon_type">
            <n-radio-button value="emoji">Emoji</n-radio-button>
            <n-radio-button value="image">上传图片</n-radio-button>
          </n-radio-group>
        </n-form-item>

        <n-form-item v-if="formData.icon_type === 'emoji'" label="选择 Emoji">
          <div class="emoji-picker">
            <span
              v-for="emoji in emojiOptions"
              :key="emoji"
              class="emoji-option"
              :class="{ selected: formData.icon_emoji === emoji }"
              @click="formData.icon_emoji = emoji"
            >{{ emoji }}</span>
          </div>
        </n-form-item>

        <n-form-item v-if="formData.icon_type === 'image'" label="上传图标">
          <div class="icon-upload-area">
            <div v-if="editingApp?.icon_image && formData.icon_type === 'image'" class="current-icon-preview">
              <img :src="editingApp.icon_image" class="preview-img" />
              <span class="preview-label">当前图标</span>
            </div>
            <n-upload
              :max="1"
              accept="image/*"
              :default-upload="false"
              @change="handleIconFileChange"
              :show-file-list="false"
            >
              <n-button>{{ editingApp?.icon_image ? '更换图标' : '选择图片' }}</n-button>
            </n-upload>
            <span v-if="pendingIconFile" class="pending-file-name">{{ pendingIconFile.name }}</span>
          </div>
        </n-form-item>

        <n-form-item label="打开方式">
          <n-radio-group v-model:value="formData.open_mode">
            <n-radio-button value="new_tab">新标签页</n-radio-button>
            <n-radio-button value="fullscreen">全屏嵌入</n-radio-button>
          </n-radio-group>
        </n-form-item>

        <n-form-item label="排序权重">
          <n-input-number v-model:value="formData.sort_order" :min="0" :max="9999" placeholder="越小越靠前" style="width: 100%" />
        </n-form-item>

        <n-form-item label="状态">
          <n-switch v-model:value="formData.is_active" />
          <span style="margin-left: 8px; color: var(--text-color-3)">{{ formData.is_active ? '已激活' : '已停用' }}</span>
        </n-form-item>
      </n-form>

      <template #action>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">
            {{ editingApp ? '保存' : '创建' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { useUserStore } from '@/stores/user'
import { externalAppApi } from '@/api'
import {
  AddOutline,
  CloseOutline,
  OpenOutline,
  EllipsisVerticalOutline,
  ExpandOutline
} from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()

// ==================== 数据 ====================

interface AppItem {
  id: number
  name: string
  url: string
  icon_type: string
  icon_emoji: string | null
  icon_image: string | null
  description: string | null
  open_mode: string
  sort_order: number
  is_active: boolean
  created_by: number | null
  created_at: string | null
  updated_at: string | null
}

const loading = ref(false)
const apps = ref<AppItem[]>([])

// Modal
const showModal = ref(false)
const editingApp = ref<AppItem | null>(null)
const saving = ref(false)
const formRef = ref<any>(null)
const pendingIconFile = ref<File | null>(null)

const formData = ref({
  name: '',
  url: '',
  icon_type: 'emoji',
  icon_emoji: '🔗',
  description: '',
  open_mode: 'new_tab',
  sort_order: 0,
  is_active: true,
})

const formRules = {
  name: [{ required: true, message: '请输入应用名称', trigger: 'blur' }],
  url: [
    { required: true, message: '请输入应用地址', trigger: 'blur' },
    { pattern: /^https?:\/\/.+/, message: '请输入有效的 URL（以 http:// 或 https:// 开头）', trigger: 'blur' }
  ]
}

// Fullscreen iframe
const fullscreenApp = ref<AppItem | null>(null)
const fullscreenIframeRef = ref<HTMLIFrameElement | null>(null)
const iframeLoading = ref(false)
const iframeError = ref(false)
let iframeErrorTimer: ReturnType<typeof setTimeout> | null = null

// Emoji options
const emojiOptions = [
  '🔗', '📝', '📊', '📁', '💬', '🎯', '🛠️', '🎮',
  '📷', '🎵', '🎬', '📚', '🗂️', '🌐', '☁️', '🔒',
  '📈', '💡', '🏠', '⚡', '🔧', '🎨', '📦', '🚀',
  '💻', '📱', '🖥️', '⌨️', '🗃️', '📋', '✅', '🔔',
]

// Action dropdown options
const appActionOptions = [
  { label: '编辑', key: 'edit' },
  { label: '删除', key: 'delete' },
]

// ==================== 方法 ====================

async function fetchApps() {
  loading.value = true
  try {
    // 管理员看全部（含未激活），普通用户只看激活的
    const res = userStore.isAdmin
      ? await externalAppApi.listAll()
      : await externalAppApi.list()
    apps.value = res.data
  } catch (e: any) {
    message.error(e.response?.data?.detail || '加载应用列表失败')
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  editingApp.value = null
  pendingIconFile.value = null
  formData.value = {
    name: '',
    url: '',
    icon_type: 'emoji',
    icon_emoji: '🔗',
    description: '',
    open_mode: 'new_tab',
    sort_order: apps.value.length * 10,
    is_active: true,
  }
  showModal.value = true
}

function openEditModal(app: AppItem) {
  editingApp.value = app
  pendingIconFile.value = null
  formData.value = {
    name: app.name,
    url: app.url,
    icon_type: app.icon_type,
    icon_emoji: app.icon_emoji || '🔗',
    description: app.description || '',
    open_mode: app.open_mode,
    sort_order: app.sort_order,
    is_active: app.is_active,
  }
  showModal.value = true
}

function handleIconFileChange(data: { file: { file: File | null } }) {
  pendingIconFile.value = data.file.file
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload: any = { ...formData.value }
    // 如果图标类型是 image，不传 icon_emoji
    if (payload.icon_type === 'image') {
      delete payload.icon_emoji
    }

    if (editingApp.value) {
      // 更新
      await externalAppApi.update(editingApp.value.id, payload)
      // 上传新图标
      if (pendingIconFile.value) {
        await externalAppApi.uploadIcon(editingApp.value.id, pendingIconFile.value)
      }
      message.success('应用已更新')
    } else {
      // 创建
      const res = await externalAppApi.create(payload)
      // 如果有待上传图标
      if (pendingIconFile.value && res.data?.id) {
        await externalAppApi.uploadIcon(res.data.id, pendingIconFile.value)
      }
      message.success('应用已创建')
    }

    showModal.value = false
    await fetchApps()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function handleAppAction(key: string, app: AppItem) {
  if (key === 'edit') {
    openEditModal(app)
  } else if (key === 'delete') {
    dialog.warning({
      title: '删除确认',
      content: `确定要删除应用「${app.name}」吗？此操作不可撤销。`,
      positiveText: '删除',
      negativeText: '取消',
      onPositiveClick: async () => {
        try {
          await externalAppApi.remove(app.id)
          message.success('应用已删除')
          await fetchApps()
        } catch (e: any) {
          message.error(e.response?.data?.detail || '删除失败')
        }
      }
    })
  }
}

function handleAppClick(app: AppItem) {
  if (app.open_mode === 'fullscreen') {
    iframeLoading.value = true
    iframeError.value = false
    fullscreenApp.value = app
    // 5秒后显示“无法加载”提示（但不关闭 iframe）
    iframeErrorTimer = setTimeout(() => {
      if (iframeLoading.value) {
        iframeError.value = true
      }
    }, 5000)
  } else {
    openInNewTab(app.url)
  }
}

function onIframeLoad() {
  iframeLoading.value = false
  iframeError.value = false
  if (iframeErrorTimer) {
    clearTimeout(iframeErrorTimer)
    iframeErrorTimer = null
  }
}

function openInNewTab(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

function closeFullscreen() {
  fullscreenApp.value = null
  iframeLoading.value = false
  iframeError.value = false
  if (iframeErrorTimer) {
    clearTimeout(iframeErrorTimer)
    iframeErrorTimer = null
  }
}

// ESC 关闭全屏
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && fullscreenApp.value) {
    closeFullscreen()
  }
}

onMounted(() => {
  fetchApps()
  window.addEventListener('keydown', handleKeydown)
})

// Cleanup
import { onUnmounted } from 'vue'
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.page-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px;
}

.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.page-title .icon {
  font-size: 26px;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}

/* ==================== 应用网格 ==================== */

.app-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}

.app-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 12px 16px;
  border-radius: 12px;
  background: var(--n-color, #fff);
  border: 1px solid var(--n-border-color, #efeff5);
  cursor: pointer;
  transition: all 0.25s ease;
  min-height: 120px;
}

.app-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border-color: var(--n-primary-color, #18a058);
}

.app-card:active {
  transform: translateY(0);
}

/* 卡片管理操作 */
.app-card-actions {
  position: absolute;
  top: 4px;
  right: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.app-card:hover .app-card-actions {
  opacity: 1;
}

.action-btn {
  padding: 4px !important;
  border-radius: 6px;
}

/* 图标 */
.app-icon-wrapper {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
  overflow: hidden;
  flex-shrink: 0;
}

.app-icon-emoji {
  font-size: 40px;
  line-height: 1;
}

.app-icon-img {
  width: 52px;
  height: 52px;
  object-fit: contain;
  border-radius: 12px;
}

/* 名称 */
.app-name {
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  line-height: 1.3;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 描述 */
.app-desc {
  font-size: 11px;
  color: var(--n-text-color-3, #999);
  text-align: center;
  margin-top: 4px;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 打开方式标记 */
.app-mode-badge {
  position: absolute;
  bottom: 6px;
  right: 8px;
  color: var(--n-text-color-3, #bbb);
}

/* 未激活标记 */
.app-inactive-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  font-size: 10px;
  color: #fff;
  background: var(--n-error-color, #e88080);
  padding: 1px 6px;
  border-radius: 4px;
  line-height: 1.5;
}

/* ==================== Emoji 选择器 ==================== */

.emoji-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 120px;
  overflow-y: auto;
}

.emoji-option {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  cursor: pointer;
  border-radius: 8px;
  border: 2px solid transparent;
  transition: all 0.15s;
}

.emoji-option:hover {
  background: var(--n-action-color, #f0f0f5);
}

.emoji-option.selected {
  border-color: var(--n-primary-color, #18a058);
  background: var(--n-primary-color-hover, #36ad6a20);
}

/* ==================== 图标上传区 ==================== */

.icon-upload-area {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.current-icon-preview {
  display: flex;
  align-items: center;
  gap: 6px;
}

.preview-img {
  width: 36px;
  height: 36px;
  object-fit: contain;
  border-radius: 6px;
  border: 1px solid var(--n-border-color, #eee);
}

.preview-label {
  font-size: 12px;
  color: var(--n-text-color-3, #999);
}

.pending-file-name {
  font-size: 12px;
  color: var(--n-text-color-2, #666);
}

/* ==================== 全屏 iframe 覆盖层 ==================== */

.fullscreen-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: var(--n-body-color, #fff);
  display: flex;
  flex-direction: column;
}

.fullscreen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: var(--n-primary-color, #18a058);
  color: #fff;
  flex-shrink: 0;
  height: 48px;
  box-sizing: border-box;
}

.fullscreen-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.fullscreen-icon-emoji {
  font-size: 20px;
}

.fullscreen-icon-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
  border-radius: 4px;
}

.fullscreen-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  color: rgba(255, 255, 255, 0.9);
}

.fullscreen-actions :deep(.n-button) {
  color: rgba(255, 255, 255, 0.9) !important;
}

.fullscreen-actions :deep(.n-button:hover) {
  color: #fff !important;
}

.fullscreen-iframe {
  flex: 1;
  width: 100%;
  border: none;
  background: var(--n-body-color, #fff);
}

/* 加载提示 */
.iframe-loading {
  position: absolute;
  inset: 48px 0 0 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1;
  pointer-events: none;
}

/* 加载失败提示 */
.iframe-error-hint {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  background: var(--n-card-color, #fff);
  border: 1px solid var(--n-border-color, #eee);
  border-radius: 10px;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  font-size: 13px;
  color: var(--n-text-color-2, #666);
}

/* Transition */
.fullscreen-fade-enter-active,
.fullscreen-fade-leave-active {
  transition: opacity 0.2s ease;
}
.fullscreen-fade-enter-from,
.fullscreen-fade-leave-to {
  opacity: 0;
}

/* ==================== 响应式 ==================== */

@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }

  .page-title {
    font-size: 18px;
  }

  .app-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  .app-card {
    padding: 16px 8px 12px;
    min-height: 100px;
  }

  .app-icon-wrapper {
    width: 48px;
    height: 48px;
    margin-bottom: 8px;
  }

  .app-icon-emoji {
    font-size: 34px;
  }

  .app-icon-img {
    width: 44px;
    height: 44px;
  }

  .app-name {
    font-size: 12px;
  }

  .app-card-actions {
    opacity: 1;
  }

  .fullscreen-header {
    padding: 6px 12px;
  }
}
</style>
