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
import urllib.request
import urllib.parse
import urllib.error
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
META_FILE = CONFIG_DIR / "frpc-web-meta.json"
FRPC_BIN = os.environ.get("FRPC_BIN", "/usr/bin/frpc")
AUTOSTART_FRPC = os.environ.get("AUTOSTART_FRPC", "1").strip().lower() not in {"0", "false", "no", "off"}

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


def _read_meta() -> dict:
    """读取 Web UI 元数据（不写入 frpc.toml）"""
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"proxy_links": {}}


def _write_meta(meta: dict):
    """写入 Web UI 元数据"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_proxy_links() -> dict:
    meta = _read_meta()
    links = meta.get("proxy_links", {})
    if isinstance(links, dict):
        return links
    return {}


def _set_proxy_link(name: str, link: str):
    """设置单个代理的快捷访问链接（空值即删除）"""
    meta = _read_meta()
    proxy_links = meta.get("proxy_links", {})
    if not isinstance(proxy_links, dict):
        proxy_links = {}

    clean_link = (link or "").strip()
    if clean_link:
        proxy_links[name] = clean_link
    else:
        proxy_links.pop(name, None)

    meta["proxy_links"] = proxy_links
    _write_meta(meta)


def _sync_proxy_links(proxy_names: list[str]):
    """清理已不存在代理的链接映射"""
    meta = _read_meta()
    proxy_links = meta.get("proxy_links", {})
    if not isinstance(proxy_links, dict):
        proxy_links = {}

    name_set = set(proxy_names)
    cleaned = {k: v for k, v in proxy_links.items() if k in name_set and isinstance(v, str) and v.strip()}
    meta["proxy_links"] = cleaned
    _write_meta(meta)


def _strip_proxy_meta(proxy: dict) -> dict:
    """剔除仅用于 Web UI 的字段，避免写入 frpc.toml 导致 frpc 解析失败"""
    cleaned = copy.deepcopy(proxy)
    cleaned.pop("customAccessLink", None)
    for key in list(cleaned.keys()):
        if key.startswith("_"):
            cleaned.pop(key, None)
    return cleaned


def _merge_proxy_meta(proxy: dict) -> dict:
    """为代理数据附加 Web UI 元字段"""
    merged = copy.deepcopy(proxy)
    link = _get_proxy_links().get(proxy.get("name", ""), "")
    if link:
        merged["customAccessLink"] = link
    return merged


def _proxies_with_meta(proxies: list[dict]) -> list[dict]:
    links = _get_proxy_links()
    result = []
    for proxy in proxies:
        merged = copy.deepcopy(proxy)
        name = proxy.get("name", "")
        link = links.get(name, "")
        if link:
            merged["customAccessLink"] = link
        result.append(merged)
    return result


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


def _restart_frpc_verified(wait_seconds: float = 3.0) -> dict:
    """重启并验证 frpc 状态（尽量确认重启已生效）"""
    before = _frpc_status()
    before_pid = before.get("pid")

    _stop_frpc()
    time.sleep(0.15)
    _start_frpc()

    deadline = time.perf_counter() + wait_seconds
    after = _frpc_status()
    while time.perf_counter() < deadline:
        after = _frpc_status()
        if after.get("running"):
            break
        time.sleep(0.12)

    after_pid = after.get("pid")
    pid_changed = bool(after_pid) and after_pid != before_pid
    restarted = bool(after.get("running")) and (pid_changed or before_pid is None)

    if not before.get("running") and after.get("running"):
        message = "frpc 已启动并生效"
    elif restarted:
        message = "frpc 已重启并生效"
    elif after.get("running"):
        message = "frpc 正在运行，但未确认 PID 变化"
    else:
        message = "frpc 重启失败"

    return {
        **after,
        "beforePid": before_pid,
        "afterPid": after_pid,
        "pidChanged": pid_changed,
        "restarted": restarted,
        "message": message,
    }


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


@app.on_event("startup")
async def _auto_start_frpc_on_boot():
    """服务启动时默认自动拉起 frpc"""
    if AUTOSTART_FRPC:
        _start_frpc()


@app.on_event("shutdown")
async def _stop_frpc_on_shutdown():
    """服务关闭时优雅停止 frpc"""
    _stop_frpc()


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


def _http_probe(url: str, timeout: float = 5.0) -> dict:
    """通过 HTTP/HTTPS 主动探测访问是否有数据响应"""
    start = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": "frp-web-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = int(resp.getcode() or 0)
            body = resp.read(65536)
            latency_ms = int((time.perf_counter() - start) * 1000)
            text_preview = body.decode("utf-8", errors="ignore")[:160]
            has_body = len(body) > 0
            ok = (200 <= status_code < 400) and has_body
            return {
                "ok": ok,
                "mode": "http",
                "status_code": status_code,
                "latency_ms": latency_ms,
                "response_bytes": len(body),
                "preview": text_preview,
                "message": "请求成功且有响应数据" if ok else "请求成功但响应为空或状态异常",
            }
    except urllib.error.HTTPError as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": False,
            "mode": "http",
            "status_code": int(getattr(e, "code", 0) or 0),
            "latency_ms": latency_ms,
            "response_bytes": 0,
            "preview": "",
            "message": f"HTTP 错误：{e}",
        }
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": False,
            "mode": "http",
            "status_code": 0,
            "latency_ms": latency_ms,
            "response_bytes": 0,
            "preview": "",
            "message": f"请求失败：{e}",
        }


def _probe_access_link(link: str) -> dict:
    """探测用户配置的访问链接"""
    clean = (link or "").strip()
    if not clean:
        return {"ok": False, "mode": "unknown", "message": "未提供访问链接"}

    lower = clean.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        result = _http_probe(clean)
        result["checked_link"] = clean
        return result

    if lower.startswith("tcp://"):
        parsed = urllib.parse.urlparse(clean)
        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            return {"ok": False, "mode": "tcp", "message": "tcp:// 链接格式错误，应为 tcp://host:port"}
        result = _tcp_connect_check(host, int(port), timeout=3.0)
        result["mode"] = "tcp"
        result["checked_link"] = clean
        return result

    if ":" in clean:
        host, port_raw = clean.rsplit(":", 1)
        try:
            port = int(port_raw)
        except Exception:
            return {"ok": False, "mode": "tcp", "message": "链接格式错误，端口必须是数字"}
        result = _tcp_connect_check(host, port, timeout=3.0)
        result["mode"] = "tcp"
        result["checked_link"] = clean
        return result

    return {
        "ok": False,
        "mode": "unknown",
        "message": "不支持的链接格式，请使用 http(s):// 或 tcp://host:port 或 host:port",
        "checked_link": clean,
    }


def _first_domain(custom_domains) -> str:
    """从 customDomains 中提取首个域名"""
    if isinstance(custom_domains, list):
        for item in custom_domains:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return ""
    if isinstance(custom_domains, str):
        return custom_domains.strip()
    return ""


def _build_default_probe_link(proxy: dict, config: dict) -> str:
    """无快捷链接时，基于代理类型 + 默认端口构建探测链接"""
    proxy_type = (proxy.get("type") or "tcp").lower()
    server_addr = (config.get("serverAddr") or "").strip()
    remote_port = proxy.get("remotePort")

    if proxy_type in ("http", "https"):
        scheme = proxy_type
        domain = _first_domain(proxy.get("customDomains"))
        if domain:
            if remote_port:
                return f"{scheme}://{domain}:{int(remote_port)}"
            return f"{scheme}://{domain}"

        subdomain = (proxy.get("subdomain") or "").strip()
        if subdomain and server_addr:
            host = f"{subdomain}.{server_addr}"
            if remote_port:
                return f"{scheme}://{host}:{int(remote_port)}"
            return f"{scheme}://{host}"

        if server_addr and remote_port:
            return f"{scheme}://{server_addr}:{int(remote_port)}"

        return ""

    # 其他类型统一做 TCP 端口连通性探测（基于 serverAddr + remotePort）
    if server_addr and remote_port:
        return f"tcp://{server_addr}:{int(remote_port)}"

    return ""


def _apply_proxy_changes() -> dict:
    """代理配置修改后自动生效：frpc 运行中则自动重启应用配置"""
    status = _frpc_status()
    if not status.get("running"):
        return {
            "applied": False,
            "action": "skipped",
            "message": "配置已保存；frpc 当前未运行，待启动后生效",
            "status": status,
        }

    restart_result = _restart_frpc_verified(wait_seconds=3.0)
    return {
        "applied": bool(restart_result.get("restarted")),
        "action": "restarted",
        "message": "配置已保存并自动重启 frpc" if restart_result.get("running") else "配置已保存，但 frpc 自动重启失败",
        "restart": restart_result,
    }


# ── API 路由 ──

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/config")
async def get_config():
    """获取完整配置"""
    data = _validate_config(_read_config())
    data["proxies"] = _proxies_with_meta(data.get("proxies", []))
    return {"config": data, "status": _frpc_status()}


@app.put("/api/config")
async def save_config(body: dict):
    """保存完整配置"""
    config = body.get("config", body)
    config = _validate_config(config)
    proxies = config.get("proxies", [])
    link_map = {}
    cleaned_proxies = []
    for proxy in proxies:
        name = proxy.get("name", "")
        if name:
            link_map[name] = (proxy.get("customAccessLink") or "").strip()
        cleaned_proxies.append(_strip_proxy_meta(proxy))
    config["proxies"] = cleaned_proxies
    _write_config(config)
    for name, link in link_map.items():
        _set_proxy_link(name, link)
    _sync_proxy_links([p.get("name", "") for p in cleaned_proxies if p.get("name")])
    config["proxies"] = _proxies_with_meta(cleaned_proxies)
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
    proxies = config.get("proxies", [])
    _sync_proxy_links([p.get("name", "") for p in proxies if p.get("name")])
    return {"proxies": _proxies_with_meta(proxies)}


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

    custom_link = (body.get("customAccessLink") or "").strip()
    proxy_body = _strip_proxy_meta(body)
    proxies.append(proxy_body)
    config["proxies"] = proxies
    _write_config(config)
    _set_proxy_link(name, custom_link)
    _sync_proxy_links([p.get("name", "") for p in proxies if p.get("name")])
    apply_result = _apply_proxy_changes()
    return {"ok": True, "proxies": _proxies_with_meta(proxies), "apply": apply_result}


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

    custom_link = (body.get("customAccessLink") or "").strip()
    proxy_body = _strip_proxy_meta(body)

    proxies[idx] = proxy_body
    config["proxies"] = proxies
    _write_config(config)

    if new_name != name:
        old_link = _get_proxy_links().get(name, "")
        _set_proxy_link(name, "")
        _set_proxy_link(new_name, custom_link or old_link)
    else:
        _set_proxy_link(new_name, custom_link)

    _sync_proxy_links([p.get("name", "") for p in proxies if p.get("name")])
    apply_result = _apply_proxy_changes()
    return {"ok": True, "proxies": _proxies_with_meta(proxies), "apply": apply_result}


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
    _set_proxy_link(name, "")
    _sync_proxy_links([p.get("name", "") for p in new_proxies if p.get("name")])
    apply_result = _apply_proxy_changes()
    return {"ok": True, "proxies": _proxies_with_meta(new_proxies), "apply": apply_result}


@app.post("/api/proxies/{name}/probe")
async def probe_proxy_mapping(name: str, body: Optional[dict] = None):
    """验证代理映射是否可用：优先 customAccessLink，其次默认协议+端口探测"""
    body = body or {}
    config = _validate_config(_read_config())
    proxies = config.get("proxies", [])
    proxy = next((p for p in proxies if p.get("name") == name), None)
    if proxy is None:
        raise HTTPException(404, f"代理 '{name}' 不存在")

    link = (body.get("link") or _get_proxy_links().get(name, "")).strip()
    if link:
        result = _probe_access_link(link)
        result["source"] = "custom_link"
        result["proxy_name"] = name
        result["checked_at"] = int(time.time())
        return result

    default_link = _build_default_probe_link(proxy, config)
    if default_link:
        result = _probe_access_link(default_link)
        result["source"] = "default_link"
        result["proxy_name"] = name
        result["checked_at"] = int(time.time())
        return result

    return {
        "ok": False,
        "skipped": True,
        "mode": "unknown",
        "source": "skipped",
        "proxy_name": name,
        "checked_at": int(time.time()),
        "message": "已跳过",
    }


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
    return _restart_frpc_verified(wait_seconds=3.0)


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
