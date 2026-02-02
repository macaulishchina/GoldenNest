# 🏠 小金库 Golden Nest

**家庭财富共创计划** - 一款以"股份所有制"方式管理家庭储蓄的 Web 应用

[![Vue 3](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript)](https://www.typescriptlang.org/)

## ✨ 项目简介

小金库是一款专为家庭设计的储蓄管理工具，将家庭储蓄比作"小型家庭企业"：
- 每位家庭成员的存款都转化为"股权"
- 采用**时间加权复利算法**激励早期存款
- 理财收益按股权比例分红
- 大额支出需要全员审批

## 🚀 核心功能

### 💰 资金管理
- 随时存入资金，系统自动记录
- 查看完整的资金流水明细
- 理财产品配置与收益登记

### 📊 股权计算
- **3% 年化复利权重**：早存入的钱有更多"话语权"
- 实时计算各成员股权占比
- 直观的股权分布可视化

### 🎯 目标追踪
- 设定家庭储蓄目标（默认 200 万）
- 进度条实时显示完成百分比
- 里程碑提醒和庆祝

### 📝 支出审批
- 大额支出需发起申请
- 全体成员投票审批
- 审批通过后自动扣减相应股权

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

```bash
# 克隆项目
git clone https://github.com/your-username/golden-nest.git
cd golden-nest

# 复制环境变量配置
cp .env.example .env

# 编辑 .env 文件，修改 SECRET_KEY
nano .env

# 启动服务
docker-compose up -d

# 访问 http://localhost
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
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic 模式
│   │   ├── services/       # 业务逻辑
│   │   └── main.py         # 应用入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # 前端代码
│   ├── src/
│   │   ├── api/            # API 接口
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # 状态管理
│   │   └── views/          # 页面组件
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🎨 股权计算公式

系统采用时间加权复利模式计算股权：

```
加权金额 = 原始金额 × (1 + 年化利率)^存入年数

股权占比 = 个人加权总额 ÷ 全家加权总额 × 100%
```

**示例**：
- 小明 1 年前存入 10 万，加权金额 = 100,000 × 1.03¹ = 103,000
- 小红 刚存入 10 万，加权金额 = 100,000 × 1.03⁰ = 100,000
- 小明股权占比 = 103,000 ÷ 203,000 ≈ 50.74%

## 🔒 安全说明

- 使用 JWT 进行身份认证
- 密码使用 bcrypt 加密存储
- 生产环境请务必修改 SECRET_KEY
- 建议使用 HTTPS

## 📄 开源协议

MIT License

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

---

**小金库** - 让家庭储蓄变得有趣又透明 🎉
