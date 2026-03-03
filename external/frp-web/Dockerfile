# FRP Web 配置客户端
# 轻量 Python 后端 + 内嵌 frpc 二进制

FROM docker.1ms.run/library/python:3.12-alpine

# 安装 frpc
ARG FRP_VERSION=0.61.1
RUN apk add --no-cache curl && \
    ARCH=$(uname -m) && \
    case "$ARCH" in \
      x86_64) FRP_ARCH="amd64" ;; \
      aarch64) FRP_ARCH="arm64" ;; \
      armv7l) FRP_ARCH="arm" ;; \
      *) echo "Unsupported arch: $ARCH" && exit 1 ;; \
    esac && \
    curl -fsSL "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_${FRP_ARCH}.tar.gz" \
      | tar -xz --strip-components=1 -C /usr/bin/ "frp_${FRP_VERSION}_linux_${FRP_ARCH}/frpc" && \
    chmod +x /usr/bin/frpc && \
    apk del curl

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .
COPY static/ static/

# 配置文件挂载点
RUN mkdir -p /etc/frp

ENV FRP_CONFIG_DIR=/etc/frp
ENV FRPC_BIN=/usr/bin/frpc

EXPOSE 8156

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8156", "--proxy-headers", "--forwarded-allow-ips", "*"]
