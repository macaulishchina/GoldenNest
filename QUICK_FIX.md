# 🚀 Golden Nest 快速修复指南

## 遇到 Docker Hub 连接问题？

如果您看到以下错误：
```
ERROR: failed to do request: Head "https://registry-1.docker.io/v2/library/python/manifests/3.11-slim": dial tcp 199.59.148.6:443: i/o timeout
```

## 🔥 立即解决方案

### Windows 用户
1. **配置Docker镜像源**：
   - 打开 Docker Desktop → Settings → Docker Engine
   - 复制根目录中 `daemon.json` 的内容
   - 粘贴到配置框，点击 "Apply & Restart"

2. **运行优化构建脚本**：
   ```cmd
   build-cn.bat
   ```

### Linux 用户
1. **自动配置镜像源**：
   ```bash
   sudo ./setup-docker-mirrors.sh
   ```

2. **运行构建脚本**：
   ```bash
   chmod +x build.sh
   ./build.sh
   ```

## 📋 项目文件说明

| 文件 | 用途 | 平台 |
|------|------|------|
| `daemon.json` | Docker镜像源配置 | Windows/Linux |
| `setup-docker-mirrors.sh` | Linux自动配置脚本 | Linux |
| `build-cn.bat` | Windows构建脚本 | Windows |
| `build.sh` | Linux构建脚本 | Linux |
| `docker-compose.yml` | 统一的Docker配置（已优化） | 通用 |

## ✅ 验证配置成功

运行以下命令检查配置：
```bash
docker info | grep -i "registry mirrors"
```

应该看到配置的镜像源列表。

## 🎯 一键启动

配置完成后，使用以下命令启动项目：

**Windows:**
```cmd
build-cn.bat
```

**Linux:**
```bash
./build.sh
```

**通用:**
```bash
docker-compose up -d
```

## 🌐 访问地址

- 前端：http://localhost:8088
- 后端API：http://localhost:8000
- 健康检查：http://localhost:8000/health

## 📞 需要帮助？

查看详细文档：
- `DOCKER_MIRROR_SETUP.md` - 镜像源配置指南
- `DOCKER_TROUBLESHOOTING.md` - 故障排除指南
- `README.md` - 项目完整文档