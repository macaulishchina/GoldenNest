#!/bin/bash
# ============================================================
# 生成自签名 SSL 证书（用于局域网 HTTPS 部署）
# 使用方法: bash generate_ssl.sh [你的局域网IP]
# 示例:     bash generate_ssl.sh 192.168.1.100
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSL_DIR="$SCRIPT_DIR/ssl"
IP="${1:-$(hostname -I 2>/dev/null | awk '{print $1}' || echo '192.168.1.100')}"

echo "========================================"
echo "  生成 SSL 自签名证书"
echo "  IP: $IP"
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
  -subj "/C=CN/ST=Local/L=Local/O=GoldenNest/CN=$IP"

# 创建扩展配置（支持 IP SAN）
cat > "$SSL_DIR/ext.cnf" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = $IP
IP.2 = 127.0.0.1
EOF

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
echo "📱 手机导入步骤（消除安全警告）："
echo "   1. 将 $SSL_DIR/ca.pem 传到手机"
echo "      - 可以通过 USB、AirDrop、微信传文件、邮件等"
echo "      - 或者启动一个临时 HTTP 服务:"
echo "        cd $SSL_DIR && python3 -m http.server 9999"
echo "        手机浏览器访问 http://$IP:9999/ca.pem 下载"
echo ""
echo "   2. 安装证书："
echo "      【iPhone】"
echo "        设置 → 已下载描述文件 → 安装"
echo "        设置 → 通用 → 关于本机 → 证书信任设置 → 开启信任"
echo "      【Android】"
echo "        设置 → 安全 → 加密与凭据 → 安装证书 → CA证书"
echo ""
echo "   3. 安装后访问 https://$IP 不再弹安全警告！"
echo ""
