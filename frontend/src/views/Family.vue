<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">👨‍👩‍👧‍👦</span> 家庭管理</h1>
    
    <!-- 初始化加载状态 -->
    <div v-if="initializing" class="initializing-container">
      <n-spin size="large" />
      <p class="initializing-text">加载中...</p>
    </div>
    
    <!-- 已有家庭的用户界面 -->
    <template v-else-if="hasFamily">
      <!-- 个人信息区域 -->
      <div v-if="currentMember" class="profile-section">
        <div class="avatar-wrapper" @click="triggerAvatarUpload">
          <!-- 使用 URL 方式加载头像 -->
          <img 
            v-if="userStore.user?.id && !selfAvatarError" 
            :src="`/api/auth/users/${userStore.user.id}/avatar?v=${userStore.user.avatar_version || 0}&t=${avatarCacheKey}`" 
            class="avatar-img"
            alt="头像"
            @error="selfAvatarError = true"
          />
          <!-- 无头像或加载失败时显示首字母 -->
          <n-avatar 
            v-else
            round 
            :size="56" 
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
        <div class="profile-info">
          <div class="profile-name">{{ userStore.user?.nickname }}</div>
          <div class="profile-meta">
            <n-tag 
              round 
              size="small" 
              :type="currentMember.role === 'admin' ? 'warning' : 'default'"
              :bordered="false"
            >
              {{ currentMember.role === 'admin' ? '👑 管理员' : '👤 成员' }}
            </n-tag>
            <span class="greeting">{{ getGreeting() }}</span>
          </div>
        </div>
      </div>

      <!-- 家庭信息卡片 -->
      <n-card class="card-hover family-info-card">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div>
            <h2 style="margin: 0; font-size: 20px">{{ family?.name }}</h2>
            <p style="margin: 8px 0 0; color: #64748b">邀请码：<n-tag size="small">{{ family?.invite_code }}</n-tag></p>
          </div>
          <n-button size="small" @click="copyInviteCode">复制邀请码</n-button>
        </div>
      </n-card>

      <!-- 通知配置（仅管理员可见） -->
      <n-collapse v-if="isCurrentUserAdmin" class="notification-collapse" :default-expanded-names="[]">
        <n-collapse-item title="🔔 通知配置" name="notification">
          <template #header-extra>
            <n-tag v-if="notificationConfig.enabled && notificationConfig.hasWebhook" type="success" size="small">
              已启用
            </n-tag>
            <n-tag v-else type="default" size="small">
              未配置
            </n-tag>
          </template>
          <n-spin :show="notificationLoading">
            <div class="notification-config-compact">
              <div class="config-row">
                <span class="config-label">启用通知</span>
                <n-switch 
                  v-model:value="notificationConfig.enabled" 
                  :loading="notificationSaving"
                  size="small"
                  @update:value="handleNotificationToggle"
                >
                  <template #checked>开</template>
                  <template #unchecked>关</template>
                </n-switch>
              </div>
              
              <div class="config-row">
                <span class="config-label">外网地址</span>
                <div class="config-value">
                  <n-input 
                    v-model:value="externalUrlForm.url" 
                    placeholder="http://localhost:8000"
                    size="small"
                    style="width: 200px;"
                    @blur="handleSaveExternalUrl"
                    @keyup.enter="handleSaveExternalUrl"
                  />
                  <span class="hint-text-inline">用于通知链接</span>
                </div>
              </div>
              
              <div class="config-row">
                <span class="config-label">企业微信机器人</span>
                <div class="config-value">
                  <template v-if="notificationConfig.hasWebhook">
                    <n-tag type="success" size="small">已配置</n-tag>
                    <span class="webhook-url-masked">{{ notificationConfig.maskedUrl }}</span>
                    <n-button size="tiny" quaternary @click="showWebhookModal = true">修改</n-button>
                    <n-popconfirm @positive-click="handleDeleteWebhook">
                      <template #trigger>
                        <n-button size="tiny" type="error" quaternary>删除</n-button>
                      </template>
                      确定删除 Webhook 配置吗？
                    </n-popconfirm>
                  </template>
                  <template v-else>
                    <n-button type="primary" size="tiny" @click="showWebhookModal = true">
                      配置 Webhook
                    </n-button>
                    <span class="hint-text-inline">推送审批通知</span>
                  </template>
                </div>
              </div>
              
              <div v-if="notificationConfig.hasWebhook" class="config-row">
                <span class="config-label">测试</span>
                <n-button 
                  size="tiny" 
                  :loading="testingNotification"
                  @click="handleTestNotification"
                >
                  发送测试消息
                </n-button>
              </div>
            </div>
          </n-spin>
        </n-collapse-item>
      </n-collapse>

      <!-- 家庭成员列表 -->
      <n-card title="家庭成员" class="card-hover">
        <n-list>
          <n-list-item v-for="member in members" :key="member.id">
            <n-thing>
              <template #avatar>
                <UserAvatar 
                  :userId="member.user_id" 
                  :name="member.nickname" 
                  :size="40" 
                  :avatarVersion="member.avatar_version"
                />
              </template>
              <template #header>
                <div class="member-header">
                  <span>{{ member.nickname }}</span>
                  <n-tag v-if="member.user_id === currentUserId" type="info" size="small" round>
                    我
                  </n-tag>
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

    <!-- 未加入家庭的用户界面 -->
    <n-card v-else class="card-hover">
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
    
    <!-- Webhook 配置弹窗 -->
    <n-modal v-model:show="showWebhookModal" preset="dialog" title="配置企业微信机器人">
      <template #default>
        <div style="padding: 16px 0;">
          <n-alert type="info" style="margin-bottom: 16px;">
            <template #header>如何获取 Webhook URL？</template>
            <ol style="margin: 8px 0 0; padding-left: 20px; line-height: 1.8;">
              <li>在企业微信群聊中，点击右上角「...」</li>
              <li>选择「群机器人」→「添加」</li>
              <li>创建一个新机器人，复制 Webhook URL</li>
            </ol>
          </n-alert>
          <n-form-item label="Webhook URL">
            <n-input 
              v-model:value="webhookForm.url" 
              type="textarea"
              placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
              :rows="3"
            />
          </n-form-item>
        </div>
      </template>
      <template #action>
        <n-space>
          <n-button @click="showWebhookModal = false">取消</n-button>
          <n-button type="primary" :loading="webhookSaving" @click="handleSaveWebhook">
            保存配置
          </n-button>
        </n-space>
      </template>
    </n-modal>

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
import { familyApi, approvalApi, api } from '@/api'
import { useUserStore } from '@/stores/user'
import { compressImage, getAvatarColor } from '@/utils/avatar'
import UserAvatar from '@/components/UserAvatar.vue'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const initializing = ref(true) // 初始化状态，等待用户数据加载完成
const avatarInputRef = ref<HTMLInputElement | null>(null)
const avatarUploading = ref(false)
const selfAvatarError = ref(false)
const avatarCacheKey = ref(Date.now())
const family = ref<any>(null)
const members = ref<any[]>([])

