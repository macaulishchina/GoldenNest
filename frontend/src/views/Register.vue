<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo">
        <span class="logo-icon">🏠</span>
        <h1 class="logo-text">加入小金库</h1>
        <p class="logo-subtitle">开启家庭理财新篇章</p>
      </div>
      
      <n-form ref="formRef" :model="formData" :rules="rules" class="login-form">
        <n-form-item path="username" label="用户名">
          <n-input 
            v-model:value="formData.username" 
            placeholder="3-50个字符"
            size="large"
          />
        </n-form-item>
        
        <n-form-item path="email" label="邮箱">
          <n-input 
            v-model:value="formData.email" 
            placeholder="用于找回密码"
            size="large"
          />
        </n-form-item>
        
        <n-form-item path="nickname" label="昵称">
          <n-input 
            v-model:value="formData.nickname" 
            placeholder="给自己起个可爱的名字"
            size="large"
          />
        </n-form-item>
        
        <n-form-item path="password" label="密码">
          <n-input 
            v-model:value="formData.password" 
            type="password"
            placeholder="至少6个字符"
            size="large"
            show-password-on="click"
          />
        </n-form-item>
        
        <n-form-item path="confirmPassword" label="确认密码">
          <n-input 
            v-model:value="formData.confirmPassword" 
            type="password"
            placeholder="再次输入密码"
            size="large"
            show-password-on="click"
            @keyup.enter="handleRegister"
          />
        </n-form-item>
        
        <n-button 
          type="primary" 
          block 
          size="large"
          :loading="loading"
          @click="handleRegister"
        >
          注册
        </n-button>
      </n-form>
      
      <div class="login-footer">
        <span>已有账号？</span>
        <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const message = useMessage()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const formData = ref({
  username: '',
  email: '',
  nickname: '',
  password: '',
  confirmPassword: ''
})

const rules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  nickname: { required: true, message: '请输入昵称', trigger: 'blur' },
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string) => {
        return value === formData.value.password
      },
      message: '两次密码输入不一致',
      trigger: 'blur'
    }
  ]
}

async function handleRegister() {
  try {
    await formRef.value?.validate()
    loading.value = true
    
    await userStore.register({
      username: formData.value.username,
      email: formData.value.email,
      password: formData.value.password,
      nickname: formData.value.nickname
    })
    
    message.success('注册成功！请登录')
    router.push('/login')
  } catch (error: any) {
    message.error(error.response?.data?.detail || '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ecfdf5 0%, #f0fdfa 50%, #f0f9ff 100%);
  padding: 24px;
}

.login-card {
  background: white;
  border-radius: 24px;
  padding: 40px;
  width: 420px;
  box-shadow: 0 20px 60px rgba(16, 185, 129, 0.1);
}

.logo {
  text-align: center;
  margin-bottom: 24px;
}

.logo-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 8px;
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  color: #10b981;
  margin: 0;
}

.logo-subtitle {
  color: #94a3b8;
  font-size: 14px;
  margin: 4px 0 0;
}

.login-form {
  margin-bottom: 20px;
}

.login-footer {
  text-align: center;
  color: #64748b;
}

.login-footer a {
  color: #10b981;
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.login-footer a:hover {
  text-decoration: underline;
}
</style>
