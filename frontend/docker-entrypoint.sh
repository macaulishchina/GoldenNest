#!/bin/sh
# 根据是否存在 SSL 证书自动选择 nginx 配置
# 有证书 → HTTPS 模式（nginx.ssl.conf）
# 无证书 → HTTP 模式（nginx.conf）

SSL_CERT="/etc/nginx/ssl/cert.pem"
SSL_KEY="/etc/nginx/ssl/key.pem"

if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    echo "✅ SSL 证书已找到，启用 HTTPS 模式"
    # 使用 envsubst 替换环境变量（如 HTTPS_PORT）
    envsubst '${HTTPS_PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
else
    echo "⚠️  未找到 SSL 证书，使用 HTTP 模式（语音功能仅在 localhost 可用）"
    echo "   如需 HTTPS，请运行: bash generate_ssl.sh <你的IP>"
    cp /etc/nginx/templates/http-only.conf /etc/nginx/conf.d/default.conf
fi

# 执行原始 CMD
exec "$@"
