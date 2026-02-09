<template>
  <div class="announcement-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>📢 家庭公告板</h1>
      <p>分享家庭动态，记录美好时刻</p>
    </div>

    <!-- 发布区域 -->
    <div class="publish-area">
      <div class="publish-card">
        <textarea 
          v-model="newContent" 
          placeholder="有什么想和家人分享的？"
          rows="3"
        ></textarea>
        <div class="publish-actions">
          <label class="upload-btn">
            🖼️ 添加图片
            <input type="file" accept="image/*" multiple @change="handleImageUpload" hidden />
          </label>
          <button class="btn-publish" @click="publish" :disabled="publishing || !newContent.trim()">
            {{ publishing ? '发布中...' : '发布公告' }}
          </button>
        </div>
        <!-- 图片预览 -->
        <div v-if="previewImages.length > 0" class="image-preview">
          <div v-for="(img, idx) in previewImages" :key="idx" class="preview-item">
            <img :src="img" alt="预览" />
            <button class="remove-btn" @click="removeImage(idx)">✕</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 时间筛选器 -->
    <div class="filter-area">
      <TimeRangeSelector v-model="timeRange" />
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span>
      <p>加载中...</p>
    </div>

    <!-- 公告列表 -->
    <div v-else class="announcement-list">
      <div v-if="announcements.length === 0" class="empty-state">
        <div class="empty-icon">📋</div>
        <p>还没有公告，快来发布第一条吧！</p>
      </div>

      <div 
        v-for="item in announcements" 
        :key="item.id" 
        class="announcement-card"
        :class="{ pinned: item.is_pinned }"
      >
        <!-- 置顶标签 -->
        <div v-if="item.is_pinned" class="pin-badge">📌 置顶</div>

        <!-- 作者信息 -->
        <div class="author-info">
          <UserAvatar :userId="item.author_id" :name="item.author_name" :avatarVersion="item.author_avatar_version" :size="40" />
          <div class="author-detail">
            <span class="author-name">{{ item.author_name }}</span>
            <span class="post-time">{{ formatTime(item.created_at) }}</span>
          </div>
          
          <!-- 操作菜单 -->
          <div class="actions-menu" v-if="item.is_mine">
            <button class="menu-btn" @click="toggleMenu(item.id)">⋮</button>
            <div v-if="activeMenu === item.id" class="menu-dropdown">
              <button @click="togglePin(item)">
                {{ item.is_pinned ? '取消置顶' : '置顶' }}
              </button>
              <button @click="deleteAnnouncement(item.id)" class="danger">删除</button>
            </div>
          </div>
        </div>

        <!-- 公告内容 -->
        <div class="content">{{ item.content }}</div>

        <!-- 图片展示 -->
        <div v-if="item.images && item.images.length > 0" class="image-gallery">
          <img 
            v-for="(img, idx) in item.images" 
            :key="idx" 
            :src="img" 
            @click="viewImage(img)"
            alt="公告图片"
          />
        </div>

        <!-- 互动区域 -->
        <div class="interaction">
          <button 
            class="like-btn" 
            :class="{ liked: item.is_liked }"
            @click="toggleLike(item)"
          >
            {{ item.is_liked ? '❤️' : '🤍' }} {{ item.likes_count }}
          </button>
          <button class="comment-btn" @click="toggleComments(item.id)">
            💬 {{ item.comments_count }}
          </button>
        </div>

        <!-- 评论区 -->
        <div v-if="expandedComments.includes(item.id)" class="comments-section">
          <div class="comment-input">
            <input 
              v-model="commentInput[item.id]" 
              placeholder="写评论..."
              @keyup.enter="addComment(item.id)"
            />
            <button @click="addComment(item.id)" :disabled="!commentInput[item.id]?.trim()">
              发送
            </button>
          </div>
          
          <div class="comments-list">
            <div v-for="comment in item.comments" :key="comment.id" class="comment-item">
              <span class="comment-author">{{ comment.author_name }}:</span>
              <span class="comment-content">{{ comment.content }}</span>
              <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
            </div>
            <div v-if="!item.comments || item.comments.length === 0" class="no-comments">
              暂无评论
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片查看器 -->
    <div v-if="viewingImage" class="image-viewer" @click="viewingImage = null">
      <img :src="viewingImage" alt="查看大图" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { api } from '@/api'
import UserAvatar from '@/components/UserAvatar.vue'
import TimeRangeSelector from '@/components/TimeRangeSelector.vue'

const message = useMessage()
const dialog = useDialog()

