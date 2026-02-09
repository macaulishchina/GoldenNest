# API 速率限制配置

## 概述

为了防止 API 滥用和保护系统资源，Golden Nest 对关键端点实施了速率限制（Rate Limiting）。

## 实现方案

- **库**: `slowapi` (基于 Flask-Limiter)
- **存储**: 内存存储（单实例部署）
- **标识**: 基于客户端 IP 地址
- **响应**: 超出限制返回 `429 Too Many Requests`

## 速率限制配置

### 🔐 认证相关

| 端点 | 限制 | 说明 |
|------|------|------|
| `POST /api/auth/login` | 5/分钟 | 防止暴力破解登录 |
| `POST /api/auth/register` | 3/小时 | 防止批量注册账号 |

### 👨‍👩‍👧‍👦 家庭管理

| 端点 | 限制 | 说明 |
|------|------|------|
| `POST /api/family/create` | 1/小时 | 每用户每小时只能创建1个家庭 |
| `POST /api/family/join` | 5/小时 | 限制家庭加入申请频率 |
| `POST /api/family/notification/test` | 10/小时 | 限制测试通知发送次数 |

### 💰 审批系统

| 端点 | 限制 | 说明 |
|------|------|------|
| `POST /api/approval/deposit` | 30/小时 | 存款申请限制 |
| `POST /api/approval/expense` | 20/天 | 支出申请限制 |
| `POST /api/approval/asset/create` | 50/天 | 资产登记申请限制 |
| `POST /api/approval/{id}/approve` | 100/小时 | 审批操作限制 |

### 🗳️ 投票系统

| 端点 | 限制 | 说明 |
|------|------|------|
| `POST /api/vote/proposals` | 20/天 | 创建普通提案限制 |
| `POST /api/vote/proposals/dividend` | 10/天 | 创建分红提案限制 |
| `POST /api/vote/proposals/{id}/vote` | 50/小时 | 投票操作限制 |

### 📢 公告系统

| 端点 | 限制 | 说明 |
|------|------|------|
| `POST /api/announcements` | 50/天 | 发布公告限制 |
| `POST /api/announcements/{id}/like` | 100/小时 | 点赞操作限制 |

## 速率限制响应

当用户超出速率限制时，API 将返回：

```json
{
  "error": "Rate limit exceeded: 5 per 1 minute"
}
```

**HTTP 状态码**: `429 Too Many Requests`

**响应头**:
- `X-RateLimit-Limit`: 限制数量
- `X-RateLimit-Remaining`: 剩余请求数
- `X-RateLimit-Reset`: 限制重置时间（Unix 时间戳）

## 设计原则

### 1. 按操作风险分级

| 风险级别 | 限制策略 | 示例操作 |
|----------|----------|----------|
| 🔴 高风险 | 严格限制 (1-5次/小时) | 创建家庭、注册、登录 |
| 🟡 中风险 | 中等限制 (10-50次/小时或天) | 存款、支出、创建提案 |
| 🟢 低风险 | 宽松限制 (50-100次/小时) | 投票、点赞、审批 |

### 2. 时间窗口选择

- **分钟级**: 高敏感操作（登录）
- **小时级**: 频繁但需控制的操作（存款、投票）
- **天级**: 低频重要操作（创建提案、支出）

### 3. 限制数值设计

基于正常使用场景估算：
- **家庭成员**: 通常 2-6 人
- **日常活跃度**: 每天 5-20 次操作
- **异常行为阈值**: 超过正常使用 5-10 倍

## 配置示例

### 添加新的速率限制

```python
from app.main import limiter
from fastapi import APIRouter

router = APIRouter()

@router.post("/example")
@limiter.limit("10/hour")  # 每小时10次
async def example_endpoint():
    pass
```

### 多层级限制

```python
@router.post("/example")
@limiter.limit("100/day")   # 每天100次
@limiter.limit("10/hour")   # 且每小时10次
async def example_endpoint():
    pass
```

### 豁免特定用户

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

def key_func():
    # 自定义限制键，可根据用户角色等调整
    return get_remote_address()

limiter = Limiter(key_func=key_func)
```

## 生产环境建议

### 1. 使用 Redis 存储

```python
# app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)
```

### 2. 基于用户 ID 限制

对于需要认证的端点，建议基于用户 ID 而非 IP：

```python
def get_user_id():
    # 从请求中提取用户 ID
    return request.state.user.id

limiter = Limiter(key_func=get_user_id)
```

### 3. 动态限制

根据用户等级、会员状态等动态调整限制：

```python
@router.post("/premium-feature")
async def premium_endpoint(current_user: User = Depends(get_current_user)):
    # VIP 用户可能有更高的限制
    if current_user.is_vip:
        limit = "100/hour"
    else:
        limit = "10/hour"
    
    @limiter.limit(limit)
    async def _handler():
        pass
    
    return await _handler()
```

## 监控和调优

### 查看限制状态

可以通过日志监控速率限制触发情况：

```python
import logging

logger = logging.getLogger(__name__)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {request.client.host} on {request.url.path}")
    return JSONResponse(
        status_code=429,
        content={"error": str(exc.detail)}
    )
```

### 调优建议

1. **初期宽松**: 上线初期可以设置较宽松的限制，收集真实使用数据
2. **逐步收紧**: 根据 99% 用户的使用模式设置合理限制
3. **A/B 测试**: 对不同限制策略进行测试，找到最佳平衡点
4. **用户反馈**: 关注因速率限制导致的用户投诉

## 相关文件

- [main.py](backend/app/main.py) - Limiter 初始化
- [auth.py](backend/app/api/auth.py) - 认证端点限制
- [family.py](backend/app/api/family.py) - 家庭管理限制
- [approval.py](backend/app/api/approval.py) - 审批系统限制
- [vote.py](backend/app/api/vote.py) - 投票系统限制
- [announcement.py](backend/app/api/announcement.py) - 公告系统限制

## 常见问题

### Q: 如何测试速率限制？

A: 可以使用 curl 或 httpie 快速发送多个请求：

```bash
# 快速发送 10 个登录请求测试限制
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}'
done
```

### Q: 本地开发时限制太严格怎么办？

A: 可以在开发环境禁用或放宽限制：

```python
# app/main.py
import os

if os.getenv("ENVIRONMENT") == "development":
    limiter.enabled = False
```

### Q: 分布式部署如何处理？

A: 必须使用 Redis 或其他集中式存储，否则每个实例独立计数，限制会失效。

## 更新日志

- **2026-02-09**: 实施全面的速率限制策略
  - 为 12 个关键端点添加速率限制
  - 涵盖认证、家庭、审批、投票、公告等模块
