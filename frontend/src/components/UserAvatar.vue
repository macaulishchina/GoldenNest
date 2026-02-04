<template>
  <div class="user-avatar" :style="{ width: sizeValue, height: sizeValue }">
    <!-- 有头像时显示图片 -->
    <img 
      v-if="avatarSrc && !imageError" 
      :src="avatarSrc" 
      :alt="name"
      class="avatar-img"
      @error="handleImageError"
    />
    <!-- 无头像或加载失败时显示首字母 -->
    <div 
      v-else 
      class="avatar-fallback"
      :style="{ backgroundColor: avatarColor, fontSize: fontSizeValue }"
    >
      {{ initial }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getAvatarColor } from '@/utils/avatar'

interface Props {
  /** 用户 ID - 优先使用，自动生成头像 URL */
  userId?: number | null
  /** 直接传入的头像 URL 或 Base64（向后兼容） */
  src?: string | null
  /** 用户名/昵称 - 用于无头像时显示首字母 */
  name?: string
  /** 尺寸 */
  size?: number | 'small' | 'medium' | 'large'
  /** 头像版本号 - 用于缓存失效（从后端获取） */
  avatarVersion?: number | null
}

const props = withDefaults(defineProps<Props>(), {
  userId: null,
  src: null,
  name: '?',
  size: 'medium',
  avatarVersion: null
})

// 图片加载错误状态
const imageError = ref(false)

// 监听 userId、src 或 avatarVersion 变化时重置错误状态
watch(() => [props.userId, props.src, props.avatarVersion], () => {
  imageError.value = false
})

// 计算最终的头像 URL
const avatarSrc = computed(() => {
  // 优先使用直接传入的 src（向后兼容，或用于上传预览）
  if (props.src) {
    return props.src
  }
  
  // 如果有 userId，生成 API URL
  if (props.userId) {
    const baseUrl = `/api/auth/users/${props.userId}/avatar`
    // 如果有 avatarVersion，添加查询参数用于缓存失效
    return props.avatarVersion ? `${baseUrl}?v=${props.avatarVersion}` : baseUrl
  }
  
  return null
})

// 处理图片加载错误
const handleImageError = () => {
  imageError.value = true
}

// 计算尺寸
const sizeValue = computed(() => {
  if (typeof props.size === 'number') {
    return `${props.size}px`
  }
  const sizeMap = {
    small: '32px',
    medium: '40px',
    large: '56px'
  }
  return sizeMap[props.size] || '40px'
})

// 字体大小
const fontSizeValue = computed(() => {
  if (typeof props.size === 'number') {
    return `${Math.round(props.size * 0.4)}px`
  }
  const fontSizeMap = {
    small: '14px',
    medium: '16px',
    large: '22px'
  }
  return fontSizeMap[props.size] || '16px'
})

// 首字母
const initial = computed(() => {
  return props.name?.[0]?.toUpperCase() || '?'
})

// 头像背景色
const avatarColor = computed(() => {
  return getAvatarColor(props.name || '')
})
</script>

<style scoped>
.user-avatar {
  position: relative;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
}
</style>