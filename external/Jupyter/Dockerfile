# JupyterLab 容器 (Level 1 - 数据分析平台)
# 基于 Python 3.12 slim，从本地 conda 环境迁移全部依赖

FROM docker.1ms.run/library/python:3.12-slim

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# 使用国内镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set install.trusted-host mirrors.aliyun.com

# 安装依赖（从 requirements.txt，与本地 conda 环境一致）
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# 工作目录
WORKDIR /workspace

# 环境变量（可被 docker-compose 覆盖）
ENV JUPYTER_PORT=8888
ENV JUPYTER_BASE_URL=/jupyter/
ENV JUPYTER_TOKEN=""

EXPOSE 8888

# 启动 JupyterLab
CMD ["sh", "-c", "\
    jupyter lab \
    --no-browser \
    --ip=0.0.0.0 \
    --port=${JUPYTER_PORT} \
    --allow-root \
    --ServerApp.base_url=${JUPYTER_BASE_URL} \
    --ServerApp.root_dir=/workspace \
    --ServerApp.allow_origin='*' \
    --ServerApp.allow_remote_access=True \
    --ServerApp.token=${JUPYTER_TOKEN} \
    --ServerApp.password='' \
    --ServerApp.tornado_settings='{\"headers\": {\"Content-Security-Policy\": \"frame-ancestors *\"}}' \
"]
