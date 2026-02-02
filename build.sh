#!/bin/bash

# Golden Nest 项目构建脚本 - Linux版
# 针对国内网络环境优化，解决 Docker Hub 连接问题

set -e  # 遇到错误时退出

echo "================================="
echo "Golden Nest 项目构建脚本 (Linux)"
echo "================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装并运行
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 错误：Docker 未安装${NC}"
    echo "请先安装Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ 错误：Docker 未运行${NC}"
    echo "请启动Docker服务: sudo systemctl start docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ 错误：Docker Compose 未安装${NC}"
    echo "请安装Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 检查Docker镜像源配置
echo -e "${BLUE}🔍 检查Docker镜像源配置...${NC}"
if ! docker info | grep -i "registry mirrors" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  警告：未检测到镜像源配置${NC}"
    echo "建议先配置Docker镜像源以提高构建速度："
    echo "  sudo ./setup-docker-mirrors.sh"
    echo ""
    read -p "是否继续构建？ (y/N): " continue_build
    if [[ ! $continue_build =~ ^[Yy]$ ]]; then
        echo "构建已取消"
        exit 0
    fi
else
    echo -e "${GREEN}✅ Docker镜像源配置正常${NC}"
fi

echo ""
echo -e "${BLUE}📂 当前目录: $(pwd)${NC}"
echo -e "${BLUE}🏗️  开始构建 Golden Nest 项目...${NC}"

# 创建必要的目录
mkdir -p data logs

echo ""
echo -e "${BLUE}步骤 1: 清理旧的容器和镜像${NC}"
docker-compose down --volumes --remove-orphans || true
docker system prune -f --volumes

echo ""
echo -e "${BLUE}步骤 2: 构建镜像（国内源优化）${NC}"
if ! docker-compose build --no-cache --pull; then
    echo ""
    echo -e "${RED}❌ 构建失败！${NC}"
    echo ""
    echo -e "${YELLOW}🔧 可能的解决方案：${NC}"
    echo "1. 运行镜像源配置脚本: sudo ./setup-docker-mirrors.sh"
    echo "2. 检查网络连接"
    echo "3. 查看详细错误信息"
    echo "4. 参考 DOCKER_TROUBLESHOOTING.md 获取帮助"
    echo ""
    exit 1
fi

echo ""
echo -e "${BLUE}步骤 3: 启动服务${NC}"
if ! docker-compose up -d; then
    echo ""
    echo -e "${RED}❌ 启动失败！${NC}"
    echo "检查日志: docker-compose logs"
    exit 1
fi

echo ""
echo -e "${BLUE}步骤 4: 等待服务启动${NC}"
sleep 10

# 检查服务状态
echo -e "${BLUE}📋 检查服务状态...${NC}"
docker-compose ps

# 检查健康状态
echo ""
echo -e "${BLUE}🏥 检查服务健康状态...${NC}"
for i in {1..30}; do
    if curl -f http://localhost:8000/health &> /dev/null; then
        echo -e "${GREEN}✅ 后端服务健康检查通过${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠️  后端服务健康检查超时，但服务可能仍在启动中${NC}"
    fi
    sleep 2
done

echo ""
echo -e "${GREEN}🎉 构建和启动成功！${NC}"
echo ""
echo -e "${BLUE}📊 服务信息：${NC}"
echo -e "- 🌐 前端地址: ${GREEN}http://localhost:8088${NC}"
echo -e "- 🔗 后端 API: ${GREEN}http://localhost:8000${NC}"
echo -e "- 📋 健康检查: ${GREEN}http://localhost:8000/health${NC}"
echo ""
echo -e "${BLUE}🛠️  常用命令：${NC}"
echo -e "- 查看日志: ${YELLOW}docker-compose logs -f${NC}"
echo -e "- 停止服务: ${YELLOW}docker-compose down${NC}"
echo -e "- 重启服务: ${YELLOW}docker-compose restart${NC}"
echo -e "- 查看状态: ${YELLOW}docker-compose ps${NC}"
echo ""
echo -e "${BLUE}💡 提示：如需修改配置，请编辑 .env 文件或环境变量${NC}"

# 如果是通过SSH连接，提供远程访问提示
if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ]; then
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${BLUE}🌐 远程访问地址（如果防火墙允许）：${NC}"
    echo -e "- 前端: ${GREEN}http://${SERVER_IP}:8088${NC}"
    echo -e "- 后端: ${GREEN}http://${SERVER_IP}:8000${NC}"
fi