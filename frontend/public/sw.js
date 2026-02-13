/**
 * 小金库 Golden Nest - Service Worker
 * 提供 PWA 安装能力和基本离线支持
 */

const CACHE_NAME = 'golden-nest-v1'

// 需要预缓存的关键资源
const PRECACHE_URLS = [
  '/',
]

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

  // API 请求直接走网络，不缓存
  if (event.request.url.includes('/api/')) return

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
        return caches.match(event.request)
      })
  )
})
