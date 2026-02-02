# 🏠 小金库 Golden Nest

**家庭财富共创计划** - 一款以"股份所有制"方式管理家庭储蓄的 Web 应用

[![Vue 3](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 项目简介

小金库是一款专为家庭设计的储蓄管理工具，将家庭储蓄比作"小型家庭企业"：
- 每位家庭成员的存款都转化为"股权"
- 采用**时间加权复利算法**激励早期存款
- 理财收益按股权比例分红
- 大额支出需要全员审批
- 丰富的趣味互动功能增强家庭凝聚力

## 🚀 核心功能

### 💰 资金管理
| 功能 | 描述 |
|------|------|
| 资金注入 | 随时存入资金，系统自动记录并计算股权 |
| 支出申请 | 大额支出需发起申请，全体成员投票审批 |
| 资金流水 | 查看完整的存入/支出/分红明细记录 |

### 📈 投资理财
| 功能 | 描述 |
|------|------|
| 理财产品 | 配置家庭理财产品，登记收益并按股权分红 |
| 年度报告 | 年末自动生成财务总结、收支分析、股权变化报告 |

### 🏢 家庭事务
| 功能 | 描述 |
|------|------|
| 家庭管理 | 创建/加入家庭，管理成员，设置储蓄目标 |
| 股权结构 | 实时计算各成员股权占比，直观可视化展示 |
| 股权赠与 | 成员间可互赠股权，记录赠予历史 |
| 股东大会 | 发起投票提案，全员同意才能通过（一票否决制）|

### ✨ 趣味互动
| 功能 | 描述 |
|------|------|
| 🐾 家庭宠物 | 养成家庭吉祥物，通过签到/存款/投资获得经验升级进化 |
| 📢 家庭公告 | 发布家庭内部公告，支持点赞、评论、置顶 |
| 🏆 成就殿堂 | 50+ 成就徽章，记录家庭理财里程碑 |

## 🎮 成就系统

系统内置丰富的成就徽章，涵盖多个类别：

| 类别 | 示例成就 |
|------|----------|
| 💰 储蓄成就 | 首次存款、万元户、十万大户、百万富翁 |
| 📊 股权成就 | 股权过半、绝对控股 |
| 👨‍👩‍👧‍👦 家庭成就 | 创建家庭、邀请成员、大家族 |
| 🐾 宠物成就 | 宠物升级、宠物进化、满级宠物 |
| 📅 签到成就 | 连续签到7天、30天、365天 |
| 🎁 赠与成就 | 首次赠与、慷慨馈赠 |
| ✅ 投票成就 | 首次投票、民主先锋 |

## 🐾 宠物养成系统

每个家庭可以养育一只吉祥物，见证家庭的成长：

```
🥒 黄瓜虫 (Lv.1-9)
    ↓ 进化
🐛 毛毛虫 (Lv.10-19)
    ↓ 进化
🦋 花蝴蝶 (Lv.20-29)
    ↓ 进化
🐉 彩虹龙 (Lv.30+)
```

**经验获取途径：**
- 每日签到：+10 EXP
- 存款操作：+5 EXP
- 理财收益：+10 EXP
- 投票参与：+3 EXP
- 发布公告：+2 EXP

## � 股权计算公式

系统采用时间加权复利模式计算股权：

```
加权金额 = 原始金额 × (1 + 年化利率)^存入年数

股权占比 = 个人加权总额 ÷ 全家加权总额 × 100%
```

**示例**：
- 小明 1 年前存入 10 万，加权金额 = 100,000 × 1.03¹ = 103,000
- 小红 刚存入 10 万，加权金额 = 100,000 × 1.03⁰ = 100,000
- 小明股权占比 = 103,000 ÷ 203,000 ≈ 50.74%

## 🛠️ 技术栈

### 后端
- **FastAPI** - 现代高性能 Python Web 框架
- **SQLAlchemy 2.0** - ORM 数据库映射
- **SQLite** - 轻量级数据库（支持异步）
- **JWT** - 安全的用户认证

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全
- **Naive UI** - 精美的 Vue 3 组件库
- **Pinia** - 状态管理
- **Vite** - 极速构建工具

## 📦 快速开始

### 方式一：Docker 部署（推荐）

#### Windows 用户
```cmd
# 克隆项目
git clone https://github.com/macaulishchina/GoldenNest.git
cd golden-nest

# 配置Docker镜像源（解决连接问题）
# 1. 打开 Docker Desktop -> Settings -> Docker Engine
# 2. 复制项目根目录中的 daemon.json 内容到配置框
# 3. 点击 Apply & Restart

# 复制环境变量配置（可选）
copy .env.example .env

# 一键构建并启动
build-cn.bat

# 访问 http://localhost:8088
```

#### Linux 用户
```bash
# 克隆项目
git clone https://github.com/macaulishchina/GoldenNest.git
cd golden-nest

# 自动配置Docker镜像源
sudo ./setup-docker-mirrors.sh

# 复制环境变量配置（可选）
cp .env.example .env

# 一键构建并启动
chmod +x build.sh
./build.sh

# 访问 http://localhost:8088
```

#### 手动方式
```bash
# 如果遇到网络问题，项目已针对国内环境优化
docker-compose build --no-cache
docker-compose up -d

# 访问 http://localhost:8088
```

### 方式二：本地开发

#### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8000
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173

## 📁 项目结构

```
golden-nest/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API 路由
│   │   │   ├── auth.py         # 认证接口
│   │   │   ├── deposit.py      # 存款接口
│   │   │   ├── expense.py      # 支出接口
│   │   │   ├── investment.py   # 理财接口
│   │   │   ├── vote.py         # 投票接口
│   │   │   ├── pet.py          # 宠物接口
│   │   │   ├── announcement.py # 公告接口
│   │   │   ├── achievement.py  # 成就接口
│   │   │   ├── gift.py         # 赠予接口
│   │   │   └── report.py       # 报告接口
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic 模式
│   │   ├── services/       # 业务逻辑
│   │   │   └── achievement.py  # 成就触发服务
│   │   └── main.py         # 应用入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # 前端代码
│   ├── src/
│   │   ├── api/            # API 接口
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # 状态管理
│   │   └── views/          # 页面组件
│   │       ├── Dashboard.vue   # 仪表盘
│   │       ├── Deposit.vue     # 资金注入
│   │       ├── Expense.vue     # 支出申请
│   │       ├── Investment.vue  # 理财管理
│   │       ├── Transaction.vue # 资金流水
│   │       ├── Family.vue      # 家庭管理
│   │       ├── Equity.vue      # 股权结构
│   │       ├── Vote.vue        # 股东大会
│   │       ├── Pet.vue         # 家庭宠物
│   │       ├── Announcement.vue# 家庭公告
│   │       ├── Achievement.vue # 成就殿堂
│   │       ├── Gift.vue        # 股权赠与
│   │       └── Report.vue      # 年度报告
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔒 安全说明

- 使用 JWT 进行身份认证
- 密码使用 bcrypt 加密存储
- 生产环境请务必修改 SECRET_KEY
- 建议使用 HTTPS

## 📄 开源协议

MIT License

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📮 联系方式

如有问题或建议，欢迎通过 Issue 反馈。

---

**小金库** - 让家庭储蓄变得有趣又透明 🎉

> 💡 小贴士：坚持每日签到，不仅能获得成就，还能让家庭宠物快速成长哦！