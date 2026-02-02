# Docker 镜像源配置指南

## 问题说明
您遇到的错误表明 Docker 无法连接到官方 Docker Hub 镜像仓库（registry-1.docker.io），这通常是由于网络连接问题或地理位置限制导致的。

## 快速解决方案

### Windows 用户（推荐）
1. 打开 Docker Desktop
2. 右键点击任务栏中的 Docker 图标，选择 "Settings"
3. 在左侧导航中选择 "Docker Engine"
4. 将本项目根目录中的 `daemon.json` 内容复制到配置框中
5. 点击 "Apply & Restart"
6. 运行构建脚本：`build-cn.bat`

### Linux 用户（推荐）
1. 运行自动配置脚本：`sudo ./setup-docker-mirrors.sh`
2. 运行构建脚本：`./build.sh`

## 详细配置方案

### 方案一：自动配置脚本（推荐）

#### Windows
```cmd
# 手动配置Docker镜像源后，运行构建脚本
build-cn.bat
```

#### Linux
```bash
# 自动配置并构建
sudo ./setup-docker-mirrors.sh
./build.sh
```

### 方案二：手动配置
将 `daemon.json` 文件复制到以下位置：
- Windows: `%userprofile%\.docker\daemon.json`
- Linux: `/etc/docker/daemon.json`

然后重启Docker服务：
- Windows: 重启 Docker Desktop
- Linux: `sudo systemctl restart docker`

### 方案三：使用统一的构建脚本
项目已提供优化的构建脚本和docker-compose配置：
- Windows: `build-cn.bat`
- Linux: `./build.sh`
- 配置文件: `docker-compose.yml`（已包含国内镜像源优化）

## 配置的镜像源列表
本配置包含了以下可靠的国内镜像源：
1. **阿里云杭州**: `https://registry.cn-hangzhou.aliyuncs.com`
2. **网易**: `https://hub-mirror.c.163.com`
3. **腾讯云**: `https://mirror.ccs.tencentyun.com`
4. **腾讯容器镜像**: `https://ccr.ccs.tencentyun.com`
5. **中科大**: `https://docker.mirrors.ustc.edu.cn`
6. **七牛云**: `https://reg-mirror.qiniu.com`

## 验证配置
配置完成后，重启 Docker 并运行以下命令验证：
```bash
docker info
```

在输出中查看 "Registry Mirrors" 部分，确认镜像源已正确配置。

## 重新构建
配置完成后，运行：
```bash
docker-compose build --no-cache
docker-compose up -d
```

## 故障排除
如果仍然遇到问题，请查看本项目的 `DOCKER_TROUBLESHOOTING.md` 文件获取更详细的故障排除指南。