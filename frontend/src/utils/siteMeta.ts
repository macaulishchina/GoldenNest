/**
 * 站点元数据工具 - 动态更新 favicon / apple-touch-icon / theme-color
 * 在应用启动时从后端获取站点配置，并更新 HTML head 中的相关元素
 */
import axios from 'axios'

interface SiteInfo {
  site_name: string
  short_name: string
  theme_color: string
  has_icon: boolean
  icon_url: string | null
}

/**
 * 初始化站点图标和 PWA 元数据
 * 无需登录即可调用（公开接口）
 */
export async function initSiteMeta() {
  try {
    const { data } = await axios.get<SiteInfo>('/api/site-config/info')

    // 更新 favicon（使用 nginx 直接服务的静态路径）
    if (data.has_icon) {
      const faviconLink = document.querySelector<HTMLLinkElement>("link[rel='icon']")
        || document.getElementById('dynamic-favicon') as HTMLLinkElement
      if (faviconLink) {
        faviconLink.href = `/pwa-icons/icon-192.png?v=${Date.now()}`
      }

      // 更新所有 apple-touch-icon
      const appleLinks = document.querySelectorAll<HTMLLinkElement>("link[rel='apple-touch-icon']")
      appleLinks.forEach((link) => {
        const sizes = link.getAttribute('sizes')
        if (sizes === '512x512') {
          link.href = `/pwa-icons/icon-512.png?v=${Date.now()}`
        } else {
          link.href = `/pwa-icons/icon-192.png?v=${Date.now()}`
        }
      })
      if (appleLinks.length === 0) {
        const appleLink = document.createElement('link')
        appleLink.rel = 'apple-touch-icon'
        appleLink.href = `/pwa-icons/icon-192.png?v=${Date.now()}`
        document.head.appendChild(appleLink)
      }
    }

    // 更新 theme-color
    if (data.theme_color) {
      let themeMeta = document.querySelector<HTMLMetaElement>("meta[name='theme-color']")
      if (!themeMeta) {
        themeMeta = document.createElement('meta')
        themeMeta.name = 'theme-color'
        document.head.appendChild(themeMeta)
      }
      themeMeta.content = data.theme_color
    }

    // 更新页面标题
    if (data.site_name) {
      document.title = data.site_name
    }
  } catch {
    // 站点配置接口不可用时静默失败，不影响应用使用
  }
}
