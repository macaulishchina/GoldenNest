@echo off
REM ============================================================
REM 生成自签名 SSL 证书（用于局域网 HTTPS 部署）
REM 使用方法: generate_ssl.bat [你的局域网IP]
REM 示例:     generate_ssl.bat 192.168.1.100
REM ============================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "SSL_DIR=%SCRIPT_DIR%ssl"
set "IP=%~1"

if "%IP%"=="" (
    echo 请输入你的局域网 IP 地址:
    echo 示例: generate_ssl.bat 192.168.1.100
    echo.
    echo 你的 IP 地址可能是:
    ipconfig | findstr /i "IPv4"
    echo.
    set /p IP="请输入 IP: "
)

echo ========================================
echo   生成 SSL 自签名证书
echo   IP: %IP%
echo   输出目录: %SSL_DIR%
echo ========================================

if not exist "%SSL_DIR%" mkdir "%SSL_DIR%"

REM 检查 openssl 是否可用
where openssl >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 未找到 openssl 命令！
    echo.
    echo 安装方法（任选其一）：
    echo   1. Git Bash 自带: 打开 Git Bash 运行 bash generate_ssl.sh %IP%
    echo   2. choco install openssl
    echo   3. 从 https://slproweb.com/products/Win32OpenSSL.html 下载安装
    echo.
    pause
    exit /b 1
)

REM 生成 CA 私钥
openssl genrsa -out "%SSL_DIR%\ca.key" 2048

REM 生成 CA 证书
openssl req -new -x509 -days 3650 -key "%SSL_DIR%\ca.key" -out "%SSL_DIR%\ca.pem" -subj "/C=CN/ST=Local/L=Local/O=GoldenNest/CN=GoldenNest Local CA"

REM 生成服务器私钥
openssl genrsa -out "%SSL_DIR%\key.pem" 2048

REM 生成服务器 CSR
openssl req -new -key "%SSL_DIR%\key.pem" -out "%SSL_DIR%\server.csr" -subj "/C=CN/ST=Local/L=Local/O=GoldenNest/CN=%IP%"

REM 创建扩展配置
(
echo authorityKeyIdentifier=keyid,issuer
echo basicConstraints=CA:FALSE
echo keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
echo subjectAltName = @alt_names
echo.
echo [alt_names]
echo DNS.1 = localhost
echo IP.1 = %IP%
echo IP.2 = 127.0.0.1
) > "%SSL_DIR%\ext.cnf"

REM 用 CA 签发服务器证书
openssl x509 -req -in "%SSL_DIR%\server.csr" -CA "%SSL_DIR%\ca.pem" -CAkey "%SSL_DIR%\ca.key" -CAcreateserial -out "%SSL_DIR%\cert.pem" -days 3650 -extfile "%SSL_DIR%\ext.cnf"

REM 清理临时文件
del /q "%SSL_DIR%\server.csr" "%SSL_DIR%\ext.cnf" "%SSL_DIR%\ca.srl" 2>nul

echo.
echo ✅ 证书生成完成！
echo.
echo 📁 文件列表：
echo    %SSL_DIR%\cert.pem   — 服务器证书
echo    %SSL_DIR%\key.pem    — 服务器私钥
echo    %SSL_DIR%\ca.pem     — CA 根证书
echo    %SSL_DIR%\ca.key     — CA 私钥
echo.
echo 📱 手机导入步骤（消除安全警告）：
echo    1. 将 %SSL_DIR%\ca.pem 传到手机（微信/邮件/USB）
echo       或者临时开个 HTTP 服务让手机下载:
echo       cd %SSL_DIR% ^&^& python -m http.server 9999
echo       手机浏览器访问 http://%IP%:9999/ca.pem
echo.
echo    2. 安装证书：
echo       【iPhone】
echo         设置 → 已下载描述文件 → 安装
echo         设置 → 通用 → 关于本机 → 证书信任设置 → 开启信任
echo       【Android】
echo         设置 → 安全 → 加密与凭据 → 安装证书 → CA证书
echo.
echo    3. 安装后访问 https://%IP% 不再弹安全警告！
echo.
pause
