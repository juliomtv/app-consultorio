/* ============================================================
   SERVICE WORKER — PWA Consultório
   Cache-first para assets estáticos, network-first para API
   ============================================================ */

const CACHE_NAME = 'consultorio-v1';
const STATIC_CACHE = 'consultorio-static-v1';

const STATIC_ASSETS = [
  '/static/css/main.css',
  '/static/css/patient.css',
  '/static/css/admin.css',
  '/static/js/app.js',
  '/static/js/patient.js',
  '/static/js/admin.js',
  '/static/js/contractions.js',
  '/static/manifest.json',
];

const NETWORK_FIRST = [
  '/api/',
  '/auth/',
];

const OFFLINE_PAGE = '/auth/login';

// ── INSTALL ─────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    }).then(() => self.skipWaiting())
  );
});

// ── ACTIVATE ─────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME && k !== STATIC_CACHE)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── FETCH ─────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorar requests não-GET e cross-origin
  if (request.method !== 'GET' || url.origin !== location.origin) return;

  // Network-first para API e rotas dinâmicas
  const isNetworkFirst = NETWORK_FIRST.some(p => url.pathname.startsWith(p));

  if (isNetworkFirst) {
    event.respondWith(networkFirst(request));
  } else if (url.pathname.startsWith('/static/')) {
    // Cache-first para assets estáticos
    event.respondWith(cacheFirst(request));
  } else {
    // Stale-while-revalidate para páginas HTML
    event.respondWith(staleWhileRevalidate(request));
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (_) {
    return new Response('Recurso não disponível offline.', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch (_) {
    const cached = await caches.match(request);
    return cached || new Response(JSON.stringify({ error: 'Offline' }), {
      headers: { 'Content-Type': 'application/json' },
      status: 503,
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request).then(response => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => null);

  return cached || await fetchPromise || new Response('Página offline.', { status: 503 });
}

// ── PUSH NOTIFICATIONS ────────────────────────────────────────
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};
  const options = {
    body: data.body || 'Você tem uma nova notificação.',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-72.png',
    vibrate: [100, 50, 100],
    data: { url: data.url || '/' },
    actions: [
      { action: 'view', title: 'Ver', icon: '/static/icons/icon-72.png' },
      { action: 'close', title: 'Fechar' },
    ],
  };
  event.waitUntil(
    self.registration.showNotification(data.title || 'Consultório', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'close') return;
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(clientList => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
