#!/bin/bash

# Golden Nest Docker 镜像源配置脚本 - Linux版
# 自动配置Docker镜像加速器以解决连接超时问题

echo "================================="
echo "Golden Nest Docker 镜像源配置脚本"
echo "================================="

# 检查是否为root用户或有sudo权限
if [[ $EUID -ne 0 && $(sudo -n true 2>/dev/null; echo $?) -ne 0 ]]; then
    echo "❌ 错误：需要root权限或sudo权限来配置Docker"
    echo "请使用: sudo $0"
    exit 1
fi

# 检查Docker是否已安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误：Docker未安装"
    echo "请先安装Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# 创建Docker配置目录
echo "🔧 创建Docker配置目录..."
sudo mkdir -p /etc/docker

# 备份现有配置（如果存在）
if [ -f /etc/docker/daemon.json ]; then
    echo "📦 备份现有配置..."
    sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
fi

# 创建daemon.json配置文件
echo "⚙️  配置Docker镜像源..."
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://hub-mirror.c.163.com",
    "https://mirror.ccs.tencentyun.com",
    "https://ccr.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://reg-mirror.qiniu.com"
  ],
  "experimental": false,
  "debug": false,
  "log-level": "info",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true
}
EOF

# 重新加载Docker配置
echo "🔄 重新加载Docker配置..."
sudo systemctl daemon-reload
sudo systemctl restart docker

# 等待Docker服务启动
echo "⏳ 等待Docker服务启动..."
sleep 3

# 验证配置
echo "✅ 验证配置..."
if docker info | grep -i "registry mirrors" > /dev/null; then
    echo "🎉 Docker镜像源配置成功！"
    echo ""
    echo "配置的镜像源："
    docker info | grep -A 10 "Registry Mirrors"
else
    echo "⚠️  警告：无法验证镜像源配置"
fi

# 测试镜像拉取
echo ""
echo "🧪 测试镜像拉取..."
if docker pull hello-world > /dev/null 2>&1; then
    echo "✅ 镜像拉取测试成功！"
    docker rmi hello-world > /dev/null 2>&1
else
    echo "❌ 镜像拉取测试失败"
    echo "请检查网络连接和镜像源配置"
fi

echo ""
echo "🏁 配置完成！现在可以使用以下命令构建Golden Nest项目："
echo "  docker-compose build --no-cache"
echo "  docker-compose up -d"
echo ""
echo "如有问题，请参考 DOCKER_TROUBLESHOOTING.md 文件"