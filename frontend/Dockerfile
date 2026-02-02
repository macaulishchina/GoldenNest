# Golden Nest Frontend Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# 配置 npm 使用国内镜像源
RUN npm config set registry https://registry.npmmirror.com && \
    npm config set disturl https://registry.npmmirror.com/-/binary/node && \
    npm config set sass_binary_site https://registry.npmmirror.com/-/binary/node-sass

# 复制依赖文件
COPY package.json ./
COPY package-lock.json ./

# 安装依赖
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# 生产阶段 - 使用 nginx 服务静态文件
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
