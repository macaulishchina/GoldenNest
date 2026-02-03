<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">👨‍👩‍👧‍👦</span> 家庭管理</h1>
    
    <n-card v-if="!hasFamily" class="card-hover">
      <n-tabs type="segment">
        <n-tab-pane name="create" tab="创建家庭">
          <n-form :model="createForm" style="max-width: 400px; margin-top: 16px">
            <n-form-item label="家庭名称">
              <n-input v-model:value="createForm.name" placeholder="如：温馨之家" />
            </n-form-item>
            <n-form-item label="储蓄目标">
              <n-input-number v-model:value="createForm.savings_target" :min="1" style="width: 100%">
                <template #prefix>¥</template>
              </n-input-number>
            </n-form-item>
            <n-button type="primary" block :loading="loading" @click="handleCreate">创建家庭</n-button>
          </n-form>
        </n-tab-pane>
        <n-tab-pane name="join" tab="加入家庭">
          <n-form :model="joinForm" style="max-width: 400px; margin-top: 16px">
            <n-form-item label="邀请码">
              <n-input v-model:value="joinForm.invite_code" placeholder="请输入邀请码" />
            </n-form-item>
            <n-button type="primary" block :loading="loading" @click="handleJoin">加入家庭</n-button>
          </n-form>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <template v-else>
      <n-card class="card-hover" style="margin-bottom: 24px">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div>
            <h2 style="margin: 0; font-size: 20px">{{ family?.name }}</h2>
            <p style="margin: 8px 0 0; color: #64748b">邀请码：<n-tag size="small">{{ family?.invite_code }}</n-tag></p>
          </div>
          <n-button size="small" @click="copyInviteCode">复制邀请码</n-button>
        </div>
      </n-card>

      <n-card title="家庭成员" class="card-hover">
        <n-list>
          <n-list-item v-for="member in members" :key="member.id">
            <n-thing>
              <template #avatar>
                <n-avatar round>{{ member.nickname[0] }}</n-avatar>
              </template>
              <template #header>
                <div class="member-header">
                  <span>{{ member.nickname }}</span>
                  <n-tag :type="member.role === 'admin' ? 'warning' : 'default'" size="small">
                    {{ member.role === 'admin' ? '管理员' : '成员' }}
                  </n-tag>
                </div>
              </template>
              <template #description>{{ member.username }}</template>
              <template #header-extra>
                <!-- 非管理员可以被剔除，且当前用户是管理员才能发起 -->
                <n-button 
                  v-if="isCurrentUserAdmin && member.role !== 'admin' && member.user_id !== currentUserId"
                  size="small"
                  type="error"
                  quaternary
                  @click="handleRemoveMember(member)"
                >
                  剔除
                </n-button>
              </template>
            </n-thing>
          </n-list-item>
        </n-list>
      </n-card>
    </template>
    
    <!-- 剔除确认弹窗 -->
    <n-modal v-model:show="showRemoveModal" preset="dialog" title="确认剔除成员">
      <template #default>
        <div style="padding: 16px 0;">
          <p>您确定要发起剔除「<strong>{{ removingMember?.nickname }}</strong>」的申请吗？</p>
          <p style="color: #666; font-size: 14px; margin-top: 12px;">
            ⚠️ 该申请需要管理员审批后才会生效
          </p>
          <n-form-item label="剔除原因（可选）" style="margin-top: 16px;">
            <n-input v-model:value="removeReason" type="textarea" placeholder="请说明剔除原因" />
          </n-form-item>
        </div>
      </template>
      <template #action>
        <n-space>
          <n-button @click="showRemoveModal = false">取消</n-button>
          <n-button type="error" :loading="removingLoading" @click="confirmRemoveMember">
            确认剔除
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { familyApi, approvalApi } from '@/api'
import { useUserStore } from '@/stores/user'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const family = ref<any>(null)
const members = ref<any[]>([])

const hasFamily = computed(() => !!userStore.user?.family_id)
const currentUserId = computed(() => userStore.user?.id)

// 判断当前用户是否是管理员
const isCurrentUserAdmin = computed(() => {
  const currentMember = members.value.find(m => m.user_id === currentUserId.value)
  return currentMember?.role === 'admin'
})

// 剔除相关状态
const showRemoveModal = ref(false)
const removingMember = ref<any>(null)
const removeReason = ref('')
const removingLoading = ref(false)

