# Golden Nest Backend Dockerfile
# 使用国内镜像源加速拉取
FROM docker.1ms.run/library/python:3.11-slim

WORKDIR /app

# 配置 apt 使用国内镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 配置 pip 使用国内镜像源并安装 Python 依赖
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制应用代码
COPY app ./app

# 创建数据目录
RUN mkdir -p /data

# 设置环境变量
ENV DATABASE_URL=sqlite+aiosqlite:///data/golden_nest.db
ENV SECRET_KEY=your-super-secret-key-change-in-production

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]