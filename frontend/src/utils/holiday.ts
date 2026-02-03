/**
 * 节日彩蛋工具模块
 * 使用 lunar-javascript 精确计算农历日期
 */
import { Solar } from 'lunar-javascript'

export interface HolidayInfo {
  name: string       // 节日名称
  emoji: string      // 节日表情
  greeting: string   // 祝福语
  priority: number   // 优先级，数值越大越优先
}

// 农历节日配置（月-日 => 节日信息）
const LUNAR_HOLIDAYS: Record<string, HolidayInfo> = {
  '1-1': { name: '春节', emoji: '🎊', greeting: '新年快乐', priority: 100 },
  '1-2': { name: '春节', emoji: '🧧', greeting: '恭喜发财', priority: 95 },
  '1-3': { name: '春节', emoji: '🎉', greeting: '万事如意', priority: 90 },
  '1-4': { name: '春节', emoji: '🎆', greeting: '阖家幸福', priority: 85 },
  '1-5': { name: '春节', emoji: '🧨', greeting: '迎财神', priority: 80 },
  '1-15': { name: '元宵节', emoji: '🏮', greeting: '元宵佳节', priority: 70 },
  '5-5': { name: '端午节', emoji: '🐲', greeting: '端午安康', priority: 70 },
  '7-7': { name: '七夕节', emoji: '💕', greeting: '七夕快乐', priority: 60 },
  '8-15': { name: '中秋节', emoji: '🥮', greeting: '中秋团圆', priority: 80 },
  '9-9': { name: '重阳节', emoji: '🌸', greeting: '重阳敬老', priority: 50 },
  '12-23': { name: '小年', emoji: '🧹', greeting: '小年福至', priority: 65 },
  '12-24': { name: '小年', emoji: '🧹', greeting: '小年福至', priority: 65 },
}

// 公历节日配置（月-日 => 节日信息）
const SOLAR_HOLIDAYS: Record<string, HolidayInfo> = {
  '1-1': { name: '元旦', emoji: '🎊', greeting: '新年快乐', priority: 60 },
  '2-14': { name: '情人节', emoji: '💝', greeting: '情人节快乐', priority: 40 },
  '3-8': { name: '妇女节', emoji: '👩', greeting: '女神节快乐', priority: 40 },
  '5-1': { name: '劳动节', emoji: '💪', greeting: '劳动光荣', priority: 50 },
  '6-1': { name: '儿童节', emoji: '🎈', greeting: '六一快乐', priority: 45 },
  '10-1': { name: '国庆节', emoji: '🇨🇳', greeting: '国庆快乐', priority: 75 },
  '10-2': { name: '国庆节', emoji: '🇨🇳', greeting: '国庆假期', priority: 70 },
  '10-3': { name: '国庆节', emoji: '🇨🇳', greeting: '国庆假期', priority: 65 },
  '12-25': { name: '圣诞节', emoji: '🎄', greeting: '圣诞快乐', priority: 40 },
}

/**
 * 获取今日节日信息
 * @param date 日期，默认今天
 * @returns 节日信息，如果没有则返回 null
 */
export function getTodayHoliday(date: Date = new Date()): HolidayInfo | null {
  const holidays: HolidayInfo[] = []
  
  // 获取农历信息
  const solar = Solar.fromDate(date)
  const lunar = solar.getLunar()
  const lunarMonth = lunar.getMonth()
  const lunarDay = lunar.getDay()
  
  // 检查除夕（特殊处理：腊月的最后一天）
  if (lunarMonth === 12) {
    // 获取当年腊月的天数
    const lunarYear = lunar.getYear()
    const nextNewYear = Solar.fromYmd(date.getFullYear() + 1, 1, 1).getLunar()
    // 如果明天是正月初一，今天就是除夕
    const tomorrow = new Date(date)
    tomorrow.setDate(tomorrow.getDate() + 1)
    const tomorrowSolar = Solar.fromDate(tomorrow)
    const tomorrowLunar = tomorrowSolar.getLunar()
    if (tomorrowLunar.getMonth() === 1 && tomorrowLunar.getDay() === 1) {
      holidays.push({ name: '除夕', emoji: '🎆', greeting: '除夕守岁', priority: 98 })
    }
  }
  
  // 检查农历节日
  const lunarKey = `${lunarMonth}-${lunarDay}`
  if (LUNAR_HOLIDAYS[lunarKey]) {
    holidays.push(LUNAR_HOLIDAYS[lunarKey])
  }
  
  // 检查公历节日
  const solarMonth = date.getMonth() + 1
  const solarDay = date.getDate()
  const solarKey = `${solarMonth}-${solarDay}`
  if (SOLAR_HOLIDAYS[solarKey]) {
    holidays.push(SOLAR_HOLIDAYS[solarKey])
  }
  
  // 返回优先级最高的节日
  if (holidays.length === 0) return null
  holidays.sort((a, b) => b.priority - a.priority)
  return holidays[0]
}

/**
 * 获取今日农历信息
 * @param date 日期，默认今天
 * @returns 农历信息字符串，如 "腊月十六"
 */
export function getLunarDateString(date: Date = new Date()): string {
  const solar = Solar.fromDate(date)
  const lunar = solar.getLunar()
  return `${lunar.getMonthInChinese()}月${lunar.getDayInChinese()}`
}

/**
 * 获取节日彩蛋显示文本
 * @param date 日期，默认今天
 * @returns 显示文本，如 "🎊 新年快乐"，没有节日返回 null
 */
export function getHolidayGreeting(date: Date = new Date()): string | null {
  const holiday = getTodayHoliday(date)
  if (!holiday) return null
  return `${holiday.emoji} ${holiday.greeting}`
}
