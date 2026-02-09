"""
小金库 (Golden Nest) - 业务常量配置
集中管理系统中的魔法数字，便于维护和调整
"""

# ==================== 时间相关常量 ====================

class TimeConstants:
    """时间相关常量"""
    DAYS_PER_YEAR = 365
    DAYS_PER_WEEK = 7
    DAYS_PER_MONTH = 30  # 近似值
    HOURS_PER_DAY = 24
    MINUTES_PER_HOUR = 60
    SECONDS_PER_MINUTE = 60


# ==================== 内容长度限制 ====================

class ContentLimits:
    """内容长度限制"""
    # 公告系统
    ANNOUNCEMENT_MAX_LENGTH = 2000  # 公告内容最大长度（字符）
    COMMENT_MAX_LENGTH = 500        # 评论内容最大长度（字符）
    
    # URL 显示
    WEBHOOK_URL_MASK_LENGTH = 50    # Webhook URL 脱敏显示长度
    WEBHOOK_URL_PREFIX_LENGTH = 40  # 保留前缀长度
    WEBHOOK_URL_SUFFIX_LENGTH = 8   # 保留后缀长度


# ==================== 股权计算常量 ====================

class EquityConstants:
    """股权计算相关常量"""
    DEFAULT_ANNUAL_RATE = 0.03      # 默认年化利率 3%
    DEFAULT_SAVINGS_TARGET = 2000000.0  # 默认储蓄目标 200万
    
    # 股权比例阈值
    EQUITY_MAJORITY = 0.5           # 过半股权（50%）
    EQUITY_ABSOLUTE_CONTROL = 0.67  # 绝对控股（67%）


# ==================== 成就里程碑 ====================

class AchievementMilestones:
    """成就系统的里程碑数值"""
    
    # 存款金额里程碑
    DEPOSIT_1K = 1000
    DEPOSIT_2K = 2000
    DEPOSIT_5K = 5000
    DEPOSIT_10K = 10000
    DEPOSIT_20K = 20000
    DEPOSIT_30K = 30000
    DEPOSIT_50K = 50000
    DEPOSIT_100K = 100000
    DEPOSIT_200K = 200000
    DEPOSIT_500K = 500000
    DEPOSIT_1M = 1000000
    
    # 存款次数里程碑
    DEPOSIT_COUNT_5 = 5
    DEPOSIT_COUNT_10 = 10
    DEPOSIT_COUNT_20 = 20
    DEPOSIT_COUNT_30 = 30
    DEPOSIT_COUNT_50 = 50
    DEPOSIT_COUNT_100 = 100
    DEPOSIT_COUNT_200 = 200
    DEPOSIT_COUNT_500 = 500
    DEPOSIT_COUNT_1000 = 1000
    
    # 连续天数里程碑
    STREAK_7_DAYS = 7
    STREAK_14_DAYS = 14
    STREAK_30_DAYS = 30
    STREAK_60_DAYS = 60
    STREAK_90_DAYS = 90
    STREAK_180_DAYS = 180
    STREAK_365_DAYS = 365
    STREAK_500_DAYS = 500
    STREAK_1000_DAYS = 1000
    
    # 家庭成员数里程碑
    FAMILY_SIZE_2 = 2
    FAMILY_SIZE_3 = 3
    FAMILY_SIZE_5 = 5
    FAMILY_SIZE_8 = 8
    FAMILY_SIZE_10 = 10


# ==================== 宠物系统常量 ====================

