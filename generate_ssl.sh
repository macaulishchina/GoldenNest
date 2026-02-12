#!/bin/bash
# ============================================================
# 生成自签名 SSL 证书（用于局域网 HTTPS 部署）
# 使用方法: bash generate_ssl.sh <IP1> [IP2] [IP3] ...
# 示例:     bash generate_ssl.sh 192.168.1.100 1.2.3.4
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSL_DIR="$SCRIPT_DIR/ssl"

# 收集所有 IP 参数
if [ $# -eq 0 ]; then
  IP_LIST=("$(hostname -I 2>/dev/null | awk '{print $1}' || echo '192.168.1.100')")
else
  IP_LIST=("$@")
fi

echo "========================================"
echo "  生成 SSL 自签名证书"
echo "  IP 列表: ${IP_LIST[*]}"
echo "  输出目录: $SSL_DIR"
echo "========================================"

mkdir -p "$SSL_DIR"

# 生成 CA 私钥
openssl genrsa -out "$SSL_DIR/ca.key" 2048

# 生成 CA 证书（10年有效期）
openssl req -new -x509 -days 3650 -key "$SSL_DIR/ca.key" \
  -out "$SSL_DIR/ca.pem" \
  -subj "/C=CN/ST=Local/L=Local/O=GoldenNest/CN=GoldenNest Local CA"

# 生成服务器私钥
openssl genrsa -out "$SSL_DIR/key.pem" 2048

# 生成服务器证书签名请求
openssl req -new -key "$SSL_DIR/key.pem" \
  -out "$SSL_DIR/server.csr" \
  -subj "/C=CN/ST=Local/L=Local/O=GoldenNest/CN=${IP_LIST[0]}"

# 创建扩展配置（支持多个 IP SAN）
cat > "$SSL_DIR/ext.cnf" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
EOF

# 动态添加所有 IP
IP_INDEX=2
for ip in "${IP_LIST[@]}"; do
  echo "IP.$IP_INDEX = $ip" >> "$SSL_DIR/ext.cnf"
  IP_INDEX=$((IP_INDEX + 1))
done

# 用 CA 签发服务器证书
openssl x509 -req -in "$SSL_DIR/server.csr" \
  -CA "$SSL_DIR/ca.pem" -CAkey "$SSL_DIR/ca.key" -CAcreateserial \
  -out "$SSL_DIR/cert.pem" -days 3650 \
  -extfile "$SSL_DIR/ext.cnf"

# 清理临时文件
rm -f "$SSL_DIR/server.csr" "$SSL_DIR/ext.cnf" "$SSL_DIR/ca.srl"

echo ""
echo "✅ 证书生成完成！"
echo ""
echo "📁 文件列表："
echo "   $SSL_DIR/cert.pem   — 服务器证书"
echo "   $SSL_DIR/key.pem    — 服务器私钥"
echo "   $SSL_DIR/ca.pem     — CA 根证书"
echo "   $SSL_DIR/ca.key     — CA 私钥"
echo ""
echo "📱 手机导入 $SSL_DIR/ca.pem 后，以下地址均受信任："
for ip in "${IP_LIST[@]}"; do
  echo "   https://$ip"
done
echo ""