"""
小金库 (Golden Nest) - 错误消息配置
集中管理用户友好的错误提示信息
"""

# ==================== 通用错误消息 ====================

class CommonErrors:
    """通用错误消息"""
    NOT_FOUND = "请求的资源不存在"
    UNAUTHORIZED = "您没有权限执行此操作"
    INVALID_INPUT = "输入数据格式不正确，请检查后重试"
    INTERNAL_ERROR = "服务器内部错误，请稍后重试"
    
    # 家庭相关
    NO_FAMILY = "您还未加入任何家庭，请先创建或加入一个家庭"
    ALREADY_HAS_FAMILY = "您已经加入了一个家庭，每个用户只能加入一个家庭"
    FAMILY_NOT_FOUND = "家庭不存在，请检查邀请码是否正确"
    NOT_ADMIN = "只有家庭管理员才能执行此操作"
    NOT_FAMILY_MEMBER = "指定的用户不是家庭成员"
    
    # 认证相关
    INVALID_CREDENTIALS = "用户名或密码错误，请重试"
    USERNAME_EXISTS = "用户名已被使用，请选择其他用户名"
    EMAIL_EXISTS = "该邮箱已被注册"
    TOKEN_EXPIRED = "登录已过期，请重新登录"
    TOKEN_INVALID = "无效的登录凭证"
    
    # 数据验证
    AMOUNT_MUST_POSITIVE = "金额必须大于0"
    AMOUNT_TOO_LARGE = "金额超出允许范围"
    INVALID_DATE = "日期格式不正确"
    INVALID_DATE_RANGE = "开始日期不能晚于结束日期"


# ==================== 审批系统错误 ====================

class ApprovalErrors:
    """审批系统错误消息"""
    REQUEST_NOT_FOUND = "审批申请不存在或已被删除"
    ALREADY_APPROVED = "您已经对此申请投过票"
    REQUEST_COMPLETED = "此申请已完成审批，无法修改"
    REQUEST_CANCELLED = "此申请已被取消"
    INSUFFICIENT_BALANCE = "家庭余额不足，无法完成支出"
    INVALID_RATIO = "扣减比例总和必须为 100%"
    NOT_REQUESTER = "只有申请人才能取消申请"
    APPROVAL_TIMEOUT = "审批申请已超时，请重新申请"
    
    # 友好提示
    PENDING_APPROVAL = "申请已提交，等待其他成员审批"
    APPROVED_SUCCESS = "您已同意此申请"
    REJECTED_SUCCESS = "您已拒绝此申请"
    CANCELLED_SUCCESS = "申请已取消"


# ==================== 投票系统错误 ====================

class VoteErrors:
    """投票系统错误消息"""
    PROPOSAL_NOT_FOUND = "提案不存在或已被删除"
    PROPOSAL_ENDED = "此提案的投票期已结束"
    PROPOSAL_DEADLINE = "投票已截止，无法继续投票"
    ALREADY_VOTED = "您已经对此提案投过票，每人只能投一次"
    INVALID_OPTION = "选项无效，请选择有效的选项"
    MIN_OPTIONS = "提案至少需要 2 个选项"
    INVALID_DIVIDEND_TYPE = "无效的分红类型，请选择收益分红或现金分红"
    DIVIDEND_AMOUNT_POSITIVE = "分红金额必须大于 0"
    
    # 友好提示
    VOTE_SUCCESS = "投票成功！"
    PROPOSAL_CREATED = "提案已创建，等待家庭成员投票"
    PROPOSAL_PASSED = "提案已通过，开始执行"
    PROPOSAL_FAILED = "提案未通过"


# ==================== 待办清单错误 ====================

class TodoErrors:
    """待办清单错误消息"""
    LIST_NOT_FOUND = "清单不存在或已被删除"
    ITEM_NOT_FOUND = "任务不存在或已被删除"
    ITEM_ALREADY_COMPLETED = "任务已完成，无需重复标记"
    ITEM_NOT_COMPLETED = "任务尚未完成，无法撤销完成状态"
    INVALID_ASSIGNEE = "指派的用户不是家庭成员，请重新选择"
    INVALID_PRIORITY = "无效的优先级，请选择低/中/高"
    INVALID_STATUS = "无效的任务状态"
    
    # 友好提示
    ITEM_COMPLETED_SUCCESS = "任务已标记为完成！"
    ITEM_UNCOMPLETED_SUCCESS = "任务已恢复为未完成状态"
    ITEM_CREATED_SUCCESS = "任务创建成功"