const hasFamily = computed(() => !!userStore.user?.family_id)
const currentUserId = computed(() => userStore.user?.id)

// 当前用户的成员信息
const currentMember = computed(() => {
  return members.value.find(m => m.user_id === currentUserId.value)
})

// 判断当前用户是否是管理员
const isCurrentUserAdmin = computed(() => {
  return currentMember.value?.role === 'admin'
})

// 时间问候语
function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了，注意休息 🌙'
  if (hour < 9) return '早上好！新的一天 🌅'
  if (hour < 12) return '上午好！加油 ☀️'
  if (hour < 14) return '中午好！记得吃饭 🍚'
  if (hour < 17) return '下午好！继续努力 🌤️'
  if (hour < 19) return '傍晚好！快下班了 🌆'
  if (hour < 22) return '晚上好！辛苦一天了 🌙'
  return '夜深了，早点休息 💤'
}

// 剔除相关状态
const showRemoveModal = ref(false)
const removingMember = ref<any>(null)
const removeReason = ref('')
const removingLoading = ref(false)

// 通知配置相关状态
const notificationLoading = ref(false)
const notificationSaving = ref(false)
const testingNotification = ref(false)
const showWebhookModal = ref(false)
const webhookForm = ref({ url: '' })
const webhookSaving = ref(false)
const notificationConfig = ref({
  enabled: true,
  hasWebhook: false,
  maskedUrl: ''
})

