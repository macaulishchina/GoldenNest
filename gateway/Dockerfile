# Gateway - 入口网关 (Level 1: 超稳定)
# 设计院前端由宿主机预构建, 通过 build context 复制到网关

FROM docker.1ms.run/library/nginx:alpine

# 复制 Nginx 配置模板
COPY gateway/nginx.conf /etc/nginx/templates/http.conf
COPY gateway/nginx-ssl.conf /etc/nginx/templates/ssl.conf.template

# 复制启动脚本
COPY gateway/docker-entrypoint.sh /docker-entrypoint-gateway.sh
RUN chmod +x /docker-entrypoint-gateway.sh

# 复制设计院前端预构建产物
COPY studio/frontend/dist /usr/share/nginx/studio

EXPOSE 80 443

ENTRYPOINT ["/docker-entrypoint-gateway.sh"]
CMD ["nginx", "-g", "daemon off;"]
