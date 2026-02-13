<template>
  <div class="site-settings">
    <n-card title="🌐 网站配置" :bordered="false">
      <n-space vertical :size="24">

        <!-- ========== 管理员专属区域 ========== -->
        <template v-if="isAdmin">
          <!-- 图标上传区域 -->
          <n-card title="网站图标" size="small" embedded>
            <template #header-extra>
              <n-text depth="3" style="font-size: 13px">
                用于浏览器标签页图标、PWA 主屏幕图标
              </n-text>
            </template>
            <n-space vertical :size="16">
              <n-space align="center" :size="20">
                <!-- 当前图标预览 -->
                <div class="icon-preview-area">
                  <div v-if="iconUrl" class="icon-preview">
                    <img :src="iconPreviewSrc" alt="站点图标" @error="handleImageError" />
                  </div>
                  <div v-else class="icon-placeholder">
                    <n-icon size="48" color="#ccc">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
                      </svg>
                    </n-icon>
                    <n-text depth="3" style="font-size: 12px">暂未设置</n-text>
                  </div>
                </div>
                <!-- 预览效果 -->
                <n-space vertical :size="8" v-if="iconUrl">
                  <n-text depth="3" style="font-size: 12px">预览效果：</n-text>
                  <n-space :size="12" align="center">
                    <div class="preview-badge" title="浏览器标签页">
                      <img :src="iconPreviewSrc" style="width: 16px; height: 16px; border-radius: 2px" />
                      <n-text style="font-size: 11px; margin-left: 4px">标签页</n-text>
                    </div>
                    <div class="preview-badge" title="主屏幕图标">
                      <img :src="iconPreviewSrc" style="width: 48px; height: 48px; border-radius: 10px" />
                    </div>
                  </n-space>
                </n-space>
              </n-space>

              <n-space :size="12">
                <n-upload
                  :show-file-list="false"
                  :custom-request="handleUploadIcon"
                  accept="image/png,image/jpeg,image/svg+xml,image/webp,image/x-icon"
                >
                  <n-button type="primary">
                    {{ iconUrl ? '更换图标' : '上传图标' }}
                  </n-button>
                </n-upload>
                <n-button v-if="iconUrl" type="error" ghost @click="handleDeleteIcon">
                  删除图标
                </n-button>
              </n-space>
              <n-text depth="3" style="font-size: 12px">
                支持 PNG、JPG、SVG、WebP、ICO 格式，建议使用 512x512 以上的正方形 PNG 图片，文件不超过 2MB
              </n-text>
            </n-space>
          </n-card>

          <!-- 站点名称设置 -->
          <n-card title="站点信息" size="small" embedded>
            <template #header-extra>
              <n-text depth="3" style="font-size: 13px">
                设置 PWA 添加到主屏幕时显示的名称
              </n-text>
            </template>
            <n-form
              ref="formRef"
              :model="formData"
              label-placement="left"
              label-width="100"
              :style="{ maxWidth: '500px' }"
            >
              <n-form-item label="站点名称" path="site_name">
                <n-input
                  v-model:value="formData.site_name"
                  placeholder="小金库 Golden Nest"
                  clearable
                />
              </n-form-item>
              <n-form-item label="简短名称" path="short_name">
                <n-input
                  v-model:value="formData.short_name"
                  placeholder="小金库"
                  clearable
                />
                <template #feedback>
                  <n-text depth="3" style="font-size: 12px">显示在手机主屏幕图标下方</n-text>
                </template>
              </n-form-item>
              <n-form-item label="主题颜色" path="theme_color">
                <n-color-picker
                  v-model:value="formData.theme_color"
                  :swatches="['#f0c040', '#18a058', '#2080f0', '#d03050', '#8b5cf6', '#f59e0b']"
                />
                <template #feedback>
                  <n-text depth="3" style="font-size: 12px">PWA 状态栏和启动画面背景色</n-text>
                </template>
              </n-form-item>
              <n-form-item>
                <n-button type="primary" :loading="saving" @click="handleSaveSettings">
                  保存设置
                </n-button>
              </n-form-item>
            </n-form>
          </n-card>
        </template>

        <!-- ========== 所有用户可见：添加到主屏幕 ========== -->
        <n-card title="📱 添加到主屏幕" size="small" embedded>
          <n-space vertical :size="12">
            <!-- iOS 描述文件安装（推荐方式） -->
            <n-alert v-if="hasIcon" type="success" :bordered="false">
              <template #header>iOS 用户推荐</template>
              <n-space vertical :size="8">
                <n-text>
                  点击下方按钮下载描述文件，一步完成主屏幕图标安装 + HTTPS 证书信任。
                </n-text>
                <n-button
                  type="primary"
                  tag="a"
                  :href="'/api/site-config/ios-profile'"
                  target="_self"
                  strong
                >
                  📲 安装 iOS 描述文件
                </n-button>
                <n-text depth="3" style="font-size: 12px">
                  下载后前往「设置 → 通用 → VPN与设备管理」完成安装。
                  安装后需在「设置 → 通用 → 关于本机 → 证书信任设置」中启用 CA 完全信任。
                </n-text>
              </n-space>
            </n-alert>

            <n-text depth="2" style="font-size: 13px; font-weight: 500">手动添加方式：</n-text>
            <n-list>
              <n-list-item>
                <n-text><b>iOS Safari</b>：点击「分享」→「添加到主屏幕」</n-text>
              </n-list-item>
              <n-list-item>
                <n-text><b>Android Chrome</b>：点击「菜单(⋮)」→「添加到主屏幕」或「安装应用」</n-text>
              </n-list-item>
            </n-list>
            <n-text depth="3" style="font-size: 12px">
              注意：使用自签名 HTTPS 证书时，iOS「添加到主屏幕」无法加载自定义图标，建议使用上方描述文件安装。
            </n-text>
          </n-space>
        </n-card>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useMessage, NCard, NSpace, NButton, NUpload, NInput, NForm, NFormItem, NText, NIcon, NList, NListItem, NColorPicker, NAlert } from 'naive-ui'