class PetConstants:
    """宠物养成系统常量"""
    
    # 宠物进化等级阈值
    EVOLUTION_EGG_MIN = 1
    EVOLUTION_EGG_MAX = 9
    EVOLUTION_CHICK_MIN = 10
    EVOLUTION_CHICK_MAX = 29
    EVOLUTION_BIRD_MIN = 30
    EVOLUTION_BIRD_MAX = 59
    EVOLUTION_PHOENIX_MIN = 60
    EVOLUTION_PHOENIX_MAX = 99
    EVOLUTION_DRAGON_MIN = 100
    EVOLUTION_DRAGON_MAX = 999
    
    # 经验值奖励
    EXP_DAILY_CHECKIN = 10          # 每日签到
    EXP_STREAK_BONUS = 5            # 连续签到奖励
    EXP_DEPOSIT = 20                # 存款操作
    EXP_INVESTMENT = 15             # 理财操作
    EXP_VOTE = 10                   # 投票操作
    EXP_PROPOSAL_PASSED = 50        # 提案通过
    EXP_EXPENSE_APPROVED = 20       # 支出审批
    EXP_GIFT_SENT = 30              # 赠送股权
    EXP_ACHIEVEMENT_UNLOCK = 25     # 解锁成就
    
    # 待办任务经验
    EXP_TODO_LOW = 5                # 完成低优先级任务
    EXP_TODO_MEDIUM = 10            # 完成中优先级任务
    EXP_TODO_HIGH = 15              # 完成高优先级任务
    EXP_TODO_ON_TIME_BONUS = 5      # 准时完成奖励
    EXP_TODO_ASSIGNED = 8           # 完成指派任务
    
    # 日历事件经验
    EXP_CALENDAR_PERSONAL = 8       # 创建个人日程
    EXP_CALENDAR_FAMILY = 15        # 创建家庭活动
    EXP_CALENDAR_BIRTHDAY = 20      # 创建生日/纪念日
    EXP_CALENDAR_FINANCE = 10       # 创建财务提醒
    EXP_CALENDAR_REPEAT_BONUS = 5   # 重复事件奖励
    EXP_CALENDAR_PARTICIPANT = 2    # 每邀请1位参与者
    EXP_CALENDAR_SYNC = 5           # 同步系统事件
    EXP_CALENDAR_SYNC_PER_EVENT = 2 # 每同步1个事件
    
    # 喂食系统
    FOOD_BASIC_HAPPINESS = 10       # 普通饲料心情值
    FOOD_BASIC_EXP = 3              # 普通饲料经验
    FOOD_BASIC_COOLDOWN = 2         # 普通饲料冷却时间（小时）
    
    FOOD_PREMIUM_HAPPINESS = 25     # 高级饲料心情值
    FOOD_PREMIUM_EXP = 8            # 高级饲料经验
    FOOD_PREMIUM_DAILY_LIMIT = 3    # 高级饲料每日限制
    FOOD_PREMIUM_COOLDOWN = 4       # 高级饲料冷却时间（小时）
    
    FOOD_LUXURY_HAPPINESS = 50      # 豪华大餐心情值
    FOOD_LUXURY_EXP = 20            # 豪华大餐经验
    FOOD_LUXURY_DAILY_LIMIT = 1     # 豪华大餐每日限制
    FOOD_LUXURY_COOLDOWN = 4        # 豪华大餐冷却时间（小时）
    
    # 心情系统
    HAPPINESS_HIGH_THRESHOLD = 80   # 高心情阈值
    HAPPINESS_MEDIUM_THRESHOLD = 50 # 中等心情阈值
    HAPPINESS_LOW_THRESHOLD = 20    # 低心情阈值
    
    HAPPINESS_MULTIPLIER_HIGH = 1.2  # 高心情经验倍率
    HAPPINESS_MULTIPLIER_MEDIUM = 1.0 # 中等心情经验倍率
    HAPPINESS_MULTIPLIER_LOW = 0.8   # 低心情经验倍率
    HAPPINESS_MULTIPLIER_VERY_LOW = 0.5  # 极低心情经验倍率
    
    HAPPINESS_DECAY_PER_DAY = 10    # 每日心情衰减值
    
    # 小游戏系统
    DAILY_GAME_LIMIT = 10           # 每日游戏次数限制
    GAME_EXP_MIN = 5                # 游戏最低经验
    GAME_EXP_MAX = 1000             # 游戏最高经验


# ==================== 通知系统常量 ====================

class NotificationConstants:
    """通知系统相关常量"""
    REMINDER_DAYS_BEFORE_DUE = 7    # 到期前几天提醒
    BATCH_NOTIFICATION_SIZE = 50    # 批量通知大小
    NOTIFICATION_RETRY_TIMES = 3    # 通知重试次数


# ==================== 投票系统常量 ====================

class VoteConstants:
    """投票系统相关常量"""
    DEFAULT_DEADLINE_DAYS = 7       # 默认投票期限（天）
    MIN_PROPOSAL_OPTIONS = 2        # 提案最少选项数
    MAX_PROPOSAL_OPTIONS = 10       # 提案最多选项数