# ==================== 日历系统错误 ====================

class CalendarErrors:
    """日历系统错误消息"""
    EVENT_NOT_FOUND = "日程不存在或已被删除"
    INVALID_REPEAT_TYPE = "无效的重复类型"
    INVALID_CATEGORY = "无效的事件分类"
    EVENT_PAST = "无法创建过去的日程"
    INVALID_END_DATE = "结束时间不能早于开始时间"
    PARTICIPANT_NOT_MEMBER = "参与者必须是家庭成员"
    ALREADY_CONFIRMED = "您已确认参与此活动"
    
    # 友好提示
    EVENT_CREATED = "日程创建成功"
    EVENT_UPDATED = "日程更新成功"
    EVENT_DELETED = "日程已删除"
    CONFIRMED_SUCCESS = "已确认参与"


# ==================== 宠物系统错误 ====================

class PetErrors:
    """宠物系统错误消息"""
    PET_NOT_FOUND = "家庭宠物不存在"
    ALREADY_FED_TODAY = "今天已经喂过此类食物"
    FOOD_COOLDOWN = "食物还在冷却中，请稍后再喂"
    FOOD_DAILY_LIMIT = "今日该食物已达到使用上限"
    GAME_LIMIT_REACHED = "今日游戏次数已达上限，明天再来吧"
    GAME_NOT_FOUND = "游戏会话不存在或已过期"
    GAME_ENDED = "游戏已结束"
    INVALID_GAME_ACTION = "无效的游戏操作"
    INVALID_CARD_POSITION = "无效的翻牌位置"
    CARD_ALREADY_FLIPPED = "该卡牌已被翻开"
    SAME_CARD = "不能翻同一张牌"
    
    # 友好提示
    FED_SUCCESS = "喂食成功，宠物很开心！"
    GAME_WIN = "恭喜获胜！"
    GAME_LOSE = "游戏失败，下次再来"
    EVOLUTION_SUCCESS = "恭喜！宠物进化成功！"


# ==================== 投资理财错误 ====================

class InvestmentErrors:
    """投资理财错误消息"""
    INVESTMENT_NOT_FOUND = "理财产品不存在或已被删除"
    INVESTMENT_INACTIVE = "理财产品已停用"
    INSUFFICIENT_AMOUNT = "投入金额不足"
    AMOUNT_EXCEEDS_PRINCIPAL = "赎回金额不能超过当前本金"
    INVALID_CURRENCY = "不支持的货币类型"
    INVALID_ASSET_TYPE = "无效的资产类型"
    POSITION_NOT_FOUND = "持仓记录不存在"
    INCOME_NEGATIVE = "收益金额不能为负数"
    
    # 友好提示
    INVESTMENT_CREATED = "理财产品创建成功"
    INVESTMENT_UPDATED = "理财产品更新成功"
    INCOME_RECORDED = "收益记录成功"
    INCREASE_SUCCESS = "加仓成功"
    DECREASE_SUCCESS = "赎回成功"


# ==================== 公告系统错误 ====================

class AnnouncementErrors:
    """公告系统错误消息"""
    ANNOUNCEMENT_NOT_FOUND = "公告不存在或已被删除"
    CONTENT_EMPTY = "公告内容不能为空"
    CONTENT_TOO_LONG = "公告内容不能超过 {max_length} 字"
    COMMENT_TOO_LONG = "评论内容不能超过 {max_length} 字"
    COMMENT_NOT_FOUND = "评论不存在或已被删除"
    TOO_MANY_IMAGES = "图片数量不能超过 {max_count} 张"
    
    # 友好提示
    ANNOUNCEMENT_CREATED = "公告发布成功"
    ANNOUNCEMENT_UPDATED = "公告更新成功"
    ANNOUNCEMENT_DELETED = "公告已删除"
    LIKE_SUCCESS = "已点赞"
    UNLIKE_SUCCESS = "已取消点赞"
    COMMENT_SUCCESS = "评论发布成功"


# ==================== 报告系统错误 ====================

