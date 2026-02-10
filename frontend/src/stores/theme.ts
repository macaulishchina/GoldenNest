import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { GlobalTheme, GlobalThemeOverrides } from 'naive-ui'
import { darkTheme } from 'naive-ui'

export type ThemeMode = 'light' | 'dark' | 'blue' | 'green' | 'purple'

export const useThemeStore = defineStore('theme', () => {
  // 从 localStorage 读取保存的主题，默认为浅色主题
  const currentTheme = ref<ThemeMode>((localStorage.getItem('theme') as ThemeMode) || 'light')

  // Naive UI 主题对象
  const naiveTheme = computed<GlobalTheme | null>(() => {
    return currentTheme.value === 'dark' ? darkTheme : null
  })

  // 主题配置列表
  const themes = [
    {
      name: 'light',
      label: '浅色主题',
      icon: '☀️',
      description: '清新明亮的浅色界面'
    },
    {
      name: 'dark',
      label: '深色主题',
      icon: '🌙',
      description: '护眼舒适的深色界面'
    },
    {
      name: 'blue',
      label: '海洋蓝',
      icon: '🌊',
      description: '清新海洋风格'
    },
    {
      name: 'green',
      label: '森林绿',
      icon: '🌲',
      description: '自然清新风格'
    },
    {
      name: 'purple',
      label: '神秘紫',
      icon: '🔮',
      description: '优雅神秘风格'
    }
  ]

  // 主题覆盖配置
  const themeOverrides = computed<GlobalThemeOverrides>(() => {
    const commonOverrides = {
      common: {},
      Button: {
        borderRadiusMedium: '8px',
        borderRadiusLarge: '10px'
      },
      Card: {
        borderRadius: '12px'
      },
      Input: {
        borderRadius: '8px'
      },
      Select: {
        peers: {
          InternalSelection: {
            borderRadius: '8px'
          }
        }
      }
    }

    switch (currentTheme.value) {
      case 'light':
        return {
          ...commonOverrides,
          common: {
            primaryColor: '#18A058',
            primaryColorHover: '#36AD6A',
            primaryColorPressed: '#0C7A43',
            primaryColorSuppl: '#36AD6A'
          }
        }
      
      case 'dark':
        return {
          ...commonOverrides,
          common: {
            primaryColor: '#63E2B7',
            primaryColorHover: '#7FE7C4',
            primaryColorPressed: '#5ACEA7',
            primaryColorSuppl: '#7FE7C4'
          }
        }
      
      case 'blue':
        return {
          ...commonOverrides,
          common: {
            primaryColor: '#2080F0',
            primaryColorHover: '#4098FC',
            primaryColorPressed: '#1060C9',
            primaryColorSuppl: '#4098FC',
            infoColor: '#2080F0',
            infoColorHover: '#4098FC',
            infoColorPressed: '#1060C9',
            infoColorSuppl: '#4098FC'
          }
        }
      
      case 'green':
        return {
          ...commonOverrides,
          common: {
            primaryColor: '#52C41A',
            primaryColorHover: '#73D13D',
            primaryColorPressed: '#389E0D',
            primaryColorSuppl: '#73D13D',
            successColor: '#52C41A',
            successColorHover: '#73D13D',
            successColorPressed: '#389E0D',
            successColorSuppl: '#73D13D'
          }
        }
      
      case 'purple':
        return {
          ...commonOverrides,
          common: {
            primaryColor: '#722ED1',
            primaryColorHover: '#9254DE',
            primaryColorPressed: '#531DAB',
            primaryColorSuppl: '#9254DE'
          }
        }
      
      default:
        return commonOverrides
    }
  })

  // 设置主题
  const setTheme = (theme: ThemeMode) => {
    console.log('切换主题:', currentTheme.value, '->', theme)
    currentTheme.value = theme
    localStorage.setItem('theme', theme)
    
    // 更新 body 的背景色类名
    document.body.className = `theme-${theme}`
    
    // 设置 CSS 变量到 document root
    applyThemeVariables(theme)
    
    console.log('body className:', document.body.className)
  }

  // 应用主题 CSS 变量
  const applyThemeVariables = (theme: ThemeMode) => {
    const root = document.documentElement
    
    // 清除所有主题变量
    const themeVars = [
      '--theme-bg-primary', '--theme-bg-secondary', '--theme-bg-card',
      '--theme-text-primary', '--theme-text-secondary', '--theme-text-tertiary',
      '--theme-border', '--theme-border-light',
      '--theme-primary', '--theme-primary-hover', '--theme-primary-light',
      '--theme-success', '--theme-success-light', '--theme-success-bg',
      '--theme-error', '--theme-error-light', '--theme-error-bg',
      '--theme-warning', '--theme-warning-light', '--theme-warning-bg',
      '--theme-info', '--theme-info-light', '--theme-info-bg',
      '--theme-purple', '--theme-purple-light',
      '--theme-shadow', '--theme-shadow-sm', '--theme-card-hover',
      '--theme-gradient-primary', '--theme-gradient-text'
    ]
    themeVars.forEach(v => root.style.removeProperty(v))
    
    switch (theme) {
      case 'light':
        root.style.setProperty('--theme-bg-primary', 'linear-gradient(135deg, #f0fdf4 0%, #ecfeff 100%)')
        root.style.setProperty('--theme-bg-secondary', '#f9fafb')
        root.style.setProperty('--theme-bg-card', '#fefffe')
        root.style.setProperty('--theme-text-primary', '#1f2937')
        root.style.setProperty('--theme-text-secondary', '#6b7280')
        root.style.setProperty('--theme-text-tertiary', '#94a3b8')
        root.style.setProperty('--theme-border', '#e5e7eb')
        root.style.setProperty('--theme-border-light', '#f3f4f6')
        root.style.setProperty('--theme-primary', '#18A058')
        root.style.setProperty('--theme-primary-hover', '#36AD6A')
        root.style.setProperty('--theme-primary-light', '#dcfce7')
        root.style.setProperty('--theme-success', '#10b981')
        root.style.setProperty('--theme-success-light', '#86efac')
        root.style.setProperty('--theme-success-bg', 'rgba(240, 253, 244, 0.95)')
        root.style.setProperty('--theme-error', '#ef4444')
        root.style.setProperty('--theme-error-light', '#fca5a5')
        root.style.setProperty('--theme-error-bg', 'rgba(254, 242, 242, 0.95)')
        root.style.setProperty('--theme-warning', '#f59e0b')
        root.style.setProperty('--theme-warning-light', '#fde68a')
        root.style.setProperty('--theme-warning-bg', 'rgba(255, 251, 235, 0.95)')
        root.style.setProperty('--theme-info', '#3b82f6')
        root.style.setProperty('--theme-info-light', '#93c5fd')
        root.style.setProperty('--theme-info-bg', 'rgba(239, 246, 255, 0.95)')
        root.style.setProperty('--theme-purple', '#8b5cf6')
        root.style.setProperty('--theme-purple-light', '#c4b5fd')
        root.style.setProperty('--theme-shadow', 'rgba(0, 0, 0, 0.1)')
        root.style.setProperty('--theme-shadow-sm', 'rgba(0, 0, 0, 0.05)')
        root.style.setProperty('--theme-card-hover', 'rgba(0, 0, 0, 0.02)')
        root.style.setProperty('--theme-gradient-primary', 'linear-gradient(135deg, #6ee7b7 0%, #34d399 100%)')
        root.style.setProperty('--theme-gradient-text', '#064e3b')
        break
        
      case 'dark':
        root.style.setProperty('--theme-bg-primary', 'linear-gradient(135deg, #18181c 0%, #1a1b23 100%)')
        root.style.setProperty('--theme-bg-secondary', '#1f2937')
        root.style.setProperty('--theme-bg-card', '#374151')
        root.style.setProperty('--theme-text-primary', '#f9fafb')
        root.style.setProperty('--theme-text-secondary', '#d1d5db')
        root.style.setProperty('--theme-text-tertiary', '#9ca3af')
        root.style.setProperty('--theme-border', '#4b5563')
        root.style.setProperty('--theme-border-light', '#374151')
        root.style.setProperty('--theme-primary', '#63E2B7')
        root.style.setProperty('--theme-primary-hover', '#7FE7C4')
        root.style.setProperty('--theme-primary-light', '#064e3b')
        root.style.setProperty('--theme-success', '#34d399')
        root.style.setProperty('--theme-success-light', '#6ee7b7')
        root.style.setProperty('--theme-success-bg', 'rgba(6, 95, 70, 0.35)')
        root.style.setProperty('--theme-error', '#f87171')
        root.style.setProperty('--theme-error-light', '#fca5a5')
        root.style.setProperty('--theme-error-bg', 'rgba(153, 27, 27, 0.35)')
        root.style.setProperty('--theme-warning', '#fbbf24')
        root.style.setProperty('--theme-warning-light', '#fcd34d')
        root.style.setProperty('--theme-warning-bg', 'rgba(146, 64, 14, 0.35)')
        root.style.setProperty('--theme-info', '#60a5fa')
        root.style.setProperty('--theme-info-light', '#93c5fd')
        root.style.setProperty('--theme-info-bg', 'rgba(30, 64, 175, 0.35)')
        root.style.setProperty('--theme-purple', '#a78bfa')
        root.style.setProperty('--theme-purple-light', '#c4b5fd')
        root.style.setProperty('--theme-purple-bg', 'rgba(91, 33, 182, 0.35)')
        root.style.setProperty('--theme-shadow', 'rgba(0, 0, 0, 0.3)')
        root.style.setProperty('--theme-shadow-sm', 'rgba(0, 0, 0, 0.2)')
        root.style.setProperty('--theme-card-hover', 'rgba(255, 255, 255, 0.05)')
        root.style.setProperty('--theme-gradient-primary', 'linear-gradient(135deg, #065f46 0%, #064e3b 100%)')
        root.style.setProperty('--theme-gradient-text', '#d1fae5')
        break
        
      case 'blue':
        root.style.setProperty('--theme-bg-primary', 'linear-gradient(135deg, #e6f4ff 0%, #f0f7ff 100%)')
        root.style.setProperty('--theme-bg-secondary', '#f0f7ff')
        root.style.setProperty('--theme-bg-card', '#f0faff')
        root.style.setProperty('--theme-text-primary', '#1e3a5f')
        root.style.setProperty('--theme-text-secondary', '#64748b')
        root.style.setProperty('--theme-text-tertiary', '#94a3b8')
        root.style.setProperty('--theme-border', '#bfdbfe')
        root.style.setProperty('--theme-border-light', '#dbeafe')
        root.style.setProperty('--theme-primary', '#2080F0')
        root.style.setProperty('--theme-primary-hover', '#4098FC')
        root.style.setProperty('--theme-primary-light', '#dbeafe')
        root.style.setProperty('--theme-success', '#10b981')
        root.style.setProperty('--theme-success-light', '#86efac')
        root.style.setProperty('--theme-success-bg', 'rgba(240, 253, 244, 0.95)')
        root.style.setProperty('--theme-error', '#ef4444')
        root.style.setProperty('--theme-error-light', '#fca5a5')
        root.style.setProperty('--theme-error-bg', 'rgba(254, 242, 242, 0.95)')
        root.style.setProperty('--theme-warning', '#f59e0b')
        root.style.setProperty('--theme-warning-light', '#fde68a')
        root.style.setProperty('--theme-warning-bg', 'rgba(255, 251, 235, 0.95)')
        root.style.setProperty('--theme-info', '#3b82f6')
        root.style.setProperty('--theme-info-light', '#93c5fd')
        root.style.setProperty('--theme-info-bg', 'rgba(219, 234, 254, 0.95)')
        root.style.setProperty('--theme-purple', '#8b5cf6')
        root.style.setProperty('--theme-purple-light', '#c4b5fd')
        root.style.setProperty('--theme-shadow', 'rgba(37, 99, 235, 0.1)')
        root.style.setProperty('--theme-shadow-sm', 'rgba(37, 99, 235, 0.05)')
        root.style.setProperty('--theme-card-hover', 'rgba(37, 99, 235, 0.02)')
        root.style.setProperty('--theme-gradient-primary', 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)')
        root.style.setProperty('--theme-gradient-text', '#ffffff')
        break
        
      case 'green':
        root.style.setProperty('--theme-bg-primary', 'linear-gradient(135deg, #f0ffe6 0%, #f6ffed 100%)')
        root.style.setProperty('--theme-bg-secondary', '#f6ffed')
        root.style.setProperty('--theme-bg-card', '#f6ffed')
        root.style.setProperty('--theme-text-primary', '#1a3a1a')
        root.style.setProperty('--theme-text-secondary', '#52796f')
        root.style.setProperty('--theme-text-tertiary', '#84a98c')
        root.style.setProperty('--theme-border', '#d9f7be')
        root.style.setProperty('--theme-border-light', '#f6ffed')
        root.style.setProperty('--theme-primary', '#52C41A')
        root.style.setProperty('--theme-primary-hover', '#73D13D')
        root.style.setProperty('--theme-primary-light', '#d9f7be')
        root.style.setProperty('--theme-success', '#10b981')
        root.style.setProperty('--theme-success-light', '#86efac')
        root.style.setProperty('--theme-success-bg', 'rgba(240, 253, 244, 0.95)')
        root.style.setProperty('--theme-error', '#ef4444')
        root.style.setProperty('--theme-error-light', '#fca5a5')
        root.style.setProperty('--theme-error-bg', 'rgba(254, 242, 242, 0.95)')
        root.style.setProperty('--theme-warning', '#f59e0b')
        root.style.setProperty('--theme-warning-light', '#fde68a')
        root.style.setProperty('--theme-warning-bg', 'rgba(255, 251, 235, 0.95)')
        root.style.setProperty('--theme-info', '#3b82f6')
        root.style.setProperty('--theme-info-light', '#93c5fd')
        root.style.setProperty('--theme-info-bg', 'rgba(239, 246, 255, 0.95)')
        root.style.setProperty('--theme-purple', '#8b5cf6')
        root.style.setProperty('--theme-purple-light', '#c4b5fd')
        root.style.setProperty('--theme-shadow', 'rgba(22, 163, 74, 0.1)')
        root.style.setProperty('--theme-shadow-sm', 'rgba(22, 163, 74, 0.05)')
        root.style.setProperty('--theme-card-hover', 'rgba(22, 163, 74, 0.02)')
        root.style.setProperty('--theme-gradient-primary', 'linear-gradient(135deg, #16a34a 0%, #15803d 100%)')
        root.style.setProperty('--theme-gradient-text', '#ffffff')
        break
        
      case 'purple':
        root.style.setProperty('--theme-bg-primary', 'linear-gradient(135deg, #f4e6ff 0%, #f9f0ff 100%)')
        root.style.setProperty('--theme-bg-secondary', '#f9f0ff')
        root.style.setProperty('--theme-bg-card', '#faf5ff')
        root.style.setProperty('--theme-text-primary', '#3a1f5f')
        root.style.setProperty('--theme-text-secondary', '#7c3aed')
        root.style.setProperty('--theme-text-tertiary', '#a78bfa')
        root.style.setProperty('--theme-border', '#e9d5ff')
        root.style.setProperty('--theme-border-light', '#f3e8ff')
        root.style.setProperty('--theme-primary', '#722ED1')
        root.style.setProperty('--theme-primary-hover', '#9254DE')
        root.style.setProperty('--theme-primary-light', '#e9d5ff')
        root.style.setProperty('--theme-success', '#10b981')
        root.style.setProperty('--theme-success-light', '#86efac')
        root.style.setProperty('--theme-success-bg', 'rgba(240, 253, 244, 0.95)')
        root.style.setProperty('--theme-error', '#ef4444')
        root.style.setProperty('--theme-error-light', '#fca5a5')
        root.style.setProperty('--theme-error-bg', 'rgba(254, 242, 242, 0.95)')
        root.style.setProperty('--theme-warning', '#f59e0b')
        root.style.setProperty('--theme-warning-light', '#fde68a')
        root.style.setProperty('--theme-warning-bg', 'rgba(255, 251, 235, 0.95)')
        root.style.setProperty('--theme-info', '#3b82f6')
        root.style.setProperty('--theme-info-light', '#93c5fd')
        root.style.setProperty('--theme-info-bg', 'rgba(239, 246, 255, 0.95)')
        root.style.setProperty('--theme-purple', '#8b5cf6')
        root.style.setProperty('--theme-purple-light', '#c4b5fd')
        root.style.setProperty('--theme-shadow', 'rgba(139, 92, 246, 0.1)')
        root.style.setProperty('--theme-shadow-sm', 'rgba(139, 92, 246, 0.05)')
        root.style.setProperty('--theme-card-hover', 'rgba(139, 92, 246, 0.02)')
        root.style.setProperty('--theme-gradient-primary', 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)')
        root.style.setProperty('--theme-gradient-text', '#ffffff')
        break
    }
  }

  // 切换到下一个主题（用于快速切换）
  const toggleTheme = () => {
    const themeNames: ThemeMode[] = ['light', 'dark', 'blue', 'green', 'purple']
    const currentIndex = themeNames.indexOf(currentTheme.value)
    const nextIndex = (currentIndex + 1) % themeNames.length
    setTheme(themeNames[nextIndex])
  }

  // 获取当前主题信息
  const currentThemeInfo = computed(() => {
    return themes.find(t => t.name === currentTheme.value) || themes[0]
  })

  // 初始化时设置 body 类名和 CSS 变量
  if (typeof window !== 'undefined') {
    document.body.className = `theme-${currentTheme.value}`
    applyThemeVariables(currentTheme.value)
  }

  return {
    currentTheme,
    naiveTheme,
    themeOverrides,
    themes,
    currentThemeInfo,
    setTheme,
    toggleTheme
  }
})