import { siteConfigApi } from '../api'
import { useUserStore } from '@/stores/user'
import type { UploadCustomRequestOptions } from 'naive-ui'

const message = useMessage()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const saving = ref(false)
const iconUrl = ref<string | null>(null)
const hasIcon = ref(false)
const iconTimestamp = ref(Date.now())
const imageError = ref(false)

const formData = ref({
  site_name: '',
  short_name: '',
  theme_color: '#f0c040',
})

const iconPreviewSrc = computed(() => {
  if (imageError.value || !iconUrl.value) return ''
  return `${iconUrl.value}?t=${iconTimestamp.value}`
})

function handleImageError() {
  imageError.value = true
}

async function loadSettings() {
  // 管理员使用管理接口加载完整设置
  if (isAdmin.value) {
    try {
      const { data } = await siteConfigApi.getSettings()
      formData.value.site_name = data.site_name || ''
      formData.value.short_name = data.short_name || ''
      formData.value.theme_color = data.theme_color || '#f0c040'
      iconUrl.value = data.icon_url || null
      hasIcon.value = data.has_icon || false
      imageError.value = false
    } catch (e: any) {
      // 管理员但没有家庭时，回退到公开接口
      await loadPublicInfo()
    }
  } else {
    await loadPublicInfo()
  }
}

async function loadPublicInfo() {
  try {
    const { data } = await siteConfigApi.getInfo()
    hasIcon.value = data.has_icon || false
    iconUrl.value = data.icon_url || null
    formData.value.site_name = data.site_name || ''
    formData.value.short_name = data.short_name || ''
    formData.value.theme_color = data.theme_color || '#f0c040'
    imageError.value = false
  } catch {
    // 静默失败
  }
}

async function handleUploadIcon({ file }: UploadCustomRequestOptions) {
  if (!file.file) return
  try {
    await siteConfigApi.uploadIcon(file.file)
    message.success('图标上传成功')
    iconTimestamp.value = Date.now()
    imageError.value = false
    await loadSettings()
    // 更新页面 favicon
    updateFavicon()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '上传失败')
  }
}

async function handleDeleteIcon() {
  try {
    await siteConfigApi.deleteIcon()
    message.success('图标已删除')
    iconUrl.value = null
    updateFavicon()
  } catch (e: any) {
    message.error('删除失败')
  }
}

async function handleSaveSettings() {
  saving.value = true
  try {
    await siteConfigApi.updateSettings({
      site_name: formData.value.site_name,
      short_name: formData.value.short_name,
      theme_color: formData.value.theme_color,
    })
    message.success('设置已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function updateFavicon() {
  // 动态更新 favicon
  const link = document.querySelector<HTMLLinkElement>("link[rel='icon']")
  if (link && iconUrl.value) {
    link.href = `${iconUrl.value}?t=${Date.now()}`
  }
  // 更新 apple-touch-icon
  const appleLink = document.querySelector<HTMLLinkElement>("link[rel='apple-touch-icon']")
  if (appleLink && iconUrl.value) {
    appleLink.href = `/api/site-config/icon/192?t=${Date.now()}`
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.site-settings {
  max-width: 800px;
  margin: 0 auto;
  padding: 8px;
}

.icon-preview-area {
  width: 100px;
  height: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
}

.icon-preview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-preview img {
  max-width: 90%;
  max-height: 90%;
  object-fit: contain;
}

.icon-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.preview-badge {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background: #f8f8f8;
  border-radius: 6px;
}

@media (max-width: 768px) {
  .site-settings {
    padding: 4px;
  }
}
</style>
