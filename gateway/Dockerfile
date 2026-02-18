# Gateway - 入口网关 (Level 1: 超稳定)
# 多阶段构建: 第一阶段构建设计院前端, 第二阶段打包到 Nginx

# ========================
# Stage 1: 构建设计院前端
# ========================
FROM docker.1ms.run/library/node:20-alpine AS studio-builder

WORKDIR /app

# 先复制依赖文件, 利用 Docker 缓存
COPY studio/frontend/package.json studio/frontend/package-lock.json* ./

# 使用国内镜像源安装依赖
RUN npm config set registry https://registry.npmmirror.com && npm install

# 复制源代码并构建
COPY studio/frontend/ ./
RUN npm run build

# ========================
# Stage 2: Nginx 网关
# ========================
FROM docker.1ms.run/library/nginx:alpine

# 复制 Nginx 配置模板
COPY gateway/nginx.conf /etc/nginx/templates/http.conf
COPY gateway/nginx-ssl.conf /etc/nginx/templates/ssl.conf.template

# 复制启动脚本
COPY gateway/docker-entrypoint.sh /docker-entrypoint-gateway.sh
RUN chmod +x /docker-entrypoint-gateway.sh

# 从构建阶段复制设计院前端产物
COPY --from=studio-builder /app/dist /usr/share/nginx/studio

EXPOSE 80 443

ENTRYPOINT ["/docker-entrypoint-gateway.sh"]
CMD ["nginx", "-g", "daemon off;"]