# ==================== 审批系统常量 ====================

class ApprovalConstants:
    """审批系统相关常量"""
    AUTO_APPROVE_THRESHOLD = 1000   # 小额自动审批阈值（可配置）
    APPROVAL_TIMEOUT_DAYS = 30      # 审批超时天数
    REMINDER_THRESHOLD_HOURS = 24   # 提醒阈值（小时）


# ==================== 投资理财常量 ====================

class InvestmentConstants:
    """投资理财相关常量"""
    DEFAULT_CURRENCY = "CNY"        # 默认货币
    MIN_INVESTMENT_AMOUNT = 100     # 最小投资金额
    MAX_INVESTMENT_AMOUNT = 10000000  # 最大投资金额
    
    # 汇率相关
    USD_TO_CNY_DEFAULT = 7.20       # 美元对人民币默认汇率
    EUR_TO_CNY_DEFAULT = 7.85       # 欧元对人民币默认汇率
    HKD_TO_CNY_DEFAULT = 0.92       # 港币对人民币默认汇率
    JPY_TO_CNY_DEFAULT = 0.048      # 日元对人民币默认汇率
    GBP_TO_CNY_DEFAULT = 9.10       # 英镑对人民币默认汇率
    CAD_TO_CNY_DEFAULT = 5.30       # 加元对人民币默认汇率


# ==================== API 速率限制常量 ====================

class RateLimitConstants:
    """API 速率限制配置"""
    # 认证相关
    LOGIN_LIMIT = "5/minute"
    REGISTER_LIMIT = "3/hour"
    
    # 家庭管理
    CREATE_FAMILY_LIMIT = "1/hour"
    JOIN_FAMILY_LIMIT = "5/hour"
    TEST_NOTIFICATION_LIMIT = "10/hour"
    
    # 审批系统
    DEPOSIT_APPROVAL_LIMIT = "30/hour"
    EXPENSE_APPROVAL_LIMIT = "20/day"
    ASSET_APPROVAL_LIMIT = "50/day"
    APPROVE_REQUEST_LIMIT = "100/hour"
    
    # 投票系统
    CREATE_PROPOSAL_LIMIT = "20/day"
    CREATE_DIVIDEND_PROPOSAL_LIMIT = "10/day"
    CAST_VOTE_LIMIT = "50/hour"
    
    # 公告系统
    CREATE_ANNOUNCEMENT_LIMIT = "50/day"
    LIKE_ANNOUNCEMENT_LIMIT = "100/hour"


# ==================== 缓存时间常量 ====================

class CacheConstants:
    """缓存相关时间常量（秒）"""
    CACHE_SHORT = 60                # 短期缓存（1分钟）
    CACHE_MEDIUM = 300              # 中期缓存（5分钟）
    CACHE_LONG = 3600               # 长期缓存（1小时）
    CACHE_DAY = 86400               # 日缓存（24小时）


# ==================== 分页常量 ====================

class PaginationConstants:
    """分页相关常量"""
    DEFAULT_PAGE_SIZE = 20          # 默认每页数量
    MAX_PAGE_SIZE = 100             # 最大每页数量
    DEFAULT_PAGE = 1                # 默认页码


# ==================== 文件上传常量 ====================

class UploadConstants:
    """文件上传相关常量"""
    MAX_AVATAR_SIZE = 2 * 1024 * 1024      # 最大头像大小 2MB
    MAX_IMAGE_SIZE = 5 * 1024 * 1024       # 最大图片大小 5MB
    MAX_ANNOUNCEMENT_IMAGES = 9            # 公告最多图片数
    
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ALLOWED_AVATAR_EXTENSIONS = ['.jpg', '.jpeg', '.png']


# ==================== 财务目标常量 ====================

class FinancialGoalConstants:
    """财务目标相关常量"""
    TARGET_PERCENTAGE_50 = 50       # 达到目标50%
    TARGET_PERCENTAGE_100 = 100     # 达到目标100%
    TARGET_PERCENTAGE_150 = 150     # 达到目标150%
    TARGET_PERCENTAGE_200 = 200     # 达到目标200%
    TARGET_PERCENTAGE_500 = 500     # 达到目标500%
