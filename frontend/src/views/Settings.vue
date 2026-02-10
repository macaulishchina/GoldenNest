<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">⚙️</span> 个人设置</h1>

    <!-- 头像 & 基本信息 -->
    <n-card class="card-hover settings-card">
      <template #header>
        <span>👤 个人资料</span>
      </template>
      <div class="profile-header">
        <div class="avatar-wrapper" @click="triggerAvatarUpload">
          <img
            v-if="userStore.user?.id && !avatarError"
            :src="`/api/auth/users/${userStore.user.id}/avatar?v=${userStore.user.avatar_version || 0}&t=${avatarCacheKey}`"
            class="avatar-img"
            alt="头像"
            @error="avatarError = true"
          />
          <n-avatar
            v-else
            round
            :size="72"
            :style="{ backgroundColor: getAvatarColor(userStore.user?.nickname || '') }"
          >
            {{ userStore.user?.nickname?.[0] || '?' }}
          </n-avatar>
          <div class="avatar-edit-hint">
            <span>📷</span>
          </div>
        </div>
        <input
          ref="avatarInputRef"
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          style="display: none"
          @change="handleAvatarChange"
        />
        <div class="profile-header-info">
          <div class="profile-username">{{ userStore.user?.username }}</div>
          <div class="profile-join-date">注册于 {{ formatDate(userStore.user?.created_at) }}</div>
        </div>
      </div>

      <n-divider />

      <n-form
        ref="profileFormRef"
        :model="profileForm"
        :rules="profileRules"
        label-placement="left"
        label-width="80"
        require-mark-placement="right-hanging"
      >
        <n-form-item label="昵称" path="nickname">
          <n-input v-model:value="profileForm.nickname" placeholder="请输入昵称" maxlength="50" show-count />
        </n-form-item>
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="profileForm.email" placeholder="请输入邮箱" />
        </n-form-item>
        <n-form-item label="手机号" path="phone">
          <n-input v-model:value="profileForm.phone" placeholder="请输入手机号（选填）" maxlength="20" />
        </n-form-item>
        <n-form-item label="性别" path="gender">
          <n-radio-group v-model:value="profileForm.gender">
            <n-space>
              <n-radio value="male">👨 男</n-radio>
              <n-radio value="female">👩 女</n-radio>
              <n-radio value="other">🧑 其他</n-radio>
              <n-radio value="">不设置</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="生日" path="birthday">
          <n-date-picker
            v-model:formatted-value="profileForm.birthday"
            type="date"
            value-format="yyyy-MM-dd"
            placeholder="请选择生日（选填）"
            clearable
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="个人简介" path="bio">
          <n-input
            v-model:value="profileForm.bio"
            type="textarea"
            placeholder="介绍一下自己吧（选填）"
            maxlength="200"
            show-count
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
        <n-form-item>
          <n-button
            type="primary"
            @click="handleProfileSave"
            :loading="profileSaving"
            :disabled="!profileChanged"
          >
            保存修改
          </n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <!-- 修改密码 -->
    <n-card class="card-hover settings-card">
      <template #header>
        <span>🔐 修改密码</span>
      </template>
      <n-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-placement="left"
        label-width="80"
        require-mark-placement="right-hanging"
      >
        <n-form-item label="当前密码" path="oldPassword">
          <n-input
            v-model:value="passwordForm.oldPassword"
            type="password"
            show-password-on="click"
            placeholder="请输入当前密码"
          />
        </n-form-item>
        <n-form-item label="新密码" path="newPassword">
          <n-input
            v-model:value="passwordForm.newPassword"
            type="password"
            show-password-on="click"
            placeholder="请输入新密码（至少6位）"
          />
        </n-form-item>
        <n-form-item label="确认密码" path="confirmPassword">
          <n-input
            v-model:value="passwordForm.confirmPassword"
            type="password"
            show-password-on="click"
            placeholder="请再次输入新密码"
          />
        </n-form-item>
        <n-form-item>
          <n-button
            type="warning"
            @click="handlePasswordChange"
            :loading="passwordSaving"
          >
            修改密码
          </n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <!-- 账号信息 -->
    <n-card class="card-hover settings-card">
      <template #header>
        <span>📋 账号信息</span>
      </template>
      <n-descriptions :column="1" label-placement="left" bordered>
        <n-descriptions-item label="用户ID">
          {{ userStore.user?.id }}
        </n-descriptions-item>
        <n-descriptions-item label="用户名">
          {{ userStore.user?.username }}
        </n-descriptions-item>
        <n-descriptions-item label="注册时间">
          {{ formatDateTime(userStore.user?.created_at) }}
        </n-descriptions-item>
        <n-descriptions-item label="账号状态">
          <n-tag :type="userStore.user?.is_active ? 'success' : 'error'" size="small">
            {{ userStore.user?.is_active ? '正常' : '已禁用' }}
          </n-tag>
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <!-- 主题设置 -->
    <n-card class="card-hover settings-card">
      <template #header>
        <span>🎨 主题设置</span>
      </template>
      <div class="theme-setting-row">
        <span>选择主题风格</span>
        <ThemeSelector />
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useMessage } from 'naive-ui'
import type { FormRules, FormInst } from 'naive-ui'
import { useUserStore } from '@/stores/user'
import { authApi, api } from '@/api'
import { getAvatarColor, compressImage } from '@/utils/avatar'
import ThemeSelector from '@/components/ThemeSelector.vue'

