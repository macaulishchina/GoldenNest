/**
 * 头像工具函数
 */

// 头像压缩配置
const AVATAR_MAX_SIZE = 200 // 头像最大尺寸 200x200
const AVATAR_QUALITY = 0.8 // JPEG 压缩质量

/**
 * 压缩图片为适合头像的大小
 * @param file 原始图片文件
 * @param maxSize 最大尺寸（默认200px）
 * @param quality 压缩质量（默认0.8）
 * @returns 压缩后的 Base64 字符串
 */
export function compressImage(
  file: File,
  maxSize: number = AVATAR_MAX_SIZE,
  quality: number = AVATAR_QUALITY
): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    
    reader.onload = (e) => {
      const img = new Image()
      
      img.onload = () => {
        // 计算压缩后的尺寸（保持宽高比）
        let width = img.width
        let height = img.height
        
        if (width > height) {
          if (width > maxSize) {
            height = Math.round((height * maxSize) / width)
            width = maxSize
          }
        } else {
          if (height > maxSize) {
            width = Math.round((width * maxSize) / height)
            height = maxSize
          }
        }
        
        // 创建 canvas 进行压缩
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('无法创建 canvas context'))
          return
        }
        
        // 绘制压缩后的图片
        ctx.drawImage(img, 0, 0, width, height)
        
        // 导出为 JPEG 格式（体积更小）
        const base64 = canvas.toDataURL('image/jpeg', quality)
        resolve(base64)
      }
      
      img.onerror = () => reject(new Error('图片加载失败'))
      img.src = e.target?.result as string
    }
    
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}

/**
 * 根据名字生成头像背景色
 * @param name 用户名或昵称
 * @returns 十六进制颜色值
 */
export function getAvatarColor(name: string): string {
  const colors = [
    '#f56a00', '#7265e6', '#ffbf00', '#00a2ae', 
    '#87d068', '#1890ff', '#eb2f96', '#722ed1'
  ]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}
