@echo off
REM Golden Nest 项目构建脚本 - Windows版
REM 针对国内网络环境优化，解决 Docker Hub 连接问题

echo =================================
echo Golden Nest 项目构建脚本 (Windows)
echo =================================

REM 检查 Docker 是否运行
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ 错误：Docker 未运行或未正确安装
    echo 请启动 Docker Desktop 后重试
    pause
    exit /b 1
)

REM 检查Docker镜像源配置
echo 🔍 检查Docker镜像源配置...
docker info | findstr /i "registry-mirrors" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ⚠️  警告：未检测到镜像源配置
    echo 建议先配置Docker镜像源以提高构建速度：
    echo 1. 打开Docker Desktop -^> Settings -^> Docker Engine
    echo 2. 使用项目根目录中的 daemon.json 配置
    echo 3. 点击 Apply ^& Restart
    echo.
    echo 是否继续构建？ (y/N)
    set /p continue=
    if /i not "%continue%"=="y" (
        echo 构建已取消
        pause
        exit /b 0
    )
)

echo.
echo 📂 当前目录: %CD%
echo 🏗️  开始构建 Golden Nest 项目...

echo.
echo 步骤 1: 清理旧的容器和镜像
docker-compose down --volumes --remove-orphans
docker system prune -f --volumes

echo.
echo 步骤 2: 构建镜像（国内源优化）
docker-compose build --no-cache --pull

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 构建失败！
    echo.
    echo 🔧 可能的解决方案：
    echo 1. 确认已配置 Docker 镜像加速器
    echo 2. 检查网络连接
    echo 3. 查看详细错误信息
    echo 4. 参考 DOCKER_TROUBLESHOOTING.md 获取帮助
    echo.
    pause
    exit /b 1
)

echo.
echo 步骤 3: 启动服务
docker-compose up -d

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 启动失败！
    echo 检查日志: docker-compose logs
    pause
    exit /b 1
)

echo.
echo 步骤 4: 等待服务启动
timeout /t 10 /nobreak >nul
docker-compose ps

echo.
echo 🎉 构建和启动成功！
echo.
echo 📊 服务信息：
echo - 🌐 前端地址: http://localhost:8088
echo - 🔗 后端 API: http://localhost:8000
echo - 📋 健康检查: http://localhost:8000/health
echo.
echo 🛠️  常用命令：
echo - 查看日志: docker-compose logs -f
echo - 停止服务: docker-compose down
echo - 重启服务: docker-compose restart
echo - 查看状态: docker-compose ps
echo.
echo 💡 提示：如需修改配置，请编辑 .env 文件或环境变量

pause