const message = useMessage()
const userStore = useUserStore()

// ========== 头像 ==========
const avatarInputRef = ref<HTMLInputElement | null>(null)
const avatarError = ref(false)
const avatarCacheKey = ref(Date.now())
const avatarUploading = ref(false)

function triggerAvatarUpload() {
  if (avatarUploading.value) return
  avatarInputRef.value?.click()
}

async function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件')
    return
  }

  if (file.size > 20 * 1024 * 1024) {
    message.error('图片大小不能超过 20MB')
    return
  }

  avatarUploading.value = true
  try {
    const base64 = await compressImage(file)
    const res = await api.put('/auth/avatar', { avatar: base64 })
    if (res.data.success) {
      await userStore.fetchUser()
      avatarError.value = false
      avatarCacheKey.value = Date.now()
      message.success('头像更新成功！')
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '头像上传失败')
  } finally {
    avatarUploading.value = false
    if (avatarInputRef.value) avatarInputRef.value.value = ''
  }
}

// ========== 个人资料 ==========
const profileFormRef = ref<FormInst | null>(null)
const profileSaving = ref(false)

const profileForm = reactive({
  nickname: '',
  email: '',
  phone: '',
  gender: '',
  birthday: null as string | null,
  bio: ''
})

// 原始值，用于判断是否有改动
const originalProfile = ref({
  nickname: '',
  email: '',
  phone: '',
  gender: '',
  birthday: null as string | null,
  bio: ''
})

const profileChanged = computed(() => {
  return (
    profileForm.nickname !== originalProfile.value.nickname ||
    profileForm.email !== originalProfile.value.email ||
    profileForm.phone !== originalProfile.value.phone ||
    profileForm.gender !== originalProfile.value.gender ||
    profileForm.birthday !== originalProfile.value.birthday ||
    profileForm.bio !== originalProfile.value.bio
  )
})

const profileRules: FormRules = {
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { max: 50, message: '昵称不能超过50个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$|^$/, message: '请输入有效的手机号', trigger: 'blur' }
  ]
}

function loadProfile() {
  const u = userStore.user
  if (!u) return
  profileForm.nickname = u.nickname || ''
  profileForm.email = u.email || ''
  profileForm.phone = u.phone || ''
  profileForm.gender = u.gender || ''
  profileForm.birthday = u.birthday || null
  profileForm.bio = u.bio || ''

  originalProfile.value = { ...profileForm, birthday: profileForm.birthday }
}

async function handleProfileSave() {
  try {
    await profileFormRef.value?.validate()
  } catch {
    return
  }

  profileSaving.value = true
  try {
    await authApi.updateProfile({
      nickname: profileForm.nickname,
      email: profileForm.email,
      phone: profileForm.phone,
      gender: profileForm.gender,
      birthday: profileForm.birthday || '',
      bio: profileForm.bio
    })
    await userStore.fetchUser()
    loadProfile()
    message.success('个人资料已更新')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    profileSaving.value = false
  }
}

// ========== 修改密码 ==========
const passwordFormRef = ref<FormInst | null>(null)
const passwordSaving = ref(false)

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const passwordRules: FormRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string) => {
        if (value !== passwordForm.newPassword) {
          return new Error('两次输入的密码不一致')
        }
        return true
      },
      trigger: 'blur'
    }
  ]
}

async function handlePasswordChange() {
  try {
    await passwordFormRef.value?.validate()
  } catch {
    return
  }

  passwordSaving.value = true
  try {
    await authApi.changePassword({
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword
    })
    message.success('密码修改成功')
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (e: any) {
    message.error(e.response?.data?.detail || '密码修改失败')
  } finally {
    passwordSaving.value = false
  }
}

// ========== 工具函数 ==========
function formatDate(dateStr?: string | null) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function formatDateTime(dateStr?: string | null) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return `${formatDate(dateStr)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ========== 生命周期 ==========
onMounted(async () => {
  if (!userStore.user) {
    await userStore.fetchUser()
  }
  loadProfile()
})

// 当用户数据加载完成时同步表单
watch(() => userStore.user, () => {
  loadProfile()
})
</script>

<style scoped>
.page-container {
  max-width: 700px;
  margin: 0 auto;
  padding: 20px 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 24px;
}

.page-title .icon {
  margin-right: 8px;
}

.settings-card {
  margin-bottom: 20px;
}

/* ===== 头像区域 ===== */
.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.avatar-wrapper {
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
}

.avatar-wrapper:hover .avatar-edit-hint {
  opacity: 1;
}

.avatar-img {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid var(--primary-color, #18a058);
}

.avatar-edit-hint {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 24px;
  height: 24px;
  background: var(--primary-color, #18a058);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  opacity: 0.7;
  transition: opacity 0.2s;
  border: 2px solid #fff;
}

.profile-header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.profile-username {
  font-size: 20px;
  font-weight: 600;
}

.profile-join-date {
  font-size: 13px;
  color: #999;
}

/* ===== 主题 ===== */
.theme-setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

/* ===== 移动端适配 ===== */
@media (max-width: 768px) {
  .page-container {
    padding: 16px 12px;
  }

  .page-title {
    font-size: 20px;
    margin-bottom: 16px;
  }
}
</style>
