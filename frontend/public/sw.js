/**
 * 小金库 Golden Nest - Service Worker
 * 提供 PWA 安装能力、基本离线支持和连接恢复
 */

const CACHE_NAME = 'golden-nest-v3'

// 不要拦截同域下的其它子应用，避免影响反向代理的多应用部署
const EXCLUDED_PREFIXES = [
  '/antigravity-manager/',
  '/studio/',
  '/jupyter/',
  '/ollama-ui/',
  '/proxy-ui/',
  '/code/',
  '/frpc/',
]

// 需要预缓存的关键资源
const PRECACHE_URLS = [
  '/',
]

// 连接异常时的离线回退页（内联 HTML，不依赖任何外部资源）
const OFFLINE_FALLBACK_HTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover">
<title>小金库 - 连接恢复</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;
justify-content:center;padding:24px}
.card{background:#1e293b;border-radius:20px;padding:40px 32px;max-width:380px;
width:100%;text-align:center;box-shadow:0 25px 50px rgba(0,0,0,.4)}
.icon{font-size:56px;margin-bottom:16px}
h1{font-size:20px;margin-bottom:8px;color:#f8fafc}
.desc{font-size:14px;color:#94a3b8;line-height:1.6;margin-bottom:24px}
.steps{text-align:left;background:#0f172a;border-radius:12px;padding:16px 20px;
margin-bottom:24px;font-size:13px;line-height:1.8;color:#cbd5e1}
.steps b{color:#f59e0b}
.btn{display:block;width:100%;padding:12px;border:none;border-radius:10px;
font-size:15px;font-weight:600;cursor:pointer;margin-bottom:10px;transition:.2s}
.btn-primary{background:#3b82f6;color:#fff}
.btn-primary:active{background:#2563eb}
.btn-secondary{background:#334155;color:#94a3b8}
.btn-secondary:active{background:#475569}
.btn-danger{background:#7f1d1d;color:#fca5a5;font-size:13px;padding:10px}
.status{margin-top:16px;font-size:12px;color:#64748b}
.status.ok{color:#22c55e}
.status.fail{color:#f59e0b}
</style>
</head>
<body>
<div class="card">
  <div class="icon">🔌</div>
  <h1>无法连接到服务器</h1>
  <p class="desc">可能是网络异常或 SSL 证书需要重新信任</p>
  <div class="steps">
    <b>恢复步骤：</b><br>
    1. 点击下方「诊断连接」按钮<br>
    2. 如看到证书警告，选择「信任」<br>
    3. 返回这里点击「重新加载」
  </div>
  <a id="diagnoseBtn" class="btn btn-primary" target="_blank">诊断连接</a>
  <button class="btn btn-secondary" onclick="location.reload()">重新加载</button>
  <button class="btn btn-danger" onclick="clearAndReload()">清除缓存并重载</button>
  <div id="statusText" class="status">正在检测服务器状态...</div>
</div>
<script>
var healthUrl = location.origin + '/api/health';
document.getElementById('diagnoseBtn').href = healthUrl;

// 自动检测连接状态
function checkHealth() {
  var s = document.getElementById('statusText');
  fetch(healthUrl, {mode:'no-cors'}).then(function(){
    s.textContent = '✓ 服务器可达，请点击「重新加载」';
    s.className = 'status ok';
  }).catch(function(){
    s.textContent = '✗ 无法访问服务器，请先点击「诊断连接」';
    s.className = 'status fail';
  });
}
checkHealth();
setInterval(checkHealth, 5000);

// 清除 SW 缓存 + 注销 SW
function clearAndReload() {
  if ('caches' in window) {
    caches.keys().then(function(names) {
      return Promise.all(names.map(function(n){ return caches.delete(n) }));
    }).then(function(){
      if (navigator.serviceWorker) {
        navigator.serviceWorker.getRegistrations().then(function(regs) {
          regs.forEach(function(r){ r.unregister() });
          location.reload();
        });
      } else {
        location.reload();
      }
    });
  } else {
    location.reload();
  }
}
</script>
</body>
</html>`

// 安装事件：预缓存关键资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  )
})

// 激活事件：清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    }).then(() => self.clients.claim())
  )
})

// 拦截请求：网络优先策略（确保总是获取最新数据）
self.addEventListener('fetch', (event) => {
  // 只处理 GET 请求
  if (event.request.method !== 'GET') return

  const url = new URL(event.request.url)

  // 同域其它子应用直接放行，交给浏览器和各自反向代理处理
  if (
    url.origin === self.location.origin &&
    EXCLUDED_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))
  ) {
    return
  }

  // API 请求直接走网络，不缓存
  if (event.request.url.includes('/api/')) return

  // 导航请求（页面加载）：网络优先，失败时返回离线恢复页
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const responseClone = response.clone()
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone)
            })
          }
          return response
        })
        .catch(() => {
          // 先尝试缓存，再回退到内联离线页
          return caches.match(event.request).then((cached) => {
            if (cached) return cached
            return new Response(OFFLINE_FALLBACK_HTML, {
              status: 200,
              headers: { 'Content-Type': 'text/html; charset=utf-8' }
            })
          })
        })
    )
    return
  }

  // 其他静态资源：网络优先，缓存回退
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // 成功获取网络响应，缓存一份
        if (response.ok) {
          const responseClone = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone)
          })
        }
        return response
      })
      .catch(() => {
        // 网络失败，尝试从缓存返回
        return caches.match(event.request).then((cached) => cached || Response.error())
      })
  )
})