class ReportErrors:
    """报告系统错误消息"""
    FUTURE_YEAR = "无法生成未来年份的报告，请选择当前或过去的年份"
    YEAR_TOO_OLD = "年份不能早于 {min_year} 年"
    NO_DATA = "所选时间范围内没有数据"
    REPORT_GENERATING = "报告生成中，请稍候..."
    
    # 友好提示
    REPORT_SUCCESS = "报告生成成功"


# ==================== 成就系统错误 ====================

class AchievementErrors:
    """成就系统错误消息"""
    ACHIEVEMENT_NOT_FOUND = "成就不存在"
    ALREADY_UNLOCKED = "您已解锁此成就"
    CONDITION_NOT_MET = "未满足解锁条件"
    
    # 友好提示
    ACHIEVEMENT_UNLOCKED = "🎉 恭喜解锁成就：{achievement_name}！"
    PROGRESS_UPDATED = "成就进度已更新"


# ==================== 通知系统错误 ====================

class NotificationErrors:
    """通知系统错误消息"""
    WEBHOOK_NOT_CONFIGURED = "未配置企业微信 Webhook URL，请先在家庭设置中配置"
    INVALID_WEBHOOK_URL = "无效的企业微信 Webhook URL，必须以 https://qyapi.weixin.qq.com/ 开头"
    NOTIFICATION_FAILED = "通知发送失败：{reason}"
    RATE_LIMITED = "通知发送频率过高，请稍后再试"
    
    # 友好提示
    TEST_NOTIFICATION_SUCCESS = "测试通知发送成功！"
    NOTIFICATION_SENT = "通知已发送"


# ==================== 资产管理错误 ====================

class AssetErrors:
    """资产管理错误消息"""
    ASSET_NOT_FOUND = "资产不存在或已被删除"
    DUPLICATE_ASSET = "已存在同名资产"
    INVALID_EXCHANGE_RATE = "汇率必须大于 0"
    CURRENCY_MISMATCH = "货币类型不匹配"
    
    # 友好提示
    ASSET_CREATED = "资产登记成功"
    ASSET_UPDATED = "资产更新成功"
    ASSET_DELETED = "资产已删除"


# ==================== 权限错误 ====================

class PermissionErrors:
    """权限相关错误消息"""
    NOT_OWNER = "只有创建者可以执行此操作"
    NOT_ADMIN = "只有管理员可以执行此操作"
    NOT_ASSIGNEE = "只有任务负责人可以标记完成"
    PERMISSION_DENIED = "您没有权限访问此资源"
    
    # 友好提示
    ADMIN_ONLY = "此操作需要管理员权限，请联系家庭管理员"
    OWNER_ONLY = "只有资源创建者可以进行修改或删除"


# ==================== 数据完整性错误 ====================

class DataIntegrityErrors:
    """数据完整性错误"""
    FOREIGN_KEY_VIOLATION = "操作失败：存在关联数据"
    UNIQUE_CONSTRAINT = "数据已存在，不能重复添加"
    INVALID_STATE_TRANSITION = "无效的状态转换"
    CONCURRENT_MODIFICATION = "数据已被其他用户修改，请刷新后重试"
    
    # 友好提示
    DELETE_HAS_REFERENCE = "无法删除：此项被其他数据引用"
    UPDATE_CONFLICT = "更新冲突，请刷新页面后重试"


# ==================== 辅助函数 ====================

def format_error(template: str, **kwargs) -> str:
    """格式化错误消息，填充参数"""
    return template.format(**kwargs)


def get_friendly_error(error_type: str, context: dict = None) -> str:
    """
    获取用户友好的错误消息
    
    Args:
        error_type: 错误类型（如 'NOT_FOUND', 'UNAUTHORIZED'）
        context: 错误上下文信息
    
    Returns:
        格式化的错误消息
    """
    context = context or {}
    
    # 尝试从各个错误类中获取对应的消息
    error_classes = [
        CommonErrors, ApprovalErrors, VoteErrors, TodoErrors,
        CalendarErrors, PetErrors, InvestmentErrors, AnnouncementErrors,
        ReportErrors, AchievementErrors, NotificationErrors, AssetErrors,
        PermissionErrors, DataIntegrityErrors
    ]
    
    for error_class in error_classes:
        if hasattr(error_class, error_type):
            message = getattr(error_class, error_type)
            if context:
                return format_error(message, **context)
            return message
    
    # 如果找不到对应的错误消息，返回通用错误
    return CommonErrors.INTERNAL_ERROR
