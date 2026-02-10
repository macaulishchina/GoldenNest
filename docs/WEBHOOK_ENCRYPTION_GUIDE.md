# Webhook URL 加密迁移指南

## 概述

为了提高安全性，企业微信 Webhook URL 现在会以加密形式存储在数据库中。本指南介绍如何迁移现有的明文 Webhook URL。

## 为什么需要加密？

企业微信 Webhook URL 包含敏感的访问令牌，如果以明文形式存储：
- 数据库泄露会直接暴露这些令牌
- 可能被用于未授权的消息发送
- 违反安全最佳实践

通过加密存储，即使数据库被泄露，攻击者也无法直接使用这些 Webhook URL。

## 加密实现

### 加密算法
- 使用 Fernet 对称加密（基于 AES-128-CBC）
- 每个 URL 独立加密
- 加密密钥从环境变量读取

### 涉及的文件
- `backend/app/core/encryption.py` - 加密服务模块
- `backend/app/core/config.py` - 配置（包含 ENCRYPTION_KEY）
- `backend/app/api/family.py` - Family API（存储/读取加密数据）
- `backend/migrate_encrypt_webhooks.py` - 数据迁移脚本

## 迁移步骤

### 1. 生成加密密钥

首先需要生成一个加密密钥：

```bash
# Windows
cd backend
python -m app.core.encryption

# Linux/Mac
cd backend
python3 -m app.core.encryption
```

这会输出一个密钥，例如：
```
生成的加密密钥（请保存到 .env 文件）：
ENCRYPTION_KEY=abc123xyz...
```

### 2. 配置加密密钥

将生成的密钥添加到 `.env` 文件：

```env
# .env 文件
DATABASE_URL=sqlite+aiosqlite:///./golden_nest.db
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=abc123xyz...  # 添加这一行
```

**重要提示：**
- 密钥必须保密，不要提交到 Git
- 如果密钥丢失，已加密的数据将无法恢复
- 建议将密钥备份到安全的地方

### 3. 运行迁移脚本

**迁移前建议备份数据库：**

```bash
# Windows
copy golden_nest.db golden_nest.db.backup

# Linux/Mac
cp golden_nest.db golden_nest.db.backup
```

运行迁移：

```bash
# Windows
cd backend
python migrate_encrypt_webhooks.py

# Linux/Mac
cd backend
python3 migrate_encrypt_webhooks.py
```

### 4. 验证迁移结果

脚本会自动验证加密是否成功。输出示例：

```
============================================================
Webhook URL 加密迁移工具
============================================================
开始迁移 Webhook URLs...
找到 2 个家庭有 Webhook URL 配置
✓ 家庭 1 (张家) 的 Webhook 已加密
✓ 家庭 2 (李家) 的 Webhook 已加密

✓ 已提交 2 个加密更新到数据库

============================================================
迁移完成！
  成功加密: 2 个
  已跳过: 0 个
  错误: 0 个
============================================================

开始验证迁移...
✓ 家庭 1 (张家) 验证通过
✓ 家庭 2 (李家) 验证通过

✓ 所有 Webhook URL 验证通过！

✓ 迁移成功完成！
```

## 常见问题

### Q: 迁移脚本可以多次运行吗？

A: 可以。脚本会自动检测已加密的数据并跳过，不会重复加密。

### Q: 如果迁移失败怎么办？

A: 
1. 检查 `.env` 文件中的 `ENCRYPTION_KEY` 是否正确配置
2. 确保数据库文件有写入权限
3. 查看错误日志了解具体原因
4. 如需回滚，使用备份的数据库文件

### Q: 更改密钥后怎么办？

A: 如果更改了 `ENCRYPTION_KEY`：
1. 旧的加密数据将无法解密
2. 需要使用旧密钥先解密，再用新密钥重新加密
3. 建议不要轻易更改密钥

### Q: 开发环境和生产环境使用同一个密钥吗？

A: 不应该。每个环境应该使用独立的密钥，确保环境隔离。

## 技术细节

### 加密流程

**存储时（family.py line ~359）：**
```python
if config_data.wechat_webhook_url:
    # 加密后存储
    family.wechat_webhook_url = encrypt_sensitive_data(config_data.wechat_webhook_url)
```

**读取时（family.py line ~312-318）：**
```python
if family.wechat_webhook_url:
    try:
        decrypted_webhook = decrypt_sensitive_data(family.wechat_webhook_url)
    except Exception:
        # 兼容旧数据（未加密）
        decrypted_webhook = family.wechat_webhook_url
```

### 向后兼容

代码包含向后兼容逻辑：
- 如果解密失败，假定是旧的明文数据，直接使用
- 这样在迁移过程中不会中断服务
- 迁移完成后，所有数据都将是加密格式

### 性能影响

- 加密/解密操作非常快（微秒级）
- 对 API 响应时间影响可忽略
- 不会显著增加 CPU 负载

## 安全最佳实践

1. **密钥管理**
   - 使用环境变量存储密钥
   - 不要在代码中硬编码
   - 定期轮换密钥（需要重新加密数据）

2. **备份策略**
   - 迁移前备份数据库
   - 安全存储密钥备份
   - 测试恢复流程

3. **访问控制**
   - 限制对 `.env` 文件的访问
   - 生产环境使用不同的密钥
   - 审计密钥的使用情况

## 相关文件

- [encryption.py](backend/app/core/encryption.py) - 加密服务实现
- [family.py](backend/app/api/family.py) - Webhook 配置 API
- [migrate_encrypt_webhooks.py](backend/migrate_encrypt_webhooks.py) - 迁移脚本
- [config.py](backend/app/core/config.py) - 应用配置
