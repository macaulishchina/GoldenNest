/**
 * 日期时间工具函数
 * 用于处理UTC时间到本地时间的转换
 */

/**
 * 将UTC时间字符串转换为本地时间并格式化显示
 * 后端存储的是UTC时间，前端显示时需要转换为本地时间
 * 
 * @param utcDateStr - UTC时间字符串（如 "2026-02-02T11:26:00" 或 "2026-02-02 11:26:00"）
 * @param format - 输出格式：'datetime' | 'date' | 'time'
 * @returns 格式化后的本地时间字符串
 */
export function formatLocalDateTime(
  utcDateStr: string | Date | null | undefined,
  format: 'datetime' | 'date' | 'time' = 'datetime'
): string {
  if (!utcDateStr) return '-'
  
  try {
    // 处理日期对象或字符串
    let date: Date
    if (utcDateStr instanceof Date) {
      date = utcDateStr
    } else {
      // 确保字符串被正确解析为UTC时间
      // 如果没有时区标识，添加 'Z' 表示UTC
      let dateStr = utcDateStr.toString()
      if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('T')) {
        // 格式如 "2026-02-02 11:26:00"，转换为ISO格式
        dateStr = dateStr.replace(' ', 'T') + 'Z'
      } else if (!dateStr.endsWith('Z') && !dateStr.includes('+')) {
        // 格式如 "2026-02-02T11:26:00"
        dateStr = dateStr + 'Z'
      }
      date = new Date(dateStr)
    }
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return utcDateStr.toString()
    }
    
    // 根据格式输出
    const options: Intl.DateTimeFormatOptions = {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
    }
    
    switch (format) {
      case 'date':
        options.year = 'numeric'
        options.month = '2-digit'
        options.day = '2-digit'
        break
      case 'time':
        options.hour = '2-digit'
        options.minute = '2-digit'
        options.second = '2-digit'
        options.hour12 = false
        break
      case 'datetime':
      default:
        options.year = 'numeric'
        options.month = '2-digit'
        options.day = '2-digit'
        options.hour = '2-digit'
        options.minute = '2-digit'
        options.second = '2-digit'
        options.hour12 = false
        break
    }
    
    return date.toLocaleString('zh-CN', options)
  } catch (e) {
    console.warn('日期格式化失败:', utcDateStr, e)
    return utcDateStr?.toString() || '-'
  }
}

/**
 * 格式化为简短的日期时间（不含秒）
 */
export function formatShortDateTime(utcDateStr: string | Date | null | undefined): string {
  if (!utcDateStr) return '-'
  
  try {
    let date: Date
    if (utcDateStr instanceof Date) {
      date = utcDateStr
    } else {
      let dateStr = utcDateStr.toString()
      if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('T')) {
        dateStr = dateStr.replace(' ', 'T') + 'Z'
      } else if (!dateStr.endsWith('Z') && !dateStr.includes('+')) {
        dateStr = dateStr + 'Z'
      }
      date = new Date(dateStr)
    }
    
    if (isNaN(date.getTime())) {
      return utcDateStr.toString()
    }
    
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  } catch (e) {
    return utcDateStr?.toString() || '-'
  }
}

/**
 * 格式化为仅日期
 */
export function formatDate(utcDateStr: string | Date | null | undefined): string {
  return formatLocalDateTime(utcDateStr, 'date')
}

/**
 * 格式化为本地日期（别名）
 */
export function formatLocalDate(utcDateStr: string | Date | null | undefined): string {
  return formatLocalDateTime(utcDateStr, 'date')
}

/**
 * 格式化为仅时间
 */
export function formatTime(utcDateStr: string | Date | null | undefined): string {
  return formatLocalDateTime(utcDateStr, 'time')
}
