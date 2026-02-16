#!/bin/sh
# Gateway 入口脚本: 根据 SSL 证书自动选择配置

SSL_CERT="/etc/nginx/ssl/cert.pem"
SSL_KEY="/etc/nginx/ssl/key.pem"

if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    echo "✅ [Gateway] SSL 证书已找到，启用 HTTPS 模式"
    envsubst '${HTTPS_PORT}' < /etc/nginx/templates/ssl.conf.template > /etc/nginx/conf.d/default.conf
else
    echo "⚠️  [Gateway] 未找到 SSL 证书，使用 HTTP 模式"
    cp /etc/nginx/templates/http.conf /etc/nginx/conf.d/default.conf
fi

exec "$@"
