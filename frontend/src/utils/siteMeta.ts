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

    // 更新 favicon
    if (data.has_icon && data.icon_url) {
      const faviconLink = document.querySelector<HTMLLinkElement>("link[rel='icon']")
        || document.getElementById('dynamic-favicon') as HTMLLinkElement
      if (faviconLink) {
        faviconLink.href = `${data.icon_url}?v=${Date.now()}`
      }

      // 更新 apple-touch-icon
      let appleLink = document.querySelector<HTMLLinkElement>("link[rel='apple-touch-icon']")
      if (!appleLink) {
        appleLink = document.createElement('link')
        appleLink.rel = 'apple-touch-icon'
        document.head.appendChild(appleLink)
      }
      appleLink.href = `/api/site-config/icon/192?v=${Date.now()}`
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