// 外网地址配置
const externalUrlForm = ref({ url: '' })
const externalUrlSaving = ref(false)

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
  const text = family.value?.invite_code || ''
  
  // 优先使用现代 Clipboard API（需要 HTTPS）
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text)
      .then(() => message.success('邀请码已复制'))
      .catch(() => fallbackCopy(text))
  } else {
    // 回退到传统方法
    fallbackCopy(text)
  }
}

// 兼容性复制方法（适用于非 HTTPS 环境）
function fallbackCopy(text: string) {
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.left = '-9999px'
  textArea.style.top = '-9999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  
  try {
    document.execCommand('copy')
    message.success('邀请码已复制')
  } catch (err) {
    message.error('复制失败，请手动复制')
  }
  
  document.body.removeChild(textArea)
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

// ========== 头像上传相关 ==========

// 触发文件选择
function triggerAvatarUpload() {
  if (avatarUploading.value) return
  avatarInputRef.value?.click()
}

// 处理头像文件选择
async function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件')
    return
  }
  
  // 验证原始文件大小（限制20MB，防止浏览器卡死）
  if (file.size > 20 * 1024 * 1024) {
    message.error('图片大小不能超过 20MB')
    return
  }
  
  avatarUploading.value = true
  
  try {
    // 先压缩图片为适合头像的大小（200x200）
    const base64 = await compressImage(file)
    
    // 压缩后检查大小（2MB限制，Base64约为原始数据的1.37倍）
    const compressedSize = base64.length * 0.75 // 估算实际字节数
    if (compressedSize > 2 * 1024 * 1024) {
      message.error('图片压缩后仍超过 2MB，请选择更小的图片')
      avatarUploading.value = false
      return
    }
    
    // 上传到服务器
    const res = await api.put('/auth/avatar', { avatar: base64 })
    
    if (res.data.success) {
      // 更新本地用户信息
      await userStore.fetchUser()
      // 刷新家庭成员列表（获取最新的 avatar_version）
      await loadData()
      // 刷新头像缓存（用于个人信息区域的自定义头像显示）
      selfAvatarError.value = false
      avatarCacheKey.value = Date.now()
      message.success('头像更新成功！')
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '头像上传失败')
  } finally {
    avatarUploading.value = false
    // 清空 input，允许再次选择相同文件
    input.value = ''
  }
}

// 读取文件为 base64
function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

// ========== 通知配置相关 ==========

// 加载通知配置
async function loadNotificationConfig() {
  if (!hasFamily.value || !isCurrentUserAdmin.value) return
  
  notificationLoading.value = true
  try {
    const res = await familyApi.getNotificationConfig()
    notificationConfig.value = {
      enabled: res.data.notification_enabled,
      hasWebhook: res.data.has_wechat_webhook,
      maskedUrl: res.data.wechat_webhook_url || ''
    }
    // 加载外网地址配置
    externalUrlForm.value.url = res.data.external_base_url || ''
  } catch (e: any) {
    console.error('Failed to load notification config:', e)
  } finally {
    notificationLoading.value = false
  }
}

// 保存外网地址配置
let lastSavedExternalUrl = ''
async function handleSaveExternalUrl() {
  const url = externalUrlForm.value.url.trim()
  
  // 如果没有变化，不保存
  if (url === lastSavedExternalUrl) return
  
  // 如果为空，允许清空
  if (!url) {
    externalUrlSaving.value = true
    try {
      await familyApi.updateNotificationConfig({ external_base_url: '' })
      lastSavedExternalUrl = ''
      message.success('外网地址已清除')
    } catch (e: any) {
      message.error(e.response?.data?.detail || '保存失败')
    } finally {
      externalUrlSaving.value = false
    }
    return
  }
  
  // 验证 URL 格式
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    message.warning('请输入有效的 URL（需以 http:// 或 https:// 开头）')
    return
  }
  
  externalUrlSaving.value = true
  try {
    await familyApi.updateNotificationConfig({ external_base_url: url })
    lastSavedExternalUrl = url
    message.success('外网地址已保存')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    externalUrlSaving.value = false
  }
}

