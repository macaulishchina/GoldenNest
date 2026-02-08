"""
外汇汇率服务 - 获取和缓存实时汇率
"""
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import httpx
import logging
from enum import Enum

from app.models.models import CurrencyType


logger = logging.getLogger(__name__)


class ExchangeRateSource(str, Enum):
    """汇率数据源"""
    EXCHANGERATE_API = "https://api.exchangerate-api.com/v4/latest/CNY"
    FRANKFURTER = "https://api.frankfurter.app/latest?from=CNY"
    # 可添加更多备用源


class ExchangeRateService:
    """外汇汇率服务"""
    
    def __init__(self):
        self.cache: Dict[str, Tuple[float, datetime]] = {}  # {currency: (rate, timestamp)}
        self.cache_duration = timedelta(hours=1)  # 缓存 1 小时
        self.primary_source = ExchangeRateSource.EXCHANGERATE_API
        self.fallback_source = ExchangeRateSource.FRANKFURTER
    
    async def get_rate_to_cny(self, from_currency: CurrencyType) -> float:
        """
        获取汇率：外币 → 人民币
        
        Args:
            from_currency: 外币类型（USD/HKD/JPY等）
            
        Returns:
            汇率（1单位外币 = X 人民币）
            
        Examples:
            USD: 7.20 (1美元 = 7.20人民币)
            JPY: 0.048 (1日元 = 0.048人民币)
        """
        if from_currency == CurrencyType.CNY:
            return 1.0
        
        # 检查缓存
        cache_key = from_currency.value
        if cache_key in self.cache:
            rate, timestamp = self.cache[cache_key]
            if datetime.utcnow() - timestamp < self.cache_duration:
                logger.debug(f"Using cached rate for {from_currency}: {rate}")
                return rate
        
        # 从 API 获取
        try:
            rate = await self._fetch_rate_from_api(from_currency)
            self.cache[cache_key] = (rate, datetime.utcnow())
            logger.info(f"Fetched rate for {from_currency}: {rate}")
            return rate
        except Exception as e:
            logger.error(f"Failed to fetch rate for {from_currency}: {e}")
            
            # 尝试使用旧缓存
            if cache_key in self.cache:
                rate, _ = self.cache[cache_key]
                logger.warning(f"Using stale cached rate for {from_currency}: {rate}")
                return rate
            
            # 使用兜底汇率
            fallback = self._get_fallback_rate(from_currency)
            logger.warning(f"Using fallback rate for {from_currency}: {fallback}")
            return fallback
    
    async def _fetch_rate_from_api(self, from_currency: CurrencyType) -> float:
        """从 API 获取汇率"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                # 主数据源
                response = await client.get(self.primary_source.value)
                response.raise_for_status()
                data = response.json()
                
                # exchangerate-api.com 返回格式: {"base": "CNY", "rates": {"USD": 0.139, ...}}
                # 我们需要反向计算: 1 USD = 1/0.139 = 7.19 CNY
                cny_to_foreign = data["rates"].get(from_currency.value)
                if cny_to_foreign:
                    return 1.0 / cny_to_foreign
                
            except Exception as e:
                logger.warning(f"Primary source failed: {e}, trying fallback")
                
                # 备用数据源
                response = await client.get(self.fallback_source.value)
                response.raise_for_status()
                data = response.json()
                
                # frankfurter.app 返回格式类似
                cny_to_foreign = data["rates"].get(from_currency.value)
                if cny_to_foreign:
                    return 1.0 / cny_to_foreign
            
            raise ValueError(f"Currency {from_currency} not found in API response")
    
    def _get_fallback_rate(self, currency: CurrencyType) -> float:
        """获取兜底汇率（硬编码的近似值）"""
        fallback_rates = {
            CurrencyType.USD: 7.20,
            CurrencyType.HKD: 0.92,
            CurrencyType.JPY: 0.048,
            CurrencyType.EUR: 7.85,
            CurrencyType.GBP: 9.15,
            CurrencyType.AUD: 4.75,
            CurrencyType.CAD: 5.30,
            CurrencyType.SGD: 5.35,
            CurrencyType.KRW: 0.0055,
        }
        return fallback_rates.get(currency, 1.0)
    
    @staticmethod
    def calculate_weighted_rate(
        old_foreign_amount: float,
        old_rate: float,
        new_foreign_amount: float,
        new_rate: float
    ) -> float:
        """
        计算加权平均汇率
        
        Args:
            old_foreign_amount: 原有外币金额
            old_rate: 原有汇率
            new_foreign_amount: 新增外币金额
            new_rate: 新增汇率
            
        Returns:
            加权平均汇率
            
        Example:
            已有 $500 @7.20, 新买 $300 @7.30
            → (500*7.20 + 300*7.30) / 800 = 7.2375
        """
        total_foreign = old_foreign_amount + new_foreign_amount
        if total_foreign == 0:
            return 0
        
        total_cny = old_foreign_amount * old_rate + new_foreign_amount * new_rate
        return total_cny / total_foreign
    
    @staticmethod
    def format_foreign_amount(amount: float, currency: CurrencyType) -> str:
        """格式化外币金额显示"""
        symbols = {
            CurrencyType.CNY: "¥",
            CurrencyType.USD: "$",
            CurrencyType.HKD: "HK$",
            CurrencyType.JPY: "¥",
            CurrencyType.EUR: "€",
            CurrencyType.GBP: "£",
            CurrencyType.AUD: "A$",
            CurrencyType.CAD: "C$",
            CurrencyType.SGD: "S$",
            CurrencyType.KRW: "₩",
        }
        symbol = symbols.get(currency, "")
        
        # JPY 和 KRW 不显示小数
        if currency in [CurrencyType.JPY, CurrencyType.KRW]:
            return f"{symbol}{amount:,.0f}"
        
        return f"{symbol}{amount:,.2f}"


# 全局单例
exchange_rate_service = ExchangeRateService()
