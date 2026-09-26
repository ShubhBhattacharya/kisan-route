// Kisan Route - Safe & Stable Service Worker
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  // Clear any corrupted or broken cache from previous attempts
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(keys.map((k) => caches.delete(k)));
    }).then(() => self.clients.claim())
  );
});

// Safe passthrough: let the browser network handle all requests directly
// This completely prevents Oppo/Realme/Vivo webview startup crashes
self.addEventListener('fetch', (event) => {
  return;
});
