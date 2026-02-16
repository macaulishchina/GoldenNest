<template>
  <div class="login-container">
    <div class="login-card-wrapper">
      <n-card class="login-card" :bordered="false">
        <template #header>
          <div style="text-align: center">
            <div style="font-size: 48px; margin-bottom: 8px">🏗️</div>
            <n-text style="font-size: 22px; font-weight: 700; color: #e94560">
              GoldenNest Studio
            </n-text>
            <div style="margin-top: 4px">
              <n-text depth="3" style="font-size: 13px">设计院 · AI 驱动迭代开发</n-text>
            </div>
          </div>
        </template>

        <!-- 自动检测主项目 session -->
        <div v-if="autoDetecting" style="text-align: center; padding: 24px 0">
          <n-spin size="medium" />
          <div style="margin-top: 12px">
            <n-text depth="3">正在检测登录状态...</n-text>
          </div>
        </div>

        <template v-else>
          <!-- 主项目快捷登录 -->
          <div v-if="mainProjectAvailable" style="margin-bottom: 20px">
            <n-button
              type="info"
              block
              size="large"
              :loading="mainProjectLoading"
              @click="loginViaMainProject"
            >
              🔗 使用主项目账户登录
            </n-button>
            <div style="text-align: center; margin-top: 6px">
              <n-text depth="3" style="font-size: 12px">
                检测到主项目 (GoldenNest) 登录态，点击一键进入
              </n-text>
            </div>
          </div>

          <n-divider v-if="mainProjectAvailable" title-placement="center">
            <n-text depth="3" style="font-size: 12px">或</n-text>
          </n-divider>

          <!-- 管理员登录 -->
          <n-form ref="formRef" :model="formData" :rules="rules" @submit.prevent="handleAdminLogin">
            <n-form-item label="用户名" path="username">
              <n-input v-model:value="formData.username" placeholder="管理员用户名" size="large" />
            </n-form-item>
            <n-form-item label="密码" path="password">
              <n-input
                v-model:value="formData.password"
                type="password"
                placeholder="管理员密码"
                size="large"
                show-password-on="click"
                @keyup.enter="handleAdminLogin"
              />
            </n-form-item>
            <n-button
              type="primary"
              block
              size="large"
              :loading="adminLoading"
              :disabled="!formData.username || !formData.password"
              @click="handleAdminLogin"
            >
              🔑 管理员登录
            </n-button>
          </n-form>

          <!-- 错误消息 -->
          <n-alert v-if="errorMsg" type="error" :title="errorMsg" style="margin-top: 16px" closable @close="errorMsg = ''" />
        </template>

        <template #footer>
          <div style="text-align: center">
            <n-text depth="3" style="font-size: 11px">
              首次部署请在环境变量中配置 STUDIO_ADMIN_PASS
            </n-text>
          </div>
        </template>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { FormInst, FormRules } from 'naive-ui'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInst | null>(null)
const autoDetecting = ref(true)
const mainProjectAvailable = ref(false)
const mainProjectLoading = ref(false)
const adminLoading = ref(false)
const errorMsg = ref('')

const formData = ref({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 目标跳转路径
const redirectTo = () => {
  const target = route.query.redirect as string
  return target || '/'
}

onMounted(async () => {
  // 如果已登录, 直接跳转
  if (authStore.isLoggedIn) {
    router.replace(redirectTo())
    return
  }

  // 自动检测
  try {
    const ok = await authStore.autoAuth()
    if (ok) {
      router.replace(redirectTo())
      return
    }
  } catch {}

  // 检测主项目 session 是否可用
  const mainToken = localStorage.getItem('token')
  mainProjectAvailable.value = !!mainToken

  autoDetecting.value = false
})

async function loginViaMainProject() {
  mainProjectLoading.value = true
  errorMsg.value = ''
  try {
    const mainToken = localStorage.getItem('token')
    if (!mainToken) {
      errorMsg.value = '未检测到主项目登录信息，请先在主项目中登录'
      return
    }
    const ok = await authStore.autoAuth()
    if (ok) {
      router.replace(redirectTo())
    } else {
      errorMsg.value = '主项目 token 已失效，请重新登录主项目'
      mainProjectAvailable.value = false
    }
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || e.message || '登录失败'
  } finally {
    mainProjectLoading.value = false
  }
}

async function handleAdminLogin() {
  adminLoading.value = true
  errorMsg.value = ''
  try {
    await authStore.adminLogin(formData.value.username, formData.value.password)
    router.replace(redirectTo())
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || '用户名或密码错误'
  } finally {
    adminLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0a1628 0%, #16213e 50%, #1a1a2e 100%);
}

.login-card-wrapper {
  width: 100%;
  max-width: 420px;
  padding: 16px;
}

.login-card {
  background: rgba(22, 33, 62, 0.95);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}
</style>
