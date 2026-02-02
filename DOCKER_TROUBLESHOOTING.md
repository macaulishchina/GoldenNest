# Docker 网络诊断和故障排除指南

## 常见错误类型

### 1. 连接超时错误 (Connection Timeout)
```
ERROR: failed to do request: Head "https://registry-1.docker.io/v2/library/python/manifests/3.11-slim": dial tcp 199.59.148.6:443: i/o timeout
```

**原因分析：**
- 网络连接到 Docker Hub 官方仓库超时
- 可能由于网络限制、防火墙或地理位置限制

### 2. DNS 解析失败
```
ERROR: failed to solve with frontend dockerfile.v0: failed to read dockerfile: failed to mount: no such host
```

### 3. 镜像拉取失败
```
ERROR: pull access denied for <image>, repository does not exist or may require 'docker login'
```

## 网络诊断命令

### 基础连接测试
```bash
# 测试 Docker Hub 连接
ping registry-1.docker.io

# 测试 HTTPS 连接
curl -I https://registry-1.docker.io/v2/

# 测试国内镜像源连接
curl -I https://registry.cn-hangzhou.aliyuncs.com/v2/

# DNS 解析测试
nslookup registry-1.docker.io
nslookup registry.cn-hangzhou.aliyuncs.com
```

### Docker 相关诊断
```bash
# 检查 Docker 配置
docker info

# 查看 Docker 版本
docker --version

# 检查镜像源配置
docker system info | findstr -i mirror

# 测试镜像拉取
docker pull hello-world
```

## 解决方案优先级

### 🔥 立即解决方案
1. **配置 Docker 镜像加速器**
   - 使用项目提供的 `daemon.json`
   - 重启 Docker Desktop
   - 验证配置: `docker info`

2. **使用优化的构建脚本**
   ```bash
   # Windows
   build-cn.bat
   
   # 或手动执行
   docker-compose -f docker-compose-cn.yml build --no-cache
   docker-compose -f docker-compose-cn.yml up -d
   ```

### 🛠️ 中级解决方案
3. **配置代理服务器**
   ```bash
   # 设置环境变量
   set HTTP_PROXY=http://your-proxy:port
   set HTTPS_PROXY=http://your-proxy:port
   ```

4. **使用特定镜像源**
   ```bash
   # 临时使用阿里云镜像
   docker pull registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim
   ```

### 🔧 高级解决方案
5. **修改系统 DNS**
   - 使用公共DNS: 8.8.8.8, 114.114.114.114
   - 配置路径: 控制面板 → 网络和Internet → 网络适配器设置

6. **防火墙和安全软件检查**
   - 临时禁用防火墙测试
   - 添加 Docker Desktop 到白名单

## 镜像源选择指南

### 推荐镜像源（按速度排序）
1. **阿里云（杭州）**: `https://registry.cn-hangzhou.aliyuncs.com`
2. **腾讯云**: `https://mirror.ccs.tencentyun.com`
3. **网易**: `https://hub-mirror.c.163.com`
4. **中科大**: `https://docker.mirrors.ustc.edu.cn`
5. **七牛云**: `https://reg-mirror.qiniu.com`

### 测试镜像源速度
```bash
# 测试各个镜像源的响应时间
curl -w "@curl-format.txt" -o NUL -s "https://registry.cn-hangzhou.aliyuncs.com/v2/"
curl -w "@curl-format.txt" -o NUL -s "https://mirror.ccs.tencentyun.com/v2/"
```

### curl-format.txt 内容：
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

## 环境特定解决方案

### 公司/企业环境
```bash
# 配置企业代理
docker build --build-arg HTTP_PROXY=http://proxy.company.com:8080 .

# 设置 Docker Desktop 代理
# Settings → Resources → Proxies
```

### 家庭网络环境
```bash
# 更换 DNS 服务器
# 路由器设置或系统网络设置
# 推荐: 114.114.114.114, 8.8.8.8, 223.5.5.5
```

### VPN 环境
```bash
# 确保 VPN 不影响 Docker
# 检查 VPN 分流设置
# 可能需要将 Docker 相关域名加入直连列表
```

## 验证配置成功

### 1. 检查镜像源配置
```bash
docker info | findstr -i registry-mirrors
```

### 2. 测试镜像拉取
```bash
docker pull hello-world
docker pull python:3.11-slim
docker pull node:20-alpine
docker pull nginx:alpine
```

### 3. 执行项目构建
```bash
# 使用优化的构建脚本
build-cn.bat

# 或手动构建
docker-compose -f docker-compose-cn.yml build --no-cache
```

## 常见问题和解答

### Q: 配置镜像源后仍然很慢？
A: 
1. 尝试不同的镜像源
2. 检查网络环境是否有限制
3. 考虑使用代理服务器

### Q: 某些镜像在国内源中找不到？
A: 
1. 检查镜像名称和标签是否正确
2. 尝试使用官方源（如果网络允许）
3. 寻找替代镜像

### Q: Docker Desktop 重启后配置丢失？
A: 
1. 确认配置文件位置正确
2. 检查文件权限
3. 重新配置并保存

### Q: 企业网络环境下无法连接？
A: 
1. 联系网络管理员开放必要端口
2. 配置正确的代理服务器
3. 使用内部镜像仓库

## 应急解决方案

### 如果所有方案都失败
1. **离线镜像导入**
   ```bash
   # 从其他机器导出镜像
   docker save python:3.11-slim > python-3.11-slim.tar
   
   # 在本机导入
   docker load < python-3.11-slim.tar
   ```

2. **使用预构建镜像**
   - 从可靠的镜像仓库下载
   - 使用 USB 或其他方式传输

3. **本地开发环境**
   - 暂时不使用 Docker
   - 直接在本地安装 Python/Node.js 环境

## 技术支持

如果问题仍然存在：
1. 收集诊断信息: `docker info > docker-info.txt`
2. 记录错误日志
3. 提供网络环境描述

---

> **提示**: 定期检查和更新镜像源配置，确保获得最佳性能。