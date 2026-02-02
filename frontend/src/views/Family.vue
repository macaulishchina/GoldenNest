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
              <n-input-number v-model:value="createForm.target_amount" :min="1" style="width: 100%">
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
              <template #header>{{ member.nickname }}</template>
              <template #description>{{ member.username }}</template>
            </n-thing>
          </n-list-item>
        </n-list>
      </n-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { familyApi } from '@/api'
import { useUserStore } from '@/stores/user'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const family = ref<any>(null)
const members = ref<any[]>([])

const hasFamily = computed(() => !!userStore.user?.family_id)

const createForm = ref({ name: '', target_amount: 2000000 })
const joinForm = ref({ invite_code: '' })

async function loadData() {
  if (!hasFamily.value) return
  try {
    const [familyRes, membersRes] = await Promise.all([
      familyApi.get(),
      familyApi.getMembers()
    ])
    family.value = familyRes.data
    members.value = membersRes.data
  } catch (e) {
    console.error(e)
  }
}

async function handleCreate() {
  if (!createForm.value.name) { message.warning('请输入家庭名称'); return }
  loading.value = true
  try {
    await familyApi.create(createForm.value)
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
    await familyApi.join(joinForm.value.invite_code)
    message.success('加入成功！欢迎加入家庭！🎉')
    await userStore.fetchUser()
    loadData()
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

onMounted(loadData)
</script>
