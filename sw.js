// U.E. Aldeana - service worker: cau offline + notificacions push (FCM).
// Puja el numero de CACHE cada cop que canvii l'app.
importScripts('https://www.gstatic.com/firebasejs/10.12.5/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.5/firebase-messaging-compat.js');
try {
  firebase.initializeApp({
    apiKey: 'AIzaSyC1kULqPKqRx6GkOdekDcpeNUttzw-O8so',
    projectId: 'uealdeana-929a8',
    messagingSenderId: '233333506339',
    appId: '1:233333506339:web:82d0dd792f4ae70d3f8c96'
  });
  firebase.messaging();   // mostra les notificacions rebudes en segon pla
} catch (e) {}

const CACHE = 'uea-v2';
const CORE = ['./', './index.html', './manifest.webmanifest'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.all(CORE.map(u => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // nomes gestionem GET del mateix domini; Firebase, Google Fonts, FCF... passen directes
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return res;
    }).catch(() => caches.match('./index.html')))
  );
});
