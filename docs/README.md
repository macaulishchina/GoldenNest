# 📚 小金库项目文档

本目录包含小金库项目的所有开发、部署和维护文档。

---

## 📑 文档索引

### 🤖 AI 系统
| 文档 | 说明 |
|------|------|
| [AI 功能指南](AI_GUIDE.md) | AI 功能清单、架构、按功能配置模型、开发指南 |
| [DashScope 模型目录](DASHSCOPE_MODELS.md) | 185 个可用模型分类索引和项目推荐选型 |

### 🚀 部署与运维
| 文档 | 说明 |
|------|------|
| [启动脚本使用指南](RUN_SCRIPTS_GUIDE.md) | 服务启动、端口管理、脚本冲突解决 |
| [数据库迁移指南](DATABASE_MIGRATION_GUIDE.md) | 模型修改、Schema 同步、手动迁移 |
| [移动端语音部署](MOBILE_VOICE_DEPLOY.md) | HTTPS 配置、SSL 证书、移动端语音功能 |

### 🔒 安全配置
| 文档 | 说明 |
|------|------|
| [Webhook 加密配置](WEBHOOK_ENCRYPTION_GUIDE.md) | 微信通知 URL 加密存储和迁移 |
| [API 速率限制配置](RATE_LIMITING_GUIDE.md) | 防暴力破解和 API 滥用的限流策略 |

### 🎨 开发参考
| 文档 | 说明 |
|------|------|
| [主题系统开发指南](THEME_GUIDE.md) | 5 套主题定制、CSS 变量、新主题扩展 |
| [代码质量报告](CODE_QUALITY_REPORT.md) | 安全加固、性能优化、代码规范改进记录 |
| [开发历史](DEVELOPMENT_HISTORY.md) | 功能迭代时间线、架构决策、已知限制 |

---

## 🔗 快速导航

| 我想要... | 看这个 |
|-----------|--------|
| 第一次启动项目 | [启动脚本使用指南](RUN_SCRIPTS_GUIDE.md) |
| 了解 AI 功能和配置 | [AI 功能指南](AI_GUIDE.md) |
| 修改数据库模型 | [数据库迁移指南](DATABASE_MIGRATION_GUIDE.md) |
| 部署到手机使用语音 | [移动端语音部署](MOBILE_VOICE_DEPLOY.md) |
| 配置微信通知 | [Webhook 加密配置](WEBHOOK_ENCRYPTION_GUIDE.md) |
| 防止 API 滥用 | [API 速率限制配置](RATE_LIMITING_GUIDE.md) |
| 自定义主题样式 | [主题系统开发指南](THEME_GUIDE.md) |
| 了解项目架构 | [根目录 CLAUDE.md](../CLAUDE.md) |

---

## 📝 文档规范

- **命名格式**：全大写 + 下划线（如 `MY_GUIDE.md`）
- **文档结构**：标题层级清晰，必要时提供目录
- **代码示例**：使用代码块并标注语言
- **交叉引用**：文档间使用相对链接互相关联

---

返回 [项目主页](../README.md) · 架构参考 [CLAUDE.md](../CLAUDE.md)
