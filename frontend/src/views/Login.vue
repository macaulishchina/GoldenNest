<template>
  <div class="auth-container">
    <!-- 主题切换按钮 -->
    <div class="theme-switcher">
      <ThemeSelector />
    </div>
    
    <div class="auth-card">
      <div class="logo" @click="handleLogoTap">
        <span class="logo-icon" :class="{ 'logo-shake': logoShaking }">🏠</span>
        <h1>小金库</h1>
        <p class="subtitle">
          <template v-if="tapCountdown > 0">还需点击 {{ tapCountdown }} 次</template>
          <template v-else>Golden Nest · 家庭财富共创计划</template>
        </p>
      </div>
      
      <n-tabs v-model:value="activeTab" type="segment" animated>
        <n-tab-pane name="login" tab="登录">
          <n-form ref="loginFormRef" :model="loginForm" :rules="loginRules" style="margin-top: 24px">
            <n-form-item path="username" label="用户名">
              <n-input v-model:value="loginForm.username" placeholder="请输入用户名" />
            </n-form-item>
            <n-form-item path="password" label="密码">
              <n-input v-model:value="loginForm.password" type="password" placeholder="请输入密码" show-password-on="click" />
            </n-form-item>
            <n-button type="primary" block :loading="loading" @click="handleLogin">登录</n-button>
          </n-form>
        </n-tab-pane>
        
        <n-tab-pane name="register" tab="注册">
          <n-form ref="registerFormRef" :model="registerForm" :rules="registerRules" style="margin-top: 24px">
            <n-form-item path="username" label="用户名">
              <n-input v-model:value="registerForm.username" placeholder="用于登录的账号" />
            </n-form-item>
            <n-form-item path="email" label="邮箱">
              <n-input v-model:value="registerForm.email" placeholder="用于找回密码" />
            </n-form-item>
            <n-form-item path="nickname" label="昵称">
              <n-input v-model:value="registerForm.nickname" placeholder="展示给家人看的名字（可选）" />
            </n-form-item>
            <n-form-item path="password" label="密码">
              <n-input v-model:value="registerForm.password" type="password" placeholder="至少6位密码" show-password-on="click" />
            </n-form-item>
            <n-button type="primary" block :loading="loading" @click="handleRegister">注册</n-button>
          </n-form>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, type FormInst } from 'naive-ui'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'
import ThemeSelector from '@/components/ThemeSelector.vue'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const userStore = useUserStore()

const loading = ref(false)
const activeTab = ref('login')
const loginFormRef = ref<FormInst | null>(null)
const registerFormRef = ref<FormInst | null>(null)
const serverOffline = ref(false)

const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', email: '', nickname: '', password: '' })

// Logo 连按彩蛋（类似 Android 开发者模式）
const TAP_THRESHOLD = 10
const TAP_TIMEOUT = 2000 // 连击超时重置
const tapCount = ref(0)
const tapCountdown = ref(0)
const logoShaking = ref(false)
let tapTimer: ReturnType<typeof setTimeout> | null = null

function handleLogoTap() {
  // 重置超时计时器
  if (tapTimer) clearTimeout(tapTimer)
  tapTimer = setTimeout(() => {
    tapCount.value = 0
    tapCountdown.value = 0
  }, TAP_TIMEOUT)

  tapCount.value++
  const remaining = TAP_THRESHOLD - tapCount.value

  // 最后 3 次显示倒数
  if (remaining > 0 && remaining <= 3) {
    tapCountdown.value = remaining
    logoShaking.value = true
    setTimeout(() => { logoShaking.value = false }, 300)
  } else if (remaining > 3) {
    // 轻微反馈
    logoShaking.value = true
    setTimeout(() => { logoShaking.value = false }, 150)
  }

  // 达到阈值，打开诊断页
  if (tapCount.value >= TAP_THRESHOLD) {
    tapCount.value = 0
    tapCountdown.value = 0
    window.open(window.location.origin + '/api/health', '_blank')
  }
}

// 页面加载时检测服务器连通性（仅用于彩蛋提示，不阻断登录）
onMounted(async () => {
  try {
    const { api } = await import('@/api')
    await api.get('/health', { timeout: 5000 })
    serverOffline.value = false
  } catch {
    serverOffline.value = true
  }
})

const loginRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' }
}

const registerRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  email: { required: true, type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  password: { required: true, min: 6, message: '密码至少6位', trigger: 'blur' }
}

async function handleLogin() {
  await loginFormRef.value?.validate()
  loading.value = true
  try {
    const res = await authApi.login(loginForm.value.username, loginForm.value.password)
    userStore.setToken(res.data.access_token)
    await userStore.fetchUser()
    message.success('欢迎回来！🎉')
    // 登录成功后跳转到原始页面或首页
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
  } catch (e: any) {
    if (e.response) {
      message.error(e.response.data?.detail || '用户名或密码错误')
    } else if (e.code === 'ECONNABORTED' || e.message?.includes('timeout')) {
      message.error('请求超时，请检查网络连接', { duration: 5000 })
    } else {
      message.error('无法连接服务器，请检查网络或点击 Logo 10 次进行诊断', { duration: 6000 })
    }
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  await registerFormRef.value?.validate()
  loading.value = true
  try {
    await authApi.register(registerForm.value)
    message.success('注册成功！请登录')
    activeTab.value = 'login'
    loginForm.value.username = registerForm.value.username
  } catch (e: any) {
    message.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
  overflow: hidden;
  /* 不设置背景，使用 body 的主题背景 */
}

.theme-switcher {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 100;
}

.auth-card {
  background: var(--theme-bg-card, white);
  border-radius: 20px;
  padding: 48px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.logo {
  text-align: center;
  margin-bottom: 32px;
  cursor: default;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.logo-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
  transition: transform 0.15s;
}

.logo-icon.logo-shake {
  animation: logo-shake 0.3s ease;
}

@keyframes logo-shake {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}

.logo h1 {
  margin: 0;
  font-size: 28px;
  color: var(--theme-text-primary, #1e293b);
}

.subtitle {
  font-size: 14px;
  color: var(--theme-text-secondary, #64748b);
  margin: 8px 0 0;
  min-height: 22px;
}
</style>