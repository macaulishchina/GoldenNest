<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="logo">
        <span class="logo-icon">🏠</span>
        <h1>小金库</h1>
        <p class="subtitle">Golden Nest · 家庭财富共创计划</p>
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, type FormInst } from 'naive-ui'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const message = useMessage()
const userStore = useUserStore()

const loading = ref(false)
const activeTab = ref('login')
const loginFormRef = ref<FormInst | null>(null)
const registerFormRef = ref<FormInst | null>(null)

const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', email: '', nickname: '', password: '' })

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
    router.push('/')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '登录失败')
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
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.auth-card {
  background: white;
  border-radius: 20px;
  padding: 48px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.logo {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.logo h1 {
  margin: 0;
  font-size: 28px;
  color: #1e293b;
}

.subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: #64748b;
}
</style>