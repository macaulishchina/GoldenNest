# Golden Nest Frontend Dockerfile
# 使用国内镜像源加速拉取
FROM docker.1ms.run/library/node:20-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package.json ./

# 配置 npm 使用国内镜像源并安装依赖
RUN npm config set registry https://registry.npmmirror.com && npm install

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# 生产阶段 - 使用 nginx 服务静态文件
FROM docker.1ms.run/library/nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置（HTTP 和 HTTPS）
COPY nginx.conf /etc/nginx/templates/http-only.conf
COPY nginx.ssl.conf /etc/nginx/templates/default.conf.template

# 启动脚本：根据是否存在 SSL 证书自动选择配置
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80 443

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]