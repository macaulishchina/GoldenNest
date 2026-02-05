"""
通用 Schema 定义
包含时间范围筛选等通用功能
"""
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pydantic import BaseModel


class TimeRange(str, Enum):
    """时间范围枚举"""
    DAY = "day"           # 最近一天
    WEEK = "week"         # 最近一周
    MONTH = "month"       # 最近一个月
    YEAR = "year"         # 最近一年
    ALL = "all"           # 全部


def get_time_range_filter(time_range: TimeRange) -> Optional[datetime]:
    """
    根据时间范围枚举返回起始时间
    
    Args:
        time_range: 时间范围枚举值
        
    Returns:
        起始时间，如果是 ALL 则返回 None
    """
    now = datetime.now()
    
    if time_range == TimeRange.DAY:
        return now - timedelta(days=1)
    elif time_range == TimeRange.WEEK:
        return now - timedelta(weeks=1)
    elif time_range == TimeRange.MONTH:
        return now - timedelta(days=30)
    elif time_range == TimeRange.YEAR:
        return now - timedelta(days=365)
    else:  # ALL
        return None


def get_time_range_dates(time_range: TimeRange) -> Tuple[Optional[datetime], datetime]:
    """
    根据时间范围返回起止时间元组
    
    Returns:
        (start_time, end_time) 元组
    """
    end_time = datetime.now()
    start_time = get_time_range_filter(time_range)
    return start_time, end_time
