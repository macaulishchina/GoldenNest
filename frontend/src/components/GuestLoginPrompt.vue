<template>
  <n-modal
    v-model:show="showModal"
    preset="card"
    title="需要登录"
    class="guest-login-modal"
    :style="{ maxWidth: '500px' }"
    :mask-closable="true"
  >
    <div class="modal-content">
      <div class="modal-icon">🔒</div>
      <p class="modal-message">
        此功能需要登录后才能使用。
        <br />
        注册账号，即可体验完整功能！
      </p>
      
      <div class="feature-list">
        <div class="feature-item">
          <n-icon :size="20" color="#18a058"><CheckmarkCircleOutline /></n-icon>
          <span>创建家庭，邀请成员共同管理财富</span>
        </div>
        <div class="feature-item">
          <n-icon :size="20" color="#18a058"><CheckmarkCircleOutline /></n-icon>
          <span>记录存款，自动计算股权占比</span>
        </div>
        <div class="feature-item">
          <n-icon :size="20" color="#18a058"><CheckmarkCircleOutline /></n-icon>
          <span>理财投资，收益按股权分配</span>
        </div>
        <div class="feature-item">
          <n-icon :size="20" color="#18a058"><CheckmarkCircleOutline /></n-icon>
          <span>家庭协作，共享日历、清单、公告</span>
        </div>
      </div>
    </div>
    
    <template #footer>
      <div class="modal-actions">
        <n-button @click="closeModal" class="cancel-button">
          继续浏览
        </n-button>
        <n-button type="primary" @click="goToRegister" class="register-button">
          立即注册 🚀
        </n-button>
        <n-button @click="goToLogin" class="login-button">
          已有账号，去登录
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CheckmarkCircleOutline } from '@vicons/ionicons5'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
}>()

const showModal = ref(props.show)

watch(() => props.show, (newVal) => {
  showModal.value = newVal
})

watch(showModal, (newVal) => {
  emit('update:show', newVal)
})

function closeModal() {
  showModal.value = false
}

function goToRegister() {
  userStore.exitGuestMode()
  closeModal()
  router.push('/register')
}

function goToLogin() {
  userStore.exitGuestMode()
  closeModal()
  router.push('/login')
}
</script>

<style scoped>
.modal-content {
  padding: 16px 0;
}

.modal-icon {
  font-size: 64px;
  text-align: center;
  margin-bottom: 16px;
}

.modal-message {
  text-align: center;
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 24px;
  color: #666;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 24px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #333;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.cancel-button {
  flex-shrink: 0;
}

.register-button {
  flex: 1;
  min-width: 140px;
}

.login-button {
  flex: 1;
  min-width: 140px;
}

@media (max-width: 600px) {
  .modal-actions {
    flex-direction: column-reverse;
  }
  
  .cancel-button,
  .register-button,
  .login-button {
    width: 100%;
  }
}
</style>
