"""
成就系统服务 - 成就定义和检测逻辑
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.models.models import (
    Achievement, UserAchievement, User, Deposit, Investment, 
    ExpenseRequest, Transaction, FamilyMember, Family,
    AchievementCategory, AchievementRarity
)


# ==================== 成就定义数据 ====================

ACHIEVEMENT_DEFINITIONS = [
    # ==================== 存款类成就 (DEPOSIT) ====================
    # 金额里程碑
    {"code": "first_deposit", "name": "初来乍到", "description": "首次存入资金", "category": "deposit", "icon": "🌱", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "1"},
    {"code": "deposit_500", "name": "零钱罐", "description": "累计存入 500 元", "category": "deposit", "icon": "🪙", "rarity": "common", "points": 8, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "500"},
    {"code": "deposit_1k", "name": "小试牛刀", "description": "累计存入 1,000 元", "category": "deposit", "icon": "💵", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "1000"},
    {"code": "deposit_2k", "name": "储蓄萌新", "description": "累计存入 2,000 元", "category": "deposit", "icon": "💴", "rarity": "common", "points": 18, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "2000"},
    {"code": "deposit_5k", "name": "积少成多", "description": "累计存入 5,000 元", "category": "deposit", "icon": "�", "rarity": "rare", "points": 25, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "5000"},
    {"code": "deposit_10k", "name": "万元户", "description": "累计存入 10,000 元", "category": "deposit", "icon": "💰", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "10000"},
    {"code": "deposit_20k", "name": "小康之家", "description": "累计存入 20,000 元", "category": "deposit", "icon": "🏡", "rarity": "rare", "points": 70, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "20000"},
    {"code": "deposit_30k", "name": "财运亨通", "description": "累计存入 30,000 元", "category": "deposit", "icon": "🧧", "rarity": "rare", "points": 85, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "30000"},
    {"code": "deposit_50k", "name": "小有积蓄", "description": "累计存入 50,000 元", "category": "deposit", "icon": "🏦", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "50000"},
    {"code": "deposit_80k", "name": "财务达人", "description": "累计存入 80,000 元", "category": "deposit", "icon": "📈", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "80000"},
    {"code": "deposit_100k", "name": "财富新贵", "description": "累计存入 100,000 元", "category": "deposit", "icon": "💎", "rarity": "epic", "points": 200, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "100000"},
    {"code": "deposit_200k", "name": "资产翻番", "description": "累计存入 200,000 元", "category": "deposit", "icon": "🏆", "rarity": "epic", "points": 300, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "200000"},
    {"code": "deposit_300k", "name": "财富密码", "description": "累计存入 300,000 元", "category": "deposit", "icon": "🔐", "rarity": "legendary", "points": 380, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "300000"},
    {"code": "deposit_500k", "name": "金融精英", "description": "累计存入 500,000 元", "category": "deposit", "icon": "🌟", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "500000"},
    {"code": "deposit_800k", "name": "财务自由", "description": "累计存入 800,000 元", "category": "deposit", "icon": "🦅", "rarity": "legendary", "points": 700, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "800000"},
    {"code": "deposit_1m", "name": "百万俱乐部", "description": "累计存入 1,000,000 元", "category": "deposit", "icon": "👑", "rarity": "legendary", "points": 1000, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "1000000"},
    {"code": "deposit_2m", "name": "富甲一方", "description": "累计存入 2,000,000 元", "category": "deposit", "icon": "🏰", "rarity": "mythic", "points": 1500, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "2000000"},
    {"code": "deposit_5m", "name": "财富巨擘", "description": "累计存入 5,000,000 元", "category": "deposit", "icon": "🌌", "rarity": "mythic", "points": 3000, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "5000000"},
    {"code": "deposit_10m", "name": "亿万传奇", "description": "累计存入 10,000,000 元", "category": "deposit", "icon": "✨", "rarity": "mythic", "points": 5000, "is_hidden": False, "trigger_type": "total_deposit", "trigger_value": "10000000"},
    
    # 存款次数
    {"code": "deposit_5_times", "name": "初露锋芒", "description": "累计存款 5 次", "category": "deposit", "icon": "✋", "rarity": "common", "points": 12, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "5"},
    {"code": "deposit_10_times", "name": "勤俭持家", "description": "累计存款 10 次", "category": "deposit", "icon": "📝", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "10"},
    {"code": "deposit_20_times", "name": "储蓄小能手", "description": "累计存款 20 次", "category": "deposit", "icon": "📋", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "20"},
    {"code": "deposit_30_times", "name": "习惯养成", "description": "累计存款 30 次", "category": "deposit", "icon": "🎯", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "30"},
    {"code": "deposit_50_times", "name": "储蓄达人", "description": "累计存款 50 次", "category": "deposit", "icon": "📊", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "50"},
    {"code": "deposit_80_times", "name": "储蓄精英", "description": "累计存款 80 次", "category": "deposit", "icon": "🎖️", "rarity": "rare", "points": 70, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "80"},
    {"code": "deposit_100_times", "name": "存钱专家", "description": "累计存款 100 次", "category": "deposit", "icon": "🏆", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "100"},
    {"code": "deposit_150_times", "name": "储蓄大师", "description": "累计存款 150 次", "category": "deposit", "icon": "🥇", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "150"},
    {"code": "deposit_200_times", "name": "财富管家", "description": "累计存款 200 次", "category": "deposit", "icon": "💼", "rarity": "epic", "points": 200, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "200"},
    {"code": "deposit_300_times", "name": "存钱机器", "description": "累计存款 300 次", "category": "deposit", "icon": "🤖", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "300"},
    {"code": "deposit_500_times", "name": "储蓄狂人", "description": "累计存款 500 次", "category": "deposit", "icon": "🔥", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "500"},
    {"code": "deposit_1000_times", "name": "千笔传说", "description": "累计存款 1000 次", "category": "deposit", "icon": "🌟", "rarity": "mythic", "points": 1000, "is_hidden": False, "trigger_type": "deposit_count", "trigger_value": "1000"},
    
    # 单笔存款金额
    {"code": "single_deposit_100", "name": "小额起步", "description": "单笔存入 100 元以上", "category": "deposit", "icon": "💸", "rarity": "common", "points": 5, "is_hidden": False, "trigger_type": "single_deposit", "trigger_value": "100"},
    {"code": "single_deposit_500", "name": "中等投入", "description": "单笔存入 500 元以上", "category": "deposit", "icon": "💳", "rarity": "common", "points": 12, "is_hidden": False, "trigger_type": "single_deposit", "trigger_value": "500"},
    {"code": "single_deposit_1k", "name": "大手笔", "description": "单笔存入 1,000 元以上", "category": "deposit", "icon": "💵", "rarity": "rare", "points": 25, "is_hidden": False, "trigger_type": "single_deposit", "trigger_value": "1000"},
    {"code": "single_deposit_5k", "name": "土豪出手", "description": "单笔存入 5,000 元以上", "category": "deposit", "icon": "🤑", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "single_deposit", "trigger_value": "5000"},
    {"code": "single_deposit_10k", "name": "万元豪掷", "description": "单笔存入 10,000 元以上", "category": "deposit", "icon": "💎", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "single_deposit", "trigger_value": "10000"},
    {"code": "single_deposit_50k", "name": "财神附体", "description": "单笔存入 50,000 元以上", "category": "deposit", "icon": "🧧", "rarity": "legendary", "points": 250, "is_hidden": False, "trigger_type": "single_deposit", "trigger_value": "50000"},
    {"code": "single_deposit_100k", "name": "一掷千金", "description": "单笔存入 100,000 元以上", "category": "deposit", "icon": "👑", "rarity": "mythic", "points": 500, "is_hidden": False, "trigger_type": "single_deposit", "trigger_value": "100000"},
    
    # ==================== 坚持类成就 (STREAK) ====================
    # 累计存款天数（改为累计而非连续，更人性化）
    {"code": "days_3", "name": "初次尝试", "description": "累计存款 3 天", "category": "streak", "icon": "�", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "3"},
    {"code": "days_5", "name": "五日积累", "description": "累计存款 5 天", "category": "streak", "icon": "✋", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "5"},
    {"code": "days_7", "name": "一周足迹", "description": "累计存款 7 天", "category": "streak", "icon": "📆", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "7"},
    {"code": "days_10", "name": "十日不辍", "description": "累计存款 10 天", "category": "streak", "icon": "🔟", "rarity": "common", "points": 40, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "10"},
    {"code": "days_14", "name": "两周达人", "description": "累计存款 14 天", "category": "streak", "icon": "📅", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "14"},
    {"code": "days_21", "name": "习惯成形", "description": "累计存款 21 天（习惯养成周期）", "category": "streak", "icon": "�", "rarity": "rare", "points": 70, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "21"},
    {"code": "days_30", "name": "月度坚持", "description": "累计存款 30 天", "category": "streak", "icon": "🔥", "rarity": "rare", "points": 100, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "30"},
    {"code": "days_45", "name": "月半之约", "description": "累计存款 45 天", "category": "streak", "icon": "🌗", "rarity": "rare", "points": 130, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "45"},
    {"code": "days_60", "name": "双月达成", "description": "累计存款 60 天", "category": "streak", "icon": "💪", "rarity": "epic", "points": 200, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "60"},
    {"code": "days_90", "name": "季度达人", "description": "累计存款 90 天（一个季度）", "category": "streak", "icon": "🌸", "rarity": "epic", "points": 250, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "90"},
    {"code": "days_100", "name": "百日积淀", "description": "累计存款 100 天", "category": "streak", "icon": "⚡", "rarity": "epic", "points": 300, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "100"},
    {"code": "days_120", "name": "四月之约", "description": "累计存款 120 天", "category": "streak", "icon": "🌻", "rarity": "epic", "points": 350, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "120"},
    {"code": "days_150", "name": "五月风华", "description": "累计存款 150 天", "category": "streak", "icon": "🌺", "rarity": "legendary", "points": 420, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "150"},
    {"code": "days_180", "name": "半年之约", "description": "累计存款 180 天", "category": "streak", "icon": "🌙", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "180"},
    {"code": "days_200", "name": "双百纪念", "description": "累计存款 200 天", "category": "streak", "icon": "🎊", "rarity": "legendary", "points": 600, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "200"},
    {"code": "days_250", "name": "坚持之星", "description": "累计存款 250 天", "category": "streak", "icon": "⭐", "rarity": "legendary", "points": 700, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "250"},
    {"code": "days_300", "name": "三百天勇士", "description": "累计存款 300 天", "category": "streak", "icon": "🛡️", "rarity": "legendary", "points": 850, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "300"},
    {"code": "days_365", "name": "周年纪念", "description": "累计存款 365 天（整整一年）", "category": "streak", "icon": "🏔️", "rarity": "mythic", "points": 1000, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "365"},
    {"code": "days_500", "name": "五百天传奇", "description": "累计存款 500 天", "category": "streak", "icon": "🌟", "rarity": "mythic", "points": 1500, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "500"},
    {"code": "days_730", "name": "两年之约", "description": "累计存款 730 天（两年）", "category": "streak", "icon": "💫", "rarity": "mythic", "points": 2500, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "730"},
    {"code": "days_1000", "name": "千日修行", "description": "累计存款 1000 天", "category": "streak", "icon": "🐉", "rarity": "mythic", "points": 5000, "is_hidden": False, "trigger_type": "deposit_days", "trigger_value": "1000"},
    
    # 存款时间段成就
    {"code": "morning_saver", "name": "晨间储蓄者", "description": "在早上6-9点存款10次", "category": "streak", "icon": "🌅", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "time_deposit_count", "trigger_value": "6-9-10"},
    {"code": "noon_saver", "name": "午间储蓄者", "description": "在中午11-14点存款10次", "category": "streak", "icon": "☀️", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "time_deposit_count", "trigger_value": "11-14-10"},
    {"code": "evening_saver", "name": "傍晚储蓄者", "description": "在傍晚17-20点存款10次", "category": "streak", "icon": "🌆", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "time_deposit_count", "trigger_value": "17-20-10"},
    {"code": "weekend_warrior", "name": "周末战士", "description": "连续4个周末都有存款", "category": "streak", "icon": "🏖️", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "weekend_streak", "trigger_value": "4"},
    {"code": "monthly_consistent", "name": "月度恒心", "description": "连续3个月每月都有存款", "category": "streak", "icon": "📊", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "monthly_streak", "trigger_value": "3"},
    {"code": "quarterly_master", "name": "季度大师", "description": "连续4个季度每季都有存款", "category": "streak", "icon": "📈", "rarity": "epic", "points": 120, "is_hidden": False, "trigger_type": "quarterly_streak", "trigger_value": "4"},
    {"code": "annual_champion", "name": "年度冠军", "description": "连续12个月每月都有存款", "category": "streak", "icon": "🏆", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "monthly_streak", "trigger_value": "12"},
    
    # ==================== 家庭类成就 (FAMILY) ====================
    # 家庭创建与加入
    {"code": "create_family", "name": "筑巢者", "description": "创建家庭", "category": "family", "icon": "🏠", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "create_family", "trigger_value": "1"},
    {"code": "join_family", "name": "新成员", "description": "加入一个家庭", "category": "family", "icon": "🤝", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "join_family", "trigger_value": "1"},
    {"code": "family_founder", "name": "家族开创者", "description": "创建家庭并邀请第一位成员", "category": "family", "icon": "🏛️", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "founder_invite", "trigger_value": "1"},
    {"code": "family_namer", "name": "取名达人", "description": "为家庭设置名称", "category": "family", "icon": "📛", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "set_family_name", "trigger_value": "1"},
    {"code": "target_setter", "name": "目标制定者", "description": "设置家庭储蓄目标", "category": "family", "icon": "🎯", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "set_target", "trigger_value": "1"},
    
    # 邀请成员
    {"code": "invite_1", "name": "迎新使者", "description": "成功邀请 1 位成员", "category": "family", "icon": "📨", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "invite_count", "trigger_value": "1"},
    {"code": "invite_2", "name": "二人同行", "description": "成功邀请 2 位成员", "category": "family", "icon": "👫", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "invite_count", "trigger_value": "2"},
    {"code": "invite_3", "name": "人气担当", "description": "成功邀请 3 位成员", "category": "family", "icon": "📬", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "invite_count", "trigger_value": "3"},
    {"code": "invite_5", "name": "社交达人", "description": "成功邀请 5 位成员", "category": "family", "icon": "🌐", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "invite_count", "trigger_value": "5"},
    {"code": "invite_10", "name": "家族招募官", "description": "成功邀请 10 位成员", "category": "family", "icon": "📣", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "invite_count", "trigger_value": "10"},
    {"code": "invite_20", "name": "人脉之王", "description": "成功邀请 20 位成员", "category": "family", "icon": "👑", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "invite_count", "trigger_value": "20"},
    
    # 家庭规模
    {"code": "family_2_members", "name": "双人世界", "description": "家庭成员达到 2 人", "category": "family", "icon": "💑", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "2"},
    {"code": "family_3_members", "name": "三口之家", "description": "家庭成员达到 3 人", "category": "family", "icon": "👨‍👩‍👧", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "3"},
    {"code": "family_4_members", "name": "四世同堂", "description": "家庭成员达到 4 人", "category": "family", "icon": "👨‍👩‍👧‍👦", "rarity": "rare", "points": 35, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "4"},
    {"code": "family_5_members", "name": "大家庭", "description": "家庭成员达到 5 人", "category": "family", "icon": "🏡", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "5"},
    {"code": "family_8_members", "name": "八口之家", "description": "家庭成员达到 8 人", "category": "family", "icon": "🏠", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "8"},
    {"code": "family_10_members", "name": "家族企业", "description": "家庭成员达到 10 人", "category": "family", "icon": "🏰", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "10"},
    {"code": "family_15_members", "name": "大家族", "description": "家庭成员达到 15 人", "category": "family", "icon": "🏯", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "15"},
    {"code": "family_20_members", "name": "家族王朝", "description": "家庭成员达到 20 人", "category": "family", "icon": "🏛️", "rarity": "legendary", "points": 350, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "20"},
    {"code": "family_50_members", "name": "百人家族", "description": "家庭成员达到 50 人", "category": "family", "icon": "🌆", "rarity": "mythic", "points": 800, "is_hidden": False, "trigger_type": "family_members", "trigger_value": "50"},
    
    # 储蓄目标进度
    {"code": "family_target_10", "name": "起步向前", "description": "家庭储蓄达到目标的 10%", "category": "family", "icon": "🚶", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "target_percentage", "trigger_value": "10"},
    {"code": "family_target_25", "name": "四分之一", "description": "家庭储蓄达到目标的 25%", "category": "family", "icon": "🏃", "rarity": "common", "points": 40, "is_hidden": False, "trigger_type": "target_percentage", "trigger_value": "25"},
    {"code": "family_target_50", "name": "半路前行", "description": "家庭储蓄达到目标的 50%", "category": "family", "icon": "🎯", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "target_percentage", "trigger_value": "50"},
    {"code": "family_target_75", "name": "曙光在望", "description": "家庭储蓄达到目标的 75%", "category": "family", "icon": "🌅", "rarity": "rare", "points": 120, "is_hidden": False, "trigger_type": "target_percentage", "trigger_value": "75"},
    {"code": "family_target_100", "name": "追梦成功", "description": "家庭储蓄达到目标", "category": "family", "icon": "🏆", "rarity": "epic", "points": 200, "is_hidden": False, "trigger_type": "target_percentage", "trigger_value": "100"},
    {"code": "family_target_150", "name": "超额完成", "description": "家庭储蓄达到目标的 150%", "category": "family", "icon": "🚀", "rarity": "epic", "points": 350, "is_hidden": False, "trigger_type": "target_percentage", "trigger_value": "150"},
    {"code": "family_target_200", "name": "双倍幸福", "description": "家庭储蓄达到目标的 200%", "category": "family", "icon": "🎊", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "target_percentage", "trigger_value": "200"},
    {"code": "family_target_500", "name": "五倍传奇", "description": "家庭储蓄达到目标的 500%", "category": "family", "icon": "⭐", "rarity": "mythic", "points": 1000, "is_hidden": False, "trigger_type": "target_percentage", "trigger_value": "500"},
    
    # 家庭资产里程碑
    {"code": "family_10k", "name": "家庭起步", "description": "家庭总资产超过 1 万", "category": "family", "icon": "🌱", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "10000"},
    {"code": "family_50k", "name": "小康家庭", "description": "家庭总资产超过 5 万", "category": "family", "icon": "🏡", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "50000"},
    {"code": "family_100k", "name": "殷实之家", "description": "家庭总资产超过 10 万", "category": "family", "icon": "🏠", "rarity": "rare", "points": 100, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "100000"},
    {"code": "family_200k", "name": "富裕家庭", "description": "家庭总资产超过 20 万", "category": "family", "icon": "🏢", "rarity": "epic", "points": 180, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "200000"},
    {"code": "family_500k", "name": "财富世家", "description": "家庭总资产超过 50 万", "category": "family", "icon": "🏰", "rarity": "epic", "points": 350, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "500000"},
    {"code": "family_1m", "name": "金窝帝国", "description": "家庭总资产超过 100 万", "category": "family", "icon": "👑", "rarity": "legendary", "points": 800, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "1000000"},
    {"code": "family_2m", "name": "百万家族", "description": "家庭总资产超过 200 万", "category": "family", "icon": "💎", "rarity": "legendary", "points": 1200, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "2000000"},
    {"code": "family_5m", "name": "财富传承", "description": "家庭总资产超过 500 万", "category": "family", "icon": "🌟", "rarity": "mythic", "points": 2000, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "5000000"},
    {"code": "family_10m", "name": "家族传奇", "description": "家庭总资产超过 1000 万", "category": "family", "icon": "✨", "rarity": "mythic", "points": 5000, "is_hidden": False, "trigger_type": "family_total_asset", "trigger_value": "10000000"},
    
    # 全员参与
    {"code": "all_deposited", "name": "全员出动", "description": "所有家庭成员都有存款记录", "category": "family", "icon": "🤲", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "all_members_deposited", "trigger_value": "1"},
    {"code": "family_activity_7", "name": "活力之家", "description": "连续7天家庭有存款活动", "category": "family", "icon": "💫", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "family_activity_streak", "trigger_value": "7"},
    {"code": "family_activity_30", "name": "持续热情", "description": "连续30天家庭有存款活动", "category": "family", "icon": "🔥", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "family_activity_streak", "trigger_value": "30"},
    
    # ==================== 股权类成就 (EQUITY) ====================
    # 股权比例里程碑
    {"code": "has_equity", "name": "股东", "description": "拥有任意股权", "category": "equity", "icon": "📜", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "0.01"},
    {"code": "equity_1", "name": "入门股东", "description": "股权占比达到 1%", "category": "equity", "icon": "🌱", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "1"},
    {"code": "equity_5", "name": "小有份额", "description": "股权占比达到 5%", "category": "equity", "icon": "📊", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "5"},
    {"code": "equity_10", "name": "小股东", "description": "股权占比达到 10%", "category": "equity", "icon": "📈", "rarity": "rare", "points": 30, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "10"},
    {"code": "equity_15", "name": "稳步提升", "description": "股权占比达到 15%", "category": "equity", "icon": "📉", "rarity": "rare", "points": 45, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "15"},
    {"code": "equity_20", "name": "两成股份", "description": "股权占比达到 20%", "category": "equity", "icon": "📌", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "20"},
    {"code": "equity_25", "name": "四分之一", "description": "股权占比达到 25%", "category": "equity", "icon": "🔶", "rarity": "rare", "points": 70, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "25"},
    {"code": "equity_30", "name": "中流砥柱", "description": "股权占比达到 30%", "category": "equity", "icon": "🏋️", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "30"},
    {"code": "equity_40", "name": "实力派", "description": "股权占比达到 40%", "category": "equity", "icon": "💪", "rarity": "epic", "points": 120, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "40"},
    {"code": "equity_50", "name": "大股东", "description": "股权占比达到 50%", "category": "equity", "icon": "🦁", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "50"},
    {"code": "equity_60", "name": "主导力量", "description": "股权占比达到 60%", "category": "equity", "icon": "🏰", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "60"},
    {"code": "equity_70", "name": "绝对控股", "description": "股权占比达到 70%", "category": "equity", "icon": "👑", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "70"},
    {"code": "equity_80", "name": "一家独大", "description": "股权占比达到 80%", "category": "equity", "icon": "🌟", "rarity": "legendary", "points": 400, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "80"},
    {"code": "equity_90", "name": "独占鳌头", "description": "股权占比达到 90%", "category": "equity", "icon": "💎", "rarity": "mythic", "points": 600, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "90"},
    {"code": "equity_100", "name": "全资所有", "description": "股权占比达到 100%", "category": "equity", "icon": "🏛️", "rarity": "mythic", "points": 800, "is_hidden": False, "trigger_type": "equity_percentage", "trigger_value": "100"},
    
    # 股权稳定性
    {"code": "equity_balance", "name": "均衡大师", "description": "所有成员股权差距不超过 5%", "category": "equity", "icon": "⚖️", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "equity_balance", "trigger_value": "5"},
    {"code": "equity_balance_3", "name": "完美平衡", "description": "所有成员股权差距不超过 3%", "category": "equity", "icon": "🎭", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "equity_balance", "trigger_value": "3"},
    {"code": "equity_stable_30", "name": "股权稳定", "description": "股权比例连续30天无变化", "category": "equity", "icon": "🧘", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "equity_stable_days", "trigger_value": "30"},
    {"code": "equity_stable_90", "name": "岿然不动", "description": "股权比例连续90天无变化", "category": "equity", "icon": "🗿", "rarity": "epic", "points": 120, "is_hidden": False, "trigger_type": "equity_stable_days", "trigger_value": "90"},
    {"code": "equity_top_holder", "name": "第一大股东", "description": "成为家庭中股权最高者", "category": "equity", "icon": "🥇", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "top_equity_holder", "trigger_value": "1"},
    {"code": "equity_growth_10", "name": "股权增长", "description": "单月股权增长超过10%", "category": "equity", "icon": "🚀", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "monthly_equity_growth", "trigger_value": "10"},
    
    # 股权赠送
    {"code": "gift_equity", "name": "慷慨解囊", "description": "赠送股权给其他成员", "category": "equity", "icon": "🎁", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "gift_equity", "trigger_value": "1"},
    {"code": "gift_equity_3", "name": "多次馈赠", "description": "累计赠送股权3次", "category": "equity", "icon": "🎀", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "gift_count", "trigger_value": "3"},
    {"code": "gift_equity_5", "name": "分享达人", "description": "累计赠送股权5次", "category": "equity", "icon": "🎗️", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "gift_count", "trigger_value": "5"},
    {"code": "gift_equity_10", "name": "无私奉献", "description": "累计赠送股权超过 10%", "category": "equity", "icon": "💝", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "total_gift_equity", "trigger_value": "10"},
    {"code": "gift_equity_20", "name": "大爱无疆", "description": "累计赠送股权超过 20%", "category": "equity", "icon": "❤️", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "total_gift_equity", "trigger_value": "20"},
    {"code": "receive_gift", "name": "受赠者", "description": "收到他人赠送的股权", "category": "equity", "icon": "📦", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "receive_gift", "trigger_value": "1"},
    {"code": "gift_all_members", "name": "雨露均沾", "description": "向所有其他成员都赠送过股权", "category": "equity", "icon": "🌈", "rarity": "legendary", "points": 250, "is_hidden": False, "trigger_type": "gift_all_members", "trigger_value": "1"},
    
    # ==================== 理财类成就 (INVESTMENT) ====================
    # 理财配置数量
    {"code": "first_investment", "name": "理财新手", "description": "配置第一个理财产品", "category": "investment", "icon": "📊", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "investment_count", "trigger_value": "1"},
    {"code": "investment_2", "name": "双管齐下", "description": "同时持有 2 种理财产品", "category": "investment", "icon": "✌️", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "active_investment_count", "trigger_value": "2"},
    {"code": "investment_3", "name": "投资组合", "description": "同时持有 3 种理财产品", "category": "investment", "icon": "📁", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "active_investment_count", "trigger_value": "3"},
    {"code": "investment_5", "name": "理财达人", "description": "同时持有 5 种理财产品", "category": "investment", "icon": "🎓", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "active_investment_count", "trigger_value": "5"},
    {"code": "investment_8", "name": "理财专家", "description": "同时持有 8 种理财产品", "category": "investment", "icon": "📈", "rarity": "epic", "points": 120, "is_hidden": False, "trigger_type": "active_investment_count", "trigger_value": "8"},
    {"code": "investment_10", "name": "投资王者", "description": "同时持有 10 种理财产品", "category": "investment", "icon": "👑", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "active_investment_count", "trigger_value": "10"},
    {"code": "investment_total_5", "name": "理财老手", "description": "累计配置过 5 个理财产品", "category": "investment", "icon": "📋", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "investment_count", "trigger_value": "5"},
    {"code": "investment_total_10", "name": "投资经验丰富", "description": "累计配置过 10 个理财产品", "category": "investment", "icon": "📚", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "investment_count", "trigger_value": "10"},
    {"code": "investment_total_20", "name": "理财大户", "description": "累计配置过 20 个理财产品", "category": "investment", "icon": "🏦", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "investment_count", "trigger_value": "20"},
    
    # 理财收益
    {"code": "first_income", "name": "首笔收益", "description": "第一次获得理财收益", "category": "investment", "icon": "🌈", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "income_count", "trigger_value": "1"},
    {"code": "income_100", "name": "收益起步", "description": "理财总收益超过 100 元", "category": "investment", "icon": "💵", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "100"},
    {"code": "income_500", "name": "稳定收入", "description": "理财总收益超过 500 元", "category": "investment", "icon": "💴", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "500"},
    {"code": "income_1k", "name": "小有收获", "description": "理财总收益超过 1,000 元", "category": "investment", "icon": "💹", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "1000"},
    {"code": "income_3k", "name": "收益稳健", "description": "理财总收益超过 3,000 元", "category": "investment", "icon": "📊", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "3000"},
    {"code": "income_5k", "name": "理财有道", "description": "理财总收益超过 5,000 元", "category": "investment", "icon": "💰", "rarity": "rare", "points": 100, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "5000"},
    {"code": "income_10k", "name": "投资大师", "description": "理财总收益超过 10,000 元", "category": "investment", "icon": "🏆", "rarity": "epic", "points": 200, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "10000"},
    {"code": "income_30k", "name": "收益精英", "description": "理财总收益超过 30,000 元", "category": "investment", "icon": "💎", "rarity": "epic", "points": 300, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "30000"},
    {"code": "income_50k", "name": "理财高手", "description": "理财总收益超过 50,000 元", "category": "investment", "icon": "🌟", "rarity": "legendary", "points": 400, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "50000"},
    {"code": "income_100k", "name": "财富自由", "description": "理财总收益超过 100,000 元", "category": "investment", "icon": "👑", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "100000"},
    {"code": "income_500k", "name": "投资传奇", "description": "理财总收益超过 500,000 元", "category": "investment", "icon": "✨", "rarity": "mythic", "points": 1000, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "500000"},
    {"code": "income_1m", "name": "财富巅峰", "description": "理财总收益超过 1,000,000 元", "category": "investment", "icon": "🏛️", "rarity": "mythic", "points": 2000, "is_hidden": False, "trigger_type": "total_income", "trigger_value": "1000000"},
    
    # 月度收益
    {"code": "income_100_month", "name": "月入小钱", "description": "单月理财收益超过 100 元", "category": "investment", "icon": "📅", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "monthly_income", "trigger_value": "100"},
    {"code": "income_500_month", "name": "月入稳定", "description": "单月理财收益超过 500 元", "category": "investment", "icon": "📆", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "monthly_income", "trigger_value": "500"},
    {"code": "income_1k_month", "name": "躺赢人生", "description": "单月理财收益超过 1,000 元", "category": "investment", "icon": "🛋️", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "monthly_income", "trigger_value": "1000"},
    {"code": "income_5k_month", "name": "被动收入", "description": "单月理财收益超过 5,000 元", "category": "investment", "icon": "🏖️", "rarity": "legendary", "points": 250, "is_hidden": False, "trigger_type": "monthly_income", "trigger_value": "5000"},
    {"code": "income_10k_month", "name": "月入过万", "description": "单月理财收益超过 10,000 元", "category": "investment", "icon": "🌴", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "monthly_income", "trigger_value": "10000"},
    
    # 本金规模
    {"code": "principal_10k", "name": "初始本金", "description": "理财本金超过 10,000 元", "category": "investment", "icon": "💵", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "total_principal", "trigger_value": "10000"},
    {"code": "principal_50k", "name": "本金积累", "description": "理财本金超过 50,000 元", "category": "investment", "icon": "💰", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "total_principal", "trigger_value": "50000"},
    {"code": "principal_100k", "name": "十万本金", "description": "理财本金超过 100,000 元", "category": "investment", "icon": "🏦", "rarity": "epic", "points": 120, "is_hidden": False, "trigger_type": "total_principal", "trigger_value": "100000"},
    {"code": "principal_500k", "name": "大额理财", "description": "理财本金超过 500,000 元", "category": "investment", "icon": "🏢", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "total_principal", "trigger_value": "500000"},
    {"code": "principal_1m", "name": "百万本金", "description": "理财本金超过 1,000,000 元", "category": "investment", "icon": "🏰", "rarity": "mythic", "points": 600, "is_hidden": False, "trigger_type": "total_principal", "trigger_value": "1000000"},
    
    # 产品多样性
    {"code": "diversified_2", "name": "初步分散", "description": "同时持有 2 种不同类型的理财", "category": "investment", "icon": "🔀", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "investment_type_count", "trigger_value": "2"},
    {"code": "diversified_3", "name": "分散投资", "description": "同时持有 3 种不同类型的理财", "category": "investment", "icon": "📊", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "investment_type_count", "trigger_value": "3"},
    {"code": "diversified_5", "name": "投资多元化", "description": "同时持有 5 种不同类型的理财", "category": "investment", "icon": "🎨", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "investment_type_count", "trigger_value": "5"},
    
    # ==================== 支出类成就 (EXPENSE) ====================
    # 支出申请数量
    {"code": "first_expense", "name": "首次消费", "description": "提交第一笔支出申请", "category": "expense", "icon": "🛍️", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "expense_count", "trigger_value": "1"},
    {"code": "expense_5", "name": "消费常客", "description": "累计提交 5 笔支出申请", "category": "expense", "icon": "🛒", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "expense_count", "trigger_value": "5"},
    {"code": "expense_10", "name": "购物达人", "description": "累计提交 10 笔支出申请", "category": "expense", "icon": "🏪", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "expense_count", "trigger_value": "10"},
    {"code": "expense_20", "name": "消费专家", "description": "累计提交 20 笔支出申请", "category": "expense", "icon": "🏬", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "expense_count", "trigger_value": "20"},
    {"code": "expense_50", "name": "支出大户", "description": "累计提交 50 笔支出申请", "category": "expense", "icon": "🏢", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "expense_count", "trigger_value": "50"},
    {"code": "expense_100", "name": "消费百笔", "description": "累计提交 100 笔支出申请", "category": "expense", "icon": "🏰", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "expense_count", "trigger_value": "100"},
    
    # 支出批准连续
    {"code": "expense_approved_3", "name": "稳定通过", "description": "连续 3 笔支出都被批准", "category": "expense", "icon": "✔️", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "approved_streak", "trigger_value": "3"},
    {"code": "expense_approved_5", "name": "精明消费", "description": "连续 5 笔支出都被批准", "category": "expense", "icon": "✅", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "approved_streak", "trigger_value": "5"},
    {"code": "expense_approved_10", "name": "消费信誉", "description": "连续 10 笔支出都被批准", "category": "expense", "icon": "🏆", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "approved_streak", "trigger_value": "10"},
    {"code": "expense_approved_20", "name": "金牌消费者", "description": "连续 20 笔支出都被批准", "category": "expense", "icon": "👑", "rarity": "legendary", "points": 150, "is_hidden": False, "trigger_type": "approved_streak", "trigger_value": "20"},
    
    # 单笔支出金额
    {"code": "single_expense_100", "name": "小额消费", "description": "单笔支出超过 100 元", "category": "expense", "icon": "💵", "rarity": "common", "points": 5, "is_hidden": False, "trigger_type": "single_expense", "trigger_value": "100"},
    {"code": "expense_500", "name": "中等消费", "description": "单笔支出超过 500 元", "category": "expense", "icon": "💴", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "single_expense", "trigger_value": "500"},
    {"code": "expense_1k", "name": "千元消费", "description": "单笔支出超过 1,000 元", "category": "expense", "icon": "💶", "rarity": "rare", "points": 25, "is_hidden": False, "trigger_type": "single_expense", "trigger_value": "1000"},
    {"code": "expense_5k", "name": "大额消费", "description": "单笔支出超过 5,000 元", "category": "expense", "icon": "💷", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "single_expense", "trigger_value": "5000"},
    {"code": "expense_10k", "name": "大额决策", "description": "单笔支出超过 10,000 元", "category": "expense", "icon": "💳", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "single_expense", "trigger_value": "10000"},
    {"code": "expense_50k", "name": "巨额消费", "description": "单笔支出超过 50,000 元", "category": "expense", "icon": "💎", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "single_expense", "trigger_value": "50000"},
    {"code": "expense_100k", "name": "财大气粗", "description": "单笔支出超过 100,000 元", "category": "expense", "icon": "👑", "rarity": "mythic", "points": 400, "is_hidden": False, "trigger_type": "single_expense", "trigger_value": "100000"},
    
    # 累计支出金额
    {"code": "total_expense_1k", "name": "支出起步", "description": "累计支出超过 1,000 元", "category": "expense", "icon": "💵", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "total_expense", "trigger_value": "1000"},
    {"code": "total_expense_10k", "name": "支出万元", "description": "累计支出超过 10,000 元", "category": "expense", "icon": "💰", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "total_expense", "trigger_value": "10000"},
    {"code": "total_expense_50k", "name": "支出五万", "description": "累计支出超过 50,000 元", "category": "expense", "icon": "🏦", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "total_expense", "trigger_value": "50000"},
    {"code": "total_expense_100k", "name": "支出十万", "description": "累计支出超过 100,000 元", "category": "expense", "icon": "🏢", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "total_expense", "trigger_value": "100000"},
    
    # 审批相关
    {"code": "first_review", "name": "首次审批", "description": "第一次审批他人的支出", "category": "expense", "icon": "📋", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "review_count", "trigger_value": "1"},
    {"code": "review_10", "name": "审批员", "description": "审批 10 次支出", "category": "expense", "icon": "📝", "rarity": "rare", "points": 35, "is_hidden": False, "trigger_type": "review_count", "trigger_value": "10"},
    {"code": "review_50", "name": "资深审批", "description": "审批 50 次支出", "category": "expense", "icon": "📊", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "review_count", "trigger_value": "50"},
    {"code": "reject_expense", "name": "铁面无私", "description": "拒绝过他人的支出申请", "category": "expense", "icon": "🚫", "rarity": "rare", "points": 30, "is_hidden": False, "trigger_type": "reject_count", "trigger_value": "1"},
    {"code": "reject_5", "name": "严格把关", "description": "拒绝 5 次支出申请", "category": "expense", "icon": "✋", "rarity": "epic", "points": 60, "is_hidden": False, "trigger_type": "reject_count", "trigger_value": "5"},
    {"code": "never_reject", "name": "和事佬", "description": "审批 10 次且从未拒绝", "category": "expense", "icon": "🕊️", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "never_reject", "trigger_value": "10"},
    {"code": "never_reject_20", "name": "大善人", "description": "审批 20 次且从未拒绝", "category": "expense", "icon": "😇", "rarity": "legendary", "points": 150, "is_hidden": False, "trigger_type": "never_reject", "trigger_value": "20"},
    
    # 效率相关
    {"code": "quick_approve", "name": "速战速决", "description": "支出申请在 1 小时内获批", "category": "expense", "icon": "⚡", "rarity": "rare", "points": 30, "is_hidden": False, "trigger_type": "quick_approve", "trigger_value": "3600"},
    {"code": "quick_approve_10min", "name": "闪电审批", "description": "支出申请在 10 分钟内获批", "category": "expense", "icon": "⚡", "rarity": "epic", "points": 60, "is_hidden": False, "trigger_type": "quick_approve", "trigger_value": "600"},
    
    # 节俭相关
    {"code": "no_expense_7", "name": "一周节俭", "description": "连续 7 天无支出申请", "category": "expense", "icon": "🌿", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "no_expense_days", "trigger_value": "7"},
    {"code": "no_expense_14", "name": "两周节俭", "description": "连续 14 天无支出申请", "category": "expense", "icon": "🍃", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "no_expense_days", "trigger_value": "14"},
    {"code": "no_expense_30", "name": "节俭之星", "description": "连续 30 天无支出申请", "category": "expense", "icon": "⭐", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "no_expense_days", "trigger_value": "30"},
    {"code": "no_expense_60", "name": "节俭达人", "description": "连续 60 天无支出申请", "category": "expense", "icon": "🌟", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "no_expense_days", "trigger_value": "60"},
    {"code": "no_expense_90", "name": "极简主义", "description": "连续 90 天无支出申请", "category": "expense", "icon": "💎", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "no_expense_days", "trigger_value": "90"},
    
    # ==================== 投票类成就 (VOTE) ====================
    # 投票参与次数
    {"code": "first_vote", "name": "公民意识", "description": "第一次参与投票", "category": "vote", "icon": "🗳️", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "vote_count", "trigger_value": "1"},
    {"code": "vote_5", "name": "投票新手", "description": "参与 5 次投票", "category": "vote", "icon": "✋", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "vote_count", "trigger_value": "5"},
    {"code": "vote_10", "name": "积极分子", "description": "参与 10 次投票", "category": "vote", "icon": "📢", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "vote_count", "trigger_value": "10"},
    {"code": "vote_20", "name": "投票达人", "description": "参与 20 次投票", "category": "vote", "icon": "📣", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "vote_count", "trigger_value": "20"},
    {"code": "vote_30", "name": "投票专家", "description": "参与 30 次投票", "category": "vote", "icon": "📊", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "vote_count", "trigger_value": "30"},
    {"code": "vote_50", "name": "民主先锋", "description": "参与 50 次投票", "category": "vote", "icon": "🏛️", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "vote_count", "trigger_value": "50"},
    {"code": "vote_100", "name": "投票狂热者", "description": "参与 100 次投票", "category": "vote", "icon": "🔥", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "vote_count", "trigger_value": "100"},
    
    # 发起提案
    {"code": "first_proposal", "name": "首次提案", "description": "发起第一个提案", "category": "vote", "icon": "📝", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "proposal_count", "trigger_value": "1"},
    {"code": "proposal_5", "name": "提案达人", "description": "发起 5 个提案", "category": "vote", "icon": "📋", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "proposal_count", "trigger_value": "5"},
    {"code": "proposal_10", "name": "提案专家", "description": "发起 10 个提案", "category": "vote", "icon": "📑", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "proposal_count", "trigger_value": "10"},
    {"code": "proposal_20", "name": "提案大师", "description": "发起 20 个提案", "category": "vote", "icon": "📚", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "proposal_count", "trigger_value": "20"},
    
    # 提案通过
    {"code": "proposal_passed", "name": "提案通过", "description": "发起的提案被通过", "category": "vote", "icon": "✅", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "proposal_passed", "trigger_value": "1"},
    {"code": "proposal_3_passed", "name": "连续成功", "description": "发起的提案被通过 3 次", "category": "vote", "icon": "🎯", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "proposal_passed", "trigger_value": "3"},
    {"code": "proposal_5_passed", "name": "提案高手", "description": "发起的提案被通过 5 次", "category": "vote", "icon": "🏆", "rarity": "epic", "points": 120, "is_hidden": False, "trigger_type": "proposal_passed", "trigger_value": "5"},
    {"code": "proposal_10_passed", "name": "意见领袖", "description": "发起的提案被通过 10 次", "category": "vote", "icon": "👔", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "proposal_passed", "trigger_value": "10"},
    {"code": "proposal_20_passed", "name": "政策制定者", "description": "发起的提案被通过 20 次", "category": "vote", "icon": "👑", "rarity": "mythic", "points": 400, "is_hidden": False, "trigger_type": "proposal_passed", "trigger_value": "20"},
    
    # 特殊投票
    {"code": "decisive_vote", "name": "一锤定音", "description": "你的投票决定了最终结果", "category": "vote", "icon": "⚖️", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "decisive_vote", "trigger_value": "1"},
    {"code": "decisive_vote_3", "name": "关键先生", "description": "3次成为决定性投票", "category": "vote", "icon": "🔑", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "decisive_vote", "trigger_value": "3"},
    {"code": "unanimous", "name": "全票通过", "description": "发起的提案获得全票赞成", "category": "vote", "icon": "🎉", "rarity": "legendary", "points": 150, "is_hidden": False, "trigger_type": "unanimous_proposal", "trigger_value": "1"},
    {"code": "unanimous_3", "name": "众望所归", "description": "3个提案获得全票通过", "category": "vote", "icon": "🌟", "rarity": "mythic", "points": 350, "is_hidden": False, "trigger_type": "unanimous_proposal", "trigger_value": "3"},
    {"code": "against_tide", "name": "逆流而上", "description": "在少数派中投票但提案仍通过", "category": "vote", "icon": "🌊", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "minority_vote", "trigger_value": "1"},
    {"code": "early_voter", "name": "先见之明", "description": "在10分钟内投票的提案获得通过", "category": "vote", "icon": "⚡", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "quick_vote_pass", "trigger_value": "600"},
    
    # 投票参与度
    {"code": "full_participation", "name": "全勤奖", "description": "连续参与 10 个提案的投票", "category": "vote", "icon": "🏅", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "vote_streak", "trigger_value": "10"},
    {"code": "vote_master", "name": "投票大师", "description": "连续参与 20 个提案的投票", "category": "vote", "icon": "🎖️", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "vote_streak", "trigger_value": "20"},
    {"code": "never_miss", "name": "从不缺席", "description": "连续参与 50 个提案的投票", "category": "vote", "icon": "💯", "rarity": "legendary", "points": 250, "is_hidden": False, "trigger_type": "vote_streak", "trigger_value": "50"},
    
    # ==================== 隐藏彩蛋成就 (HIDDEN) ====================
    # 数字寓意
    {"code": "love_520", "name": "我爱你", "description": "存入 520 元", "category": "hidden", "icon": "💕", "rarity": "rare", "points": 52, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "520"},
    {"code": "love_1314", "name": "一生一世", "description": "存入 1314 元", "category": "hidden", "icon": "💍", "rarity": "rare", "points": 131, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "1314"},
    {"code": "lucky_666", "name": "顺顺利利", "description": "存入 666 元", "category": "hidden", "icon": "🍀", "rarity": "rare", "points": 66, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "666"},
    {"code": "lucky_888", "name": "发发发", "description": "存入 888 元", "category": "hidden", "icon": "🧧", "rarity": "rare", "points": 88, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "888"},
    {"code": "lucky_8888", "name": "发财密码", "description": "存入 8888 元", "category": "hidden", "icon": "💰", "rarity": "epic", "points": 188, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "8888"},
    {"code": "love_1999", "name": "要你久久", "description": "存入 1999 元", "category": "hidden", "icon": "💞", "rarity": "rare", "points": 99, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "1999"},
    {"code": "lucky_168", "name": "一路发", "description": "存入 168 元", "category": "hidden", "icon": "🛤️", "rarity": "rare", "points": 68, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "168"},
    {"code": "lucky_518", "name": "我要发", "description": "存入 518 元", "category": "hidden", "icon": "💸", "rarity": "rare", "points": 58, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "518"},
    {"code": "programmer_1024", "name": "程序员情怀", "description": "存入 1024 元", "category": "hidden", "icon": "💻", "rarity": "epic", "points": 102, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "1024"},
    {"code": "binary_256", "name": "二进制大师", "description": "存入 256 元", "category": "hidden", "icon": "🤖", "rarity": "rare", "points": 56, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "256"},
    {"code": "binary_512", "name": "内存升级", "description": "存入 512 元", "category": "hidden", "icon": "🔢", "rarity": "rare", "points": 62, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "512"},
    {"code": "binary_2048", "name": "游戏人生", "description": "存入 2048 元", "category": "hidden", "icon": "🎮", "rarity": "epic", "points": 128, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "2048"},
    {"code": "pi_314", "name": "圆周率先生", "description": "存入 314.15 元", "category": "hidden", "icon": "🥧", "rarity": "epic", "points": 100, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "314.15"},
    {"code": "golden_1618", "name": "黄金比例", "description": "存入 1618 元", "category": "hidden", "icon": "🌀", "rarity": "epic", "points": 118, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "1618"},
    {"code": "answer_42", "name": "答案之书", "description": "存入 42 元", "category": "hidden", "icon": "📖", "rarity": "rare", "points": 42, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "42"},
    {"code": "lucky_777", "name": "幸运数字", "description": "存入 777 元", "category": "hidden", "icon": "🎰", "rarity": "rare", "points": 77, "is_hidden": True, "trigger_type": "exact_deposit", "trigger_value": "777"},
    
    # 时间类彩蛋
    {"code": "early_bird", "name": "早起的鸟儿有虫吃", "description": "在早上 5:00-6:00 操作", "category": "hidden", "icon": "🐦", "rarity": "rare", "points": 30, "is_hidden": True, "trigger_type": "time_range", "trigger_value": "5-6"},
    {"code": "night_owl", "name": "夜猫子", "description": "在凌晨 0:00-1:00 操作", "category": "hidden", "icon": "🦉", "rarity": "rare", "points": 30, "is_hidden": True, "trigger_type": "time_range", "trigger_value": "0-1"},
    {"code": "midnight_snack", "name": "深夜食堂", "description": "在凌晨 3:00-4:00 操作", "category": "hidden", "icon": "🍜", "rarity": "epic", "points": 50, "is_hidden": True, "trigger_type": "time_range", "trigger_value": "3-4"},
    {"code": "on_time", "name": "准时打卡", "description": "在整点操作", "category": "hidden", "icon": "⏰", "rarity": "rare", "points": 25, "is_hidden": True, "trigger_type": "exact_hour", "trigger_value": "0"},
    {"code": "new_year", "name": "元旦快乐", "description": "1月1日操作", "category": "hidden", "icon": "🎉", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "date", "trigger_value": "01-01"},
    {"code": "valentine", "name": "情人节", "description": "2月14日存款", "category": "hidden", "icon": "💝", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "date", "trigger_value": "02-14"},
    {"code": "women_day", "name": "女神节", "description": "3月8日存款", "category": "hidden", "icon": "💐", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "date", "trigger_value": "03-08"},
    {"code": "april_fool", "name": "愚人节", "description": "4月1日操作", "category": "hidden", "icon": "🃏", "rarity": "rare", "points": 40, "is_hidden": True, "trigger_type": "date", "trigger_value": "04-01"},
    {"code": "labor_day", "name": "劳动节", "description": "5月1日存款", "category": "hidden", "icon": "👷", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "date", "trigger_value": "05-01"},
    {"code": "love_day_520", "name": "520表白日", "description": "5月20日存款", "category": "hidden", "icon": "💗", "rarity": "epic", "points": 80, "is_hidden": True, "trigger_type": "date", "trigger_value": "05-20"},
    {"code": "children_day", "name": "儿童节", "description": "6月1日操作", "category": "hidden", "icon": "🧸", "rarity": "rare", "points": 40, "is_hidden": True, "trigger_type": "date", "trigger_value": "06-01"},
    {"code": "programmer_day", "name": "程序员节", "description": "10月24日操作", "category": "hidden", "icon": "👨‍💻", "rarity": "epic", "points": 80, "is_hidden": True, "trigger_type": "date", "trigger_value": "10-24"},
    {"code": "singles_day", "name": "光棍节", "description": "11月11日操作", "category": "hidden", "icon": "🕯️", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "date", "trigger_value": "11-11"},
    {"code": "christmas_eve", "name": "平安夜", "description": "12月24日操作", "category": "hidden", "icon": "🎄", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "date", "trigger_value": "12-24"},
    {"code": "new_year_eve", "name": "跨年夜", "description": "12月31日 23:00 后操作", "category": "hidden", "icon": "🎆", "rarity": "epic", "points": 80, "is_hidden": True, "trigger_type": "date_time", "trigger_value": "12-31-23"},
    
    # 中国传统节日（农历日期用范围覆盖，因每年公历日期不同）
    {"code": "spring_festival", "name": "新春大吉", "description": "春节期间（正月初一至初七）存款", "category": "hidden", "icon": "🧧", "rarity": "epic", "points": 100, "is_hidden": True, "trigger_type": "lunar_date_range", "trigger_value": "1-1/1-7"},
    {"code": "spring_eve", "name": "除夕守岁", "description": "除夕夜（腊月三十或二十九）存款", "category": "hidden", "icon": "🏮", "rarity": "legendary", "points": 150, "is_hidden": True, "trigger_type": "lunar_new_year_eve", "trigger_value": "true"},
    {"code": "lantern_festival", "name": "元宵佳节", "description": "元宵节（正月十五）存款", "category": "hidden", "icon": "🏮", "rarity": "epic", "points": 88, "is_hidden": True, "trigger_type": "lunar_date", "trigger_value": "1-15"},
    {"code": "qingming", "name": "清明时节", "description": "清明节期间（4月4日-4月6日）存款", "category": "hidden", "icon": "🌿", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "date_range", "trigger_value": "04-04/04-06"},
    {"code": "dragon_boat", "name": "端午安康", "description": "端午节期间（5月25日-6月25日）存款", "category": "hidden", "icon": "🐉", "rarity": "epic", "points": 88, "is_hidden": True, "trigger_type": "date_range", "trigger_value": "05-25/06-25"},
    {"code": "qixi", "name": "七夕之约", "description": "七夕情人节存款（8月前后）", "category": "hidden", "icon": "💑", "rarity": "epic", "points": 77, "is_hidden": True, "trigger_type": "date_range", "trigger_value": "08-01/08-31"},
    {"code": "mid_autumn", "name": "中秋团圆", "description": "中秋节期间存款（9-10月）", "category": "hidden", "icon": "🥮", "rarity": "epic", "points": 88, "is_hidden": True, "trigger_type": "date_range", "trigger_value": "09-08/10-08"},
    {"code": "chongyang", "name": "重阳敬老", "description": "重阳节（九月九日前后）存款", "category": "hidden", "icon": "🌼", "rarity": "rare", "points": 60, "is_hidden": True, "trigger_type": "date_range", "trigger_value": "10-01/10-31"},
    {"code": "national_day", "name": "国庆献礼", "description": "国庆节（10月1日-7日）存款", "category": "hidden", "icon": "🇨🇳", "rarity": "epic", "points": 100, "is_hidden": True, "trigger_type": "date_range", "trigger_value": "10-01/10-07"},
    {"code": "laba", "name": "腊八粥香", "description": "腊八节（12月下旬-1月初）存款", "category": "hidden", "icon": "🥣", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "date_range", "trigger_value": "12-20/01-15"},
    {"code": "xiaonian", "name": "小年福至", "description": "小年（腊月二十三、二十四）存款", "category": "hidden", "icon": "🎋", "rarity": "rare", "points": 60, "is_hidden": True, "trigger_type": "lunar_date_range", "trigger_value": "12-23/12-24"},
    
    # 生日与纪念日
    {"code": "birthday_deposit", "name": "生日快乐", "description": "在自己生日当天存款", "category": "hidden", "icon": "🎂", "rarity": "epic", "points": 100, "is_hidden": True, "trigger_type": "birthday", "trigger_value": "true"},
    {"code": "anniversary", "name": "周年纪念", "description": "在注册周年纪念日存款", "category": "hidden", "icon": "🎊", "rarity": "legendary", "points": 150, "is_hidden": True, "trigger_type": "anniversary", "trigger_value": "true"},
    {"code": "first_day_of_month", "name": "开门红", "description": "每月1号存款", "category": "hidden", "icon": "📅", "rarity": "common", "points": 20, "is_hidden": True, "trigger_type": "day_of_month", "trigger_value": "1"},
    {"code": "last_day_of_month", "name": "月末冲刺", "description": "每月最后一天存款", "category": "hidden", "icon": "🏁", "rarity": "rare", "points": 40, "is_hidden": True, "trigger_type": "last_day_of_month", "trigger_value": "true"},
    {"code": "salary_day", "name": "发薪日", "description": "每月15号存款", "category": "hidden", "icon": "💰", "rarity": "common", "points": 25, "is_hidden": True, "trigger_type": "day_of_month", "trigger_value": "15"},
    {"code": "lucky_friday", "name": "幸运星期五", "description": "周五存款10次", "category": "hidden", "icon": "🍀", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "weekday_count", "trigger_value": "4-10"},
    
    # 行为类彩蛋
    {"code": "perfect_balance", "name": "强迫症福音", "description": "账户余额达到整万", "category": "hidden", "icon": "✨", "rarity": "rare", "points": 50, "is_hidden": True, "trigger_type": "balance_pattern", "trigger_value": "10000"},
    {"code": "perfect_number", "name": "完美主义者", "description": "账户余额为 12345.67", "category": "hidden", "icon": "🔢", "rarity": "legendary", "points": 150, "is_hidden": True, "trigger_type": "exact_balance", "trigger_value": "12345.67"},
    {"code": "countdown", "name": "倒计时", "description": "账户余额为 54321", "category": "hidden", "icon": "⏳", "rarity": "epic", "points": 100, "is_hidden": True, "trigger_type": "exact_balance", "trigger_value": "54321"},
    {"code": "palindrome", "name": "轮回", "description": "账户余额首尾相同", "category": "hidden", "icon": "🔄", "rarity": "rare", "points": 60, "is_hidden": True, "trigger_type": "palindrome_balance", "trigger_value": "true"},
    {"code": "consecutive", "name": "连续剧", "description": "账户余额连号", "category": "hidden", "icon": "📺", "rarity": "epic", "points": 80, "is_hidden": True, "trigger_type": "consecutive_balance", "trigger_value": "true"},
    {"code": "bounce_back", "name": "触底反弹", "description": "余额降到100以下后又回到1000以上", "category": "hidden", "icon": "📈", "rarity": "epic", "points": 100, "is_hidden": True, "trigger_type": "bounce_back", "trigger_value": "100-1000"},
    {"code": "explorer", "name": "探险家", "description": "访问过所有功能页面", "category": "hidden", "icon": "🗺️", "rarity": "rare", "points": 40, "is_hidden": True, "trigger_type": "visit_all_pages", "trigger_value": "true"},
    
    # ==================== 特殊成就 (SPECIAL) ====================
    # 成就解锁数量
    {"code": "first_achievement", "name": "开启旅程", "description": "解锁第一个成就", "category": "special", "icon": "🌟", "rarity": "common", "points": 5, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "1"},
    {"code": "achievement_5", "name": "小有成就", "description": "解锁 5 个成就", "category": "special", "icon": "⭐", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "5"},
    {"code": "achievement_10", "name": "初出茅庐", "description": "解锁 10 个成就", "category": "special", "icon": "🎖️", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "10"},
    {"code": "achievement_15", "name": "渐入佳境", "description": "解锁 15 个成就", "category": "special", "icon": "🏵️", "rarity": "common", "points": 45, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "15"},
    {"code": "achievement_20", "name": "驾轻就熟", "description": "解锁 20 个成就", "category": "special", "icon": "🎗️", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "20"},
    {"code": "achievement_25", "name": "成就猎人", "description": "解锁 25 个成就", "category": "special", "icon": "🏅", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "25"},
    {"code": "achievement_30", "name": "三十而立", "description": "解锁 30 个成就", "category": "special", "icon": "🎯", "rarity": "rare", "points": 100, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "30"},
    {"code": "achievement_40", "name": "成就达人", "description": "解锁 40 个成就", "category": "special", "icon": "🏆", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "40"},
    {"code": "achievement_50", "name": "收藏家", "description": "解锁 50 个成就", "category": "special", "icon": "🏆", "rarity": "epic", "points": 200, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "50"},
    {"code": "achievement_60", "name": "成就专家", "description": "解锁 60 个成就", "category": "special", "icon": "💫", "rarity": "epic", "points": 300, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "60"},
    {"code": "achievement_75", "name": "成就狂魔", "description": "解锁 75 个成就", "category": "special", "icon": "💎", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "75"},
    {"code": "achievement_100", "name": "传奇玩家", "description": "解锁 100 个成就", "category": "special", "icon": "👑", "rarity": "legendary", "points": 1000, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "100"},
    {"code": "achievement_150", "name": "成就大师", "description": "解锁 150 个成就", "category": "special", "icon": "🌠", "rarity": "mythic", "points": 1500, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "150"},
    {"code": "achievement_200", "name": "成就之王", "description": "解锁 200 个成就", "category": "special", "icon": "✨", "rarity": "mythic", "points": 2500, "is_hidden": False, "trigger_type": "achievement_count", "trigger_value": "200"},
    {"code": "achievement_all", "name": "神话缔造者", "description": "解锁全部成就", "category": "special", "icon": "🌟", "rarity": "mythic", "points": 5000, "is_hidden": False, "trigger_type": "achievement_all", "trigger_value": "true"},
    
    # 账户年龄
    {"code": "day_7", "name": "一周新人", "description": "注册满 7 天", "category": "special", "icon": "📅", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "7"},
    {"code": "day_30", "name": "月度会员", "description": "注册满 30 天", "category": "special", "icon": "📆", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "30"},
    {"code": "day_90", "name": "季度用户", "description": "注册满 90 天", "category": "special", "icon": "🗓️", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "90"},
    {"code": "day_180", "name": "半年之交", "description": "注册满 180 天", "category": "special", "icon": "📋", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "180"},
    {"code": "year_1", "name": "一周年纪念", "description": "注册满一周年", "category": "special", "icon": "🎂", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "365"},
    {"code": "year_2", "name": "二周年庆", "description": "注册满两周年", "category": "special", "icon": "🎊", "rarity": "epic", "points": 200, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "730"},
    {"code": "year_3", "name": "三年之约", "description": "注册满三周年", "category": "special", "icon": "🎉", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "1095"},
    {"code": "year_5", "name": "活化石", "description": "注册满五周年", "category": "special", "icon": "🦕", "rarity": "mythic", "points": 500, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "1825"},
    {"code": "year_10", "name": "传奇老兵", "description": "注册满十周年", "category": "special", "icon": "🏛️", "rarity": "mythic", "points": 1000, "is_hidden": False, "trigger_type": "account_age", "trigger_value": "3650"},
    
    # 活跃度
    {"code": "login_7", "name": "常客", "description": "连续登录 7 天", "category": "special", "icon": "🔑", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "login_streak", "trigger_value": "7"},
    {"code": "login_30", "name": "活跃用户", "description": "连续登录 30 天", "category": "special", "icon": "🔐", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "login_streak", "trigger_value": "30"},
    {"code": "login_100", "name": "签到达人", "description": "连续登录 100 天", "category": "special", "icon": "📊", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "login_streak", "trigger_value": "100"},
    {"code": "login_365", "name": "铁杆粉丝", "description": "连续登录 365 天", "category": "special", "icon": "🔥", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "login_streak", "trigger_value": "365"},
    
    # 积分相关
    {"code": "points_100", "name": "积分起步", "description": "累计获得 100 积分", "category": "special", "icon": "💯", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "total_points", "trigger_value": "100"},
    {"code": "points_500", "name": "积分新手", "description": "累计获得 500 积分", "category": "special", "icon": "🔢", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "total_points", "trigger_value": "500"},
    {"code": "points_1000", "name": "千分玩家", "description": "累计获得 1000 积分", "category": "special", "icon": "📈", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "total_points", "trigger_value": "1000"},
    {"code": "points_5000", "name": "五千积分", "description": "累计获得 5000 积分", "category": "special", "icon": "📊", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "total_points", "trigger_value": "5000"},
    {"code": "points_10000", "name": "万分玩家", "description": "累计获得 10000 积分", "category": "special", "icon": "🏆", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "total_points", "trigger_value": "10000"},
    {"code": "points_50000", "name": "积分之王", "description": "累计获得 50000 积分", "category": "special", "icon": "👑", "rarity": "mythic", "points": 1000, "is_hidden": False, "trigger_type": "total_points", "trigger_value": "50000"},
    
    # 全面发展
    {"code": "diversified", "name": "多元发展", "description": "在3个类别中都有成就", "category": "special", "icon": "🌈", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "category_count", "trigger_value": "3"},
    {"code": "well_rounded", "name": "全面发展", "description": "在5个类别中都有成就", "category": "special", "icon": "🎨", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "category_count", "trigger_value": "5"},
    {"code": "completionist", "name": "完美主义", "description": "在每个类别中都有成就", "category": "special", "icon": "🌟", "rarity": "legendary", "points": 250, "is_hidden": False, "trigger_type": "all_categories", "trigger_value": "true"},
    
    # 稀有度收集
    {"code": "rare_collector", "name": "稀有收藏", "description": "获得 5 个稀有成就", "category": "special", "icon": "💙", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "rarity_count", "trigger_value": "rare-5"},
    {"code": "epic_collector", "name": "史诗收藏", "description": "获得 5 个史诗成就", "category": "special", "icon": "💜", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "rarity_count", "trigger_value": "epic-5"},
    {"code": "legendary_collector", "name": "传奇收藏", "description": "获得 5 个传奇成就", "category": "special", "icon": "💛", "rarity": "legendary", "points": 250, "is_hidden": False, "trigger_type": "rarity_count", "trigger_value": "legendary-5"},
    {"code": "mythic_collector", "name": "神话收藏", "description": "获得 3 个神话成就", "category": "special", "icon": "❤️", "rarity": "mythic", "points": 500, "is_hidden": False, "trigger_type": "rarity_count", "trigger_value": "mythic-3"},
    
    # ==================== 待办任务类成就 (TODO) ====================
    # 完成任务数量
    {"code": "first_todo", "name": "初试身手", "description": "完成第一个待办任务", "category": "todo", "icon": "✅", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "1"},
    {"code": "todo_5", "name": "起步达人", "description": "累计完成 5 个待办任务", "category": "todo", "icon": "📋", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "5"},
    {"code": "todo_10", "name": "任务新手", "description": "累计完成 10 个待办任务", "category": "todo", "icon": "📝", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "10"},
    {"code": "todo_20", "name": "勤劳小蜜蜂", "description": "累计完成 20 个待办任务", "category": "todo", "icon": "🐝", "rarity": "common", "points": 40, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "20"},
    {"code": "todo_30", "name": "任务达人", "description": "累计完成 30 个待办任务", "category": "todo", "icon": "🎯", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "30"},
    {"code": "todo_50", "name": "执行力专家", "description": "累计完成 50 个待办任务", "category": "todo", "icon": "💪", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "50"},
    {"code": "todo_100", "name": "百事通", "description": "累计完成 100 个待办任务", "category": "todo", "icon": "💯", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "100"},
    {"code": "todo_200", "name": "任务狂人", "description": "累计完成 200 个待办任务", "category": "todo", "icon": "🔥", "rarity": "epic", "points": 250, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "200"},
    {"code": "todo_500", "name": "任务传说", "description": "累计完成 500 个待办任务", "category": "todo", "icon": "⭐", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "500"},
    {"code": "todo_1000", "name": "千任务大师", "description": "累计完成 1000 个待办任务", "category": "todo", "icon": "👑", "rarity": "mythic", "points": 1000, "is_hidden": False, "trigger_type": "todo_complete_count", "trigger_value": "1000"},
    
    # 连续完成任务
    {"code": "todo_streak_3", "name": "三连胜", "description": "连续 3 天都有完成任务", "category": "todo", "icon": "🔥", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "todo_day_streak", "trigger_value": "3"},
    {"code": "todo_streak_7", "name": "周计划达成", "description": "连续 7 天都有完成任务", "category": "todo", "icon": "📅", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "todo_day_streak", "trigger_value": "7"},
    {"code": "todo_streak_14", "name": "双周达人", "description": "连续 14 天都有完成任务", "category": "todo", "icon": "📆", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "todo_day_streak", "trigger_value": "14"},
    {"code": "todo_streak_30", "name": "月度之星", "description": "连续 30 天都有完成任务", "category": "todo", "icon": "🌟", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "todo_day_streak", "trigger_value": "30"},
    {"code": "todo_streak_60", "name": "双月坚持", "description": "连续 60 天都有完成任务", "category": "todo", "icon": "💎", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "todo_day_streak", "trigger_value": "60"},
    {"code": "todo_streak_100", "name": "百日习惯", "description": "连续 100 天都有完成任务", "category": "todo", "icon": "🏆", "rarity": "mythic", "points": 500, "is_hidden": False, "trigger_type": "todo_day_streak", "trigger_value": "100"},
    
    # 准时完成任务（截止日期前完成）
    {"code": "on_time_5", "name": "守时达人", "description": "准时完成 5 个有截止日期的任务", "category": "todo", "icon": "⏰", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "todo_on_time_count", "trigger_value": "5"},
    {"code": "on_time_10", "name": "时间管理者", "description": "准时完成 10 个有截止日期的任务", "category": "todo", "icon": "⏱️", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "todo_on_time_count", "trigger_value": "10"},
    {"code": "on_time_25", "name": "时间大师", "description": "准时完成 25 个有截止日期的任务", "category": "todo", "icon": "🕐", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "todo_on_time_count", "trigger_value": "25"},
    {"code": "on_time_50", "name": "效率之王", "description": "准时完成 50 个有截止日期的任务", "category": "todo", "icon": "👑", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "todo_on_time_count", "trigger_value": "50"},
    
    # 创建清单
    {"code": "first_list", "name": "清单创始人", "description": "创建第一个待办清单", "category": "todo", "icon": "📑", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "todo_list_count", "trigger_value": "1"},
    {"code": "list_3", "name": "多清单管理", "description": "创建 3 个待办清单", "category": "todo", "icon": "📚", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "todo_list_count", "trigger_value": "3"},
    {"code": "list_5", "name": "清单达人", "description": "创建 5 个待办清单", "category": "todo", "icon": "🗂️", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "todo_list_count", "trigger_value": "5"},
    {"code": "list_10", "name": "分类大师", "description": "创建 10 个待办清单", "category": "todo", "icon": "🏛️", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "todo_list_count", "trigger_value": "10"},
    
    # 高优先级任务完成
    {"code": "high_priority_5", "name": "重点突破", "description": "完成 5 个高优先级任务", "category": "todo", "icon": "🚨", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "todo_high_priority_count", "trigger_value": "5"},
    {"code": "high_priority_20", "name": "优先级大师", "description": "完成 20 个高优先级任务", "category": "todo", "icon": "🎖️", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "todo_high_priority_count", "trigger_value": "20"},
    {"code": "high_priority_50", "name": "首要事项专家", "description": "完成 50 个高优先级任务", "category": "todo", "icon": "🥇", "rarity": "legendary", "points": 200, "is_hidden": False, "trigger_type": "todo_high_priority_count", "trigger_value": "50"},
    
    # 团队协作（完成指派给自己的任务）
    {"code": "team_task_5", "name": "好帮手", "description": "完成 5 个指派给自己的任务", "category": "todo", "icon": "🤝", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "todo_assigned_complete", "trigger_value": "5"},
    {"code": "team_task_20", "name": "团队之星", "description": "完成 20 个指派给自己的任务", "category": "todo", "icon": "⭐", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "todo_assigned_complete", "trigger_value": "20"},
    {"code": "team_task_50", "name": "协作大师", "description": "完成 50 个指派给自己的任务", "category": "todo", "icon": "🌟", "rarity": "epic", "points": 120, "is_hidden": False, "trigger_type": "todo_assigned_complete", "trigger_value": "50"},
    
    # ==================== 日历类成就 (CALENDAR) ====================
    # 创建事件数量
    {"code": "first_event", "name": "日历初体验", "description": "创建第一个日历事件", "category": "calendar", "icon": "📅", "rarity": "common", "points": 10, "is_hidden": False, "trigger_type": "calendar_event_count", "trigger_value": "1"},
    {"code": "event_5", "name": "日程安排者", "description": "创建 5 个日历事件", "category": "calendar", "icon": "🗓️", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "calendar_event_count", "trigger_value": "5"},
    {"code": "event_10", "name": "计划达人", "description": "创建 10 个日历事件", "category": "calendar", "icon": "📆", "rarity": "common", "points": 30, "is_hidden": False, "trigger_type": "calendar_event_count", "trigger_value": "10"},
    {"code": "event_20", "name": "时间规划师", "description": "创建 20 个日历事件", "category": "calendar", "icon": "⏰", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "calendar_event_count", "trigger_value": "20"},
    {"code": "event_50", "name": "日程专家", "description": "创建 50 个日历事件", "category": "calendar", "icon": "📊", "rarity": "rare", "points": 80, "is_hidden": False, "trigger_type": "calendar_event_count", "trigger_value": "50"},
    {"code": "event_100", "name": "时间管理大师", "description": "创建 100 个日历事件", "category": "calendar", "icon": "🎯", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "calendar_event_count", "trigger_value": "100"},
    {"code": "event_200", "name": "日历达人", "description": "创建 200 个日历事件", "category": "calendar", "icon": "🏆", "rarity": "legendary", "points": 300, "is_hidden": False, "trigger_type": "calendar_event_count", "trigger_value": "200"},
    
    # 使用系统同步功能
    {"code": "first_sync", "name": "同步启动", "description": "首次使用日历同步功能", "category": "calendar", "icon": "🔄", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "calendar_sync_count", "trigger_value": "1"},
    {"code": "sync_5", "name": "同步习惯", "description": "使用 5 次日历同步功能", "category": "calendar", "icon": "🔁", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "calendar_sync_count", "trigger_value": "5"},
    {"code": "sync_10", "name": "同步达人", "description": "使用 10 次日历同步功能", "category": "calendar", "icon": "♻️", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "calendar_sync_count", "trigger_value": "10"},
    {"code": "sync_30", "name": "同步专家", "description": "使用 30 次日历同步功能", "category": "calendar", "icon": "🌀", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "calendar_sync_count", "trigger_value": "30"},
    
    # 家庭活动类事件
    {"code": "family_event_5", "name": "家庭活动策划者", "description": "创建 5 个家庭活动事件", "category": "calendar", "icon": "🏠", "rarity": "common", "points": 25, "is_hidden": False, "trigger_type": "calendar_family_event_count", "trigger_value": "5"},
    {"code": "family_event_15", "name": "家庭活动达人", "description": "创建 15 个家庭活动事件", "category": "calendar", "icon": "🏡", "rarity": "rare", "points": 60, "is_hidden": False, "trigger_type": "calendar_family_event_count", "trigger_value": "15"},
    {"code": "family_event_30", "name": "家庭活动专家", "description": "创建 30 个家庭活动事件", "category": "calendar", "icon": "🏰", "rarity": "epic", "points": 120, "is_hidden": False, "trigger_type": "calendar_family_event_count", "trigger_value": "30"},
    
    # 生日/纪念日事件
    {"code": "birthday_event_1", "name": "生日记录者", "description": "创建第一个生日/纪念日事件", "category": "calendar", "icon": "🎂", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "calendar_birthday_event_count", "trigger_value": "1"},
    {"code": "birthday_event_5", "name": "纪念日收藏家", "description": "创建 5 个生日/纪念日事件", "category": "calendar", "icon": "🎉", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "calendar_birthday_event_count", "trigger_value": "5"},
    {"code": "birthday_event_10", "name": "重要日子大师", "description": "创建 10 个生日/纪念日事件", "category": "calendar", "icon": "🎊", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "calendar_birthday_event_count", "trigger_value": "10"},
    
    # 添加参与者
    {"code": "invite_participant_5", "name": "邀请达人", "description": "累计邀请 5 位成员参与日历事件", "category": "calendar", "icon": "👋", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "calendar_participant_invite_count", "trigger_value": "5"},
    {"code": "invite_participant_20", "name": "社交策划师", "description": "累计邀请 20 位成员参与日历事件", "category": "calendar", "icon": "👥", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "calendar_participant_invite_count", "trigger_value": "20"},
    {"code": "invite_participant_50", "name": "活动组织者", "description": "累计邀请 50 位成员参与日历事件", "category": "calendar", "icon": "🎪", "rarity": "epic", "points": 100, "is_hidden": False, "trigger_type": "calendar_participant_invite_count", "trigger_value": "50"},
    
    # 重复事件
    {"code": "repeat_event_1", "name": "循环开始", "description": "创建第一个重复事件", "category": "calendar", "icon": "🔁", "rarity": "common", "points": 15, "is_hidden": False, "trigger_type": "calendar_repeat_event_count", "trigger_value": "1"},
    {"code": "repeat_event_5", "name": "规律生活", "description": "创建 5 个重复事件", "category": "calendar", "icon": "🔄", "rarity": "rare", "points": 40, "is_hidden": False, "trigger_type": "calendar_repeat_event_count", "trigger_value": "5"},
    {"code": "repeat_event_10", "name": "习惯养成师", "description": "创建 10 个重复事件", "category": "calendar", "icon": "♾️", "rarity": "epic", "points": 80, "is_hidden": False, "trigger_type": "calendar_repeat_event_count", "trigger_value": "10"},

    # ==================== 宠物类成就 (PET) ====================
    # 进化里程碑
    {"code": "pet_first_evolution", "name": "初次进化", "description": "宠物首次进化（达到 Lv.10）", "category": "special", "icon": "🐣", "rarity": "common", "points": 20, "is_hidden": False, "trigger_type": "pet_level", "trigger_value": "10"},
    {"code": "pet_bird", "name": "展翅高飞", "description": "宠物进化为金凤雏（达到 Lv.30）", "category": "special", "icon": "🐦", "rarity": "rare", "points": 50, "is_hidden": False, "trigger_type": "pet_level", "trigger_value": "30"},
    {"code": "pet_phoenix", "name": "凤凰涅槃", "description": "宠物进化为金凤凰（达到 Lv.60）", "category": "special", "icon": "🦅", "rarity": "epic", "points": 150, "is_hidden": False, "trigger_type": "pet_level", "trigger_value": "60"},
    {"code": "pet_dragon", "name": "龙腾四海", "description": "宠物进化为金龙（达到 Lv.100）", "category": "special", "icon": "🐉", "rarity": "legendary", "points": 500, "is_hidden": False, "trigger_type": "pet_level", "trigger_value": "100"},
    # 陪伴时长
    {"code": "pet_companion_365", "name": "忠实伙伴", "description": "宠物陪伴满 365 天", "category": "special", "icon": "💛", "rarity": "epic", "points": 200, "is_hidden": False, "trigger_type": "pet_age", "trigger_value": "365"},
]


# ==================== 分类名称映射 ====================

CATEGORY_NAMES = {
    "deposit": "存款类",
    "streak": "坚持类",
    "family": "家庭类",
    "equity": "股权类",
    "investment": "理财类",
    "expense": "支出类",
    "vote": "投票类",
    "todo": "待办任务",
    "calendar": "共享日历",
    "hidden": "隐藏彩蛋",
    "special": "特殊成就",
}


# ==================== 成就服务类 ====================

class AchievementService:
    """成就系统服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def init_achievements(self):
        """初始化成就定义（幂等操作，支持并发请求）"""
        from sqlalchemy import text
        
        # 获取已存在的成就code列表
        result = await self.db.execute(select(Achievement.code))
        existing_codes = set(result.scalars().all())
        
        # 如果所有成就都已存在，跳过
        if len(existing_codes) >= len(ACHIEVEMENT_DEFINITIONS):
            return
        
        # 使用原生SQL的 INSERT OR IGNORE 来避免重复插入错误
        for ach_data in ACHIEVEMENT_DEFINITIONS:
            if ach_data["code"] in existing_codes:
                continue  # 已存在，跳过
            
            # 使用 INSERT OR IGNORE 原生SQL
            stmt = text("""
                INSERT OR IGNORE INTO achievements 
                (code, name, description, category, icon, rarity, points, is_hidden, trigger_type, trigger_value, created_at)
                VALUES (:code, :name, :description, :category, :icon, :rarity, :points, :is_hidden, :trigger_type, :trigger_value, :created_at)
            """)
            
            await self.db.execute(stmt, {
                "code": ach_data["code"],
                "name": ach_data["name"],
                "description": ach_data["description"],
                "category": ach_data["category"],
                "icon": ach_data["icon"],
                "rarity": ach_data["rarity"],
                "points": ach_data["points"],
                "is_hidden": 1 if ach_data["is_hidden"] else 0,
                "trigger_type": ach_data["trigger_type"],
                "trigger_value": ach_data.get("trigger_value"),
                "created_at": datetime.utcnow().isoformat(),
            })
        
        await self.db.commit()
    
    async def get_all_definitions(self, include_hidden: bool = False) -> List[Achievement]:
        """获取所有成就定义"""
        query = select(Achievement)
        if not include_hidden:
            query = query.where(Achievement.is_hidden == False)
        result = await self.db.execute(query.order_by(Achievement.category, Achievement.id))
        return result.scalars().all()
    
    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """获取用户已解锁的成就"""
        result = await self.db.execute(
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at.desc())
        )
        return result.scalars().all()
    
    async def has_achievement(self, user_id: int, achievement_code: str) -> bool:
        """检查用户是否已解锁某成就"""
        result = await self.db.execute(
            select(UserAchievement)
            .join(Achievement)
            .where(
                and_(
                    UserAchievement.user_id == user_id,
                    Achievement.code == achievement_code
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def unlock_achievement(self, user_id: int, achievement_code: str, auto_commit: bool = False) -> Optional[UserAchievement]:
        """解锁成就
        
        Args:
            user_id: 用户ID
            achievement_code: 成就代码
            auto_commit: 是否自动提交事务（默认False，由调用方控制）
        """
        # 检查是否已解锁
        if await self.has_achievement(user_id, achievement_code):
            return None
        
        # 获取成就定义
        result = await self.db.execute(
            select(Achievement).where(Achievement.code == achievement_code)
        )
        achievement = result.scalar_one_or_none()
        
        if not achievement:
            return None
        
        # 创建解锁记录
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            unlocked_at=datetime.utcnow()
        )
        self.db.add(user_achievement)
        await self.db.flush()  # 只 flush 不 commit，让调用方控制事务
        
        if auto_commit:
            await self.db.commit()
            await self.db.refresh(user_achievement)
        
        return user_achievement
    
    async def check_and_unlock(self, user_id: int, context: Dict[str, Any] = None) -> List[UserAchievement]:
        """检查并解锁符合条件的成就"""
        new_unlocks = []
        context = context or {}
        
        # 确保成就定义已初始化
        await self.init_achievements()
        
        # 获取所有成就定义
        all_achievements = await self.db.execute(select(Achievement))
        achievements = all_achievements.scalars().all()
        
        # 获取用户已解锁的成就
        unlocked_result = await self.db.execute(
            select(UserAchievement.achievement_id)
            .where(UserAchievement.user_id == user_id)
        )
        unlocked_ids = set(row[0] for row in unlocked_result.fetchall())
        
        # 检查每个未解锁的成就
        for achievement in achievements:
            if achievement.id in unlocked_ids:
                continue
            
            if await self._check_achievement_condition(user_id, achievement, context):
                user_achievement = await self.unlock_achievement(user_id, achievement.code)
                if user_achievement:
                    new_unlocks.append(user_achievement)
        
        return new_unlocks
    
    async def _check_achievement_condition(self, user_id: int, achievement: Achievement, context: Dict[str, Any]) -> bool:
        """检查单个成就条件是否满足"""
        trigger_type = achievement.trigger_type
        trigger_value = achievement.trigger_value
        
        # 存款次数检查
        if trigger_type == "deposit_count":
            result = await self.db.execute(
                select(func.count(Deposit.id)).where(Deposit.user_id == user_id)
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # 累计存款金额检查
        elif trigger_type == "total_deposit":
            result = await self.db.execute(
                select(func.sum(Deposit.amount)).where(Deposit.user_id == user_id)
            )
            total = result.scalar() or 0
            return total >= float(trigger_value)
        
        # 精确存款金额检查（彩蛋）
        elif trigger_type == "exact_deposit":
            if "deposit_amount" in context:
                return abs(context["deposit_amount"] - float(trigger_value)) < 0.01
            return False
        
        # 累计存款天数检查
        elif trigger_type == "deposit_days":
            days = await self._calculate_deposit_days(user_id)
            return days >= int(trigger_value)
        
        # 理财产品数量检查
        elif trigger_type == "investment_count":
            result = await self.db.execute(
                select(func.count(Investment.id))
                .join(FamilyMember, FamilyMember.family_id == Investment.family_id)
                .where(FamilyMember.user_id == user_id)
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # 活跃理财产品数量检查
        elif trigger_type == "active_investment_count":
            result = await self.db.execute(
                select(func.count(Investment.id))
                .join(FamilyMember, FamilyMember.family_id == Investment.family_id)
                .where(
                    and_(
                        FamilyMember.user_id == user_id,
                        Investment.is_active == True
                    )
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # 支出申请数量检查
        elif trigger_type == "expense_count":
            result = await self.db.execute(
                select(func.count(ExpenseRequest.id)).where(ExpenseRequest.requester_id == user_id)
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # 成就解锁数量检查
        elif trigger_type == "achievement_count":
            result = await self.db.execute(
                select(func.count(UserAchievement.id)).where(UserAchievement.user_id == user_id)
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # 时间段检查（彩蛋）
        elif trigger_type == "time_range":
            now = datetime.now()
            start_hour, end_hour = map(int, trigger_value.split("-"))
            return start_hour <= now.hour < end_hour
        
        # 日期检查（彩蛋）
        elif trigger_type == "date":
            now = datetime.now()
            month, day = map(int, trigger_value.split("-"))
            return now.month == month and now.day == day
        
        # 账户年龄检查
        elif trigger_type == "account_age":
            result = await self.db.execute(
                select(User.created_at).where(User.id == user_id)
            )
            created_at = result.scalar()
            if created_at:
                days = (datetime.utcnow() - created_at).days
                return days >= int(trigger_value)
            return False
        
        # ==================== 投票类成就检测 ====================
        elif trigger_type == "vote_count":
            from app.models.models import Vote, Proposal
            result = await self.db.execute(
                select(func.count(Vote.id))
                .join(Proposal, Vote.proposal_id == Proposal.id)
                .join(FamilyMember, FamilyMember.family_id == Proposal.family_id)
                .where(
                    Vote.user_id == user_id,
                    FamilyMember.user_id == user_id
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "proposal_count":
            from app.models.models import Proposal
            result = await self.db.execute(
                select(func.count(Proposal.id)).where(Proposal.creator_id == user_id)
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "proposal_passed":
            from app.models.models import Proposal, ProposalStatus
            result = await self.db.execute(
                select(func.count(Proposal.id)).where(
                    Proposal.creator_id == user_id,
                    Proposal.status == ProposalStatus.PASSED
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # ==================== 签到连续天数检测 ====================
        elif trigger_type == "login_streak":
            from app.models.models import FamilyPet
            # 通过宠物的连续签到天数判断
            result = await self.db.execute(
                select(FamilyPet.checkin_streak)
                .join(FamilyMember, FamilyMember.family_id == FamilyPet.family_id)
                .where(FamilyMember.user_id == user_id)
            )
            streak = result.scalar() or 0
            return streak >= int(trigger_value)
        
        # ==================== 股权赠送检测 ====================
        elif trigger_type == "gift_count":
            from app.models.models import EquityGift, EquityGiftStatus
            result = await self.db.execute(
                select(func.count(EquityGift.id)).where(
                    EquityGift.from_user_id == user_id,
                    EquityGift.status == EquityGiftStatus.ACCEPTED
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "receive_gift":
            from app.models.models import EquityGift, EquityGiftStatus
            result = await self.db.execute(
                select(func.count(EquityGift.id)).where(
                    EquityGift.to_user_id == user_id,
                    EquityGift.status == EquityGiftStatus.ACCEPTED
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # ==================== 单笔存款金额检测 ====================
        elif trigger_type == "single_deposit":
            if "deposit_amount" in context:
                return context["deposit_amount"] >= float(trigger_value)
            return False
        
        # ==================== 理财收益检测 ====================
        elif trigger_type == "income_count":
            from app.models.models import InvestmentIncome
            result = await self.db.execute(
                select(func.count(InvestmentIncome.id))
                .join(Investment, InvestmentIncome.investment_id == Investment.id)
                .join(FamilyMember, FamilyMember.family_id == Investment.family_id)
                .where(FamilyMember.user_id == user_id)
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "total_income":
            from app.models.models import InvestmentIncome
            result = await self.db.execute(
                select(func.sum(InvestmentIncome.amount))
                .join(Investment, InvestmentIncome.investment_id == Investment.id)
                .join(FamilyMember, FamilyMember.family_id == Investment.family_id)
                .where(FamilyMember.user_id == user_id)
            )
            total = result.scalar() or 0
            return total >= float(trigger_value)
        
        elif trigger_type == "monthly_income":
            from app.models.models import InvestmentIncome
            # 统计当月收益
            now = datetime.now()
            start_of_month = datetime(now.year, now.month, 1)
            result = await self.db.execute(
                select(func.sum(InvestmentIncome.amount))
                .join(Investment, InvestmentIncome.investment_id == Investment.id)
                .join(FamilyMember, FamilyMember.family_id == Investment.family_id)
                .where(
                    FamilyMember.user_id == user_id,
                    InvestmentIncome.income_date >= start_of_month
                )
            )
            monthly_total = result.scalar() or 0
            return monthly_total >= float(trigger_value)
        
        elif trigger_type == "total_principal":
            result = await self.db.execute(
                select(func.sum(Investment.principal))
                .join(FamilyMember, FamilyMember.family_id == Investment.family_id)
                .where(
                    FamilyMember.user_id == user_id,
                    Investment.is_active == True
                )
            )
            total = result.scalar() or 0
            return total >= float(trigger_value)
        
        elif trigger_type == "investment_type_count":
            result = await self.db.execute(
                select(func.count(func.distinct(Investment.investment_type)))
                .join(FamilyMember, FamilyMember.family_id == Investment.family_id)
                .where(
                    FamilyMember.user_id == user_id,
                    Investment.is_active == True
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # ==================== 支出类成就检测 ====================
        elif trigger_type == "single_expense":
            if "expense_amount" in context:
                return context["expense_amount"] >= float(trigger_value)
            return False
        
        elif trigger_type == "total_expense":
            from app.models.models import ExpenseStatus
            result = await self.db.execute(
                select(func.sum(ExpenseRequest.amount)).where(
                    ExpenseRequest.requester_id == user_id,
                    ExpenseRequest.status == ExpenseStatus.APPROVED
                )
            )
            total = result.scalar() or 0
            return total >= float(trigger_value)
        
        elif trigger_type == "review_count":
            from app.models.models import ExpenseApproval
            result = await self.db.execute(
                select(func.count(ExpenseApproval.id)).where(
                    ExpenseApproval.approver_id == user_id
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "reject_count":
            from app.models.models import ExpenseApproval
            result = await self.db.execute(
                select(func.count(ExpenseApproval.id)).where(
                    ExpenseApproval.approver_id == user_id,
                    ExpenseApproval.is_approved == False
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "approved_streak":
            from app.models.models import ExpenseStatus
            # 获取用户最近N次支出申请（按ID降序）
            result = await self.db.execute(
                select(ExpenseRequest.status)
                .where(ExpenseRequest.requester_id == user_id)
                .order_by(ExpenseRequest.id.desc())
                .limit(int(trigger_value))
            )
            statuses = result.scalars().all()
            if len(statuses) < int(trigger_value):
                return False
            return all(s == ExpenseStatus.APPROVED for s in statuses)
        
        # ==================== 日期范围检测（彩蛋）====================
        elif trigger_type == "date_range":
            now = datetime.now()
            parts = trigger_value.split("/")
            if len(parts) == 2:
                start_month, start_day = map(int, parts[0].split("-"))
                end_month, end_day = map(int, parts[1].split("-"))
                # 处理跨年情况
                current_date = (now.month, now.day)
                start_date = (start_month, start_day)
                end_date = (end_month, end_day)
                if start_date <= end_date:
                    return start_date <= current_date <= end_date
                else:
                    # 跨年情况，如 12-20 到 01-15
                    return current_date >= start_date or current_date <= end_date
            return False
        
        # ==================== 农历日期检测（精确匹配）====================
        elif trigger_type == "lunar_date":
            try:
                from zhdate import ZhDate
                now = datetime.now()
                lunar = ZhDate.from_datetime(now)
                target_month, target_day = map(int, trigger_value.split("-"))
                return lunar.lunar_month == target_month and lunar.lunar_day == target_day
            except Exception:
                return False
        
        # ==================== 农历日期范围检测 ====================
        elif trigger_type == "lunar_date_range":
            try:
                from zhdate import ZhDate
                now = datetime.now()
                lunar = ZhDate.from_datetime(now)
                parts = trigger_value.split("/")
                if len(parts) == 2:
                    start_month, start_day = map(int, parts[0].split("-"))
                    end_month, end_day = map(int, parts[1].split("-"))
                    current = (lunar.lunar_month, lunar.lunar_day)
                    start = (start_month, start_day)
                    end = (end_month, end_day)
                    if start <= end:
                        return start <= current <= end
                    else:
                        # 跨农历年情况，如 12-23 到 1-7
                        return current >= start or current <= end
                return False
            except Exception:
                return False
        
        # ==================== 除夕检测（特殊处理） ====================
        elif trigger_type == "lunar_new_year_eve":
            try:
                from zhdate import ZhDate
                now = datetime.now()
                lunar = ZhDate.from_datetime(now)
                # 除夕是腊月最后一天（可能是二十九或三十）
                # 方法：检查明天是否是正月初一
                tomorrow = now + timedelta(days=1)
                lunar_tomorrow = ZhDate.from_datetime(tomorrow)
                return lunar_tomorrow.lunar_month == 1 and lunar_tomorrow.lunar_day == 1
            except Exception:
                return False
        
        # ==================== 家庭类成就检测 ====================
        elif trigger_type == "create_family":
            # 通过 context 判断是否刚刚创建了家庭
            if context.get("action") == "create_family":
                return True
            # 或者检查用户是否是某个家庭的 admin（创建者）
            result = await self.db.execute(
                select(FamilyMember).where(
                    FamilyMember.user_id == user_id,
                    FamilyMember.role == "admin"
                )
            )
            return result.scalar_one_or_none() is not None
        
        elif trigger_type == "join_family":
            # 通过 context 判断是否刚刚加入了家庭
            if context.get("action") == "join_family":
                return True
            # 或者检查用户是否是某个家庭的成员（非创建者）
            result = await self.db.execute(
                select(FamilyMember).where(
                    FamilyMember.user_id == user_id,
                    FamilyMember.role == "member"
                )
            )
            return result.scalar_one_or_none() is not None
        
        elif trigger_type == "family_members":
            # 检查用户所在家庭的成员数量
            result = await self.db.execute(
                select(func.count(FamilyMember.id))
                .where(FamilyMember.family_id.in_(
                    select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
                ))
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "invite_count":
            # 用户邀请的成员数量（通过审批记录来判断）
            from app.models.models import ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus, ApprovalRecord
            # 获取用户所在的家庭
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            # 统计该家庭中被批准加入的成员申请（用户审批通过的）
            result = await self.db.execute(
                select(func.count(ApprovalRecord.id))
                .join(ApprovalRequest, ApprovalRecord.request_id == ApprovalRequest.id)
                .where(
                    ApprovalRequest.family_id == family_id,
                    ApprovalRequest.request_type == ApprovalRequestType.MEMBER_JOIN,
                    ApprovalRequest.status == ApprovalRequestStatus.APPROVED,
                    ApprovalRecord.approver_id == user_id,
                    ApprovalRecord.is_approved == True
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # ==================== 待办任务类成就检测 (TODO) ====================
        elif trigger_type == "todo_complete_count":
            # 完成的待办任务数量
            from app.models.models import TodoItem, TodoList
            # 获取用户所在的家庭
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(TodoItem.id))
                .join(TodoList, TodoItem.list_id == TodoList.id)
                .where(
                    TodoList.family_id == family_id,
                    TodoItem.is_completed == True,
                    TodoItem.completed_by == user_id
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "todo_day_streak":
            # 连续完成任务天数
            from app.models.models import TodoItem, TodoList
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            # 获取所有完成日期
            result = await self.db.execute(
                select(func.date(TodoItem.completed_at))
                .join(TodoList, TodoItem.list_id == TodoList.id)
                .where(
                    TodoList.family_id == family_id,
                    TodoItem.is_completed == True,
                    TodoItem.completed_by == user_id,
                    TodoItem.completed_at.isnot(None)
                )
                .distinct()
                .order_by(func.date(TodoItem.completed_at).desc())
            )
            dates = [row[0] for row in result.fetchall()]
            
            if not dates:
                return False
            
            # 检查今天或昨天是否有完成任务
            today = datetime.now().date()
            if dates[0] < today - timedelta(days=1):
                return False
            
            # 计算连续天数
            streak = 1
            for i in range(1, len(dates)):
                if (dates[i-1] - dates[i]).days == 1:
                    streak += 1
                else:
                    break
            
            return streak >= int(trigger_value)
        
        elif trigger_type == "todo_on_time_count":
            # 准时完成的任务数量（有截止日期且在截止日期前完成）
            from app.models.models import TodoItem, TodoList
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(TodoItem.id))
                .join(TodoList, TodoItem.list_id == TodoList.id)
                .where(
                    TodoList.family_id == family_id,
                    TodoItem.is_completed == True,
                    TodoItem.completed_by == user_id,
                    TodoItem.due_date.isnot(None),
                    TodoItem.completed_at <= TodoItem.due_date
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "todo_list_count":
            # 创建的清单数量
            from app.models.models import TodoList
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(TodoList.id))
                .where(
                    TodoList.family_id == family_id,
                    TodoList.created_by == user_id
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "todo_high_priority_count":
            # 完成的高优先级任务数量
            from app.models.models import TodoItem, TodoList
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(TodoItem.id))
                .join(TodoList, TodoItem.list_id == TodoList.id)
                .where(
                    TodoList.family_id == family_id,
                    TodoItem.is_completed == True,
                    TodoItem.completed_by == user_id,
                    TodoItem.priority == "high"
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "todo_assigned_complete":
            # 完成的指派给自己的任务数量
            from app.models.models import TodoItem, TodoList
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(TodoItem.id))
                .join(TodoList, TodoItem.list_id == TodoList.id)
                .where(
                    TodoList.family_id == family_id,
                    TodoItem.is_completed == True,
                    TodoItem.completed_by == user_id,
                    TodoItem.assignee_id == user_id,
                    TodoItem.created_by != user_id  # 不是自己创建的
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        # ==================== 日历类成就检测 (CALENDAR) ====================
        elif trigger_type == "calendar_event_count":
            # 创建的日历事件数量
            from app.models.models import CalendarEvent
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(CalendarEvent.id))
                .where(
                    CalendarEvent.family_id == family_id,
                    CalendarEvent.created_by == user_id
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "calendar_sync_count":
            # 通过 context 传递同步次数
            if "sync_count" in context:
                return context["sync_count"] >= int(trigger_value)
            # 或者查询数据库中的系统生成事件数量（作为同步的代理指标）
            from app.models.models import CalendarEvent
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            # 统计系统生成的事件（is_system = True）
            result = await self.db.execute(
                select(func.count(CalendarEvent.id))
                .where(
                    CalendarEvent.family_id == family_id,
                    CalendarEvent.is_system == True
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "calendar_family_event_count":
            # 创建的家庭活动类事件数量
            from app.models.models import CalendarEvent
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(CalendarEvent.id))
                .where(
                    CalendarEvent.family_id == family_id,
                    CalendarEvent.created_by == user_id,
                    CalendarEvent.category == "family"
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "calendar_birthday_event_count":
            # 创建的生日/纪念日事件数量
            from app.models.models import CalendarEvent
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(CalendarEvent.id))
                .where(
                    CalendarEvent.family_id == family_id,
                    CalendarEvent.created_by == user_id,
                    or_(
                        CalendarEvent.category == "birthday",
                        CalendarEvent.category == "anniversary"
                    )
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "calendar_participant_invite_count":
            # 邀请参与者数量
            from app.models.models import CalendarEvent, CalendarEventParticipant
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            # 统计用户创建的事件中的参与者数量
            result = await self.db.execute(
                select(func.count(CalendarEventParticipant.id))
                .join(CalendarEvent, CalendarEventParticipant.event_id == CalendarEvent.id)
                .where(
                    CalendarEvent.family_id == family_id,
                    CalendarEvent.created_by == user_id
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)
        
        elif trigger_type == "calendar_repeat_event_count":
            # 创建的重复事件数量
            from app.models.models import CalendarEvent, CalendarRepeatType
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            
            result = await self.db.execute(
                select(func.count(CalendarEvent.id))
                .where(
                    CalendarEvent.family_id == family_id,
                    CalendarEvent.created_by == user_id,
                    CalendarEvent.repeat_type != CalendarRepeatType.NONE
                )
            )
            count = result.scalar() or 0
            return count >= int(trigger_value)

        # 宠物等级检查
        elif trigger_type == "pet_level":
            from app.models.models import FamilyPet
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            pet_result = await self.db.execute(
                select(FamilyPet.level).where(FamilyPet.family_id == family_id)
            )
            pet_level = pet_result.scalar()
            if pet_level is None:
                return False
            return pet_level >= int(trigger_value)

        # 宠物年龄检查
        elif trigger_type == "pet_age":
            from app.models.models import FamilyPet
            fm_result = await self.db.execute(
                select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
            )
            family_id = fm_result.scalar()
            if not family_id:
                return False
            pet_result = await self.db.execute(
                select(FamilyPet.created_at).where(FamilyPet.family_id == family_id)
            )
            created_at = pet_result.scalar()
            if created_at is None:
                return False
            age_days = (datetime.now() - created_at).days
            return age_days >= int(trigger_value)

        return False
    
    async def _calculate_deposit_days(self, user_id: int) -> int:
        """计算累计存款天数（不同日期的存款天数总和）"""
        result = await self.db.execute(
            select(func.count(func.distinct(func.date(Deposit.deposit_date))))
            .where(Deposit.user_id == user_id)
        )
        count = result.scalar() or 0
        return count
    
    async def _calculate_deposit_streak(self, user_id: int) -> int:
        """计算连续存款天数（保留用于某些特殊隐藏成就）"""
        result = await self.db.execute(
            select(Deposit.deposit_date)
            .where(Deposit.user_id == user_id)
            .order_by(Deposit.deposit_date.desc())
        )
        dates = [row[0].date() for row in result.fetchall()]
        
        if not dates:
            return 0
        
        # 去重并排序
        unique_dates = sorted(set(dates), reverse=True)
        
        if not unique_dates:
            return 0
        
        # 检查今天或昨天是否有存款
        today = datetime.now().date()
        if unique_dates[0] < today - timedelta(days=1):
            return 0
        
        # 计算连续天数
        streak = 1
        for i in range(1, len(unique_dates)):
            if (unique_dates[i-1] - unique_dates[i]).days == 1:
                streak += 1
            else:
                break
        
        return streak
    
    async def get_progress(self, user_id: int) -> Dict[str, Any]:
        """获取用户成就进度统计"""
        # 获取所有非隐藏成就
        all_result = await self.db.execute(
            select(Achievement).where(Achievement.is_hidden == False)
        )
        all_achievements = all_result.scalars().all()
        
        # 获取用户已解锁成就
        unlocked_result = await self.db.execute(
            select(UserAchievement)
            .join(Achievement)
            .where(UserAchievement.user_id == user_id)
        )
        unlocked = unlocked_result.scalars().all()
        unlocked_ids = {ua.achievement_id for ua in unlocked}
        
        # 计算总分和已得分
        total_points = sum(a.points for a in all_achievements)
        earned_points = sum(
            a.points for a in all_achievements if a.id in unlocked_ids
        )
        
        # 按分类统计
        categories = {}
        for a in all_achievements:
            cat = a.category  # category 现在是字符串类型
            if cat not in categories:
                categories[cat] = {"total": 0, "unlocked": 0}
            categories[cat]["total"] += 1
            if a.id in unlocked_ids:
                categories[cat]["unlocked"] += 1
        
        # 按稀有度统计 (前端需要 by_rarity)
        rarities = {}
        for a in all_achievements:
            rar = a.rarity  # rarity 现在是字符串类型
            if rar not in rarities:
                rarities[rar] = {"total": 0, "unlocked": 0}
            rarities[rar]["total"] += 1
            if a.id in unlocked_ids:
                rarities[rar]["unlocked"] += 1
        
        category_progress = [
            {
                "category": cat,
                "category_name": CATEGORY_NAMES.get(cat, cat),
                "total": data["total"],
                "unlocked": data["unlocked"],
                "percentage": round(data["unlocked"] / data["total"] * 100, 1) if data["total"] > 0 else 0
            }
            for cat, data in categories.items()
        ]
        
        return {
            # 兼容前端字段名
            "unlocked_count": len(unlocked),
            "total_count": len(all_achievements),
            "total_points": earned_points,  # 前端需要的是已获得的点数
            "max_points": total_points,
            "by_rarity": rarities,  # 前端需要的按稀有度统计
            "by_category": categories,  # 前端需要的按分类统计 (对象格式)
            # 保留原有字段，兼容其他可能的调用
            "total_achievements": len(all_achievements),
            "unlocked_achievements": len(unlocked),
            "earned_points": earned_points,
            "percentage": round(len(unlocked) / len(all_achievements) * 100, 1) if all_achievements else 0,
            "categories": category_progress,
        }