// 状态
const loading = ref(false)
const publishing = ref(false)
const announcements = ref([])
const newContent = ref('')
const timeRange = ref('month')
const previewImages = ref([])
const imageFiles = ref([])
const activeMenu = ref(null)
const expandedComments = ref([])
const commentInput = reactive({})
const viewingImage = ref(null)

// 加载公告列表
const loadAnnouncements = async () => {
  loading.value = true
  try {
    const res = await api.get('/announcements', {
      params: { time_range: timeRange.value }
    })
    // 后端返回 { total, page, page_size, items: [...] }
    announcements.value = res.data.items || []
  } catch (err) {
    console.error('获取公告失败:', err)
  } finally {
    loading.value = false
  }
}

// 监听时间范围变化
watch(timeRange, () => {
  loadAnnouncements()
})

// 发布公告
const publish = async () => {
  if (!newContent.value.trim()) return
  
  publishing.value = true
  try {
    // 如果有图片，先上传图片
    let images = []
    if (imageFiles.value.length > 0) {
      const formData = new FormData()
      imageFiles.value.forEach((file, idx) => {
        formData.append('files', file)
      })
      // 这里假设有图片上传API，如果没有则使用base64
      images = previewImages.value // 暂时使用base64
    }

    await api.post('/announcements', {
      content: newContent.value,
      images: images
    })
    
    newContent.value = ''
    previewImages.value = []
    imageFiles.value = []
    await loadAnnouncements()
  } catch (err) {
    message.error(err.response?.data?.detail || '发布失败')
  } finally {
    publishing.value = false
  }
}

// 处理图片上传
const handleImageUpload = (e) => {
  const files = Array.from(e.target.files)
  files.forEach(file => {
    if (previewImages.value.length >= 9) {
      message.warning('最多上传9张图片')
      return
    }
    
    const reader = new FileReader()
    reader.onload = (event) => {
      previewImages.value.push(event.target.result)
      imageFiles.value.push(file)
    }
    reader.readAsDataURL(file)
  })
}

// 移除预览图片
const removeImage = (idx) => {
  previewImages.value.splice(idx, 1)
  imageFiles.value.splice(idx, 1)
}

// 切换菜单
const toggleMenu = (id) => {
  activeMenu.value = activeMenu.value === id ? null : id
}

// 点击外部关闭菜单
const closeMenuOnClickOutside = (e) => {
  if (!e.target.closest('.actions-menu')) {
    activeMenu.value = null
  }
}

// 置顶/取消置顶
const togglePin = async (item) => {
  try {
    await api.put(`/announcements/${item.id}`, {
      is_pinned: !item.is_pinned
    })
    await loadAnnouncements()
    activeMenu.value = null
  } catch (err) {
    message.error(err.response?.data?.detail || '操作失败')
  }
}

// 删除公告
const deleteAnnouncement = (id) => {
  dialog.warning({
    title: '确认删除',
    content: '确定删除这条公告吗？',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.delete(`/announcements/${id}`)
        await loadAnnouncements()
        activeMenu.value = null
        message.success('删除成功')
      } catch (err) {
        message.error(err.response?.data?.detail || '删除失败')
      }
    }
  })
}

// 点赞
const toggleLike = async (item) => {
  try {
    const res = await api.post(`/announcements/${item.id}/like`)
    if (res.data.action === 'unliked') {
      item.is_liked = false
      item.likes_count--
    } else {
      item.is_liked = true
      item.likes_count++
    }
  } catch (err) {
    console.error('点赞失败:', err)
  }
}

// 展开/收起评论
const toggleComments = async (id) => {
  const idx = expandedComments.value.indexOf(id)
  if (idx === -1) {
    expandedComments.value.push(id)
    // 加载评论
    await loadComments(id)
  } else {
    expandedComments.value.splice(idx, 1)
  }
}

// 加载评论
const loadComments = async (announcementId) => {
  try {
    const res = await api.get(`/announcements/${announcementId}/comments`)
    const announcement = announcements.value.find(a => a.id === announcementId)
    if (announcement) {
      announcement.comments = res.data
    }
  } catch (err) {
    console.error('加载评论失败:', err)
  }
}

// 添加评论
const addComment = async (announcementId) => {
  const content = commentInput[announcementId]?.trim()
  if (!content) return

  try {
    await api.post(`/announcements/${announcementId}/comments`, { content })
    commentInput[announcementId] = ''
    await loadComments(announcementId)
    
    // 更新评论数
    const announcement = announcements.value.find(a => a.id === announcementId)
    if (announcement) {
      announcement.comments_count++
    }
  } catch (err) {
    message.error(err.response?.data?.detail || '评论失败')
  }
}