const createForm = ref({ name: '', savings_target: 2000000 })
const joinForm = ref({ invite_code: '' })

async function loadData() {
  if (!hasFamily.value) return
  try {
    const res = await familyApi.getMy()
    family.value = res.data
    // members 是嵌套在 family 响应中的
    members.value = res.data.members || []
  } catch (e) {
    console.error(e)
  }
}

async function handleCreate() {
  if (!createForm.value.name) { message.warning('请输入家庭名称'); return }
  loading.value = true
  try {
    await familyApi.create({
      name: createForm.value.name,
      savings_target: createForm.value.savings_target
    })
    message.success('家庭创建成功！🏠')
    await userStore.fetchUser()
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建失败')
  } finally {
    loading.value = false
  }
}

async function handleJoin() {
  if (!joinForm.value.invite_code) { message.warning('请输入邀请码'); return }
  loading.value = true
  try {
    const res = await familyApi.join(joinForm.value.invite_code)
    
    // 检查返回状态：直接加入还是待审批
    if (res.data.status === 'joined') {
      message.success('加入成功！欢迎加入家庭！🎉')
      await userStore.fetchUser()
      loadData()
    } else if (res.data.status === 'pending') {
      message.info(res.data.message || '已提交加入申请，等待家庭成员审批')
    } else {
      message.success('操作成功')
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '加入失败')
  } finally {
    loading.value = false
  }
}

function copyInviteCode() {
  navigator.clipboard.writeText(family.value?.invite_code || '')
  message.success('邀请码已复制')
}

// 发起剔除成员
function handleRemoveMember(member: any) {
  removingMember.value = member
  removeReason.value = ''
  showRemoveModal.value = true
}

async function confirmRemoveMember() {
  if (!removingMember.value) return
  
  removingLoading.value = true
  try {
    await approvalApi.createMemberRemove({
      target_user_id: removingMember.value.user_id,
      reason: removeReason.value || undefined
    })
    message.success('剔除申请已提交，等待管理员审批')
    showRemoveModal.value = false
    removingMember.value = null
    removeReason.value = ''
  } catch (e: any) {
    message.error(e.response?.data?.detail || '提交申请失败')
  } finally {
    removingLoading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.member-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 移动端响应式 */
@media (max-width: 767px) {
  .page-container {
    padding: 16px;
    padding-bottom: 80px; /* 为底部导航留空间 */
  }
  
  .page-title {
    font-size: 1.5rem;
    margin-bottom: 16px;
  }
  
  /* 表单全宽 */
  :deep(.n-form) {
    max-width: 100% !important;
  }
  
  :deep(.n-form-item) {
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
  }
  
  :deep(.n-form-item-label) {
    display: block;
    text-align: left;
    padding-bottom: 8px;
    width: auto !important;
  }
  
  :deep(.n-input),
  :deep(.n-input-number) {
    width: 100% !important;
    font-size: 16px; /* 防止 iOS 放大 */
  }
  
  /* 提交按钮 */
  :deep(.n-button[type="primary"]) {
    height: 48px;
    font-size: 15px;
  }
  
  /* 标签页优化 */
  :deep(.n-tabs-tab) {
    padding: 12px 16px;
    font-size: 15px;
  }
  
  /* 卡片内容 */
  :deep(.n-card) {
    margin-bottom: 16px !important;
  }
  
  /* 成员列表优化 */
  :deep(.n-list-item) {
    padding: 12px 0;
  }
  
  :deep(.n-thing-header-wrapper) {
    flex-wrap: wrap;
  }
  
  /* 弹窗全屏 */
  :deep(.n-modal-body-wrapper) {
    max-width: calc(100vw - 32px) !important;
    margin: 16px !important;
  }
  
  :deep(.n-dialog) {
    width: 100% !important;
    max-width: calc(100vw - 32px);
  }
  
  :deep(.n-dialog .n-form-item) {
    display: flex;
    flex-direction: column;
  }
  
  :deep(.n-dialog .n-form-item-label) {
    display: block;
    text-align: left;
    padding-bottom: 8px;
    width: auto !important;
  }
  
  /* 操作按钮 */
  :deep(.n-space) {
    flex-wrap: wrap;
    gap: 8px !important;
  }
  
  :deep(.n-button) {
    min-height: 36px;
  }
}
</style>
