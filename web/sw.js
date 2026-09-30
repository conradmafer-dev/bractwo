'use strict';
const CACHE_PREFIX = 'bractwo-app-shell-';
const CACHE_NAME = CACHE_PREFIX + '0.8.18-ui29';
const OFFLINE = '/offline.html';
const FALLBACK_ASSETS = [OFFLINE, '/icons/icon-192.png', '/icons/icon-512.png', '/icons/apple-touch-icon.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(FALLBACK_ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(names => Promise.all(names.filter(name => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME).map(name => caches.delete(name)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (request.mode === 'navigate') {
    // Do not cache HTML: reconnects must load the deployed game, never old code.
    event.respondWith(fetch(request).catch(async () => (await caches.open(CACHE_NAME)).match(OFFLINE)));
  } else if (FALLBACK_ASSETS.includes(url.pathname) && !url.search) {
    event.respondWith(caches.open(CACHE_NAME).then(async cache => (await cache.match(request)) || fetch(request)));
  }
  // Everything else, including API requests and gameplay assets, bypasses caches.
});