// 查看图片
const viewImage = (img) => {
  viewingImage.value = img
}

// 格式化时间
const formatTime = (dateStr) => {
  if (!dateStr) return ''
  // 后端返回的是 ISO 格式的 UTC 时间，确保正确解析
  // 如果没有时区标识，添加 Z 表示 UTC
  let isoStr = dateStr
  if (!dateStr.endsWith('Z') && !dateStr.includes('+')) {
    isoStr = dateStr + 'Z'
  }
  const date = new Date(isoStr)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  if (diff < 604800000) return Math.floor(diff / 86400000) + '天前'
  
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

onMounted(() => {
  loadAnnouncements()
  document.addEventListener('click', closeMenuOnClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenuOnClickOutside)
})
</script>

<style scoped>
.announcement-page {
  padding: 20px;
  max-width: 700px;
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

/* 筛选区域 */
.filter-area {
  margin-bottom: 16px;
}

/* 发布区域 */
.publish-area {
  margin-bottom: 24px;
}

.publish-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.publish-card textarea {
  width: 100%;
  border: none;
  resize: none;
  font-size: 16px;
  padding: 0;
  margin-bottom: 12px;
  box-sizing: border-box;
}

.publish-card textarea:focus {
  outline: none;
}

.publish-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-btn {
  padding: 8px 16px;
  background: #f5f5f5;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.upload-btn:hover {
  background: #e8e8e8;
}

.btn-publish {
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  transition: opacity 0.2s;
}

.btn-publish:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.image-preview {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.preview-item {
  position: relative;
  width: 80px;
  height: 80px;
}

.preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.preview-item .remove-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
}

/* 加载状态 */
.loading {
  text-align: center;
  padding: 40px;
  color: var(--theme-text-secondary);
}

.spinner {
  display: inline-block;
  width: 30px;
  height: 30px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

/* 公告卡片 */
.announcement-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.announcement-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.announcement-card.pinned {
  border: 2px solid #ffc107;
}

.pin-badge {
  display: inline-block;
  background: var(--theme-warning-light);
  color: #ff9800;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  margin-bottom: 12px;
}

/* 作者信息 */
.author-info {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  margin-right: 12px;
}

.author-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.author-name {
  font-weight: 500;
  color: #333;
}

.post-time {
  font-size: 12px;
  color: var(--theme-text-tertiary);
}

/* 操作菜单 */
.actions-menu {
  position: relative;
}

.menu-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  color: #999;
}

.menu-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  overflow: hidden;
  z-index: 10;
}

.menu-dropdown button {
  display: block;
  width: 100%;
  padding: 10px 20px;
  border: none;
  background: none;
  text-align: left;
  cursor: pointer;
  font-size: 14px;
}

.menu-dropdown button:hover {
  background: #f5f5f5;
}

.menu-dropdown button.danger {
  color: #f44336;
}

/* 公告内容 */
.content {
  font-size: 15px;
  line-height: 1.6;
  color: #333;
  margin-bottom: 12px;
  white-space: pre-wrap;
}

/* 图片展示 */
.image-gallery {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.image-gallery img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.image-gallery img:hover {
  opacity: 0.9;
}

/* 互动区域 */
.interaction {
  display: flex;
  gap: 20px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.like-btn,
.comment-btn {
  background: none;
  border: none;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 20px;
  transition: background 0.2s;
}

.like-btn:hover,
.comment-btn:hover {
  background: #f5f5f5;
}

.like-btn.liked {
  color: #f44336;
}

/* 评论区 */
.comments-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.comment-input {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.comment-input input {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  font-size: 14px;
}

.comment-input input:focus {
  outline: none;
  border-color: #667eea;
}

.comment-input button {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
}

.comment-input button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.comment-item {
  font-size: 14px;
  padding: 8px;
  background: #f9f9f9;
  border-radius: 8px;
}

.comment-author {
  font-weight: 500;
  color: #667eea;
  margin-right: 8px;
}

.comment-content {
  color: #333;
}

.comment-time {
  float: right;
  font-size: 12px;
  color: #999;
}

.no-comments {
  text-align: center;
  color: #999;
  padding: 12px;
  font-size: 14px;
}

/* 图片查看器 */
.image-viewer {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  cursor: pointer;
}

.image-viewer img {
  max-width: 90%;
  max-height: 90%;
  object-fit: contain;
}
</style>
