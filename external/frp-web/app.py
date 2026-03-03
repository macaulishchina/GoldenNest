"""
FRP Web Configuration Client
简洁优雅的 frpc 配置管理 Web UI
"""

import os
import json
import copy
import subprocess
import signal
from pathlib import Path
import socket
import time
from typing import Optional

import tomli
import tomli_w
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── 配置路径 ──
CONFIG_DIR = Path(os.environ.get("FRP_CONFIG_DIR", "/etc/frp"))
CONFIG_FILE = CONFIG_DIR / "frpc.toml"
FRPC_BIN = os.environ.get("FRPC_BIN", "/usr/bin/frpc")

app = FastAPI(title="FRP Web Config", docs_url=None, redoc_url=None)

# ── 静态文件 ──
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── 工具函数 ──

def _read_config() -> dict:
    """读取 frpc.toml，不存在则返回默认结构"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as f:
            return tomli.load(f)
    return {
        "serverAddr": "127.0.0.1",
        "serverPort": 7000,
        "auth": {"token": ""},
        "proxies": [],
    }


def _write_config(data: dict):
    """写入 frpc.toml"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)


def _validate_config(data: dict) -> dict:
    """规范化配置，确保必要字段存在"""
    data.setdefault("serverAddr", "127.0.0.1")
    data.setdefault("serverPort", 7000)
    data.setdefault("auth", {})
    data["auth"].setdefault("token", "")
    data.setdefault("proxies", [])
    return data


# ── frpc 进程管理 ──

_frpc_process: Optional[subprocess.Popen] = None


def _start_frpc():
    """启动 frpc 进程"""
    global _frpc_process
    _stop_frpc()
    if not CONFIG_FILE.exists():
        return
    if not Path(FRPC_BIN).exists():
        return
    try:
        _frpc_process = subprocess.Popen(
            [FRPC_BIN, "-c", str(CONFIG_FILE)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        _frpc_process = None


def _stop_frpc():
    """停止 frpc 进程"""
    global _frpc_process
    if _frpc_process and _frpc_process.poll() is None:
        _frpc_process.send_signal(signal.SIGTERM)
        try:
            _frpc_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _frpc_process.kill()
    _frpc_process = None


def _frpc_status() -> dict:
    """获取 frpc 运行状态"""
    running = _frpc_process is not None and _frpc_process.poll() is None
    return {
        "running": running,
        "pid": _frpc_process.pid if running else None,
        "binExists": Path(FRPC_BIN).exists(),
        "configExists": CONFIG_FILE.exists(),
    }


def _tcp_connect_check(host: str, port: int, timeout: float = 3.0) -> dict:
    """检查 TCP 连接可达性"""
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {
                "ok": True,
                "message": f"连接成功：{host}:{port}",
                "latency_ms": latency_ms,
            }
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": False,
            "message": f"连接失败：{host}:{port}（{e}）",
            "latency_ms": latency_ms,
        }


# ── API 路由 ──

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/config")
async def get_config():
    """获取完整配置"""
    data = _read_config()
    return {"config": data, "status": _frpc_status()}


@app.put("/api/config")
async def save_config(body: dict):
    """保存完整配置"""
    config = body.get("config", body)
    config = _validate_config(config)
    _write_config(config)
    return {"ok": True, "config": config}


@app.put("/api/server")
async def save_server(body: dict):
    """仅更新服务端连接配置"""
    config = _read_config()
    config["serverAddr"] = body.get("serverAddr", config.get("serverAddr", "127.0.0.1"))
    config["serverPort"] = int(body.get("serverPort", config.get("serverPort", 7000)))
    auth = body.get("auth", {})
    if auth:
        config.setdefault("auth", {})
        config["auth"]["token"] = auth.get("token", config["auth"].get("token", ""))
        method = auth.get("method", "")
        if method:
            config["auth"]["method"] = method

    # 额外通用字段
    for key in ("user", "loginFailExit", "log", "transport", "webServer"):
        if key in body:
            config[key] = body[key]

    _write_config(config)
    return {"ok": True, "config": config}


@app.post("/api/server/check")
async def check_server_connection(body: dict):
    """检查服务端连接 (TCP 可达性)"""
    host = (body.get("serverAddr") or "").strip()
    port_raw = body.get("serverPort")

    if not host:
        raise HTTPException(400, "serverAddr 不能为空")
    try:
        port = int(port_raw)
    except Exception:
        raise HTTPException(400, "serverPort 必须是数字")
    if port <= 0 or port > 65535:
        raise HTTPException(400, "serverPort 必须在 1-65535 之间")

    result = _tcp_connect_check(host, port, timeout=3.0)
    return result


@app.get("/api/proxies")
async def list_proxies():
    """获取代理列表"""
    config = _read_config()
    return {"proxies": config.get("proxies", [])}


@app.post("/api/proxies")
async def add_proxy(body: dict):
    """添加代理"""
    config = _read_config()
    proxies = config.get("proxies", [])

    # 检查名称唯一性
    name = body.get("name", "")
    if not name:
        raise HTTPException(400, "代理名称不能为空")
    if any(p.get("name") == name for p in proxies):
        raise HTTPException(409, f"代理 '{name}' 已存在")

    proxies.append(body)
    config["proxies"] = proxies
    _write_config(config)
    return {"ok": True, "proxies": proxies}


@app.put("/api/proxies/{name}")
async def update_proxy(name: str, body: dict):
    """更新代理"""
    config = _read_config()
    proxies = config.get("proxies", [])
    idx = next((i for i, p in enumerate(proxies) if p.get("name") == name), None)
    if idx is None:
        raise HTTPException(404, f"代理 '{name}' 不存在")

    # 如果改了名称要检查唯一性
    new_name = body.get("name", name)
    if new_name != name and any(p.get("name") == new_name for p in proxies):
        raise HTTPException(409, f"代理 '{new_name}' 已存在")

    proxies[idx] = body
    config["proxies"] = proxies
    _write_config(config)
    return {"ok": True, "proxies": proxies}


@app.delete("/api/proxies/{name}")
async def delete_proxy(name: str):
    """删除代理"""
    config = _read_config()
    proxies = config.get("proxies", [])
    new_proxies = [p for p in proxies if p.get("name") != name]
    if len(new_proxies) == len(proxies):
        raise HTTPException(404, f"代理 '{name}' 不存在")
    config["proxies"] = new_proxies
    _write_config(config)
    return {"ok": True, "proxies": new_proxies}


@app.post("/api/frpc/start")
async def start_frpc():
    """启动 frpc"""
    _start_frpc()
    return _frpc_status()


@app.post("/api/frpc/stop")
async def stop_frpc():
    """停止 frpc"""
    _stop_frpc()
    return _frpc_status()


@app.post("/api/frpc/restart")
async def restart_frpc():
    """重启 frpc"""
    _stop_frpc()
    _start_frpc()
    return _frpc_status()


@app.get("/api/frpc/status")
async def frpc_status():
    """获取 frpc 状态"""
    return _frpc_status()


@app.get("/api/config/raw")
async def get_raw_config():
    """获取原始 TOML 配置内容"""
    if CONFIG_FILE.exists():
        return {"raw": CONFIG_FILE.read_text(encoding="utf-8")}
    return {"raw": ""}


@app.put("/api/config/raw")
async def save_raw_config(body: dict):
    """直接保存原始 TOML 内容"""
    raw = body.get("raw", "")
    try:
        # 验证 TOML 格式
        tomli.loads(raw)
    except Exception as e:
        raise HTTPException(400, f"TOML 格式错误: {e}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(raw, encoding="utf-8")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8156)