// 切换通知开关
async function handleNotificationToggle(enabled: boolean) {
  notificationSaving.value = true
  try {
    await familyApi.updateNotificationConfig({ notification_enabled: enabled })
    message.success(enabled ? '已开启通知' : '已关闭通知')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
    // 恢复原值
    notificationConfig.value.enabled = !enabled
  } finally {
    notificationSaving.value = false
  }
}

// 保存 Webhook 配置
async function handleSaveWebhook() {
  if (!webhookForm.value.url) {
    message.warning('请输入 Webhook URL')
    return
  }
  
  if (!webhookForm.value.url.startsWith('https://qyapi.weixin.qq.com/')) {
    message.warning('请输入有效的企业微信 Webhook URL')
    return
  }
  
  webhookSaving.value = true
  try {
    const res = await familyApi.updateNotificationConfig({ 
      wechat_webhook_url: webhookForm.value.url 
    })
    notificationConfig.value = {
      ...notificationConfig.value,
      hasWebhook: res.data.has_wechat_webhook,
      maskedUrl: res.data.wechat_webhook_url || ''
    }
    showWebhookModal.value = false
    webhookForm.value.url = ''
    message.success('Webhook 配置已保存')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    webhookSaving.value = false
  }
}

// 删除 Webhook 配置
async function handleDeleteWebhook() {
  try {
    await familyApi.deleteWebhook()
    notificationConfig.value.hasWebhook = false
    notificationConfig.value.maskedUrl = ''
    message.success('Webhook 配置已删除')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

// 测试通知
async function handleTestNotification() {
  testingNotification.value = true
  try {
    const res = await familyApi.testNotification()
    if (res.data.success) {
      message.success(res.data.message || '测试消息发送成功')
    } else {
      message.warning(res.data.message || '发送失败')
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '测试失败')
  } finally {
    testingNotification.value = false
  }
}

onMounted(async () => {
  try {
    // 如果用户数据还没加载完成，先等待加载
    if (!userStore.user && userStore.token) {
      await userStore.fetchUser()
    }
    // 加载家庭数据
    await loadData()
    // 加载完家庭数据后再加载通知配置
    loadNotificationConfig()
  } finally {
    // 无论成功失败，都关闭初始化状态
    initializing.value = false
  }
})
</script>

<style scoped>
/* 初始化加载状态 */
.initializing-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #64748b;
}

.initializing-text {
  margin-top: 16px;
  font-size: 14px;
}

/* 个人信息区域 */
.profile-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  color: white;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.profile-info {
  flex: 1;
}

.profile-name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px;
}

.profile-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.greeting {
  font-size: 13px;
  opacity: 0.9;
}

/* 头像编辑区域 */
.avatar-wrapper {
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
}

.avatar-img {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.avatar-wrapper:hover .avatar-edit-hint {
  opacity: 1;
}

.avatar-wrapper:active {
  transform: scale(0.95);
}

.avatar-edit-hint {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 22px;
  height: 22px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  opacity: 0.9;
  transition: all 0.2s;
}

.member-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 通知配置区域 */
.notification-config {
  min-height: 100px;
}

.webhook-config {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.webhook-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.webhook-url-masked {
  font-size: 12px;
  color: #64748b;
  word-break: break-all;
  max-width: 300px;
}

.hint-text {
  font-size: 12px;
  color: #94a3b8;
  margin-left: 8px;
}

/* 家庭信息卡片 */
.family-info-card {
  margin-bottom: 16px;
}

/* 通知配置折叠面板 */
.notification-collapse {
  margin-bottom: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.notification-collapse :deep(.n-collapse-item) {
  margin-top: 0 !important;
}

.notification-collapse :deep(.n-collapse-item__header) {
  padding: 12px 16px !important;
  font-weight: 500;
}

.notification-collapse :deep(.n-collapse-item__header-main) {
  padding-top: 0 !important;
}

.notification-collapse :deep(.n-collapse-item__content-inner) {
  padding: 12px 16px 16px;
}

/* 紧凑配置行样式 */
.notification-config-compact {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 32px;
}

.config-label {
  flex-shrink: 0;
  width: 100px;
  font-size: 13px;
  color: #64748b;
}

.config-value {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
}

.hint-text-inline {
  font-size: 11px;
  color: #94a3b8;
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
